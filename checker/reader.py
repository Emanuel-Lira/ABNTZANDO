from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from typing import Dict, List, Any
from io import BytesIO

class DocumentReader:
    def __init__(self, file_path_or_bytes):
        if isinstance(file_path_or_bytes, bytes):
            self.doc = Document(BytesIO(file_path_or_bytes))
        else:
            self.doc = Document(file_path_or_bytes)

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
        """Margens de cada seção do documento, em cm"""
        return [
            {
                'top': secao.top_margin.cm if secao.top_margin is not None else 0.0,
                'bottom': secao.bottom_margin.cm if secao.bottom_margin is not None else 0.0,
                'left': secao.left_margin.cm if secao.left_margin is not None else 0.0,
                'right': secao.right_margin.cm if secao.right_margin is not None else 0.0,
            }
            for secao in self.doc.sections
        ]

    def get_paragraphs_info(self) -> List[Dict[str, Any]]:
        """Extrai informações de cada parágrafo"""
        paragraphs_info = []

        for idx, para in enumerate(self.doc.paragraphs):
            if not para.text.strip():
                continue

            para_info = {
                'index': idx,
                'text': para.text,
                'style': para.style.name if para.style else None,
                'alignment': str(para.alignment),
                'font_info': self.get_paragraph_font_info(para),
                'spacing': self._get_effective_spacing(para),
                'indentation': {
                    'first_line': self._get_effective_first_line(para),
                    'left': para.paragraph_format.left_indent.cm if para.paragraph_format.left_indent else 0,
                    'right': para.paragraph_format.right_indent.cm if para.paragraph_format.right_indent else 0,
                }
            }
            paragraphs_info.append(para_info)

        return paragraphs_info

    def _get_effective_first_line(self, paragraph) -> float:
        """Recuo de primeira linha em cm, seguindo: direto > estilo do parágrafo > Normal"""
        valor = paragraph.paragraph_format.first_line_indent
        if valor is None:
            valor = paragraph.style.paragraph_format.first_line_indent if paragraph.style else None
        if valor is None:
            valor = self.doc.styles['Normal'].paragraph_format.first_line_indent
        return valor.cm if valor is not None else 0.0

    def _get_effective_spacing(self, paragraph) -> Dict[str, Any]:
        """Extrai valor efetivo de espaçamento (entrelinhas e espaço entre parágrafos)"""
        pf = paragraph.paragraph_format

        # 1. Valor direto do parágrafo
        line_spacing = pf.line_spacing
        space_before = pf.space_before.pt if pf.space_before else 0
        space_after = pf.space_after.pt if pf.space_after else 0

        # 2. Se não tiver, tentar estilo do parágrafo
        if not line_spacing:
            try:
                para_style = paragraph.style
                if para_style and para_style.paragraph_format:
                    line_spacing = para_style.paragraph_format.line_spacing
            except:
                pass

        # 3. Se ainda não tiver, tentar estilo Normal
        if not line_spacing:
            try:
                base_style = self.doc.styles['Normal']
                if base_style and base_style.paragraph_format:
                    line_spacing = base_style.paragraph_format.line_spacing
            except:
                pass

        # 4. Padrão: 1.5
        if not line_spacing:
            line_spacing = 1.5

        return {
            'line_spacing': line_spacing,
            'space_before': space_before,
            'space_after': space_after,
        }

    def get_paragraph_font_info(self, paragraph) -> Dict[str, Any]:
        """Fonte e tamanho efetivos: run com texto > estilo do parágrafo > estilos base > docDefaults"""
        run = next((r for r in paragraph.runs if r.text.strip()), None)
        nome = run.font.name if run is not None else None
        tamanho = run.font.size.pt if run is not None and run.font.size is not None else None

        if nome is None:
            nome = self._nome_na_cadeia(paragraph.style)
        if tamanho is None:
            tamanho = self._tamanho_na_cadeia(paragraph.style)

        return {
            'font_name': nome,
            'font_size': tamanho,
            'bold': None,
            'italic': None,
        }

    def _nome_na_cadeia(self, estilo) -> Any:
        atual = estilo
        while atual is not None:
            if atual.font.name:
                return atual.font.name
            atual = atual.base_style
        valores = self.doc.styles.element.xpath('./w:docDefaults/w:rPrDefault/w:rPr/w:rFonts/@w:ascii')
        return valores[0] if valores else None

    def _tamanho_na_cadeia(self, estilo) -> Any:
        atual = estilo
        while atual is not None:
            if atual.font.size is not None:
                return atual.font.size.pt
            atual = atual.base_style
        valores = self.doc.styles.element.xpath('./w:docDefaults/w:rPrDefault/w:rPr/w:sz/@w:val')
        return int(valores[0]) / 2 if valores else None

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
                if run.font.size:
                    styles_info['used_sizes'].add(run.font.size.pt)

        styles_info['used_fonts'] = list(styles_info['used_fonts'])
        styles_info['used_sizes'] = list(styles_info['used_sizes'])

        return styles_info
