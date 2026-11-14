import re
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class OrganizationIssue:
    id: str
    title: str
    description: str
    severity: str
    location: str = ""

class OrganizationValidator:
    """Valida estrutura e organização do documento"""

    def __init__(self, paragraphs: List[Dict[str, Any]]):
        self.paragraphs = paragraphs
        self.issues: List[OrganizationIssue] = []

    def validate(self) -> List[OrganizationIssue]:
        """Executa todas as validações de organização"""
        self.issues = []

        # Validar numeração de títulos
        self._check_numbering()

        # Validar seções obrigatórias
        self._check_required_sections()

        return self.issues

    def _check_numbering(self):
        """Verifica se títulos numerados não têm saltos ou pulos de nível"""
        titles = self._extract_numbered_titles()

        if not titles:
            # Sem títulos numerados é ok (pode ser documento simples)
            return

        # Verificar saltos (ex: 1, 2, 3, 5 - falta 4)
        # Verificar pulos de nível (ex: 1, 1.1, 1.1.1, 2 - falta 1.2)

        issues = []

        for i in range(len(titles) - 1):
            current = titles[i]
            next_title = titles[i + 1]

            # Comparar numerações
            violation = self._check_sequence(current['number'], next_title['number'])

            if violation:
                issues.append({
                    'current': current['number'],
                    'next': next_title['number'],
                    'current_para': current['para_num'],
                    'next_para': next_title['para_num']
                })

        if issues:
            problem_desc = []
            for issue in issues[:3]:  # Mostrar até 3 exemplos
                problem_desc.append(f"{issue['current']} → {issue['next']}")

            self.issues.append(OrganizationIssue(
                id='org.numeracao',
                title='Numeração de títulos com saltos',
                description=f"Títulos numerados com saltos ou pulos de nível. Exemplos: {', '.join(problem_desc)}",
                severity='error',
                location=f"Títulos (parágrafos {issues[0]['current_para']} em diante)"
            ))

    def _check_sequence(self, current: str, next_num: str) -> bool:
        """Verifica se a sequência de numeração é válida"""
        current_parts = [int(x) for x in current.split('.')]
        next_parts = [int(x) for x in next_num.split('.')]

        # Se próximo tem menos níveis (ex: 1.1 → 2)
        if len(next_parts) < len(current_parts):
            # Último número do próximo deve ser current[0] + 1
            if len(next_parts) == 1:
                expected = current_parts[0] + 1
                return next_parts[0] != expected
            return False

        # Se próximo tem mais níveis (ex: 1 → 1.1)
        if len(next_parts) > len(current_parts):
            # Prefixo deve ser igual
            if next_parts[:len(current_parts)] != current_parts:
                return True  # Violação
            # Próximo nível deve ser 1
            return next_parts[len(current_parts)] != 1

        # Mesmo número de níveis
        # Verificar se incrementou corretamente
        for i in range(len(current_parts) - 1):
            if current_parts[i] != next_parts[i]:
                return True  # Violação em nível anterior

        # Último nível deve incrementar em 1
        return next_parts[-1] != current_parts[-1] + 1

    def _extract_numbered_titles(self) -> List[Dict[str, Any]]:
        """Extrai títulos numerados do documento"""
        titles = []

        for idx, para in enumerate(self.paragraphs):
            text = para.get('text', '').strip()

            # Padrão: "1.", "1.1.", "2.3.1.", etc seguido de espaço
            match = re.match(r'^([\d.]+\.?)\s+(.+)$', text)

            if match:
                number = match.group(1).rstrip('.')

                # Validar formato (números separados por ponto)
                if re.match(r'^[\d.]+$', number):
                    titles.append({
                        'number': number,
                        'text': match.group(2),
                        'index': idx,
                        'para_num': idx + 1
                    })

        return titles

    def _check_required_sections(self):
        """Verifica se seções obrigatórias estão presentes"""
        text_completo = '\n'.join([p.get('text', '').lower() for p in self.paragraphs])

        tem_introducao = bool(re.search(r'\bintroduç[aã]o\b', text_completo))
        tem_referencias = bool(re.search(r'\breferências?\b', text_completo))

        if not tem_introducao:
            self.issues.append(OrganizationIssue(
                id='org.secoes',
                title='Introdução não encontrada',
                description='Recomenda-se que o documento tenha uma seção de Introdução',
                severity='warning',
                location='Documento inteiro'
            ))

        if not tem_referencias:
            self.issues.append(OrganizationIssue(
                id='org.secoes',
                title='Referências não encontradas',
                description='Recomenda-se que o documento tenha uma seção de Referências',
                severity='warning',
                location='Documento inteiro'
            ))
