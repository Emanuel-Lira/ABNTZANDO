import pathlib

import pytest

from checker import analisar

DOCUMENTO = pathlib.Path(__file__).resolve().parent / 'fixtures' / 'teste-abnt-f6-f7.docx'

ESPERADOS = [
    # (id, localizacao, campo, trecho esperado no campo, severidade)
    ('org.sumario_coerente', 'Capítulo 2', 'encontrado', 'ausente', 'erro'),
    ('org.sumario_coerente', 'Capítulo 3', 'encontrado', '3.3 (no corpo)', 'erro'),
    ('org.sumario_coerente', 'Pré-textual', 'esperado', 'APÊNDICE A', 'erro'),
    ('alinhamento.justificado', 'Capítulo 5', 'encontrado', 'à esquerda', 'aviso'),
    ('recuo.primeira_linha', 'Capítulo 5', 'encontrado', '0 cm', 'aviso'),
    ('org.sumario_coerente', 'Capítulo 5', 'encontrado', '5 Conclusões', 'aviso'),
    ('org.numeracao', 'Capítulo 3', 'encontrado', '3.3 depois de 3.1', 'erro'),
    ('ref.ordem', 'Referências', 'encontrado', 'COSTA, 2021b', 'erro'),
    ('cit.sem_referencia', 'Capítulo 2', 'encontrado', '(MENDES, 2015)', 'erro'),
    ('ref.sem_citacao', 'Referências', 'encontrado', 'MENDES, 2012', 'aviso'),
    ('fonte.tamanho_apoio', 'Capítulo 4', 'encontrado', '12 pt', 'erro'),
]

IDS_PROIBIDOS = {'ref.presente', 'ref.ano', 'ref.sobrenome', 'ref.separacao', 'fonte.tamanho_fonte', 'org.sumario_presente'}


@pytest.fixture(scope='module')
def issues():
    return [i.to_dict() for i in analisar(DOCUMENTO.read_bytes())]


def test_lista_exata_de_itens(issues):
    assert len(issues) == len(ESPERADOS)
    for id_, loc, campo, trecho, sev in ESPERADOS:
        achados = [i for i in issues if i['id'] == id_ and i['localizacao'] == loc]
        assert achados, f'faltou {id_} em {loc}'
        assert any(trecho in i[campo] for i in achados), f'{id_} em {loc}: {campo} sem "{trecho}"'
        assert achados[0]['severidade'] == sev


def test_nenhum_item_proibido(issues):
    ids = {i['id'] for i in issues}
    assert not ids & IDS_PROIBIDOS


def test_localizacao_sempre_preenchida(issues):
    for i in issues:
        assert i['localizacao'] and 'undefined' not in i['localizacao']


def test_valores_de_formatacao_sem_ponto_decimal(issues):
    for i in issues:
        if i['categoria'] in ('Fonte', 'Espaçamento', 'Margens'):
            assert '.' not in i['esperado'] and '.' not in i['encontrado'], i
