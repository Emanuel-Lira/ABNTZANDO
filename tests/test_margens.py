from checker import analisar
from tests.test_documento_perfeito import gerar_documento


def _margens(itens):
    return [i for i in itens if i.id == 'pag.margens']


def test_margens_erradas_geram_um_item_por_secao():
    itens = _margens(analisar(gerar_documento(margens=(2.5, 1.5, 2.2, 0.4))))
    assert len(itens) == 1
    assert itens[0].location == 'Seção 1'
    assert itens[0].esperado == '3 cm sup. e esq., 2 cm inf. e dir.'
    assert itens[0].encontrado == '2,5 cm sup., 1,5 cm esq., 2,2 cm inf., 0,4 cm dir.'


def test_secao_com_margem_errada_aponta_o_numero_da_secao():
    itens = _margens(analisar(gerar_documento(margens_secao2=(3, 3, 2, 1))))
    assert [i.location for i in itens] == ['Seção 2']
    assert itens[0].encontrado == '3 cm sup., 3 cm esq., 2 cm inf., 1 cm dir.'


def test_margens_corretas_nao_geram_item():
    assert _margens(analisar(gerar_documento())) == []
