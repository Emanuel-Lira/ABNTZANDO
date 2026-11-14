import re
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ReferenceIssue:
    id: str
    title: str
    description: str
    severity: str
    location: str = ""

class ReferencesValidator:
    """Valida formato e conteúdo da seção REFERÊNCIAS"""

    def __init__(self, paragraphs: List[Dict[str, Any]]):
        self.paragraphs = paragraphs
        self.issues: List[ReferenceIssue] = []

    def validate(self) -> List[ReferenceIssue]:
        """Executa todas as validações de referências"""
        self.issues = []

        # Encontrar seção de referências
        ref_section = self._find_references_section()

        if not ref_section['start']:
            self.issues.append(ReferenceIssue(
                id='ref.presente',
                title='Seção de referências não encontrada',
                description='Nenhuma seção REFERÊNCIAS foi encontrada no documento',
                severity='error',
                location='Documento inteiro'
            ))
            return self.issues

        # Extrair entradas de referências
        entries = self._extract_entries(ref_section)

        if not entries:
            self.issues.append(ReferenceIssue(
                id='ref.presente',
                title='Seção de referências vazia',
                description='A seção REFERÊNCIAS não contém nenhuma entrada',
                severity='error',
                location=f"Parágrafo {ref_section['start'] + 1}"
            ))
            return self.issues

        # Validar cada regra
        self._check_order(entries)
        self._check_sobrenome(entries)
        self._check_year(entries)
        self._check_separation(ref_section, entries)

        return self.issues

    def _find_references_section(self) -> Dict[str, Any]:
        """Encontra o parágrafo que inicia a seção REFERÊNCIAS"""
        for idx, para in enumerate(self.paragraphs):
            text = para.get('text', '').strip()

            if re.match(
                r'^(REFERÊNCIAS|Referências|REFERENCIAS|Referencias|REFERÊNCIAS\s+BIBLIOGRÁFICAS|Referências\s+Bibliográficas)',
                text,
                re.IGNORECASE
            ):
                return {'start': idx, 'title': text}

        return {'start': None, 'title': None}

    def _extract_entries(self, ref_section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrai as entradas de referência após o título"""
        entries = []

        if not ref_section['start']:
            return entries

        # Começar a partir do parágrafo após o título
        for idx in range(ref_section['start'] + 1, len(self.paragraphs)):
            para = self.paragraphs[idx]
            text = para.get('text', '').strip()

            # Pular parágrafos vazios
            if not text:
                continue

            # Parar se encontrar outra seção (ex: apêndice)
            if re.match(r'^(APÊNDICE|ANEXO|CONCLUSÃO|INTRODUÇÃO)', text, re.IGNORECASE):
                break

            entries.append({
                'text': text,
                'index': idx,
                'para_num': idx + 1
            })

        return entries

    def _check_order(self, entries: List[Dict[str, Any]]):
        """Verifica se entradas estão em ordem alfabética"""
        if len(entries) < 2:
            return

        # Extrair sobrenomes (primeira palavra maiúscula)
        sobrenomes = []
        for entry in entries:
            match = re.match(r'^([A-Z][A-Za-z]+)', entry['text'])
            if match:
                sobrenomes.append(match.group(1).lower())
            else:
                sobrenomes.append('')

        # Verificar se está ordenado
        sorted_sobrenomes = sorted(sobrenomes)
        if sobrenomes != sorted_sobrenomes:
            self.issues.append(ReferenceIssue(
                id='ref.ordem',
                title='Referências fora de ordem alfabética',
                description='As entradas de referência devem estar em ordem alfabética pelo sobrenome',
                severity='error',
                location=f"Referências (parágrafos {entries[0]['para_num']} a {entries[-1]['para_num']})"
            ))

    def _check_sobrenome(self, entries: List[Dict[str, Any]]):
        """Verifica se sobrenome está em maiúsculas"""
        issues_count = 0
        problematic_entries = []

        for entry in entries:
            text = entry['text']

            # Padrão esperado: SOBRENOME, Nome... ou SOBRENOME; Nome...
            if not re.match(r'^[A-Z][A-Z\s]+[,;]', text):
                issues_count += 1
                if issues_count <= 3:  # Limitar a 3 exemplos
                    problematic_entries.append(entry['para_num'])

        if issues_count > 0:
            localizacao = f"Referências ({issues_count} entradas)"
            if problematic_entries:
                localizacao += f", ex: parágrafos {', '.join(map(str, problematic_entries))}"

            self.issues.append(ReferenceIssue(
                id='ref.sobrenome',
                title='Sobrenome não em maiúsculas',
                description='O sobrenome deve estar totalmente em maiúsculas no início de cada referência',
                severity='error',
                location=localizacao
            ))

    def _check_year(self, entries: List[Dict[str, Any]]):
        """Verifica se ano está presente em cada entrada"""
        issues_count = 0
        problematic_entries = []

        for entry in entries:
            text = entry['text']

            # Procurar padrão de ano (entre 1800 e 2100)
            if not re.search(r'\b(19|20)\d{2}[a-z]?\b', text, re.IGNORECASE):
                issues_count += 1
                if issues_count <= 3:  # Limitar a 3 exemplos
                    problematic_entries.append(entry['para_num'])

        if issues_count > 0:
            localizacao = f"Referências ({issues_count} entradas)"
            if problematic_entries:
                localizacao += f", ex: parágrafos {', '.join(map(str, problematic_entries))}"

            self.issues.append(ReferenceIssue(
                id='ref.ano',
                title='Ano não encontrado',
                description='Cada referência deve conter o ano de publicação',
                severity='error',
                location=localizacao
            ))

    def _check_separation(self, ref_section: Dict[str, Any], entries: List[Dict[str, Any]]):
        """Verifica se entradas estão separadas por linha em branco"""
        if not ref_section['start'] or len(entries) < 2:
            return

        # Procurar parágrafos vazios entre entradas
        empty_count = 0
        start_idx = ref_section['start'] + 1

        for idx in range(start_idx, len(self.paragraphs)):
            para = self.paragraphs[idx]
            text = para.get('text', '').strip()

            # Se vazio, é separação
            if not text:
                empty_count += 1
            # Se for nova entrada (maiúsculas no início), checar se teve separação
            elif re.match(r'^[A-Z]', text) and empty_count == 0:
                # Encontrou entrada sem separação anterior
                pass

        # Avisar se houver falta de separação (simplificado)
        if empty_count == 0 and len(entries) > 1:
            self.issues.append(ReferenceIssue(
                id='ref.separacao',
                title='Referências não separadas por linha em branco',
                description='Recomenda-se separar cada entrada de referência com uma linha em branco',
                severity='warning',
                location=f"Referências (parágrafos {entries[0]['para_num']} a {entries[-1]['para_num']})"
            ))
