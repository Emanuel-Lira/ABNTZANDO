# ABNTzando

Uma ferramenta para validar e corrigir a formatação ABNT de documentos Word.

## Setup

### 1. Criar ambiente virtual

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Rodar localmente

```bash
uvicorn api.index:app --reload
```

Acesse `http://localhost:8000` no navegador.

## Estrutura

- `api/index.py` - FastAPI app principal
- `checker/reader.py` - Leitura de .docx
- `checker/rules.py` - Regras ABNT
- `checker/fixer.py` - Correção de documentos
- `checker/llm.py` - Análise com IA
- `public/index.html` - Frontend HTML
