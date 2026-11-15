"""Gera um .docx sintético para testes de leitura e análise.

Não usa o documento de nenhum estudante. O documento tem capa, sumário, seções
numeradas, corpo com recuo, uma imagem em linha e referências, e traz alguns
problemas conhecidos (alinhamento, recuo e tamanho de fonte) para que a análise
precise encontrá-los.

reempacotar() reescreve o arquivo como um app de celular faria: com outra
compactação ZIP e, opcionalmente, sem o estilo 'Normal' em word/styles.xml.

Uso manual (grava os arquivos em tests/fixtures/, que são ignorados pelo git):
    python tests/fixtures/make_fixture.py
"""
import struct
import sys
import zipfile
import zlib
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.shared import Cm, Pt

TNR = 'Times New Roman'
W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def _png(largura: int = 16, altura: int = 16) -> bytes:
    """PNG mínimo (um retângulo vermelho), sem depender de Pillow."""
    linhas = b''.join(b'\x00' + b'\xc0\x40\x40' * largura for _ in range(altura))

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return struct.pack('>I', len(dados)) + tipo + dados + struct.pack('>I', zlib.crc32(tipo + dados) & 0xFFFFFFFF)

    cabecalho = struct.pack('>IIBBBBB', largura, altura, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + bloco(b'IHDR', cabecalho)
            + bloco(b'IDAT', zlib.compress(linhas)) + bloco(b'IEND', b''))


def _texto(doc, texto, *, estilo=None, alinhamento=None, recuo=None, espaco=1.5,
           depois=0, tamanho=12, negrito=False):
    p = doc.add_paragraph(texto, style=estilo)
    run = p.runs[0]
    run.font.name = TNR
    run.font.size = Pt(tamanho)
    run.font.bold = negrito
    pf = p.paragraph_format
    pf.line_spacing = espaco
    pf.space_after = Pt(depois)
    if alinhamento is not None:
        pf.alignment = alinhamento
    if recuo is not None:
        pf.first_line_indent = Cm(recuo)
    return p


def _quebra_de_pagina(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def documento_sintetico() -> bytes:
    """Documento sintético com problemas conhecidos, em bytes de .docx."""
    doc = Document()
    secao = doc.sections[0]
    secao.top_margin = secao.left_margin = Cm(3)
    secao.bottom_margin = secao.right_margin = Cm(2)

    # Capa
    _texto(doc, 'UNIVERSIDADE EXEMPLO', alinhamento=WD_ALIGN_PARAGRAPH.CENTER, espaco=1.0, negrito=True)
    _texto(doc, 'Trabalho sintético para testes', alinhamento=WD_ALIGN_PARAGRAPH.CENTER, espaco=1.0)
    _quebra_de_pagina(doc)

    # Sumário
    _texto(doc, 'SUMÁRIO', espaco=1.0, negrito=True)
    for entrada in ['1 Introdução', '2 Desenvolvimento', '2.1 Subtítulo', '3 Conclusão', 'REFERÊNCIAS']:
        _texto(doc, entrada, espaco=1.0)
    _quebra_de_pagina(doc)

    # Seções numeradas e corpo
    _texto(doc, '1 Introdução', estilo='Heading 1')
    _texto(doc, 'Este trabalho apresenta uma discussão sobre o tema proposto (SILVA, 2020).',
           alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=1.25)
    # Problemas conhecidos: alinhado à esquerda e sem recuo
    _texto(doc, 'Texto de corpo alinhado à esquerda, sem recuo, para gerar um achado conhecido.',
           alinhamento=WD_ALIGN_PARAGRAPH.LEFT, recuo=0)

    _texto(doc, '2 Desenvolvimento', estilo='Heading 1')
    # Problema conhecido: letra de 11 pt no corpo
    _texto(doc, 'Este trecho usa letra de 11 pt, fora do padrão de 12 pt do texto.',
           alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=1.25, tamanho=11)

    # Imagem em linha com legenda
    figura = doc.add_paragraph()
    figura.alignment = WD_ALIGN_PARAGRAPH.CENTER
    figura.add_run().add_picture(BytesIO(_png()), width=Cm(3))
    _texto(doc, 'Figura 1: Ilustração de teste.', alinhamento=WD_ALIGN_PARAGRAPH.CENTER,
           tamanho=10, espaco=1.0)

    _texto(doc, '2.1 Subtítulo', estilo='Heading 2')
    _texto(doc, 'Os resultados confirmam a hipótese inicial (SILVA, 2020).',
           alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=1.25)

    _texto(doc, '3 Conclusão', estilo='Heading 1')
    _texto(doc, 'Conclui-se que o tema merece novos estudos.',
           alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, recuo=1.25)

    # Referências
    _texto(doc, 'REFERÊNCIAS', espaco=1.0, negrito=True)
    _texto(doc, 'SILVA, João. Formação docente. São Paulo: Editora, 2020.', espaco=1.0, depois=12)
    _texto(doc, 'SOUZA, Maria. Práticas pedagógicas. Rio de Janeiro: Editora, 2019.', espaco=1.0, depois=12)

    saida = BytesIO()
    doc.save(saida)
    return saida.getvalue()


def _remover_estilo_normal(styles_xml: bytes) -> bytes:
    from lxml import etree

    arvore = etree.fromstring(styles_xml)
    for estilo in arvore.findall(f'{{{W_NS}}}style'):
        if estilo.get(f'{{{W_NS}}}styleId') == 'Normal':
            arvore.remove(estilo)
    return etree.tostring(arvore, xml_declaration=True, encoding='UTF-8', standalone=True)


def reempacotar(docx_bytes: bytes, *, stored: bool, sem_normal: bool = False) -> bytes:
    """Reescreve o .docx com outra compactação ZIP; opcionalmente remove o estilo 'Normal'."""
    compressao = zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED
    entrada = zipfile.ZipFile(BytesIO(docx_bytes))
    saida = BytesIO()
    with zipfile.ZipFile(saida, 'w', compressao) as destino:
        for item in entrada.infolist():
            dados = entrada.read(item.filename)
            if sem_normal and item.filename == 'word/styles.xml':
                dados = _remover_estilo_normal(dados)
            destino.writestr(item.filename, dados, compress_type=compressao)
    return saida.getvalue()


if __name__ == '__main__':
    pasta = Path(__file__).resolve().parent
    base = documento_sintetico()
    (pasta / 'sintetico-deflated.docx').write_bytes(reempacotar(base, stored=False))
    (pasta / 'sintetico-stored.docx').write_bytes(reempacotar(base, stored=True))
    (pasta / 'sintetico-stored-sem-normal.docx').write_bytes(reempacotar(base, stored=True, sem_normal=True))
    print('arquivos gravados em', pasta, file=sys.stderr)
