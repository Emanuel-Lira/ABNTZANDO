import hashlib
import pathlib
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient

from api.index import app
from checker.sugestao_sumario import SemTitulosNumerados, sugerir_sumario

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = RAIZ / 'tests' / 'fixtures' / 'teste-abnt-f6-f7.docx'
cliente = TestClient(app)


def _docx(doc) -> bytes:
    saida = BytesIO()
    doc.save(saida)
    return saida.getvalue()


def _doc_sem_titulos():
    doc = Document()
    doc.add_paragraph('Texto corrido sem títulos numerados nenhum.')
    return _docx(doc)


def test_sugestao_do_fixture_traz_niveis_corretos():
    entradas = sugerir_sumario(Document(BytesIO(FIXTURE.read_bytes())))
    por_texto = {e['texto']: e['nivel'] for e in entradas}
    assert por_texto['1 Introdução'] == 1
    assert por_texto['2.1 Conceitos básicos'] == 2
    assert por_texto['REFERÊNCIAS'] == 1


def test_capitulo_entra_com_nivel_1():
    doc = Document()
    doc.add_paragraph('CAPÍTULO 1 - Introdução')
    doc.add_paragraph('Texto do capítulo com pelo menos dez letras.')
    assert sugerir_sumario(doc) == [{'nivel': 1, 'texto': 'CAPÍTULO 1 - Introdução'}]


def test_titulo_sem_numero_nao_entra():
    doc = Document()
    doc.add_paragraph('Introdução sem número', style='Heading 1')
    doc.add_paragraph('1 Metodologia', style='Heading 1')
    assert sugerir_sumario(doc) == [{'nivel': 1, 'texto': '1 Metodologia'}]


def test_documento_sem_titulos_levanta_erro():
    with pytest.raises(SemTitulosNumerados):
        sugerir_sumario(Document(BytesIO(_doc_sem_titulos())))


def test_endpoint_devolve_json_e_nao_altera_o_arquivo():
    dados = FIXTURE.read_bytes()
    antes = hashlib.sha256(dados).hexdigest()
    resposta = cliente.post('/api/sugestao-sumario', files={'file': ('trabalho.docx', dados, 'application/octet-stream')})
    assert resposta.status_code == 200
    assert resposta.headers['content-type'].startswith('application/json')
    entradas = resposta.json()['entradas']
    assert {'nivel': 1, 'texto': '1 Introdução'} in entradas
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == antes


def test_endpoint_sem_titulos_retorna_422():
    resposta = cliente.post('/api/sugestao-sumario', files={'file': ('vazio.docx', _doc_sem_titulos(), 'application/octet-stream')})
    assert resposta.status_code == 422
    assert resposta.json()['status'] == 'error'
    assert 'título numerado' in resposta.json()['message']


def test_endpoint_arquivo_grande_retorna_413():
    grande = b'0' * (10 * 1024 * 1024 + 10)
    resposta = cliente.post('/api/sugestao-sumario', files={'file': ('grande.docx', grande, 'application/octet-stream')})
    assert resposta.status_code == 413


def test_endpoint_nao_docx_retorna_422():
    resposta = cliente.post('/api/sugestao-sumario', files={'file': ('nao.pdf', b'%PDF', 'application/pdf')})
    assert resposta.status_code == 422


def test_interface_tem_sugestao_com_copiar_e_sem_geracao_de_docx():
    html = (RAIZ / 'public' / 'index.html').read_text(encoding='utf-8')
    assert 'id="sumarioButton">Sugerir sumário' in html
    assert "fetch('/api/sugestao-sumario'" in html
    assert 'id="copiarSumario"' in html
    assert '/api/sumario' not in html
