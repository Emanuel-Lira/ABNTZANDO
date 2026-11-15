"""Contrato do frontend: erro do servidor nunca vira "Nenhum problema encontrado"."""
import pathlib

HTML = pathlib.Path(__file__).resolve().parent.parent / 'public' / 'index.html'


def _trecho(html, inicio, fim):
    return html[html.index(inicio):html.index(fim, html.index(inicio))]


def test_handlefile_checa_response_ok_antes_de_renderizar():
    html = HTML.read_text(encoding='utf-8')
    corpo = _trecho(html, 'async function handleFile(file)', 'function mostrarErroAnalise')
    assert 'response.ok' in corpo
    assert corpo.index('response.ok') < corpo.index('displayResults(corpo)')


def test_erro_mostra_tentar_de_novo_e_nao_renderiza_sucesso():
    html = HTML.read_text(encoding='utf-8')
    erro = _trecho(html, 'function mostrarErroAnalise', 'function displayResults')
    assert 'Tentar de novo' in erro
    assert 'role="alert"' in erro
    assert 'Nenhum problema encontrado' not in erro
    assert 'success-state' not in erro
