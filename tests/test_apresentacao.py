import pathlib

from checker import analisar
from checker.rules import CATEGORIAS

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DOCUMENTO = RAIZ / 'tests' / 'fixtures' / 'teste-abnt-f6-f7.docx'
HTML = RAIZ / 'public' / 'index.html'
ORDEM = ['Margens', 'Fonte', 'Espaçamento', 'Alinhamento', 'Referências', 'Organização', 'Recuo']


def _issues():
    return [i.to_dict() for i in analisar(DOCUMENTO.read_bytes())]


def test_backend_devolve_so_valores():
    for d in _issues():
        assert 'Esperado:' not in d['esperado'] and 'Encontrado:' not in d['esperado']
        assert 'Esperado:' not in d['encontrado'] and 'Encontrado:' not in d['encontrado']
        assert 'description' not in d


def test_rotulos_montados_em_um_unico_lugar():
    html = HTML.read_text(encoding='utf-8')
    assert html.count('Esperado: ${') == 1
    assert html.count('Encontrado: ${') == 1
    bloco = html[html.index('function valoresDoItem'):html.index('function gerarConteudoMarkdown')]
    assert 'Esperado: ${' in bloco and 'Encontrado: ${' in bloco


def test_ordem_de_categorias_no_backend_e_na_interface():
    assert CATEGORIAS == ORDEM
    assert f"const ORDEM_CATEGORIAS = {ORDEM!r}".replace('"', "'") in HTML.read_text(encoding='utf-8')


def test_categorias_e_erros_antes_de_avisos():
    issues = _issues()
    chaves = [(ORDEM.index(i['categoria']), 0 if i['severidade'] == 'erro' else 1) for i in issues]
    assert chaves == sorted(chaves)
    assert all(i['categoria'] in ORDEM for i in issues)
