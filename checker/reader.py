"""Leitura de um .docx: parágrafos, margens, estilos e fontes.

Os valores numéricos de w:spacing, w:ind, w:sz e w:pgMar são lidos do XML bruto
e passados por safe_int, que aceita decimais (709.5 vira 710) e nunca lança
ValueError por causa de um atributo malformado.
"""
from docx import Document
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from typing import Any, Dict, List, Optional
from io import BytesIO
import logging

logger = logging.getLogger(__name__)
TWIPS_POR_CM = 567.0
TWIPS_POR_PT = 20.0
_avisados: set = set()  # um aviso por nome de atributo


def _avisar(atributo: str, mensagem: str) -> None:
    chave = atributo or '?'
    if chave not in _avisados:
        _avisados.add(chave)
        logger.warning("Atributo %s: %s", chave, mensagem)


def safe_int(value, default=None, atributo: str = ''):
    """Lê um atributo numérico do XML do Word.

    Aceita inteiros e decimais ('709.5' vira int(round(709.5)) = 710). Vazio, ausente
    ou não numérico devolve `default`. Registra um aviso por nome de atributo, uma vez.
    """
    if value is None:
        return default
    texto = str(value).strip()
    if not texto:
        return default
    try:
        return int(texto)
    except ValueError:
        pass
    try:
        numero = int(round(float(texto)))
    except (ValueError, OverflowError):
        _avisar(atributo, f'valor não numérico {texto!r}; usando o padrão')
        return default
    _avisar(atributo, f'valor decimal {texto!r} arredondado para {numero}')
    return numero


def _valor(elemento, tag: str, atributo: str, rotulo: str):
    """Número de w:<tag>/@w:<atributo> dentro de elemento, ou None se ausente."""
    if elemento is None:
        return None
    filho = elemento.find(qn(tag))
    if filho is None:
        return None
    return safe_int(filho.get(qn(atributo)), atributo=rotulo)


def _cm(twips) -> float:
    return twips / TWIPS_POR_CM if twips is not None else 0.0


class DocumentReader:
    def __init__(self, file_path_or_bytes):
        if isinstance(file_path_or_bytes, bytes):
            self.doc = Document(BytesIO(file_path_or_bytes))
        else:
            self.doc = Document(file_path_or_bytes)
        self._avisou_estilo_normal = False

    def _estilo_normal(self):
        """Estilo 'Normal' pelo nome. Sem ele (arquivo regravado por outro app), devolve None e avisa uma vez."""
        for estilo in self.doc.styles:
            if estilo.name == 'Normal':
                return estilo
        if not self._avisou_estilo_normal:
            logger.warning("Estilo 'Normal' ausente no documento; usando os valores padrão do Word (docDefaults).")
            self._avisou_estilo_normal = True
        return None

    def _defaults(self, tipo: str):
        """w:pPr ou w:rPr dentro de docDefaults, ou None."""
        raiz = self.doc.styles.element.find(qn('w:docDefaults'))
        if raiz is None:
            return None
        grupo = raiz.find(qn('w:pPrDefault' if tipo == 'pPr' else 'w:rPrDefault'))
        return grupo.find(qn(f'w:{tipo}')) if grupo is not None else None

    def _cadeia_paragrafo(self, paragraph) -> List[Any]:
        """w:pPr em ordem de precedência: parágrafo, estilo e base, Normal, docDefaults."""
        cadeia = []
        if paragraph._p.pPr is not None:
            cadeia.append(paragraph._p.pPr)
        estilo = paragraph.style
        while estilo is not None:
            el = estilo.element.find(qn('w:pPr'))
            if el is not None:
                cadeia.append(el)
            estilo = estilo.base_style
        normal = self._estilo_normal()
        if normal is not None and normal.element.find(qn('w:pPr')) is not None:
            cadeia.append(normal.element.find(qn('w:pPr')))
        padrao = self._defaults('pPr')
        if padrao is not None:
            cadeia.append(padrao)
        return cadeia

    def _cadeia_run(self, paragraph, run) -> List[Any]:
        """w:rPr em ordem de precedência: run, estilo e base, Normal, docDefaults."""
        cadeia = []
        if run is not None and run._r.rPr is not None:
            cadeia.append(run._r.rPr)
        estilo = paragraph.style
        while estilo is not None:
            el = estilo.element.find(qn('w:rPr'))
            if el is not None:
                cadeia.append(el)
            estilo = estilo.base_style
        normal = self._estilo_normal()
        if normal is not None and normal.element.find(qn('w:rPr')) is not None:
            cadeia.append(normal.element.find(qn('w:rPr')))
        padrao = self._defaults('rPr')
        if padrao is not None:
            cadeia.append(padrao)
        return cadeia

    def get_document_info(self) -> Dict[str, Any]:
        """Extrai informações gerais do documento"""
        info = {
            'page_count': len(self.doc.paragraphs),
            'secoes_margens': self.get_margens_por_secao(),
            'paragraphs': self.get_paragraphs_info(),
            'styles': self.get_styles_info(),
        }
        return info

    def get_margens_por_secao(self) -> List[Dict[str, float]]:
        """Margens de cada seção do documento, em cm (lidas de w:pgMar)"""
        resultado = []
        for secao in self.doc.sections:
            pgmar = secao._sectPr.find(qn('w:pgMar'))
            linha = {}
            for lado in ('top', 'bottom', 'left', 'right'):
                bruto = pgmar.get(qn(f'w:{lado}')) if pgmar is not None else None
                linha[lado] = _cm(safe_int(bruto, atributo=f'w:pgMar/@w:{lado}'))
            resultado.append(linha)
        return resultado

    def get_paragraphs_info(self) -> List[Dict[str, Any]]:
        """Extrai informações de cada parágrafo"""
        paragraphs_info = []

        for idx, para in enumerate(self.doc.paragraphs):
            if not para.text.strip():
                continue

            ppr = para._p.pPr
            para_info = {
                'index': idx,
                'text': para.text,
                'style': para.style.name if para.style else None,
                'alignment': str(para.alignment),
                'alignment_efetivo': self._get_effective_alignment(para),
                'font_info': self.get_paragraph_font_info(para),
                'spacing': self._get_effective_spacing(para),
                'indentation': {
                    'first_line': self._get_effective_first_line(para),
                    'left': _cm(_valor(ppr, 'w:ind', 'w:left', 'w:ind/@w:left')),
                    'right': _cm(_valor(ppr, 'w:ind', 'w:right', 'w:ind/@w:right')),
                }
            }
            paragraphs_info.append(para_info)

        return paragraphs_info

    def _get_effective_alignment(self, paragraph) -> Optional[str]:
        """Alinhamento efetivo: parágrafo > estilo e estilos base > docDefaults.

        Devolve 'both' (justificado), 'left', 'center', 'right' ou None (sem definição).
        O alinhamento não existe no nível de run no Word, então não é consultado.
        """
        mapa = {
            WD_ALIGN_PARAGRAPH.JUSTIFY: 'both',
            WD_ALIGN_PARAGRAPH.LEFT: 'left',
            WD_ALIGN_PARAGRAPH.CENTER: 'center',
            WD_ALIGN_PARAGRAPH.RIGHT: 'right',
        }
        valor = paragraph.paragraph_format.alignment
        if valor is not None:
            return mapa.get(valor, str(valor))
        estilo = paragraph.style
        while estilo is not None:
            valor = estilo.paragraph_format.alignment
            if valor is not None:
                return mapa.get(valor, str(valor))
            estilo = estilo.base_style
        padrao = self.doc.styles.element.xpath('./w:docDefaults/w:pPrDefault/w:pPr/w:jc/@w:val')
        return padrao[0] if padrao else None

    def _get_effective_first_line(self, paragraph) -> float:
        """Recuo de primeira linha em cm (w:ind/@w:firstLine, ou -w:hanging), seguindo a cadeia de estilos"""
        for el in self._cadeia_paragrafo(paragraph):
            ind = el.find(qn('w:ind'))
            if ind is None:
                continue
            primeira = safe_int(ind.get(qn('w:firstLine')), atributo='w:ind/@w:firstLine')
            if primeira is not None:
                return _cm(primeira)
            suspensao = safe_int(ind.get(qn('w:hanging')), atributo='w:ind/@w:hanging')
            if suspensao is not None:
                return _cm(-suspensao)
        return 0.0

    def _entrelinhas(self, paragraph) -> Optional[float]:
        """Entrelinhas efetivas: múltiplo (lineRule auto) ou pontos (exact/atLeast)."""
        for el in self._cadeia_paragrafo(paragraph):
            sp = el.find(qn('w:spacing'))
            if sp is None:
                continue
            linha = safe_int(sp.get(qn('w:line')), atributo='w:spacing/@w:line')
            if linha is None:
                continue
            regra = sp.get(qn('w:lineRule'), 'auto')
            return linha / 240.0 if regra == 'auto' else linha / TWIPS_POR_PT
        return None

    def _get_effective_spacing(self, paragraph) -> Dict[str, Any]:
        """Extrai valor efetivo de espaçamento (entrelinhas e espaço entre parágrafos)"""
        ppr = paragraph._p.pPr
        antes = _valor(ppr, 'w:spacing', 'w:before', 'w:spacing/@w:before')
        depois = _valor(ppr, 'w:spacing', 'w:after', 'w:spacing/@w:after')

        line_spacing = self._entrelinhas(paragraph)
        if not line_spacing:
            line_spacing = 1.5  # padrão quando nada define a entrelinha

        return {
            'line_spacing': line_spacing,
            'space_before': antes / TWIPS_POR_PT if antes is not None else 0,
            'space_after': depois / TWIPS_POR_PT if depois is not None else 0,
        }

    def get_paragraph_font_info(self, paragraph) -> Dict[str, Any]:
        """Fonte e tamanho efetivos: run com texto > estilo do parágrafo > estilos base > docDefaults"""
        run = next((r for r in paragraph.runs if r.text.strip()), None)
        nome = run.font.name if run is not None else None
        tamanho = self._tamanho_pt(paragraph, run)

        if nome is None:
            nome = self._nome_na_cadeia(paragraph.style)

        return {
            'font_name': nome,
            'font_size': tamanho,
            'bold': None,
            'italic': None,
        }

    def _tamanho_pt(self, paragraph, run) -> Optional[float]:
        """Tamanho efetivo em pontos, de w:sz (meios pontos)."""
        for el in self._cadeia_run(paragraph, run):
            meios = _valor(el, 'w:sz', 'w:val', 'w:sz/@w:val')
            if meios is not None:
                return meios / 2
        return None

    def _nome_na_cadeia(self, estilo) -> Any:
        atual = estilo
        while atual is not None:
            if atual.font.name:
                return atual.font.name
            atual = atual.base_style
        valores = self.doc.styles.element.xpath('./w:docDefaults/w:rPrDefault/w:rPr/w:rFonts/@w:ascii')
        return valores[0] if valores else None

    def get_styles_info(self) -> Dict[str, Any]:
        """Extrai informações dos estilos do documento"""
        styles_info = {
            'total_styles': len(self.doc.styles),
            'used_fonts': set(),
            'used_sizes': set(),
        }

        for para in self.doc.paragraphs:
            for run in para.runs:
                if run.font.name:
                    styles_info['used_fonts'].add(run.font.name)
                meios = _valor(run._r.rPr, 'w:sz', 'w:val', 'w:sz/@w:val')
                if meios:
                    styles_info['used_sizes'].add(meios / 2)

        styles_info['used_fonts'] = list(styles_info['used_fonts'])
        styles_info['used_sizes'] = list(styles_info['used_sizes'])

        return styles_info
