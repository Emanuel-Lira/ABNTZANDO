from io import BytesIO

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_BREAK
from docx.shared import Cm, Pt

from checker import analisar

TNR = 'Times New Roman'
REFERENCIAS_PADRAO = [
    'SILVA, João. Formação docente. São Paulo: Editora, 2020.',
    'SOUZA, Maria. Práticas pedagógicas. Rio de Janeiro: Editora, 2019.',
]


def _texto(doc, texto, estilo=None, espaco=1.5, depois=0, recuo=None,
           negrito=False, run_vazio=False):
    p = doc.add_paragraph(style=estilo)
    if run_vazio:
        p.add_run('')
    run = p.add_run(texto)
    run.font.name = TNR
    run.font.size = Pt(12)
    run.font.bold = negrito
    pf = p.paragraph_format
    pf.line_spacing = espaco
    pf.space_after = Pt(depois)
    if recuo is not None:
        pf.first_line_indent = Cm(recuo)
    return p


def _margens(secao, valores):
    secao.top_margin, secao.left_margin, secao.bottom_margin, secao.right_margin = (Cm(v) for v in valores)


def gerar_documento(referencias=None, paragrafos_extra=(), run_vazio=False,
                    margens=(3, 3, 2, 2), margens_secao2=None) -> bytes:
    doc = Document()
    _margens(doc.sections[0], margens)

    _texto(doc, 'SUMÁRIO', negrito=True)
    for entrada in ['1 Introdução', '2 Desenvolvimento', '2.1 Subtítulo', '3 Conclusão', 'REFERÊNCIAS']:
        _texto(doc, entrada, espaco=1.0)

    quebra = doc.add_paragraph()
    quebra.add_run().add_break(WD_BREAK.PAGE)

    _texto(doc, '1 Introdução', estilo='Heading 1')
    _texto(doc, 'Este trabalho apresenta uma discussão sobre o tema proposto (SOUZA, 2019).',
           recuo=1.25, run_vazio=run_vazio)
    _texto(doc, '2 Desenvolvimento', estilo='Heading 1')
    _texto(doc, 'A formação docente é discutida por diversos autores (SILVA, 2020).', recuo=1.25)
    _texto(doc, '2.1 Subtítulo', estilo='Heading 2')
    _texto(doc, 'Os resultados confirmam a hipótese inicial da pesquisa, conforme SOUZA (2019).', recuo=1.25)
    for texto in paragrafos_extra:
        _texto(doc, texto, recuo=1.25)
    _texto(doc, '3 Conclusão', estilo='Heading 1')
    _texto(doc, 'Conclui-se que a formação continuada é indispensável ao professor.', recuo=1.25)

    _texto(doc, 'REFERÊNCIAS', espaco=1.0, negrito=True)
    for ref in (REFERENCIAS_PADRAO if referencias is None else referencias):
        _texto(doc, ref, espaco=1.0, depois=12)

    if margens_secao2 is not None:
        secao2 = doc.add_section(WD_SECTION.NEW_PAGE)
        _margens(secao2, margens_secao2)

    saida = BytesIO()
    doc.save(saida)
    return saida.getvalue()


def gerar_documento_perfeito() -> bytes:
    return gerar_documento()


def test_documento_perfeito_nao_gera_itens():
    assert analisar(gerar_documento_perfeito()) == []
