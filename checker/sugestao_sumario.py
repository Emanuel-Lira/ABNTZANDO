from typing import List

from analise_estrutura import CAPITULO, NUM_TITULO, TITULOS_REFERENCIAS, classificar, eh_titulo, normaliza

NIVEIS_SUMARIO = 3
ZONAS_SUMARIO = {'corpo', 'referencias'}


class SemTitulosNumerados(Exception):
    pass


def nivel_do_titulo(texto: str):
    if CAPITULO.match(texto.strip()):
        return 1
    m = NUM_TITULO.match(texto)
    if m:
        return m.group(1).count('.') + 1
    return None


def sugerir_sumario(doc) -> List[dict]:
    """Títulos numerados, CAPÍTULO n e REFERÊNCIAS, com nível. Não altera o documento."""
    entradas = []
    for it in classificar(doc):
        if it['tipo'] != 'p' or it['zona'] not in ZONAS_SUMARIO or not it['texto']:
            continue
        if normaliza(it['texto']) in TITULOS_REFERENCIAS and len(it['texto']) <= 40:
            entradas.append({'nivel': 1, 'texto': it['texto']})
            continue
        if not eh_titulo(it):
            continue
        nivel = nivel_do_titulo(it['texto'])
        if nivel is not None and nivel <= NIVEIS_SUMARIO:
            entradas.append({'nivel': nivel, 'texto': it['texto']})
    if not entradas:
        raise SemTitulosNumerados()
    return entradas
