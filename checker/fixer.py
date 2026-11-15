from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH
from typing import List, Dict, Any
from io import BytesIO

from analise_estrutura import titulos_do_documento, zonas_por_paragrafo

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
        """Aplica correções seguras: margens, fonte e espaçamento

        Correções aplicadas:
        - Margens: 3cm superior/esquerda, 2cm inferior/direita
        - Fonte: Times New Roman 12pt (se não recomendada)
        - Espaçamento: 1.5 entrelinhas no texto
        """
        # Corrigir margens (sempre seguro)
        self.fix_margins()

        # Corrigir fonte (seguro - apenas não recomendadas)
        self.fix_fonts()

        # Corrigir espaçamento entre linhas (seguro)
        self.fix_spacing()

        # Justificar e recuar o texto do corpo (títulos e textos curtos ficam de fora)
        self.fix_alinhamento_e_recuo()

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
        """Corrige fonte para Times New Roman 12pt se estiver incorreta

        Estratégia segura:
        - Se font.name é None ou não é Times/Arial: corrige para Times
        - Se font.size é None: corrige para 12pt
        - Mantém a formatação direta explícita
        """
        try:
            for para in self.doc.paragraphs:
                # Pular parágrafos vazios
                if not para.text.strip():
                    continue

                # Pular se não tem runs
                if not para.runs:
                    continue

                # Corrigir cada run
                for run in para.runs:
                    # Corrigir font.name se não for recomendada
                    if run.font.name:
                        # Se não é Times ou Arial, corrige
                        if run.font.name not in ['Times New Roman', 'Arial']:
                            run.font.name = self.FONT_NAME
                    else:
                        # Se é None, corrige para Times
                        run.font.name = self.FONT_NAME

                    # Corrigir font.size se não for 12pt
                    if run.font.size:
                        # Se não é 12pt, corrige
                        if run.font.size.pt != self.FONT_SIZE:
                            run.font.size = Pt(self.FONT_SIZE)
                    else:
                        # Se é None, corrige para 12pt
                        run.font.size = Pt(self.FONT_SIZE)
        except Exception as e:
            print(f"Erro ao corrigir fontes: {e}")

    def fix_spacing(self):
        """Corrige espaçamento entre linhas para 1.5 (entrelinhas)

        Nota: Aplicará 1.5 para todos os parágrafos
        (idealmente seria 1.5 em corpo e 1.0 em referências, mas isso requer detecção de zona)
        """
        try:
            for para in self.doc.paragraphs:
                # Pular parágrafos vazios
                if not para.text.strip():
                    continue

                # Corrigir espaçamento para 1.5
                current = para.paragraph_format.line_spacing

                # Se tiver valor e não for 1.5, corrige
                if current and current != self.LINE_SPACING:
                    para.paragraph_format.line_spacing = self.LINE_SPACING
                elif not current:
                    # Se for None, também define
                    para.paragraph_format.line_spacing = self.LINE_SPACING
        except Exception as e:
            print(f"Erro ao corrigir espaçamento: {e}")

    def fix_alinhamento_e_recuo(self):
        """Justifica e aplica recuo de primeira linha de 1,25 cm (709 twips) nos parágrafos do corpo"""
        try:
            zonas = zonas_por_paragrafo(self.doc)
            titulos = titulos_do_documento(self.doc)
            for n, para in enumerate(self.doc.paragraphs, start=1):
                texto = para.text.strip()
                if not texto or zonas.get(n) != 'corpo' or n in titulos:
                    continue
                para.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                if len(texto) >= 10:
                    para.paragraph_format.first_line_indent = Cm(1.25)
        except Exception as e:
            print(f"Erro ao corrigir alinhamento e recuo: {e}")

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
