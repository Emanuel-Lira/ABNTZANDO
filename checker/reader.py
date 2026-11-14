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
            'margins': self.get_margins(),
            'paragraphs': self.get_paragraphs_info(),
            'styles': self.get_styles_info(),
        }
        return info

    def get_margins(self) -> Dict[str, float]:
        """Retorna as margens do documento em cm"""
        try:
            sections = self.doc.sections
            if not sections:
                return {}

            section = sections[0]
            margins = {
                'top': section.top_margin.cm,
                'bottom': section.bottom_margin.cm,
                'left': section.left_margin.cm,
                'right': section.right_margin.cm,
            }
            return margins
        except:
            return {}

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
                    'first_line': para.paragraph_format.first_line_indent.cm if para.paragraph_format.first_line_indent else 0,
                    'left': para.paragraph_format.left_indent.cm if para.paragraph_format.left_indent else 0,
                    'right': para.paragraph_format.right_indent.cm if para.paragraph_format.right_indent else 0,
                }
            }
            paragraphs_info.append(para_info)

        return paragraphs_info

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
        """Extrai valor efetivo de fonte seguindo cadeia de estilos"""
        font_name = None
        font_size = None

        # 1. Tentar formatação direta do primeiro run
        if paragraph.runs:
            run = paragraph.runs[0]
            if run.font.name:
                font_name = run.font.name
            if run.font.size:
                font_size = run.font.size.pt

        # 2. Se não tiver, tentar estilo do parágrafo
        if not font_name or not font_size:
            try:
                para_style = paragraph.style
                if para_style and para_style.font:
                    if not font_name and para_style.font.name:
                        font_name = para_style.font.name
                    if not font_size and para_style.font.size:
                        font_size = para_style.font.size.pt
            except:
                pass

        # 3. Se ainda não tiver, tentar estilo base (Normal)
        if not font_name or not font_size:
            try:
                base_style = self.doc.styles['Normal']
                if base_style and base_style.font:
                    if not font_name and base_style.font.name:
                        font_name = base_style.font.name
                    if not font_size and base_style.font.size:
                        font_size = base_style.font.size.pt
            except:
                pass

        # 4. Padrões finais
        if not font_name:
            font_name = 'Times New Roman'
        if not font_size:
            font_size = 12

        return {
            'font_name': font_name,
            'font_size': font_size,
            'bold': None,
            'italic': None,
        }

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
