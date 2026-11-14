import re
from typing import List, Tuple, Dict, Set
from difflib import SequenceMatcher
from dataclasses import dataclass

@dataclass
class EntradaSumario:
    titulo: str
    numeracao: str = None
    pagina: int = None
    indice: int = 0

@dataclass
class TituloCorpo:
    titulo: str
    numeracao: str = None
    nivel: int = 0
    paragrafo: int = None
    estilo: str = None

class VerificadorSumario:
    """Verifica sumário contra títulos do documento"""

    def __init__(self, document_info: Dict):
        self.document_info = document_info
        self.paragraphs = document_info.get('paragraphs', [])

    def extrair_sumario(self, texto: str) -> Tuple[List[EntradaSumario], bool]:
        """Extrai entradas do sumário. Retorna (lista, é_campo_TOC)"""
        entradas = []
        eh_campo_toc = False

        # Encontrar seção de SUMÁRIO ou Índice
        padrao_titulo = r'(?:^|\n)\s*(?:SUMÁRIO|Índice|ÍNDICE)(?:\s|$)'
        match = re.search(padrao_titulo, texto, re.IGNORECASE | re.MULTILINE)

        if not match:
            return [], False

        inicio = match.end()
        # Encontrar próxima seção (INTRODUÇÃO, DESENVOLVIMENTO, etc)
        padrao_proxima = r'\n(?:INTRODUÇÃO|DESENVOLVIMENTO|METODOLOGIA|RESULTADOS|CONCLUSÃO|REFERÊNCIAS)'
        match_fim = re.search(padrao_proxima, texto[inicio:], re.IGNORECASE | re.MULTILINE)

        if match_fim:
            secao_sumario = texto[inicio:inicio + match_fim.start()]
        else:
            secao_sumario = texto[inicio:]

        # Verificar se é campo TOC (Microsoft Word)
        if 'TOC' in secao_sumario or '{ TOC' in secao_sumario:
            eh_campo_toc = True

        # Padrão para entradas do sumário
        # 1. Numeração. Título.........................página
        # 2. Título...............................página
        # 3. Título (sem número de página em sumário simples)

        padrao_entrada = r'^[\s]*([\d.]+\.?)?\s*([A-Z][A-Za-záéíóúàâãõç\s]+?)(?:\.*\s*(\d+))?\s*$'

        for idx, linha in enumerate(secao_sumario.split('\n')):
            if not linha.strip() or len(linha.strip()) < 3:
                continue

            match = re.match(padrao_entrada, linha.strip())
            if match:
                numeracao = match.group(1)
                titulo = match.group(2).strip()
                pagina = int(match.group(3)) if match.group(3) else None

                if titulo:
                    entrada = EntradaSumario(
                        titulo=titulo,
                        numeracao=numeracao,
                        pagina=pagina,
                        indice=idx
                    )
                    entradas.append(entrada)

        return entradas, eh_campo_toc

    def extrair_titulos_corpo(self) -> List[TituloCorpo]:
        """Extrai títulos do corpo do documento por estilo"""
        titulos = []

        # Estilos de título do Word
        estilos_titulo = ['Heading 1', 'Heading 2', 'Heading 3', 'Heading 4', 'Title', 'Subtitle']

        for para in self.paragraphs:
            estilo = para.get('style', '')

            # Verificar se é um estilo de título
            eh_titulo = any(titulo in estilo for titulo in estilos_titulo)

            if eh_titulo:
                texto = para['text'].strip()
                if texto:
                    # Extrair numeração se houver (ex: "1.2.3 Título")
                    padrao_num = r'^([\d.]+\.?)\s+(.+)$'
                    match = re.match(padrao_num, texto)

                    if match:
                        numeracao = match.group(1)
                        titulo = match.group(2)
                    else:
                        numeracao = None
                        titulo = texto

                    titulo_corpo = TituloCorpo(
                        titulo=titulo,
                        numeracao=numeracao,
                        paragrafo=para['index'] + 1,
                        estilo=estilo,
                        nivel=len(estilo.replace('Heading', '').strip())
                    )
                    titulos.append(titulo_corpo)

        return titulos

    def normalizar_texto(self, texto: str) -> str:
        """Normaliza texto para comparação"""
        texto = texto.lower()
        texto = re.sub(r'[áàâã]', 'a', texto)
        texto = re.sub(r'[éè]', 'e', texto)
        texto = re.sub(r'[í]', 'i', texto)
        texto = re.sub(r'[óõô]', 'o', texto)
        texto = re.sub(r'[ú]', 'u', texto)
        texto = re.sub(r'[ç]', 'c', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    def similaridade(self, texto1: str, texto2: str) -> float:
        """Calcula similaridade entre textos"""
        norm1 = self.normalizar_texto(texto1)
        norm2 = self.normalizar_texto(texto2)
        return SequenceMatcher(None, norm1, norm2).ratio()

    def verificar(self, texto: str) -> List[Dict]:
        """Retorna lista de problemas encontrados"""
        problemas = []

        # Extrair sumário
        entradas_sumario, eh_campo_toc = self.extrair_sumario(texto)

        if not entradas_sumario:
            return [{
                'id': 'sumario.nao_encontrado',
                'titulo': 'Sumário não encontrado',
                'descricao': 'Nenhuma seção de SUMÁRIO ou Índice foi encontrada no documento.',
                'severity': 'error',
                'categoria': 'Sumário'
            }]

        # Extrair títulos do corpo
        titulos_corpo = self.extrair_titulos_corpo()

        if not titulos_corpo:
            return [{
                'id': 'titulos.sem_estilo',
                'titulo': 'Títulos sem estilo de título',
                'descricao': 'Títulos não estão marcados com estilo de título. Não foi possível comparar com o sumário.',
                'severity': 'warning',
                'categoria': 'Sumário'
            }]

        # Comparar entradas com títulos
        titulos_encontrados = set()

        for entrada in entradas_sumario:
            # Procurar título correspondente
            melhor_match = None
            melhor_score = 0

            for titulo in titulos_corpo:
                score = self.similaridade(entrada.titulo, titulo.titulo)
                if score > melhor_score:
                    melhor_score = score
                    melhor_match = titulo

            if melhor_score > 0.9 and melhor_match:
                titulos_encontrados.add(id(melhor_match))

                # Verificar numeração
                if entrada.numeracao and melhor_match.numeracao:
                    if entrada.numeracao.rstrip('.') != melhor_match.numeracao.rstrip('.'):
                        problema = {
                            'id': 'sumario.numeracao',
                            'titulo': 'Numeração diferente',
                            'descricao': f'No sumário: {entrada.numeracao}. No corpo: {melhor_match.numeracao}.',
                            'severity': 'error',
                            'categoria': 'Sumário'
                        }
                        problemas.append(problema)
            else:
                # Entrada do sumário sem título correspondente
                problema = {
                    'id': 'sumario.entrada_orfa',
                    'titulo': 'Entrada do sumário sem título no corpo',
                    'descricao': f'{entrada.titulo} está no sumário, mas não há título correspondente.',
                    'severity': 'error',
                    'categoria': 'Sumário'
                }
                problemas.append(problema)

        # Verificar títulos não listados no sumário
        for titulo in titulos_corpo:
            if id(titulo) not in titulos_encontrados:
                problema = {
                    'id': 'sumario.titulo_ausente',
                    'titulo': 'Título no corpo sem entrada no sumário',
                    'descricao': f'{titulo.titulo} aparece no texto, mas não está no sumário.',
                    'severity': 'error',
                    'categoria': 'Sumário'
                }
                problemas.append(problema)

        # Verificar ordem
        titulos_ordenados = [t.titulo for t in titulos_corpo if any(s == id(t) for s in titulos_encontrados)]
        sumario_ordenado = [e.titulo for e in entradas_sumario]

        if self._verificar_ordem_diferente(sumario_ordenado, titulos_ordenados):
            problema = {
                'id': 'sumario.ordem',
                'titulo': 'Ordem diferente',
                'descricao': 'A ordem dos títulos no sumário é diferente da ordem no corpo.',
                'severity': 'warning',
                'categoria': 'Sumário'
            }
            problemas.append(problema)

        # Verificar se é campo TOC desatualizado
        if eh_campo_toc:
            problema = {
                'id': 'sumario.campo_desatualizado',
                'titulo': 'Sumário automático pode estar desatualizado',
                'descricao': 'Clique com o botão direito no sumário e escolha Atualizar campo.',
                'severity': 'warning',
                'categoria': 'Sumário'
            }
            problemas.append(problema)

        return problemas

    def _verificar_ordem_diferente(self, lista1: List[str], lista2: List[str]) -> bool:
        """Verifica se duas listas têm ordem diferente"""
        if len(lista1) != len(lista2):
            return False

        # Comparar índices dos elementos
        indices_lista1 = {texto: idx for idx, texto in enumerate(lista1)}
        for idx, texto in enumerate(lista2):
            if texto in indices_lista1 and indices_lista1[texto] != idx:
                return True

        return False
