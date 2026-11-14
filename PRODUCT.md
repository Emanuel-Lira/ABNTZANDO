# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Primary: Brazilian students writing academic papers (TCC, dissertations, papers) in Word (`.docx`) who must follow ABNT formatting before submitting. Their job is to get a document that complies with ABNT, and to understand why each item is flagged so they learn the norm.

## Product Purpose
ABNTzando validates and corrects ABNT formatting of Word documents. It runs deterministic checks against the ABNT rules and reports each violation with its evidence and an explanation. Success means a student uploads a document, understands every flagged item, and leaves with a formatting-compliant file without having their writing altered.

## Positioning
Deterministic rule checks, each item shown with its evidence and explanation so the student learns the norm, not just receives a verdict. Automatic correction is limited to formatting; the text of the student's work is never changed. Optional LLM analysis (`ANTHROPIC_API_KEY`) supports citation and reference review.

## Operating Context
- Input is a `.docx` uploaded through the single-page web UI (`public/index.html`).
- Results appear as itemized issue cards grouped by category: Margens, Fonte, Espaçamento, Referências, Organização, Recuo.
- Students typically work alone, on desktop or phone, near a submission deadline.
- Current stack: FastAPI (`api/index.py`) serving a static HTML/CSS/JS page; Word parsing in `checker/reader.py`; rules in `checker/rules.py`; fixes in `checker/fixer.py`; summary suggestions in `checker/sugestao_sumario.py`.
- Light and dark themes are supported; the theme choice is persisted per browser (`localStorage` key `abntzando.tema`).

## Capabilities and Constraints
- Checks and corrections cover font family (Times New Roman or Arial), text size (12 pt; 10 pt for legends; "Fonte:" line 10 or 12 pt), line spacing (1.5 in text, 1.0 in references), margins, section organization, and numbering. First-line indent is out of scope for now (`VERIFICAR_RECUO = False`).
- Zones `capa`, `sumario`, and `pre_textual` are ignored by the checks.
- User-facing copy is Brazilian Portuguese. ABNT terminology is fixed (for example "Referências", "Fonte:", "Sumário").
- Auto-fix must never alter the text content of the document.
- Without `ANTHROPIC_API_KEY`, the LLM-based analysis is unavailable; the deterministic checks still work.

## Brand Commitments
- The app name is "ABNTzando com Lala". Do not change it without approval.
- "Lala" is a personal nickname. It is not a persona and not a mascot. Do not add characters, mascots, or persona elements.
- All interface text and copy is pt-BR, with short sentences and no all-caps text.
- Terminology follows the ABNT standards: NBR 14724, NBR 6023, NBR 10520, NBR 6024, and NBR 6027.

## Evidence on Hand
- Golden documents and tests under `tests/` (including `tests/golden/`, currently untracked).
- ABNT reference material in `PRÁTICAS PRIVATIVAS (1).docx` and `public/data/glossario.json`.
- No testimonials, customer counts, or case studies exist. Do not invent any.

## Product Principles
- Explain every finding with its evidence so the student learns the norm.
- Fix formatting only; never change the student's words.
- Deterministic checks are the source of truth; AI assistance is additive and optional.
- Keep the flow simple enough for a stressed student near a deadline.

## Accessibility & Inclusion
- Target: WCAG 2.x Level AA.
- Minimum text contrast: 4.5:1.
- Focus must be visible on every interactive element.
- Respect `prefers-reduced-motion`: reduce or remove non-essential motion when the user asks for it.
