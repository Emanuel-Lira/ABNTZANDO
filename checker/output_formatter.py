from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import re

@dataclass
class FormattedIssue:
    """Issue formatada conforme spec"""
    id: str
    categoria: str
    severidade: str
    titulo: str
    localizacao: str
    esperado: str
    encontrado: str
    evidencia: Optional[str] = None
    corrigivel: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'categoria': self.categoria,
            'severidade': self.severidade,
            'titulo': self.titulo,
            'localizacao': self.localizacao,
            'esperado': self.esperado,
            'encontrado': self.encontrado,
            'evidencia': self.evidencia,
            'corrigivel': self.corrigivel,
        }

class LineCalculator:
    """Calcula linhas dentro de parágrafos"""

    CHARS_PER_LINE = 80  # Estimativa de caracteres por linha

    def __init__(self, paragraphs: List[Dict[str, Any]]):
        self.paragraphs = paragraphs
        self._line_map = self._build_line_map()

    def _build_line_map(self) -> Dict[int, Dict[str, Any]]:
        """Mapeia cada parágrafo com seu número de linhas"""
        line_map = {}

        for idx, para in enumerate(self.paragraphs):
            text = para.get('text', '')

            # Contar linhas baseado em quebras e comprimento
            lines = self._count_lines(text)

            line_map[idx] = {
                'lines': lines,
                'text': text
            }

        return line_map

    def _count_lines(self, text: str) -> int:
        """Conta número estimado de linhas no texto"""
        if not text:
            return 1

        # Contar quebras de linha explícitas
        explicit_breaks = text.count('\n')

        # Calcular quebras por comprimento (assume ~80 chars por linha)
        length_breaks = max(0, len(text) // self.CHARS_PER_LINE)

        return max(1, explicit_breaks + length_breaks + 1)

    def get_line_range(self, para_idx: int) -> tuple:
        """Retorna (primeira_linha, última_linha) do parágrafo"""
        if para_idx not in self._line_map:
            return (1, 1)

        lines = self._line_map[para_idx]['lines']
        return (1, lines)

    def format_location_with_lines(self, para_indices: List[int]) -> str:
        """Formata localização com parágrafo e linhas

        Ex: "Parágrafo 5 (linhas 2-4), Parágrafo 7 (linhas 1-3)"
        """
        locations = []

        for idx in para_indices:
            if idx not in self._line_map:
                continue

            first_line, last_line = self.get_line_range(idx)
            para_num = idx + 1

            if first_line == last_line:
                location = f"Parágrafo {para_num} (linha {first_line})"
            else:
                location = f"Parágrafo {para_num} (linhas {first_line}-{last_line})"

            locations.append(location)

        return ", ".join(locations)

def formatar_valor(numero: Any, unidade: str = "") -> str:
    """Formata valor com vírgula decimal e unidade

    Exemplos:
    - formatar_valor(1.5) → "1,5"
    - formatar_valor(12.0) → "12"
    - formatar_valor(3.0, "cm") → "3 cm"
    - formatar_valor(1.25, "cm") → "1,25 cm"
    """
    if numero is None:
        return ""

    try:
        # Converter para float se for string numérica
        if isinstance(numero, str):
            numero = float(numero)

        # Formatar com 2 casas decimais
        texto = f"{numero:.2f}"

        # Remover zeros desnecessários
        texto = texto.rstrip('0').rstrip('.')

        # Converter ponto para vírgula
        texto = texto.replace('.', ',')

        # Adicionar unidade
        if unidade:
            return f"{texto} {unidade}".strip()

        return texto
    except:
        return str(numero)

class OutputFormatter:
    """Formata issues para saída JSON conforme spec"""

    # Mapeamento de fix_type para categoria
    CATEGORIA_MAP = {
        'margin': 'Margens',
        'font': 'Fonte',
        'font_size': 'Fonte',
        'line_spacing': 'Espaçamento',
        'indentation': 'Indentação',
        'alignment': 'Alinhamento',
        'citation': 'Citações',
        'table_of_contents': 'Sumário',
        'references': 'Referências',
        'organization': 'Organização',
    }

    # Ordem de categorias na saída
    CATEGORIA_ORDER = [
        'Margens',
        'Fonte',
        'Espaçamento',
        'Referências',
        'Organização',
        'Citações',
        'Sumário',
        'Indentação',
        'Alinhamento',
    ]

    def __init__(self, paragraphs: List[Dict[str, Any]]):
        self.paragraphs = paragraphs
        self.line_calc = LineCalculator(paragraphs)

    def aggregate_and_format(self, issues: List[Any]) -> List[Dict[str, Any]]:
        """Agrega issues por regra e formata para saída

        Returns: lista de FormattedIssue formatadas
        """
        # Agrupar por ID de regra
        agregados: Dict[str, Dict[str, Any]] = {}

        for issue in issues:
            # Usar titulo como ID provisório se não houver fix_type
            rule_id = self._get_rule_id(issue)

            if rule_id not in agregados:
                agregados[rule_id] = {
                    'rule_id': rule_id,
                    'title': issue.title,
                    'description': issue.description,
                    'severity': issue.severity,
                    'fix_type': issue.fix_type,
                    'localizacoes': [],  # Para acumular parágrafos
                    'first_issue': issue,  # Guardar primeiro issue como referência
                }

            # Extrair número do parágrafo da localização
            para_num = self._extract_paragraph_number(issue.location)
            if para_num is not None:
                agregados[rule_id]['localizacoes'].append(para_num - 1)  # Converter para índice

        # Converter para FormattedIssue
        formatted_issues = []

        for rule_id, data in agregados.items():
            # Remover duplicatas de localização
            localizacoes_unicas = sorted(set(data['localizacoes']))

            # Formatar localização com linhas
            localizacao_str = self.line_calc.format_location_with_lines(localizacoes_unicas)

            # Extrair esperado e encontrado da description
            esperado, encontrado = self._extract_values_from_description(data['description'])

            # Determinar categoria
            categoria = self.CATEGORIA_MAP.get(data['fix_type'], 'Outro')

            # Criar issue formatada
            formatted = FormattedIssue(
                id=rule_id,
                categoria=categoria,
                severidade='erro' if data['severity'] == 'error' else 'aviso',
                titulo=data['title'],
                localizacao=localizacao_str,
                esperado=esperado,
                encontrado=encontrado,
                evidencia=data['first_issue'].text_preview,
                corrigivel=data['first_issue'].fixable,
            )

            formatted_issues.append(formatted)

        # Ordenar por categoria
        formatted_issues.sort(
            key=lambda x: (
                self.CATEGORIA_ORDER.index(x.categoria) if x.categoria in self.CATEGORIA_ORDER else 999,
                0 if x.severidade == 'erro' else 1,  # Erros antes de avisos
                x.titulo
            )
        )

        return formatted_issues

    def _get_rule_id(self, issue: Any) -> str:
        """Gera um ID único para agrupar issues similares"""
        # Usar fix_type como base
        if issue.fix_type:
            # Se for margin, diferenciar por direção (top, left, etc)
            if 'margin' in issue.title.lower():
                if 'superior' in issue.description.lower():
                    return 'pag.margens.top'
                elif 'inferior' in issue.description.lower():
                    return 'pag.margens.bottom'
                elif 'esquerda' in issue.description.lower():
                    return 'pag.margens.left'
                elif 'direita' in issue.description.lower():
                    return 'pag.margens.right'

            return issue.fix_type

        # Fallback: usar título
        return issue.title.lower().replace(' ', '_')

    def _extract_paragraph_number(self, location: str) -> Optional[int]:
        """Extrai número do parágrafo da string de localização

        Ex: "Parágrafo 5" → 5
        Ex: "Parágrafo 5 a 7" → 5
        """
        match = re.search(r'Parágrafo\s+(\d+)', location)
        if match:
            return int(match.group(1))

        return None

    def _extract_values_from_description(self, description: str) -> tuple:
        """Extrai esperado e encontrado da description

        Ex: "Esperado: 1.5 | Encontrado: 1.0" → ("1,5", "1,0")
        """
        esperado = ""
        encontrado = ""

        # Padrão: "Esperado: X | Encontrado: Y"
        match = re.search(r'Esperado:\s*([^|]+)\s*\|\s*Encontrado:\s*(.+)', description)
        if match:
            esperado_raw = match.group(1).strip()
            encontrado_raw = match.group(2).strip()

            # Tentar extrair números
            num_match_e = re.search(r'(\d+\.?\d*)', esperado_raw)
            num_match_c = re.search(r'(\d+\.?\d*)', encontrado_raw)

            if num_match_e:
                num_e = float(num_match_e.group(1))
                esperado = formatar_valor(num_e)
            else:
                esperado = esperado_raw

            if num_match_c:
                num_c = float(num_match_c.group(1))
                encontrado = formatar_valor(num_c)
            else:
                encontrado = encontrado_raw
        else:
            # Se não encontrar padrão, usar description completa
            encontrado = description

        return (esperado, encontrado)
