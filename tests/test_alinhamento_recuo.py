from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK

from checker import DocumentFixer, analisar
from tests.test_documento_perfeito import _margens, _texto


def _documento(corpo):
    """Monta um trabalho mínimo: sumário, quebra de página, corpo e referências."""
    doc = Document()
    _margens(doc.sections[0], (3, 3, 2, 2))
    _texto(doc, 'SUMÁRIO', negrito=True)
    _texto(doc, '1 Introdução', espaco=1.0)
    _texto(doc, 'REFERÊNCIAS', espaco=1.0)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    _texto(doc, '1 Introdução', estilo='Heading 1')
    for texto, alinhamento, recuo in corpo:
        _texto(doc, texto, alinhamento=alinhamento, recuo=recuo)
    _texto(doc, 'REFERÊNCIAS', espaco=1.0, negrito=True)
    _texto(doc, 'SILVA, João. Título. São Paulo: Editora, 2020.', espaco=1.0, depois=12)
    saida = BytesIO()
    doc.save(saida)
    return saida.getvalue()


def _achados(dados, id_):
    return [i for i in analisar(dados) if i.id == id_]


def test_corpo_justificado_com_recuo_nao_alerta():
    dados = _documento([('Texto do corpo justificado com recuo certo, de forma completa.',
                         WD_ALIGN_PARAGRAPH.JUSTIFY, 1.25)])
    assert _achados(dados, 'alinhamento.justificado') == []
    assert _achados(dados, 'recuo.primeira_linha') == []


def test_corpo_alinhado_a_esquerda_gera_aviso_corrigivel():
    dados = _documento([('Texto do corpo alinhado à esquerda, com recuo certo, de forma completa.',
                         WD_ALIGN_PARAGRAPH.LEFT, 1.25)])
    itens = _achados(dados, 'alinhamento.justificado')
    assert len(itens) == 1
    assert itens[0].severity == 'warning'
    assert itens[0].fixable is True


def test_corpo_sem_recuo_gera_aviso_corrigivel():
    dados = _documento([('Texto do corpo justificado mas sem recuo de primeira linha.',
                         WD_ALIGN_PARAGRAPH.JUSTIFY, 0)])
    itens = _achados(dados, 'recuo.primeira_linha')
    assert len(itens) == 1
    assert itens[0].severity == 'warning'
    assert itens[0].fixable is True


def test_referencia_sem_recuo_nao_alerta():
    dados = _documento([('Texto do corpo justificado com recuo certo, de forma completa.',
                         WD_ALIGN_PARAGRAPH.JUSTIFY, 1.25)])
    assert _achados(dados, 'recuo.primeira_linha') == []


def test_correcao_justifica_e_aplica_recuo_no_corpo():
    dados = _documento([('Texto do corpo alinhado à esquerda sem recuo nenhum aqui.',
                         WD_ALIGN_PARAGRAPH.LEFT, 0)])
    corrigido = DocumentFixer(dados).fix_all()
    assert _achados(corrigido, 'alinhamento.justificado') == []
    assert _achados(corrigido, 'recuo.primeira_linha') == []
