from checker import analisar
from tests.test_documento_perfeito import REFERENCIAS_PADRAO, gerar_documento

LEI = 'Lei nº 7.498, de 25 de junho de 1986.'
CITACAO_LEI = 'O exercício profissional é regido pela Lei nº 7.498/1986.'


def _ids(itens):
    return [i.id for i in itens]


def test_entrada_de_lei_gera_aviso_e_nao_checa_sobrenome_nem_ordem():
    itens = analisar(gerar_documento(referencias=REFERENCIAS_PADRAO + [LEI],
                                     paragrafos_extra=[CITACAO_LEI]))
    ids = _ids(itens)
    assert 'ref.legislacao' in ids
    assert 'ref.sobrenome' not in ids and 'ref.ordem' not in ids
    aviso = next(i for i in itens if i.id == 'ref.legislacao')
    assert aviso.severity == 'warning'
    assert aviso.title.startswith('Entrada de legislação deve começar pelo nome da jurisdição em maiúsculas')


def test_lei_citada_no_texto_nao_entra_em_sem_citacao_nem_revisar():
    itens = analisar(gerar_documento(referencias=REFERENCIAS_PADRAO + [LEI],
                                     paragrafos_extra=[CITACAO_LEI]))
    ids = _ids(itens)
    assert 'ref.sem_citacao' not in ids
    assert 'ref.legislacao_revisar' not in ids


def test_lei_sem_citacao_no_texto_marca_revisar():
    itens = analisar(gerar_documento(referencias=REFERENCIAS_PADRAO + [LEI]))
    revisar = [i for i in itens if i.id == 'ref.legislacao_revisar']
    assert len(revisar) == 1
    assert revisar[0].severity == 'warning'
    assert 'revisar' in revisar[0].title
    assert 'ref.sem_citacao' not in _ids(itens)


def test_varias_normas_na_mesma_linha_geram_erro():
    linha = 'Lei nº 1.000, de 1990; Decreto nº 2.000, de 1991.'
    itens = analisar(gerar_documento(referencias=REFERENCIAS_PADRAO + [linha]))
    erros = [i for i in itens if i.id == 'ref.legislacao_multipla']
    assert len(erros) == 1
    assert erros[0].severity == 'error'
    assert erros[0].title == 'Cada norma deve ser uma entrada própria'
    assert 'ref.sobrenome' not in _ids(itens)
