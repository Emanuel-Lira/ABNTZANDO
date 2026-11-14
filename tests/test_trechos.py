import pathlib

from checker import analisar
from tests.test_documento_perfeito import gerar_documento

DOCUMENTO = pathlib.Path(__file__).resolve().parent / 'fixtures' / 'teste-abnt-f6-f7.docx'
HTML = pathlib.Path(__file__).resolve().parent.parent / 'public' / 'index.html'


def _por_id(itens, id_):
    return next(i for i in itens if i.id == id_)


def test_item_de_paragrafo_traz_trecho_do_texto():
    item = _por_id(analisar(DOCUMENTO.read_bytes()), 'fonte.tamanho_apoio')
    assert item.location == 'Capítulo 4'
    assert [(t['paragrafo'], 'Tabela 1' in t['texto']) for t in item.trechos] == [(40, True)]


def test_varios_paragrafos_geram_um_trecho_por_paragrafo():
    item = _por_id(analisar(DOCUMENTO.read_bytes()), 'ref.sem_citacao')
    assert [t['paragrafo'] for t in item.trechos] == [45, 51]


def test_trecho_e_curto_e_sem_quebra_de_linha():
    longo = 'Texto muito longo ' * 20
    itens = analisar(gerar_documento(referencias=['SILVA, João. ' + longo + ' 2020.']))
    for item in itens:
        for t in item.trechos:
            assert len(t['texto']) <= 80
            assert '\n' not in t['texto']


def test_trecho_e_escapado_na_interface():
    html = HTML.read_text(encoding='utf-8')
    assert 'function escaparHtml' in html
    bloco = html[html.index('function trechosDoItem'):html.index('function valoresDoItem')]
    assert 'escaparHtml(t.texto)' in bloco
