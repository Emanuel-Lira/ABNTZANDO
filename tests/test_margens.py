from checker import analisar
from tests.test_documento_perfeito import gerar_documento


def _margens(itens):
    return [i for i in itens if i.id == 'pag.margens']


def test_margens_erradas_geram_um_item_por_secao():
    itens = _margens(analisar(gerar_documento(margens=(2.5, 1.5, 2.2, 0.4))))
    assert len(itens) == 1
    assert itens[0].location == 'Seção 1'
    assert itens[0].esperado == [
        {'campo': 'superior', 'valor': 3.0}, {'campo': 'esquerda', 'valor': 3.0},
        {'campo': 'inferior', 'valor': 2.0}, {'campo': 'direita', 'valor': 2.0},
    ]
    assert itens[0].encontrado == [
        {'secao': 1, 'superior': 2.5, 'esquerda': 1.5, 'inferior': 2.2, 'direita': 0.4},
    ]


def test_secao_com_margem_errada_aponta_o_numero_da_secao():
    itens = _margens(analisar(gerar_documento(margens_secao2=(3, 3, 2, 1))))
    assert [i.location for i in itens] == ['Seção 2']
    assert itens[0].encontrado == [
        {'secao': 2, 'superior': 3, 'esquerda': 3, 'inferior': 2, 'direita': 1},
    ]


def test_secoes_consecutivas_viram_intervalo():
    from checker.rules import ABNTRules
    secoes = [{'top': 2.0, 'left': 3.0, 'bottom': 2.0, 'right': 2.0}] * 3 +              [{'top': 3.0, 'left': 3.0, 'bottom': 2.0, 'right': 2.0}] * 5
    regra = ABNTRules({'secoes_margens': secoes}, {}, set(), [])
    regra.check_margins()
    assert regra.issues[0].location == 'Seções 1 a 3'


def test_secoes_nao_consecutivas_listam_os_numeros():
    from checker.rules import ABNTRules
    errada = {'top': 2.0, 'left': 3.0, 'bottom': 2.0, 'right': 2.0}
    certa = {'top': 3.0, 'left': 3.0, 'bottom': 2.0, 'right': 2.0}
    regra = ABNTRules({'secoes_margens': [errada, certa, errada, certa, errada]}, {}, set(), [])
    regra.check_margins()
    assert regra.issues[0].location == 'Seções 1, 3 e 5'


def test_margens_corretas_nao_geram_item():
    assert _margens(analisar(gerar_documento())) == []
