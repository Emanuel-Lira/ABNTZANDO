from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from typing import List, Dict, Any
from io import BytesIO

class DocumentFixer:
    """Aplica correções ABNT ao documento"""

    MARGIN_TOP = 3.0
    MARGIN_BOTTOM = 2.0
    MARGIN_LEFT = 3.0
    MARGIN_RIGHT = 2.0

    FONT_NAME = 'Times New Roman'
    FONT_SIZE = 12

    LINE_SPACING = 1.5
    FIRST_LINE_INDENT = 1.25

    def __init__(self, file_bytes: bytes):
        self.doc = Document(BytesIO(file_bytes))
        self.original_bytes = file_bytes

    def fix_all(self) -> bytes:
        """Aplica as correções seguras: margens e espaçamento"""
        # Corrigir margens (sempre seguro)
        self.fix_margins()
        # Corrigir espaçamento entre linhas (seguro)
        self.fix_spacing()

        output = BytesIO()
        self.doc.save(output)
        output.seek(0)
        return output.getvalue()

    def fix_margins(self):
        """Corrige as margens - correção segura"""
        try:
            for section in self.doc.sections:
                section.top_margin = Cm(self.MARGIN_TOP)
                section.bottom_margin = Cm(self.MARGIN_BOTTOM)
                section.left_margin = Cm(self.MARGIN_LEFT)
                section.right_margin = Cm(self.MARGIN_RIGHT)
        except Exception as e:
            print(f"Erro ao corrigir margens: {e}")

    def fix_fonts(self):
        """Corrige a fonte com cuidado"""
        try:
            for para in self.doc.paragraphs:
                # Apenas parágrafo com texto
                if not para.text.strip():
                    continue

                # Apenas se tiver runs
                if not para.runs:
                    continue

                # Aplicar apenas para runs sem formatação específica
                for run in para.runs:
                    # Se a fonte for None ou não recomendada, corrige
                    if run.font.name is None or run.font.name not in ['Times New Roman', 'Arial']:
                        run.font.name = self.FONT_NAME

                    if run.font.size is None:
                        run.font.size = Pt(self.FONT_SIZE)
        except Exception as e:
            print(f"Erro ao corrigir fontes: {e}")

    def fix_spacing(self):
        """Corrige espaçamento entre linhas para 1.5"""
        try:
            for para in self.doc.paragraphs:
                if not para.text.strip():
                    continue

                # Corrige o espaçamento para 1.5 (seguro)
                para.paragraph_format.line_spacing = self.LINE_SPACING
        except Exception as e:
            print(f"Erro ao corrigir espaçamento: {e}")

    def fix_indentation(self):
        """Corrige indentação com cuidado"""
        try:
            for para in self.doc.paragraphs:
                if not para.text.strip() or len(para.text) < 10:
                    continue

                # Apenas se não tiver recuo definido
                if para.paragraph_format.first_line_indent is None:
                    para.paragraph_format.first_line_indent = Cm(self.FIRST_LINE_INDENT)
        except Exception as e:
            print(f"Erro ao corrigir indentação: {e}")

    def get_fixed_document(self) -> bytes:
        """Retorna o documento corrigido em bytes"""
        output = BytesIO()
        self.doc.save(output)
        output.seek(0)
        return output.getvalue()
