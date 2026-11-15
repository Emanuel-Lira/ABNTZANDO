from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from docx.shared import Length

from analise_estrutura import analisar_estrutura, eh_titulo, lista_pt, loc_paragrafos, normaliza, zonas_por_paragrafo, capitulos_por_paragrafo, LOCAIS_ATUAIS

from .output_formatter import formatar_valor
from .reader import DocumentReader

SEVERIDADE = {'erro': 'error', 'aviso': 'warning'}
# Recuo de primeira linha está fora do escopo enxuto do spec. Para reativar,
# mude para True (no futuro, pelo perfil de norma).
VERIFICAR_RECUO = True
ZONAS_IGNORADAS = {'capa', 'sumario', 'pre_textual'}
FONTES_ACEITAS = ['Times New Roman', 'Arial']
TITULOS_REFERENCIAS = {'referencias', 'referencias bibliograficas'}
CATEGORIAS = ['Margens', 'Fonte', 'Espaçamento', 'Alinhamento', 'Referências', 'Organização', 'Recuo']

REGRAS_FORMATACAO = {
    'fonte.familia': ('Fonte', 'Fonte fora de Times New Roman ou Arial', 'Times New Roman ou Arial'),
    'fonte.tamanho_texto': ('Fonte', 'Tamanho de fonte fora de 12 pt no texto', '12 pt'),
    'fonte.tamanho_apoio': ('Fonte', 'Tamanho de fonte fora de 10 pt na legenda', '10 pt'),
    'fonte.tamanho_fonte': ('Fonte', 'Tamanho da linha "Fonte:" fora de 10 ou 12 pt', '10 ou 12 pt'),
    'espaco.texto': ('Espaçamento', 'Entrelinhas fora de 1,5 no texto', '1,5'),
    'espaco.referencias': ('Espaçamento', 'Entrelinhas fora de 1,0 nas referências', '1,0'),
    'recuo.primeira_linha': ('Recuo', 'Recuo de primeira linha fora de 1,25 cm', '1,25 cm'),
    'alinhamento.justificado': ('Alinhamento', 'Texto do corpo sem alinhamento justificado', 'Justificado'),
}
# Severidade e correção automática de cada regra de formatação
REGRAS_FORMATACAO_META = {
    'fonte.familia': {'severidade': 'erro', 'corrigivel': True},
    'fonte.tamanho_texto': {'severidade': 'erro', 'corrigivel': True},
    'fonte.tamanho_apoio': {'severidade': 'erro', 'corrigivel': True},
    'fonte.tamanho_fonte': {'severidade': 'erro', 'corrigivel': True},
    'espaco.texto': {'severidade': 'erro', 'corrigivel': True},
    'espaco.referencias': {'severidade': 'erro', 'corrigivel': True},
    'recuo.primeira_linha': {'severidade': 'aviso', 'corrigivel': True},
    'alinhamento.justificado': {'severidade': 'aviso', 'corrigivel': True},
}
ALINHAMENTO_TEXTO = {'left': 'à esquerda', 'center': 'centralizado', 'right': 'à direita'}
UNIDADE_FORMATACAO = {
    'fonte.tamanho_texto': 'pt',
    'fonte.tamanho_apoio': 'pt',
    'fonte.tamanho_fonte': 'pt',
    'recuo.primeira_linha': 'cm',
}


@dataclass
class Issue:
    id: str
    categoria: str
    title: str
    severity: str  # 'error' ou 'warning'
    location: str
    fixable: bool
    esperado: str = ''
    encontrado: str = ''
    norma: str = 'NBR 14724'
    fix_type: Optional[str] = None
    text_preview: Optional[str] = None
    paragrafos: List[int] = field(default_factory=list)
    trechos: List[Dict[str, Any]] = field(default_factory=list)
    valores: Dict[int, str] = field(default_factory=dict)  # valor encontrado em cada parágrafo

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'categoria': self.categoria,
            'severidade': 'erro' if self.severity == 'error' else 'aviso',
            'titulo': self.title,
            'localizacao': self.location,
            'esperado': self.esperado,
            'encontrado': self.encontrado,
            'norma': self.norma,
            'corrigivel': self.fixable,
            # campos lidos pela interface atual
            'title': self.title,
            'severity': self.severity,
            'location': self.location,
            'fixable': self.fixable,
            'text_preview': self.text_preview,
            'trechos': self.trechos,
        }


def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, (bool, Length))


def _igual(valor, alvo: float, tolerancia: float = 0.05) -> bool:
    return _numero(valor) and abs(valor - alvo) <= tolerancia


def _formatar(id_: str, valor) -> str:
    if id_ == 'fonte.familia':
        return str(valor)
    if id_ == 'alinhamento.justificado':
        return ALINHAMENTO_TEXTO.get(valor, 'sem alinhamento definido')
    if not _numero(valor):
        return 'valor exato'
    return formatar_valor(valor, UNIDADE_FORMATACAO.get(id_, ''))


MARGENS_ESPERADAS = {'top': 3.0, 'left': 3.0, 'bottom': 2.0, 'right': 2.0}


CAMPOS_MARGEM = [('superior', 'top'), ('esquerda', 'left'), ('inferior', 'bottom'), ('direita', 'right')]


def _texto_secoes(numeros: List[int]) -> str:
    """'Seção 1', 'Seções 1 a 8' (consecutivas) ou 'Seções 2, 5 e 7'."""
    if len(numeros) == 1:
        return f'Seção {numeros[0]}'
    if numeros == list(range(numeros[0], numeros[0] + len(numeros))):
        return f'Seções {numeros[0]} a {numeros[-1]}'
    return f'Seções {lista_pt(numeros)}'


def _de_estrutura(item: Dict[str, Any]) -> Issue:
    return Issue(
        id=item['id'],
        categoria=item['categoria'],
        title=item['titulo'],
        severity=SEVERIDADE[item['severidade']],
        location=item['localizacao'],
        fixable=item['corrigivel'],
        esperado=item['esperado'],
        encontrado=item['encontrado'],
        norma=item['norma'],
        paragrafos=list(item.get('paragrafos', [])),
    )


class ABNTRules:
    """Verifica margens, formatação por zona e estrutura do trabalho (NBR 14724)"""

    def __init__(self, document_info: Dict[str, Any], zonas: Dict[int, str],
                 titulos: Set[int], estrutura: List[Dict[str, Any]]):
        self.document_info = document_info
        self.zonas = zonas
        self.titulos = titulos
        self.estrutura = estrutura
        self.issues: List[Issue] = []

    def check_all(self) -> List[Issue]:
        self.issues = []
        self.check_margins()
        self.check_formatacao()
        self.issues += [_de_estrutura(item) for item in self.estrutura]
        return self.issues

    def check_margins(self):
        secoes = self.document_info.get('secoes_margens', [])
        if not secoes:
            self.issues.append(Issue(
                id='pag.margens',
                categoria='Margens',
                title='Margens não detectadas',
                severity='warning',
                location='Documento inteiro',
                fixable=False,
            ))
            return

        erradas = [
            (n, m) for n, m in enumerate(secoes, start=1)
            if any(abs(m[lado] - valor) > 0.1 for lado, valor in MARGENS_ESPERADAS.items())
        ]
        if not erradas:
            return

        numeros = [n for n, _ in erradas]
        localizacao = _texto_secoes(numeros)
        esperado = [
            {'campo': campo, 'valor': MARGENS_ESPERADAS[lado]}
            for campo, lado in CAMPOS_MARGEM
        ]
        encontrado = [
            {'secao': n, **{campo: round(m[lado], 2) for campo, lado in CAMPOS_MARGEM}}
            for n, m in erradas
        ]
        self.issues.append(Issue(
            id='pag.margens',
            categoria='Margens',
            title='Margens fora do padrão ABNT',
            severity='error',
            location=localizacao,
            fixable=True,
            esperado=esperado,
            encontrado=encontrado,
            fix_type='margin',
        ))

    def check_formatacao(self):
        falhas: Dict[str, list] = {}

        def falha(id_: str, n: int, valor):
            falhas.setdefault(id_, []).append((n, valor))

        for para in self.document_info.get('paragraphs', []):
            texto = para['text'].strip()
            n = para['index'] + 1
            zona = self.zonas.get(n)
            if not texto or zona is None or zona in ZONAS_IGNORADAS:
                continue

            nome = para['font_info'].get('font_name')
            tamanho = para['font_info'].get('font_size')
            entrelinhas = para['spacing']['line_spacing']
            recuo = para['indentation']['first_line']
            e_titulo = n in self.titulos
            e_linha_fonte = texto.lower().startswith('fonte:')

            if zona in ('corpo', 'referencias', 'legenda') and nome is not None and nome not in FONTES_ACEITAS:
                falha('fonte.familia', n, nome)

            if zona in ('corpo', 'referencias') and tamanho is not None and not _igual(tamanho, 12.0):
                falha('fonte.tamanho_texto', n, tamanho)
            elif zona == 'legenda' and tamanho is not None:
                if e_linha_fonte:
                    if not (_igual(tamanho, 10.0) or _igual(tamanho, 12.0)):
                        falha('fonte.tamanho_fonte', n, tamanho)
                elif not _igual(tamanho, 10.0):
                    falha('fonte.tamanho_apoio', n, tamanho)

            if zona == 'corpo' and not _igual(entrelinhas, 1.5):
                falha('espaco.texto', n, entrelinhas)
            if zona == 'referencias' and normaliza(texto) not in TITULOS_REFERENCIAS \
                    and not _igual(entrelinhas, 1.0):
                falha('espaco.referencias', n, entrelinhas)

            if VERIFICAR_RECUO and zona == 'corpo' and not e_titulo and len(texto) >= 10 \
                    and not _igual(recuo, 1.25, tolerancia=0.1):
                falha('recuo.primeira_linha', n, recuo)

            if zona == 'corpo' and not e_titulo and para['alignment_efetivo'] != 'both':
                falha('alinhamento.justificado', n, para['alignment_efetivo'])

        for id_, ocorrencias in falhas.items():
            categoria, titulo, esperado = REGRAS_FORMATACAO[id_]
            paragrafos = [n for n, _ in ocorrencias]
            valores_por_paragrafo = {n: _formatar(id_, v) for n, v in ocorrencias}
            n_lugares = len(paragrafos)
            encontrado = f"em {n_lugares} lugar" + ('es' if n_lugares > 1 else '')
            self.issues.append(Issue(
                id=id_,
                categoria=categoria,
                title=titulo,
                severity='warning' if REGRAS_FORMATACAO_META[id_]['severidade'] == 'aviso' else 'error',
                location=loc_paragrafos(paragrafos),
                fixable=REGRAS_FORMATACAO_META[id_]['corrigivel'],
                esperado=esperado,
                encontrado=encontrado,
                fix_type=id_.split('.')[0],
                paragrafos=paragrafos,
                valores=valores_por_paragrafo,
            ))


def analisar(file_bytes: bytes) -> List[Issue]:
    reader = DocumentReader(file_bytes)
    # Capítulo de cada parágrafo vale para toda a análise: estrutura, regras e trechos
    locais = capitulos_por_paragrafo(reader.doc)
    token = LOCAIS_ATUAIS.set(locais)
    try:
        info = reader.get_document_info()
        zonas = zonas_por_paragrafo(reader.doc)
        estrutura = analisar_estrutura(reader.doc)
        titulos = {
            i + 1 for i, p in enumerate(reader.doc.paragraphs)
            if eh_titulo({'tipo': 'p', 'texto': p.text.strip(), 'obj': p})
        }
        textos = {i + 1: p.text.strip() for i, p in enumerate(reader.doc.paragraphs)}
        issues = ABNTRules(info, zonas, titulos, estrutura).check_all()
    finally:
        LOCAIS_ATUAIS.reset(token)
    for issue in issues:
        issue.trechos = [
            {'paragrafo': n, 'capitulo': locais.get(n), 'texto': _trecho(textos[n]),
             'valor': issue.valores.get(n)}
            for n in issue.paragrafos if textos.get(n)
        ]
    return sorted(issues, key=_chave_ordenacao)


TAMANHO_TRECHO = 80


def _trecho(texto: str) -> str:
    texto = ' '.join(texto.split())
    if len(texto) <= TAMANHO_TRECHO:
        return texto
    return texto[:TAMANHO_TRECHO - 1].rstrip() + '…'


def _chave_ordenacao(issue: Issue):
    ordem = CATEGORIAS.index(issue.categoria) if issue.categoria in CATEGORIAS else len(CATEGORIAS)
    return (ordem, 0 if issue.severity == 'error' else 1)
