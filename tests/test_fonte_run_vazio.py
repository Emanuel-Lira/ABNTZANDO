from checker import analisar
from tests.test_documento_perfeito import gerar_documento


def test_run_vazio_sem_tamanho_nao_gera_item_de_fonte():
    itens = analisar(gerar_documento(run_vazio=True))
    assert [i.to_dict()['id'] for i in itens if i.categoria == 'Fonte'] == []
    assert itens == []
