"""Regressão: um .docx regravado por outro app não pode sumir da análise.

Usa só o documento sintético de tests/fixtures/make_fixture.py, nunca o de um estudante.
"""
import logging

import pytest

from checker import analisar
from tests.fixtures.make_fixture import documento_sintetico, reempacotar

# Problemas que o documento sintético contém de propósito
CONHECIDOS = {'alinhamento.justificado', 'fonte.tamanho_texto', 'recuo.primeira_linha'}


@pytest.fixture(scope='module')
def base():
    return documento_sintetico()


@pytest.mark.parametrize('stored', [False, True], ids=['deflated', 'stored'])
def test_regravado_analisa_sem_avisos(base, caplog, stored):
    dados = reempacotar(base, stored=stored)
    with caplog.at_level(logging.WARNING, logger='checker.reader'):
        itens = analisar(dados)
    # Se o documento tem problemas conhecidos, zero achados é falha, não "sem problemas"
    assert itens, 'documento com problemas conhecidos não pode voltar sem achados'
    assert CONHECIDOS <= {i.id for i in itens}
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


def test_sem_estilo_normal_analisa_e_avisa_uma_vez(base, caplog):
    dados = reempacotar(base, stored=True, sem_normal=True)
    with caplog.at_level(logging.WARNING, logger='checker.reader'):
        itens = analisar(dados)
    assert itens, 'sem o estilo Normal a análise não pode voltar vazia'
    assert CONHECIDOS <= {i.id for i in itens}
    avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(avisos) == 1
    assert 'Normal' in avisos[0].getMessage()
