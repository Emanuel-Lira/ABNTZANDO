"""Regressão com o arquivo real Erika_merged.docx (local, nunca versionado).

Pula sozinho se o arquivo não estiver em tests/fixtures/local/. Não copia nem
imprime o conteúdo do documento; só checa exceções, achados e os valores lidos.
"""
import pathlib

import pytest

from checker import analisar
from checker.reader import DocumentReader

ARQUIVO = pathlib.Path(__file__).resolve().parent / 'fixtures' / 'local' / 'Erika_merged.docx'
TAG_LINHA = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}line'

pytestmark = pytest.mark.skipif(
    not ARQUIVO.exists(),
    reason='arquivo local tests/fixtures/local/Erika_merged.docx ausente',
)


def test_analise_nao_lanca_valueerror():
    try:
        analisar(ARQUIVO.read_bytes())
    except ValueError as erro:
        pytest.fail(f'ValueError na análise: {erro}')


def test_analise_retorna_achados():
    itens = analisar(ARQUIVO.read_bytes())
    assert itens, 'a análise não pode voltar vazia para este documento'


def test_onze_paragrafos_com_278_sao_lidos_como_278():
    dados = ARQUIVO.read_bytes()
    reader = DocumentReader(dados)
    com_278 = [
        p for p in reader.doc.paragraphs
        if any(sp.get(TAG_LINHA) == '278.00000000000006' for sp in p._p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}spacing'))
    ]
    assert len(com_278) == 11, f'esperava 11 parágrafos com w:line decimal, achei {len(com_278)}'

    info = reader.get_document_info()
    textos = {p.text.strip() for p in com_278}
    lidos = [p['spacing']['line_spacing'] for p in info['paragraphs'] if p['text'].strip() in textos]
    assert len(lidos) == 11
    assert all(valor == pytest.approx(278 / 240) for valor in lidos)
