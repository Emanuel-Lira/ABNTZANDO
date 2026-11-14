import re
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass

@dataclass
class Citacao:
    autor: str
    ano: str
    pagina: str = None
    paragrafo: int = None
    texto_completo: str = None

@dataclass
class Referencia:
    autor: str
    ano: str
    texto_completo: str = None

class VerificadorCitacoes:
    """Verifica citações cruzadas entre texto e referências"""

    # Padrões de citação
    PADROES_CITACAO = [
        # (SILVA, 2020), (SILVA; SOUZA, 2019), (SILVA et al., 2018), (SILVA, 2020, p. 45)
        r'\(([A-Z\s]+(?:;[A-Z\s]+)*(?:\s+et\s+al\.)?),\s*(\d{4}[a-z]?)(?:,\s*p\.?\s*\d+)?\)',
        # Silva (2020) afirma...
        r'([A-Z][a-z]+)\s*\((\d{4}[a-z]?)\)',
        # (IBGE, 2020) - entidade institucional
        r'\(([A-Z0-9\s\-]+),\s*(\d{4}[a-z]?)\)',
    ]

    def extrair_citacoes(self, texto: str) -> Dict[str, List[Citacao]]:
        """Extrai todas as citações do texto"""
        citacoes = {}

        # Dividir em parágrafos
        paragrafos = texto.split('\n\n')

        for idx, paragrafo in enumerate(paragrafos, 1):
            # Pular se está na seção de referências
            if self._esta_em_referencias(paragrafo):
                continue

            for padrao in self.PADROES_CITACAO:
                matches = re.finditer(padrao, paragrafo)
                for match in matches:
                    autor = match.group(1).strip().upper()
                    ano = match.group(2).strip()

                    # Normalizar autor
                    autor_normalizado = self._normalizar_autor(autor)
                    chave = f"{autor_normalizado},{ano}"

                    if chave not in citacoes:
                        citacoes[chave] = []

                    citacao = Citacao(
                        autor=autor_normalizado,
                        ano=ano,
                        paragrafo=idx,
                        texto_completo=match.group(0)
                    )
                    citacoes[chave].append(citacao)

        return citacoes

    def extrair_referencias(self, texto: str) -> Dict[str, Referencia]:
        """Extrai referências da seção de REFERÊNCIAS"""
        referencias = {}

        # Encontrar seção de REFERÊNCIAS
        match = re.search(r'(?:^|\n)\s*(?:REFERÊNCIAS|Referências)(?:\s|$)', texto, re.IGNORECASE | re.MULTILINE)
        if not match:
            return referencias

        inicio = match.end()
        secao_ref = texto[inicio:]

        # Padrão: SOBRENOME, Nome. Título. Ano.
        padrao_ref = r'^([A-Z\s]+),\s+[^.]+\.\s+[^.]*?(\d{4}[a-z]?)\.'

        for linha in secao_ref.split('\n'):
            if not linha.strip():
                continue

            match = re.match(padrao_ref, linha)
            if match:
                autor = match.group(1).strip().upper()
                ano = match.group(2).strip()

                autor_normalizado = self._normalizar_autor(autor)
                chave = f"{autor_normalizado},{ano}"

                referencias[chave] = Referencia(
                    autor=autor_normalizado,
                    ano=ano,
                    texto_completo=linha.strip()
                )

        return referencias

    def _normalizar_autor(self, autor: str) -> str:
        """Normaliza o autor para comparação"""
        # Pega o primeiro sobrenome (antes de ; ou "et al")
        primeiro = autor.split(';')[0].split('et')[0].strip().upper()
        return primeiro

    def _esta_em_referencias(self, paragrafo: str) -> bool:
        """Verifica se o parágrafo está após a seção de REFERÊNCIAS"""
        # Simplificado: considera tudo após "REFERÊNCIAS" como parte da seção
        return 'REFERÊNCIAS' in paragrafo.upper()

    def verificar(self, texto: str) -> List[Dict]:
        """Retorna lista de problemas encontrados"""
        problemas = []

        citacoes = self.extrair_citacoes(texto)
        referencias = self.extrair_referencias(texto)

        if not referencias:
            return [{
                'id': 'citacao.sem_secao_referencias',
                'titulo': 'Seção de referências não encontrada',
                'descricao': 'Nenhuma seção de REFERÊNCIAS foi encontrada no documento.',
                'severity': 'error',
                'categoria': 'Citações'
            }]

        # Verificar citações sem referência
        for chave_citacao, lista_citacoes in citacoes.items():
            if chave_citacao not in referencias:
                problema = {
                    'id': 'citacao.sem_referencia',
                    'titulo': 'Citação sem referência',
                    'descricao': f'{lista_citacoes[0].texto_completo} citada não aparece na lista de referências.',
                    'severity': 'error',
                    'categoria': 'Citações',
                    'paragrafos': [c.paragrafo for c in lista_citacoes]
                }
                problemas.append(problema)

        # Verificar referências sem citação
        for chave_ref, ref in referencias.items():
            if chave_ref not in citacoes:
                problema = {
                    'id': 'referencia.sem_citacao',
                    'titulo': 'Referência não citada',
                    'descricao': f'{ref.texto_completo[:60]}... está na lista, mas não foi citada no texto.',
                    'severity': 'warning',
                    'categoria': 'Referências'
                }
                problemas.append(problema)

        # Verificar sufixos a/b ambíguos
        problemas.extend(self._verificar_sufixos_ambiguos(citacoes, referencias))

        return problemas

    def _verificar_sufixos_ambiguos(self, citacoes: Dict, referencias: Dict) -> List[Dict]:
        """Verifica se há sufixos a/b ambíguos"""
        problemas = []

        # Agrupar por autor+ano sem sufixo
        citacoes_sem_sufixo = {}
        for chave in citacoes.keys():
            autor, ano = chave.split(',')
            chave_base = f"{autor},{ano[0:4]}"
            if chave_base not in citacoes_sem_sufixo:
                citacoes_sem_sufixo[chave_base] = []
            citacoes_sem_sufixo[chave_base].append(chave)

        # Agrupar referências similarmente
        refs_sem_sufixo = {}
        for chave in referencias.keys():
            autor, ano = chave.split(',')
            chave_base = f"{autor},{ano[0:4]}"
            if chave_base not in refs_sem_sufixo:
                refs_sem_sufixo[chave_base] = []
            refs_sem_sufixo[chave_base].append(chave)

        # Detectar ambiguidade
        for chave_base in citacoes_sem_sufixo.keys():
            citacoes_grupo = citacoes_sem_sufixo.get(chave_base, [])
            refs_grupo = refs_sem_sufixo.get(chave_base, [])

            # Se há múltiplas referências mas citação sem sufixo
            if len(refs_grupo) > 1 and any(len(c.split(',')[1]) == 4 for c in citacoes_grupo):
                problema = {
                    'id': 'citacao.ano_ambiguo',
                    'titulo': 'Mesmo autor e ano sem sufixo',
                    'descricao': f'Mesmo autor e ano devem usar sufixos a, b tanto na lista quanto no texto.',
                    'severity': 'warning',
                    'categoria': 'Citações'
                }
                problemas.append(problema)

        return problemas
