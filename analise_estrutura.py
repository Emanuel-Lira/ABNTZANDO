"""Análise de estrutura do trabalho: zonas, sumário, numeração, referências e citações.

Módulo independente, depende só de python-docx. Devolve itens no formato do SPEC:
id, categoria, severidade, titulo, localizacao, esperado, encontrado, norma, corrigivel.
"""
import re
import unicodedata
from contextvars import ContextVar

from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

# ----- padrões -----
NUM_TITULO = re.compile(r"^(\d{1,2}(?:\.\d{1,2})*)\.?\s+(.{1,120})$")
CAPITULO = re.compile(r"^CAP[ÍI]TULO\s+(\d+)\b\s*[-–—:.]?\s*(.{0,120})$", re.IGNORECASE)
LEGENDA = re.compile(r"^(tabela|figura|quadro|gr[aá]fico)\s+\d+([.\-]\d+)*\s*[:.\-–]?(\s|$)", re.IGNORECASE)
FONTE_LINHA = re.compile(r"^fonte\s*:", re.IGNORECASE)
LIXO_SUMARIO = re.compile(r"[\s.…_·\-]{2,}\d*\s*$")
ANO = re.compile(r"\b((?:19|20)\d{2})([a-z])?\b")
CIT_PAREN = re.compile(
    r"\(([A-ZÀ-Ú]{2,}(?:\s[A-ZÀ-Ú]{2,})*)(?:\s+et\s+al\.)?"
    r"(?:;\s*([A-ZÀ-Ú]{2,}(?:\s[A-ZÀ-Ú]{2,})*))?"
    r",\s*((?:19|20)\d{2})[a-z]?(?:,\s*p\.\s*\d+)?\)"
)
CIT_NARR = re.compile(r"\b([A-ZÀ-Ú][A-Za-zÀ-ÿ]+)(?:\s+et\s+al\.)?\s+\(((?:19|20)\d{2})[a-z]?\)")
LEI_PREFIXO = re.compile(r"^(lei|decreto|resolucao|portaria)\b")
LEI_NUMERO = re.compile(r"\b(?:lei|decreto|resolu[cç][aã]o|portaria)\s*(?:n[º°o.]\s*)?(\d[\d.]*)", re.IGNORECASE)

TITULOS_SUMARIO = {"sumario", "indice"}
TITULOS_REFERENCIAS = {"referencias", "referencias bibliograficas"}
ZONAS_SEM_FORMATACAO = {"capa", "sumario", "pre_textual"}
ZONAS_CITACAO = {"corpo", "legenda", "tabela", "pos_textual"}


# ----- utilitários -----
def sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")


def normaliza(t: str) -> str:
    return re.sub(r"\s+", " ", sem_acento(t).lower()).strip()


def tem_quebra(p: Paragraph) -> bool:
    if p.paragraph_format.page_break_before:
        return True
    return bool(p._p.xpath('.//w:br[@w:type="page"]'))


def tem_estilo_titulo(p: Paragraph) -> bool:
    if p.style is None:
        return False
    sid = (p.style.style_id or "").lower()
    nome = (p.style.name or "").lower()
    return sid.startswith(("heading", "ttulo")) or nome.startswith(("heading", "título", "titulo"))


def eh_capitulo(texto: str) -> bool:
    return bool(CAPITULO.match(texto.strip()))


def eh_titulo(it) -> bool:
    if it["tipo"] != "p" or not it["texto"]:
        return False
    if tem_estilo_titulo(it["obj"]) or eh_capitulo(it["texto"]):
        return True
    return bool(NUM_TITULO.match(it["texto"])) and not it["texto"].endswith(".") and len(it["texto"]) <= 120


def separa_numero(texto: str):
    base = LIXO_SUMARIO.sub("", texto).strip()
    m = NUM_TITULO.match(base)
    if m:
        return m.group(1), m.group(2).strip()
    return None, base


def rotulo(d: dict) -> str:
    return f"{d['num']} {d['texto']}" if d["num"] else d["texto"]


def espaco(p: Paragraph, atributo: str) -> float:
    valor = getattr(p.paragraph_format, atributo)
    return valor.pt if valor is not None else 0.0


def lista_pt(itens):
    itens = [str(i) for i in itens]
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


class Localizacao(str):
    """Texto de localização que guarda os números dos parágrafos para mostrar trechos."""
    nums: list


# Capítulo (ou zona) de cada parágrafo, da análise em curso
LOCAIS_ATUAIS: ContextVar = ContextVar('locais_atuais', default=None)


def loc_paragrafos(nums) -> Localizacao:
    numeros = list(dict.fromkeys(int(n) for n in nums if n is not None))
    locais = LOCAIS_ATUAIS.get()
    nomes = list(dict.fromkeys(locais[n] for n in numeros if locais and n in locais))
    if not numeros:
        texto = "Documento"
    elif nomes:
        capitulos = [s.split(" ", 1)[1] for s in nomes if s.startswith("Capítulo ")]
        if len(nomes) == len(capitulos) and len(capitulos) > 1:
            texto = f"Capítulos {lista_pt(capitulos)}"
        else:
            texto = lista_pt(nomes)
    else:
        textos = [str(n) for n in numeros]
        rot = "Parágrafos" if len(textos) > 1 else "Parágrafo"
        if len(textos) > 10:
            texto = f"{rot} {', '.join(textos[:10])} e mais {len(textos) - 10}"
        else:
            texto = f"{rot} {lista_pt(textos)}"
    loc = Localizacao(texto)
    loc.nums = numeros
    return loc


def item(id_, categoria, severidade, titulo, localizacao, esperado, encontrado,
         norma="NBR 14724", corrigivel=False, paragrafos=None) -> dict:
    if paragrafos is None:
        paragrafos = getattr(localizacao, "nums", [])
    return {
        "id": id_,
        "categoria": categoria,
        "severidade": severidade,
        "titulo": titulo,
        "localizacao": str(localizacao),
        "esperado": esperado,
        "encontrado": encontrado,
        "norma": norma,
        "corrigivel": corrigivel,
        "paragrafos": list(paragrafos),
    }


# ----- 1. classificação de zonas -----
def classificar(doc):
    """Devolve a lista de blocos (parágrafos e tabelas) na ordem do documento, cada um com 'zona'.

    Numeração de parágrafos: 1-based, contando só parágrafos do corpo (não células de tabela).
    """
    itens = []
    n = 0
    for el in doc.element.body.iterchildren():
        if el.tag == qn("w:p"):
            n += 1
            p = Paragraph(el, doc)
            itens.append({"tipo": "p", "n": n, "obj": p, "texto": p.text.strip(), "zona": "corpo"})
        elif el.tag == qn("w:tbl"):
            itens.append({"tipo": "tbl", "n": None, "obj": Table(el, doc), "texto": "", "zona": "tabela"})

    def quebra(i):
        return itens[i]["tipo"] == "p" and tem_quebra(itens[i]["obj"])

    # sumário
    s = next((i for i, it in enumerate(itens)
              if it["tipo"] == "p" and normaliza(it["texto"]) in TITULOS_SUMARIO), None)
    q = next((i for i in range(len(itens)) if quebra(i)), None)

    # capa: até a primeira quebra, se ela vier antes do sumário
    fim_capa = -1
    if q is not None and (s is None or q < s):
        fim_capa = q
        for it in itens[: q + 1]:
            it["zona"] = "capa"

    # sumário: do título até a próxima quebra
    fim_sumario = fim_capa
    if s is not None:
        j = s
        while j < len(itens):
            itens[j]["zona"] = "sumario"
            if j > s and quebra(j):
                break
            j += 1
        fim_sumario = j

    # início do corpo: primeiro título depois do sumário
    c = next((i for i in range(fim_sumario + 1, len(itens)) if eh_titulo(itens[i])), None)

    # o que fica entre o sumário e o corpo não é analisado
    if c is not None:
        for i in range(fim_sumario + 1, c):
            if itens[i]["zona"] == "corpo":
                itens[i]["zona"] = "pre_textual"

    # referências: último título REFERÊNCIAS depois do início do corpo
    inicio_busca = c if c is not None else fim_sumario + 1
    r = None
    for i in range(inicio_busca, len(itens)):
        it = itens[i]
        if it["tipo"] == "p" and normaliza(it["texto"]) in TITULOS_REFERENCIAS and len(it["texto"]) <= 40:
            r = i
    if r is not None:
        fim = len(itens)
        for i in range(r + 1, len(itens)):
            t = normaliza(itens[i]["texto"])
            if itens[i]["tipo"] == "p" and (t.startswith("apendice") or t.startswith("anexo")) \
                    and len(itens[i]["texto"]) <= 60:
                fim = i
                break
        for i in range(r, fim):
            itens[i]["zona"] = "referencias"
        for i in range(fim, len(itens)):
            itens[i]["zona"] = "pos_textual"

    # legendas e linhas "Fonte:" dentro do corpo
    for it in itens:
        if it["zona"] == "corpo" and it["tipo"] == "p" and (
                LEGENDA.match(it["texto"]) or FONTE_LINHA.match(it["texto"])):
            it["zona"] = "legenda"

    return itens


# ----- 2. sumário -----
def analisa_sumario(itens, comparar: bool):
    out = []
    tem_sumario = any(it["zona"] == "sumario" and it["tipo"] == "p"
                      and normaliza(it["texto"]) in TITULOS_SUMARIO for it in itens)
    if not tem_sumario:
        return [item("org.sumario_presente", "Organização", "erro", "Sumário não encontrado",
                     "Documento", "Seção SUMÁRIO ou ÍNDICE", "ausente")]
    if not comparar:
        return out

    campo_toc = any("TOC" in (el.text or "")
                    for it in itens if it["zona"] == "sumario" and it["tipo"] == "p"
                    for el in it["obj"]._p.xpath(".//w:instrText"))
    if campo_toc:
        out.append(item("org.campo_sumario", "Organização", "aviso", "Sumário é campo automático do Word",
                        "Sumário", "Sumário atualizado",
                        "pode estar desatualizado. Clique com o botão direito no sumário e escolha Atualizar campo",
                        norma="boas práticas"))

    entradas = []
    for it in itens:
        if it["zona"] != "sumario" or it["tipo"] != "p" or not it["texto"]:
            continue
        if normaliza(it["texto"]) in TITULOS_SUMARIO:
            continue
        num, txt = separa_numero(it["texto"])
        entradas.append({"num": num, "chave": normaliza(txt), "texto": txt, "n": it["n"]})

    titulos = []
    for it in itens:
        no_corpo = it["zona"] == "corpo" and eh_titulo(it)
        e_refs = (it["zona"] == "referencias" and it["tipo"] == "p"
                  and normaliza(it["texto"]) in TITULOS_REFERENCIAS)
        if no_corpo or e_refs:
            num, txt = separa_numero(it["texto"])
            titulos.append({"num": num, "chave": normaliza(txt), "texto": txt, "n": it["n"]})

    pos_sumario = {}
    for pos, e in enumerate(entradas):
        pos_sumario.setdefault(e["chave"], pos)
    por_chave = {e["chave"]: e for e in entradas}
    chaves_corpo = {t["chave"] for t in titulos}

    # título do corpo sem entrada ou com numeração diferente
    for t in titulos:
        if t["chave"] not in por_chave:
            out.append(item("org.sumario_coerente", "Organização", "erro",
                            "Título no corpo sem entrada no sumário",
                            loc_paragrafos([t["n"]]),
                            f"“{rotulo(t)}” no sumário", "ausente"))
            continue
        e = por_chave[t["chave"]]
        if t["num"] and e["num"] and t["num"] != e["num"]:
            out.append(item("org.sumario_coerente", "Organização", "erro",
                            "Numeração diferente entre sumário e corpo",
                            loc_paragrafos([t["n"]]),
                            f"{e['num']} (conforme o sumário)", f"{t['num']} (no corpo)"))

    # entrada do sumário sem título no corpo
    for e in entradas:
        if e["chave"] not in chaves_corpo:
            out.append(item("org.sumario_coerente", "Organização", "erro",
                            "Entrada do sumário sem título no corpo",
                            loc_paragrafos([e["n"]]),
                            f"Título “{rotulo(e)}” no corpo", "ausente",
                            paragrafos=[e["n"]]))

    # ordem
    casados = [t for t in titulos if t["chave"] in pos_sumario]
    for a, b in zip(casados, casados[1:]):
        if pos_sumario[a["chave"]] > pos_sumario[b["chave"]]:
            out.append(item("org.sumario_coerente", "Organização", "aviso",
                            "Ordem diferente entre sumário e corpo",
                            loc_paragrafos([b["n"]]),
                            f"“{rotulo(a)}” antes de “{rotulo(b)}”",
                            f"“{rotulo(b)}” aparece antes de “{rotulo(a)}” no sumário"))
    return out


# ----- 3. numeração dos títulos do corpo -----
def proximo_valido(a, b):
    """a e b são listas de inteiros, ex.: [3, 1] e [3, 2]. Devolve (ok, esperado)."""
    if len(b) == len(a):
        esperado = a[:-1] + [a[-1] + 1]
    elif len(b) == len(a) + 1:
        esperado = a + [1]
    elif len(b) < len(a):
        esperado = a[: len(b) - 1] + [a[len(b) - 1] + 1]
    else:
        return False, a[:-1] + [a[-1] + 1]
    return b == esperado, esperado


def analisa_numeracao(itens):
    sequencia = []
    for it in itens:
        if it["zona"] == "corpo" and eh_titulo(it):
            m = NUM_TITULO.match(it["texto"])
            if m:
                sequencia.append((m.group(1), it["n"]))

    registros = []
    anterior = None
    for num, n in sequencia:
        partes = [int(x) for x in num.split(".")]
        if anterior is None:
            ok, esperado = partes == [1], [1]
            ant_str = "início"
        else:
            ok, esperado = proximo_valido(anterior[0], partes)
            ant_str = anterior[1]
        if not ok:
            registros.append((ant_str, num, n, ".".join(map(str, esperado))))
        anterior = (partes, num)

    if not registros:
        return []
    return [item("org.numeracao", "Organização", "erro", "Títulos numerados com saltos",
                 loc_paragrafos([r[2] for r in registros]),
                 f"Depois de {registros[0][0]} vem {registros[0][3]}",
                 "; ".join(f"{r[1]} depois de {r[0]}" for r in registros))]


# ----- 4. referências -----
def eh_legislacao(texto: str) -> bool:
    return bool(LEI_PREFIXO.match(normaliza(texto)))


def normas_na_entrada(texto: str) -> int:
    return sum(1 for parte in texto.split(";") if eh_legislacao(parte.strip()))


def chave_lei(texto: str):
    """(número sem pontos, ano) de uma norma citada; ano é None se não estiver logo depois do número."""
    m = LEI_NUMERO.search(texto)
    if not m:
        return None
    ano = ANO.search(texto[m.end(): m.end() + 40])
    return re.sub(r"\D", "", m.group(1)), (ano.group(1) if ano else None)


def rot_ref(e: dict) -> str:
    return f"{e['sobrenome']}, {e['ano'] or 's.d.'}{e['sufixo']}"


def analisa_referencias(itens):
    tem_titulo = any(it["zona"] == "referencias" and it["tipo"] == "p"
                     and normaliza(it["texto"]) in TITULOS_REFERENCIAS for it in itens)
    if not tem_titulo:
        return [item("ref.presente", "Referências", "erro", "Seção de referências não encontrada",
                     "Documento", "Seção REFERÊNCIAS", "ausente", norma="NBR 6023")], []

    entradas = []
    for idx, it in enumerate(itens):
        if it["zona"] != "referencias" or it["tipo"] != "p" or not it["texto"]:
            continue
        if normaliza(it["texto"]) in TITULOS_REFERENCIAS:
            continue
        t = it["texto"]
        sobrenome = re.split(r"[,.]", t, maxsplit=1)[0].strip()
        m = ANO.search(t)
        entradas.append({
            "idx": idx,
            "n": it["n"],
            "texto": t,
            "sobrenome": sobrenome,
            "maiuscula": sem_acento(sobrenome).replace(" ", "").isupper(),
            "chave": normaliza(sobrenome),
            "ano": m.group(1) if m else None,
            "sufixo": (m.group(2) or "") if m else "",
            "legislacao": eh_legislacao(t),
            "normas": normas_na_entrada(t),
            "lei": chave_lei(t),
        })

    out = []

    nao_maiuscula = [e for e in entradas if not e["legislacao"] and not e["maiuscula"]]
    if nao_maiuscula:
        out.append(item("ref.sobrenome", "Referências", "erro", "Sobrenome não está em maiúsculas",
                        loc_paragrafos([e["n"] for e in nao_maiuscula]),
                        "SOBRENOME em maiúsculas no início da entrada",
                        "; ".join(e["sobrenome"] for e in nao_maiuscula[:5]), norma="NBR 6023"))

    sem_ano = [e for e in entradas if not e["ano"]]
    if sem_ano:
        out.append(item("ref.ano", "Referências", "erro", "Ano ausente na referência",
                        loc_paragrafos([e["n"] for e in sem_ano]),
                        "Ano de publicação em cada entrada", "sem ano", norma="NBR 6023"))

    desordem = []
    ordenaveis = [e for e in entradas if not e["legislacao"]]
    for a, b in zip(ordenaveis, ordenaveis[1:]):
        ka = (a["chave"], int(a["ano"] or 0), a["sufixo"])
        kb = (b["chave"], int(b["ano"] or 0), b["sufixo"])
        if ka > kb:
            desordem.append((a, b))
    if desordem:
        out.append(item("ref.ordem", "Referências", "erro", "Referências fora de ordem alfabética",
                        loc_paragrafos([b["n"] for _, b in desordem]),
                        "Ordem alfabética pelo sobrenome; mesmo autor, por ano e sufixo",
                        "; ".join(f"{rot_ref(a)} aparece antes de {rot_ref(b)}" for a, b in desordem[:5]),
                        norma="NBR 6023"))

    sem_separacao = []
    for e in entradas[1:]:
        idx = e["idx"]
        anterior = itens[idx - 1]
        if anterior["tipo"] == "p" and (anterior["texto"] == "" or espaco(anterior["obj"], "space_after") >= 12):
            continue
        if espaco(itens[idx]["obj"], "space_before") >= 12:
            continue
        sem_separacao.append(e)
    if sem_separacao:
        out.append(item("ref.separacao", "Referências", "aviso", "Entradas sem separação entre si",
                        loc_paragrafos([e["n"] for e in sem_separacao]),
                        "Linha em branco entre as entradas",
                        "entradas encostadas", norma="NBR 6023"))

    multiplas = [e for e in entradas if e["normas"] > 1]
    if multiplas:
        out.append(item("ref.legislacao_multipla", "Referências", "erro",
                        "Cada norma deve ser uma entrada própria",
                        loc_paragrafos([e["n"] for e in multiplas]),
                        "Uma norma por entrada",
                        f"{multiplas[0]['normas']} normas na mesma entrada", norma="NBR 6023"))
    legislacoes = [e for e in entradas if e["legislacao"] and e["normas"] <= 1]
    if legislacoes:
        out.append(item("ref.legislacao", "Referências", "aviso",
                        "Entrada de legislação deve começar pelo nome da jurisdição em maiúsculas (ex.: BRASIL. Lei nº...)",
                        loc_paragrafos([e["n"] for e in legislacoes]),
                        "Jurisdição em maiúsculas, ex.: BRASIL. Lei nº ...",
                        "; ".join(e["texto"][:40] for e in legislacoes[:3]), norma="NBR 6023"))

    return out, entradas


# ----- 5. citações cruzadas -----
def coletar_citacoes(itens):
    cits = []
    for it in itens:
        if it["zona"] not in ZONAS_CITACAO:
            continue
        if it["tipo"] == "p":
            texto, origem = it["texto"], it["n"]
        else:
            texto = " ".join(c.text for linha in it["obj"].rows for c in linha.cells)
            origem = "tabela"
        if not texto:
            continue
        for m in CIT_PAREN.finditer(texto):
            nomes = [m.group(1)] + ([m.group(2)] if m.group(2) else [])
            for nome in nomes:
                cits.append({"chave": normaliza(nome), "ano": m.group(3), "trecho": m.group(0), "origem": origem})
        for m in CIT_NARR.finditer(texto):
            cits.append({"chave": normaliza(m.group(1)), "ano": m.group(2), "trecho": m.group(0), "origem": origem})
    return cits


def checar_citacoes(itens, refs):
    if not refs:
        return []  # sem lista de referências, a checagem não faz sentido
    out = []
    refs_comuns = [r for r in refs if not r["legislacao"]]
    chaves_refs = {(r["chave"], r["ano"]) for r in refs_comuns if r["ano"]}
    citadas = set()
    faltam = {}
    for c in coletar_citacoes(itens):
        k = (c["chave"], c["ano"])
        citadas.add(k)
        if k not in chaves_refs:
            faltam.setdefault(c["trecho"], []).append(c["origem"])

    if faltam:
        locs = [o for lista in faltam.values() for o in lista]
        out.append(item("cit.sem_referencia", "Referências", "erro",
                        "Citação sem entrada na lista de referências",
                        loc_paragrafos(locs),
                        "Entrada correspondente na lista de referências",
                        "; ".join(faltam.keys()), norma="NBR 10520"))

    nao_citadas = [r for r in refs_comuns if r["ano"] and (r["chave"], r["ano"]) not in citadas]
    if nao_citadas:
        out.append(item("ref.sem_citacao", "Referências", "aviso",
                        "Referência que não é citada no texto",
                        loc_paragrafos([r["n"] for r in nao_citadas]),
                        "Cada entrada citada no texto",
                        "; ".join(f"{r['sobrenome']}, {r['ano']}" for r in nao_citadas), norma="NBR 6023"))

    leis_no_texto = _leis_no_texto(itens)
    sem_lei = [r for r in refs if r["legislacao"] and r["lei"] and not _lei_citada(r["lei"], leis_no_texto)]
    if sem_lei:
        out.append(item("ref.legislacao_revisar", "Referências", "aviso",
                        "Legislação listada sem citação correspondente no texto (revisar)",
                        loc_paragrafos([r["n"] for r in sem_lei]),
                        "Citação da norma no corpo do texto",
                        "; ".join(r["texto"][:40] for r in sem_lei[:3]), norma="NBR 6023"))
    return out


def _leis_no_texto(itens):
    texto = "\n".join(it["texto"] for it in itens if it["zona"] in ZONAS_CITACAO and it["tipo"] == "p")
    leis = []
    for m in LEI_NUMERO.finditer(texto):
        ano = ANO.search(texto[m.end(): m.end() + 40])
        leis.append((re.sub(r"\D", "", m.group(1)), ano.group(1) if ano else None))
    return leis


def _lei_citada(lei, citadas):
    numero, ano = lei
    return any(n == numero and (a is None or ano is None or a == ano) for n, a in citadas)


# ----- ponto de entrada -----
def analisar_estrutura(doc) -> list:
    itens = classificar(doc)
    tem_estilo = any(it["tipo"] == "p" and it["zona"] == "corpo" and tem_estilo_titulo(it["obj"]) for it in itens)

    achados = []
    if not tem_estilo:
        achados.append(item("org.estilo_titulos", "Organização", "aviso", "Títulos sem estilo de título",
                            "Documento", "Títulos com estilo Título 1 ou Título 2",
                            "nenhum parágrafo com estilo de título", norma="boas práticas"))

    achados += analisa_sumario(itens, comparar=tem_estilo)
    if tem_estilo:
        achados += analisa_numeracao(itens)

    achados_refs, refs = analisa_referencias(itens)
    achados += achados_refs
    achados += checar_citacoes(itens, refs)

    tem_intro = any(eh_titulo(it) and "introducao" in normaliza(separa_numero(it["texto"])[1])
                    for it in itens if it["zona"] == "corpo" and it["tipo"] == "p")
    if not tem_intro:
        achados.append(item("org.secoes", "Organização", "aviso", "Seção de introdução não encontrada",
                            "Documento", "Seção 1 Introdução", "ausente"))
    return achados


def zonas_por_paragrafo(doc) -> dict:
    """Mapa {número do parágrafo: zona}. Use para as regras de formatação pularem as zonas certas."""
    return {it["n"]: it["zona"] for it in classificar(doc) if it["tipo"] == "p"}


def capitulos_por_paragrafo(doc) -> dict:
    """Mapa {número do parágrafo: local}, com local 'Capítulo N', 'Pré-textual', 'Referências' ou 'Pós-textual'.

    Cada parágrafo do corpo recebe o capítulo do título numerado mais recente (1, 2, 3...).
    Partes sem número (capa, sumário, pré-textual, referências) têm rótulo próprio.
    """
    mapa = {}
    atual = "Sem capítulo numerado"
    for it in classificar(doc):
        if it["tipo"] != "p":
            continue
        zona = it["zona"]
        if zona == "referencias":
            mapa[it["n"]] = "Referências"
            continue
        if zona == "pos_textual":
            mapa[it["n"]] = "Pós-textual"
            continue
        if zona in ("capa", "sumario", "pre_textual"):
            mapa[it["n"]] = "Pré-textual"
            continue
        if zona == "corpo" and eh_titulo(it):
            numero, _ = separa_numero(it["texto"])
            if numero:
                atual = f"Capítulo {numero.split('.')[0]}"
            else:
                m = CAPITULO.match(it["texto"].strip())
                if m:
                    atual = f"Capítulo {m.group(1)}"
        mapa[it["n"]] = atual
    return mapa
