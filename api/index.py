from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path
import json
import tempfile
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from checker import DocumentReader, ABNTRules, DocumentFixer

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

        # Extrair informações do documento
        reader = DocumentReader(contents)
        doc_info = reader.get_document_info()

        # Verificar regras ABNT
        checker = ABNTRules(doc_info)
        issues = checker.check_all()

        # Converter issues para JSON
        issues_json = [
            {
                'title': issue.title,
                'description': issue.description,
                'severity': issue.severity,
                'location': issue.location,
                'fixable': issue.fixable,
                'text_preview': issue.text_preview,
            }
            for issue in issues
        ]

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

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}
