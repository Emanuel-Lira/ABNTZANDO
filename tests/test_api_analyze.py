"""A API nunca responde 200 com lista vazia quando a análise falha."""
from fastapi.testclient import TestClient

import api.index as api_index
from tests.fixtures.make_fixture import documento_sintetico

DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def _cliente():
    return TestClient(api_index.app)


def test_falha_na_analise_vira_500_com_erro_explicito(monkeypatch):
    def quebra(_):
        raise ValueError('falha simulada')

    monkeypatch.setattr(api_index, 'analisar', quebra)
    resposta = _cliente().post('/api/analyze', files={'file': ('x.docx', b'qualquer', DOCX)})
    assert resposta.status_code == 500
    assert resposta.json() == {'erro': 'Não foi possível analisar este documento.', 'detalhe': 'ValueError'}


def test_documento_com_problemas_responde_200_com_achados():
    resposta = _cliente().post('/api/analyze', files={'file': ('x.docx', documento_sintetico(), DOCX)})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo['status'] == 'success'
    assert corpo['total_issues'] == len(corpo['issues']) > 0
