"""Gera um .docx sintético com atributos decimais no XML do Word.

O Word grava inteiros em w:line e w:firstLine, mas alguns aplicativos gravam decimais
(por exemplo w:line="278.00000000000006" e w:firstLine="709.5"). Um leitor que converte
esses atributos com int() lança ValueError. Não usa o documento de nenhum estudante.
"""
from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

TNR = 'Times New Roman'


def _corpo(doc, texto):
    p = doc.add_paragraph(texto)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = p.runs[0]
    run.font.name = TNR
    run.font.size = Pt(12)
    return p


def documento_decimal() -> bytes:
    """Um título e dois parágrafos de corpo com atributos decimais no XML."""
    doc = Document()
    doc.add_paragraph('1 Introdução', style='Heading 1')

    # w:spacing/@w:line com decimal (278.00000000000006 → 278)
    com_linha = _corpo(doc, 'Corpo com entrelinha decimal, gravada por aplicativo que escreve decimais no XML.')
    espacamento = com_linha._p.get_or_add_pPr().get_or_add_spacing()
    espacamento.set(qn('w:line'), '278.00000000000006')
    espacamento.set(qn('w:lineRule'), 'auto')

    # w:ind/@w:firstLine com decimal (709.5 → 710)
    com_recuo = _corpo(doc, 'Corpo com recuo decimal, 709.5 twips em vez de um inteiro.')
    com_recuo._p.get_or_add_pPr().get_or_add_ind().set(qn('w:firstLine'), '709.5')

    saida = BytesIO()
    doc.save(saida)
    return saida.getvalue()
