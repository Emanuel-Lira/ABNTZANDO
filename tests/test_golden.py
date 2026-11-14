import json
import pathlib

from checker import analisar

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DOCUMENTO = RAIZ / 'tests' / 'fixtures' / 'teste-abnt-f6-f7.docx'
GOLDEN = RAIZ / 'tests' / 'golden' / 'teste-abnt-f6-f7.json'
CAMPOS = ['id', 'categoria', 'severidade', 'localizacao', 'esperado', 'encontrado']


def test_saida_igual_ao_golden():
    golden = json.loads(GOLDEN.read_text(encoding='utf-8'))
    atual = [{k: i.to_dict()[k] for k in CAMPOS} for i in analisar(DOCUMENTO.read_bytes())]
    assert atual == golden
