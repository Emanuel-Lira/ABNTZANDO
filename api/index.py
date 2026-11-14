from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path
import json
import tempfile
import traceback
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from docx import Document

from checker import analisar, DocumentFixer
from checker.sugestao_sumario import SemTitulosNumerados, sugerir_sumario

try:
    from docx2pdf import convert
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir arquivos estáticos da pasta public
public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/static", StaticFiles(directory=public_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_html():
    index_file = public_dir / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ABNTzando</h1><p>API rodando</p>"

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    """Analisa um documento .docx e retorna os problemas encontrados"""
    try:
        # Ler arquivo
        contents = await file.read()

        issues_json = [issue.to_dict() for issue in analisar(contents)]

        return {
            "status": "success",
            "issues": issues_json,
            "total_issues": len(issues_json),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "issues": []
        }

@app.post("/api/fix")
async def fix(file: UploadFile = File(...)):
    """Corrige apenas as margens do documento (correção segura)"""
    try:
        # Ler arquivo
        contents = await file.read()

        # Aplicar apenas correção de margens (segura)
        fixer = DocumentFixer(contents)
        fixed_document = fixer.fix_all()

        # Retornar documento com margens corrigidas
        return StreamingResponse(
            iter([fixed_document]),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": "attachment; filename=documento_corrigido.docx"}
        )
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

TAMANHO_MAXIMO_SUMARIO = 10 * 1024 * 1024


def _erro(status: int, mensagem: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"status": "error", "message": mensagem})


@app.post("/api/sugestao-sumario")
async def sugestao_sumario(file: UploadFile = File(...)):
    """Lista de títulos sugerida para o sumário. Não altera o documento."""
    nome = Path(file.filename or "").name
    if not nome.lower().endswith(".docx"):
        return _erro(422, "Envie um arquivo .docx.")

    conteudo = await file.read(TAMANHO_MAXIMO_SUMARIO + 1)
    if len(conteudo) > TAMANHO_MAXIMO_SUMARIO:
        return _erro(413, "O arquivo passa do limite de 10 MB.")
    if not conteudo:
        return _erro(422, "O arquivo está vazio.")

    try:
        doc = Document(BytesIO(conteudo))
    except Exception:
        return _erro(422, "Não foi possível abrir o arquivo. Verifique se é um .docx válido.")

    try:
        entradas = sugerir_sumario(doc)
    except SemTitulosNumerados:
        return _erro(422, "Nenhum título numerado encontrado. Use títulos como '1 Introdução', "
                          "'2.1 Conceitos' ou 'CAPÍTULO 1'.")
    except Exception:
        traceback.print_exc()
        return _erro(500, "Não foi possível sugerir o sumário.")

    return {"status": "success", "entradas": entradas}


@app.post("/api/convert-pdf")
async def convert_to_pdf(file: UploadFile = File(...)):
    """Converte documento .docx para PDF"""
    try:
        contents = await file.read()

        if not PDF_SUPPORT:
            # Se não tiver suporte PDF, retornar o documento original como fallback
            return StreamingResponse(
                iter([contents]),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename={file.filename}"},
                status_code=200
            )

        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_docx:
            tmp_docx.write(contents)
            tmp_docx_path = tmp_docx.name

        # Converter para PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_pdf:
            tmp_pdf_path = tmp_pdf.name

        try:
            convert(tmp_docx_path, tmp_pdf_path)
        except Exception as convert_error:
            print(f"Erro na conversão PDF: {convert_error}")
            Path(tmp_docx_path).unlink(missing_ok=True)
            # Fallback: retornar DOCX se PDF falhar
            return StreamingResponse(
                iter([contents]),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename={file.filename}"},
                status_code=200
            )

        # Ler PDF convertido
        with open(tmp_pdf_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()

        # Verificar se o PDF foi gerado corretamente
        if not pdf_bytes or len(pdf_bytes) < 100:
            Path(tmp_docx_path).unlink(missing_ok=True)
            Path(tmp_pdf_path).unlink(missing_ok=True)
            # Fallback: retornar DOCX se PDF estiver vazio
            return StreamingResponse(
                iter([contents]),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={"Content-Disposition": f"attachment; filename={file.filename}"},
                status_code=200
            )

        # Limpar temporários
        Path(tmp_docx_path).unlink(missing_ok=True)
        Path(tmp_pdf_path).unlink(missing_ok=True)

        # Retornar PDF
        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={file.filename.replace('.docx', '.pdf')}"}
        )
    except Exception as e:
        print(f"Erro ao converter PDF: {str(e)}")
        return {
            "status": "error",
            "message": f"Conversão para PDF indisponível. Tente baixar como DOCX."
        }

@app.get("/api/glossario")
async def get_glossario():
    """Retorna os termos do glossário"""
    glossario = {
        "termos": [
            {
                "id": "item-0",
                "nome": "Alinhamento",
                "definicao": "Distribuição do texto em relação às margens da página. A ABNT recomenda alinhamento justificado ou à esquerda para o corpo do trabalho.",
                "norma": "NBR 14724",
                "relacionados": ["margem", "espaçamento"]
            },
            {
                "id": "item-1",
                "nome": "Citação direta",
                "definicao": "Reprodução literal de um trecho de outro autor, mantendo as palavras, vírgulas e pontuação originais. Deve aparecer entre aspas.",
                "norma": "NBR 10520",
                "relacionados": ["citação indireta", "referência"]
            },
            {
                "id": "item-2",
                "nome": "Citação indireta",
                "definicao": "Reescrita com suas próprias palavras de uma ideia de outro autor, mantendo o sentido original. Não usa aspas.",
                "norma": "NBR 10520",
                "relacionados": ["citação direta", "referência"]
            },
            {
                "id": "item-3",
                "nome": "Citação longa",
                "definicao": "Citação direta com mais de três linhas que deve ser destacada do texto principal com recuo de 4 cm, fonte 10 ou 11 pt e espaçamento simples.",
                "norma": "NBR 10520",
                "relacionados": ["citação direta", "recuo"]
            },
            {
                "id": "item-4",
                "nome": "Entrelinhas",
                "definicao": "Espaço vertical entre as linhas dentro de um parágrafo. A ABNT recomenda 1,5 para o corpo do texto e 1,0 para citações longas.",
                "norma": "NBR 14724, 5.2",
                "relacionados": ["espaçamento", "recuo"]
            },
            {
                "id": "item-5",
                "nome": "Espaçamento",
                "definicao": "Distância entre elementos na página, como entre parágrafos ou entre títulos e texto. A ABNT pede espaçamento simples (1,0) entre parágrafos no corpo.",
                "norma": "NBR 14724, 5.3",
                "relacionados": ["entrelinhas", "margem"]
            },
            {
                "id": "item-6",
                "nome": "Folha de rosto",
                "definicao": "Primeira página do trabalho que contém: autor, título, subtítulo, instituição, curso, nome do orientador e data. Deve estar em branco no verso.",
                "norma": "NBR 14724, 7.1.1",
                "relacionados": ["sumário", "paginação"]
            },
            {
                "id": "item-7",
                "nome": "Fonte",
                "definicao": "Tipo de letra usado no documento. A ABNT recomenda Times New Roman ou Arial em tamanho 12 pt para o corpo do texto.",
                "norma": "NBR 14724, 5.1",
                "relacionados": ["tamanho de fonte", "espaçamento"]
            },
            {
                "id": "item-8",
                "nome": "Indentação",
                "definicao": "Recuo da primeira linha de um parágrafo em relação às outras linhas. A ABNT pede recuo de 1,25 cm na primeira linha dos parágrafos.",
                "norma": "NBR 14724, 5.2",
                "relacionados": ["recuo", "alinhamento"]
            },
            {
                "id": "item-9",
                "nome": "Margem",
                "definicao": "Espaço em branco entre o texto e a borda da página. A ABNT pede: 3 cm (superior e esquerda) e 2 cm (inferior e direita).",
                "norma": "NBR 14724, 5.0",
                "relacionados": ["alinhamento", "espaçamento"]
            },
            {
                "id": "item-10",
                "nome": "Paginação",
                "definicao": "Numeração das páginas do trabalho, colocada no canto superior direito a 2 cm da borda. Começa a contar na folha de rosto, mas só aparece a partir da introdução.",
                "norma": "NBR 14724, 7.9",
                "relacionados": ["folha de rosto", "sumário"]
            },
            {
                "id": "item-11",
                "nome": "Recuo",
                "definicao": "Movimento de um trecho de texto para dentro em relação à margem esquerda. Usado em citações longas (4 cm) e na primeira linha de parágrafos (1,25 cm).",
                "norma": "NBR 14724, 5.2",
                "relacionados": ["indentação", "margem"]
            },
            {
                "id": "item-12",
                "nome": "Referência",
                "definicao": "Lista de todas as obras consultadas para a elaboração do trabalho, listadas em ordem alfabética no final do documento.",
                "norma": "NBR 6023",
                "relacionados": ["citação direta", "citação indireta"]
            },
            {
                "id": "item-13",
                "nome": "Resumo",
                "definicao": "Síntese do trabalho que apresenta os objetivos, métodos e conclusões principais em um único parágrafo. Deve ter entre 100 e 250 palavras.",
                "norma": "NBR 14724, 7.2",
                "relacionados": ["sumário", "introdução"]
            },
            {
                "id": "item-14",
                "nome": "Sumário",
                "definicao": "Lista das divisões, seções e outras partes do trabalho com indicação da página onde começam. Deve refletir a estrutura do documento.",
                "norma": "NBR 14724, 7.3",
                "relacionados": ["folha de rosto", "paginação"]
            },
            {
                "id": "item-15",
                "nome": "Tamanho de fonte",
                "definicao": "Medida da altura das letras em pontos (pt). A ABNT recomenda 12 pt para o corpo do texto, 10 ou 11 pt para notas de rodapé e citações longas.",
                "norma": "NBR 14724, 5.1",
                "relacionados": ["fonte", "espaçamento"]
            }
        ]
    }
    return glossario

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}
