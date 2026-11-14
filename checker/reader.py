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
                'alignment': str(para.alignment),
                'font_info': self.get_paragraph_font_info(para),
                'spacing': {
                    'line_spacing': para.paragraph_format.line_spacing,
                    'space_before': para.paragraph_format.space_before.pt if para.paragraph_format.space_before else 0,
                    'space_after': para.paragraph_format.space_after.pt if para.paragraph_format.space_after else 0,
                },
                'indentation': {
                    'first_line': para.paragraph_format.first_line_indent.cm if para.paragraph_format.first_line_indent else 0,
                    'left': para.paragraph_format.left_indent.cm if para.paragraph_format.left_indent else 0,
                    'right': para.paragraph_format.right_indent.cm if para.paragraph_format.right_indent else 0,
                }
            }
            paragraphs_info.append(para_info)

        return paragraphs_info

    def get_paragraph_font_info(self, paragraph) -> Dict[str, Any]:
        """Extrai informações de fonte de um parágrafo"""
        if not paragraph.runs:
            return {'font_name': None, 'font_size': None}

        run = paragraph.runs[0]
        font_info = {
            'font_name': run.font.name,
            'font_size': run.font.size.pt if run.font.size else None,
            'bold': run.font.bold,
            'italic': run.font.italic,
        }
        return font_info

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
