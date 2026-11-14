import pytest

from checker.output_formatter import formatar_valor


@pytest.mark.parametrize('valor, esperado', [
    (1.5, '1,5'),
    (12.0, '12'),
    (1.25, '1,25'),
    (3.0, '3'),
    (10.0, '10'),
])
def test_formatar_valor_virgula_decimal(valor, esperado):
    assert formatar_valor(valor) == esperado


def test_formatar_valor_com_unidade():
    assert formatar_valor(1.25, 'cm') == '1,25 cm'
