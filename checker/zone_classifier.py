import re
from typing import Dict, List, Any

class ZoneClassifier:
    """Classifica parágrafos em zonas do documento"""

    def __init__(self, paragraphs: List[Dict[str, Any]]):
        self.paragraphs = paragraphs
        self.zones: Dict[int, str] = {}
        self._classify()

    def _classify(self):
        """Classifica todos os parágrafos em zonas"""

        # Encontrar limites importantes
        first_title_idx = self._find_first_title()
        references_idx = self._find_references_section()
        toc_idx = self._find_table_of_contents()

        for idx, para in enumerate(self.paragraphs):
            text = para.get('text', '').strip()
            style = para.get('style', '')

            # Zona: CAPA (antes do sumário ou primeiro título)
            if idx < (toc_idx if toc_idx >= 0 else first_title_idx):
                self.zones[idx] = 'capa'
                continue

            # Zona: SUMÁRIO (entre SUMÁRIO e próximo título ou quebra)
            if toc_idx >= 0 and idx > toc_idx:
                # Se encontramos um título principal depois do sumário, saímos da zona sumário
                if idx > toc_idx and self._is_title(para):
                    if not self._is_summary_entry(text):
                        self.zones[idx] = 'corpo'
                        continue

                # Ainda no sumário
                if idx < first_title_idx:
                    self.zones[idx] = 'sumario'
                    continue

            # Zona: REFERÊNCIAS (a partir do título REFERÊNCIAS)
            if references_idx >= 0 and idx >= references_idx:
                self.zones[idx] = 'referencias'
                continue

            # Zona: LEGENDA (começa com "Tabela", "Figura", "Fonte:")
            if self._is_legend(text):
                self.zones[idx] = 'legenda'
                continue

            # Zona: CORPO (padrão, entre primeiro título e referências)
            if first_title_idx >= 0 and idx >= first_title_idx:
                if references_idx < 0 or idx < references_idx:
                    self.zones[idx] = 'corpo'
                    continue

            # Padrão: corpo
            self.zones[idx] = 'corpo'

    def _find_first_title(self) -> int:
        """Encontra índice do primeiro título numerado"""
        for idx, para in enumerate(self.paragraphs):
            text = para.get('text', '').strip()

            # Título numerado: "1.", "1.1.", "2.3.1.", etc
            if re.match(r'^[\d.]+\s+', text):
                return idx

            # Ou com estilo de título
            if self._is_title(para):
                return idx

        return -1

    def _find_table_of_contents(self) -> int:
        """Encontra índice da seção SUMÁRIO/ÍNDICE"""
        for idx, para in enumerate(self.paragraphs):
            text = para.get('text', '').strip()

            if re.match(r'^(SUMÁRIO|ÍNDICE|Sumário|Índice|Sumario|Indice)', text):
                return idx

        return -1

    def _find_references_section(self) -> int:
        """Encontra índice da seção REFERÊNCIAS (após primeiro título numerado)"""
        first_title = self._find_first_title()

        if first_title < 0:
            return -1

        last_match = -1
        for idx in range(first_title, len(self.paragraphs)):
            para = self.paragraphs[idx]
            text = para.get('text', '').strip()

            if re.match(r'^(REFERÊNCIAS|Referências|REFERENCIAS|Referencias|REFERÊNCIAS\s+BIBLIOGRÁFICAS|Referências\s+Bibliográficas)', text, re.IGNORECASE):
                last_match = idx

        return last_match

    def _is_title(self, para: Dict[str, Any]) -> bool:
        """Verifica se é um título por estilo"""
        style = para.get('style', '').lower()
        return any(h in style for h in ['heading', 'título', 'title'])

    def _is_summary_entry(self, text: str) -> bool:
        """Verifica se é entrada do sumário"""
        # Entradas de sumário costumam ter numeração, texto e número de página
        # Ex: "1. Introdução...........................5"
        return bool(re.match(r'^[\d.]+\s+', text))

    def _is_legend(self, text: str) -> bool:
        """Verifica se é legenda (Tabela, Figura, Quadro, Gráfico, Fonte:)"""
        if len(text) > 100:
            return False

        # Tabela 1, Figura 2.1, Quadro 1:, Gráfico 3, Fonte:
        return bool(re.match(
            r'^(Tabela|Figura|Quadro|Gráfico|Grafico|Fonte)\s*[:\d]',
            text,
            re.IGNORECASE
        ))

    def get_zone(self, idx: int) -> str:
        """Retorna a zona de um parágrafo"""
        return self.zones.get(idx, 'corpo')

    def get_all_zones(self) -> Dict[int, str]:
        """Retorna todas as zonas"""
        return self.zones.copy()
