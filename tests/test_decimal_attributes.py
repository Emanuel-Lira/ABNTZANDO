"""Atributos decimais no XML (w:line, w:firstLine) não derrubam a análise."""
import logging

import pytest
from fastapi.testclient import TestClient

import api.index as api_index
import checker.reader as reader_mod
from checker import analisar
from checker.reader import DocumentReader
from tests.fixtures.make_decimal_spacing import documento_decimal

DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


def _paragrafo(info, trecho):
    return next(p for p in info['paragraphs'] if trecho in p['text'])


def test_analise_completa_sem_valueerror():
    itens = analisar(documento_decimal())
    assert isinstance(itens, list)


def test_api_responde_200_com_atributos_decimais():
    resposta = TestClient(api_index.app).post('/api/analyze', files={'file': ('d.docx', documento_decimal(), DOCX)})
    assert resposta.status_code == 200
    assert resposta.json()['status'] == 'success'


def test_decimais_sao_arredondados():
    info = DocumentReader(documento_decimal()).get_document_info()
    entrelinha = _paragrafo(info, 'entrelinha decimal')['spacing']['line_spacing']
    recuo = _paragrafo(info, 'recuo decimal')['indentation']['first_line']
    assert entrelinha == pytest.approx(278 / 240)   # 278.00000000000006 → 278
    assert recuo == pytest.approx(710 / 567)        # 709.5 → round → 710 twips


def test_um_aviso_por_atributo(monkeypatch, caplog):
    monkeypatch.setattr(reader_mod, '_avisados', set())
    with caplog.at_level(logging.WARNING, logger='checker.reader'):
        DocumentReader(documento_decimal()).get_document_info()
    avisos = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert sum('w:spacing/@w:line' in a for a in avisos) == 1
    assert sum('w:ind/@w:firstLine' in a for a in avisos) == 1
