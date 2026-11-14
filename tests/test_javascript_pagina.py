import pathlib
import re

import esprima

RAIZ = pathlib.Path(__file__).resolve().parent.parent
HTML = RAIZ / 'public' / 'index.html'


def _scripts():
    html = HTML.read_text(encoding='utf-8')
    return re.findall(r'<script>(.*?)</script>', html, re.S)


def test_scripts_da_pagina_sao_javascript_valido():
    for numero, codigo in enumerate(_scripts()):
        esprima.parseScript(codigo)
