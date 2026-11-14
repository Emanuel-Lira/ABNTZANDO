from typing import List, Dict, Any
from dataclasses import dataclass
from .citacoes import VerificadorCitacoes
from .sumario import VerificadorSumario
from .zone_classifier import ZoneClassifier
from .references_validator import ReferencesValidator

@dataclass
class Issue:
    title: str
    description: str
    severity: str  # 'error' ou 'warning'
    location: str
    fixable: bool
    fix_type: str = None  # tipo de correção a aplicar
    text_preview: str = None  # preview do texto do parágrafo

class ABNTRules:
    """Verifica documento contra as normas ABNT NBR 14724"""

    # Valores ABNT padrão
    MARGIN_TOP = 3.0  # cm
    MARGIN_BOTTOM = 2.0  # cm
    MARGIN_LEFT = 3.0  # cm
    MARGIN_RIGHT = 2.0  # cm

    FONT_NAMES = ['Times New Roman', 'Arial']
    FONT_SIZE = 12  # pt

    LINE_SPACING = 1.5
    LINE_SPACING_CITATIONS = 1.0

    FIRST_LINE_INDENT = 1.25  # cm

    def __init__(self, document_info: Dict[str, Any]):
        self.document_info = document_info
        self.issues: List[Issue] = []

        # Classificar parágrafos em zonas
        paragraphs = document_info.get('paragraphs', [])
        self.zone_classifier = ZoneClassifier(paragraphs)
        self.zones = self.zone_classifier.get_all_zones()

    def _get_zone(self, idx: int) -> str:
        """Retorna a zona de um parágrafo"""
        return self.zones.get(idx, 'corpo')

    def _get_text_preview(self, text: str, max_length: int = 100) -> str:
        """Retorna um preview do texto com tamanho máximo"""
        text = text.strip()
        if len(text) > max_length:
            return text[:max_length] + '...'
        return text

    def check_all(self) -> List[Issue]:
        """Executa todas as verificações"""
        self.issues = []

        self.check_margins()
        self.check_fonts_comprehensive()
        self.check_spacing_comprehensive()
        self.check_indentation_comprehensive()
        self.check_alignment()
        self.check_citacoes()
        self.check_sumario()
        self.check_references_format()

        return self.issues

    def check_margins(self):
        """Verifica se as margens estão corretas"""
        margins = self.document_info.get('margins', {})

        if not margins:
            self.issues.append(Issue(
                title='Margens não detectadas',
                description='Não foi possível detectar as margens do documento.',
                severity='warning',
                location='Documento inteiro',
                fixable=False
            ))
            return

        checks = [
            ('top', self.MARGIN_TOP, 'superior'),
            ('left', self.MARGIN_LEFT, 'esquerda'),
            ('bottom', self.MARGIN_BOTTOM, 'inferior'),
            ('right', self.MARGIN_RIGHT, 'direita'),
        ]

        for margin_key, expected_value, margin_name in checks:
            actual_value = margins.get(margin_key, 0)
            if abs(actual_value - expected_value) > 0.1:
                self.issues.append(Issue(
                    title=f'Margem {margin_name} incorreta',
                    description=f'Esperado: {expected_value} cm | Encontrado: {actual_value:.2f} cm',
                    severity='error',
                    location='Configuração de página',
                    fixable=True,
                    fix_type='margin'
                ))

    def check_fonts(self):
        """Verifica se a fonte está correta (mantido para compatibilidade)"""
        self.check_fonts_comprehensive()

    def check_fonts_comprehensive(self):
        """Verifica se a fonte está correta - todos os parágrafos"""
        paragraphs = self.document_info.get('paragraphs', [])

        font_issues = {}
        size_issues = {}

        for para in paragraphs:
            if not para['text'].strip() or len(para['text']) < 5:
                continue

            font_info = para.get('font_info', {})
            font_name = font_info.get('font_name')
            font_size = font_info.get('font_size')

            # Detectar todas as fontes não recomendadas
            if font_name and font_name not in self.FONT_NAMES and font_name != 'Calibri':
                if font_name not in font_issues:
                    font_issues[font_name] = para["index"] + 1

            # Detectar todos os tamanhos incorretos
            if font_size and font_size != self.FONT_SIZE:
                if font_size not in size_issues:
                    size_issues[font_size] = para["index"] + 1

        # Adicionar issues de fonte
        for font_name, para_num in list(font_issues.items())[:3]:  # Limitar a 3 issues
            para = paragraphs[para_num - 1] if para_num - 1 < len(paragraphs) else None
            self.issues.append(Issue(
                title='Fonte não recomendada',
                description=f'Encontrado: {font_name} | Esperado: Times New Roman ou Arial',
                severity='error',
                location=f'Parágrafo {para_num}',
                fixable=False,
                fix_type='font',
                text_preview=self._get_text_preview(para['text']) if para else None
            ))

        # Adicionar issues de tamanho
        for font_size, para_num in list(size_issues.items())[:3]:  # Limitar a 3 issues
            para = paragraphs[para_num - 1] if para_num - 1 < len(paragraphs) else None
            self.issues.append(Issue(
                title='Tamanho de fonte incorreto',
                description=f'Encontrado: {font_size} pt | Esperado: {self.FONT_SIZE} pt',
                severity='error',
                location=f'Parágrafo {para_num}',
                fixable=False,
                fix_type='font_size',
                text_preview=self._get_text_preview(para['text']) if para else None
            ))

    def check_spacing(self):
        """Verifica espaçamento entre linhas (mantido para compatibilidade)"""
        self.check_spacing_comprehensive()

    def check_spacing_comprehensive(self):
        """Verifica espaçamento entre linhas - todos os parágrafos"""
        paragraphs = self.document_info.get('paragraphs', [])
        spacing_issues = 0

        for para in paragraphs:
            if not para['text'].strip():
                continue

            spacing = para.get('spacing', {})
            line_spacing = spacing.get('line_spacing')

            if line_spacing is not None:
                if line_spacing is not None and abs(line_spacing - self.LINE_SPACING) > 0.1:
                    if spacing_issues < 3:  # Limitar a 3 issues
                        self.issues.append(Issue(
                            title='Espaçamento entre linhas incorreto',
                            description=f'Esperado: {self.LINE_SPACING} | Encontrado: {line_spacing}',
                            severity='error',
                            location=f'Parágrafo {para["index"] + 1}',
                            fixable=True,
                            fix_type='line_spacing',
                            text_preview=self._get_text_preview(para['text'])
                        ))
                        spacing_issues += 1

    def check_indentation(self):
        """Verifica indentação de primeira linha (mantido para compatibilidade)"""
        self.check_indentation_comprehensive()

    def check_indentation_comprehensive(self):
        """Verifica indentação de primeira linha - todos os parágrafos"""
        paragraphs = self.document_info.get('paragraphs', [])
        indent_issues = 0

        for para in paragraphs:
            if not para['text'].strip() or len(para['text']) < 10:
                continue

            indent = para.get('indentation', {})
            first_line = indent.get('first_line', 0)

            # Verifica se precisa ter indentação (parágrafos de corpo)
            if first_line == 0:
                if indent_issues < 3:  # Limitar a 3 issues
                    self.issues.append(Issue(
                        title='Indentação de primeira linha ausente',
                        description=f'Esperado: {self.FIRST_LINE_INDENT} cm | Encontrado: {first_line:.2f} cm',
                        severity='error',
                        location=f'Parágrafo {para["index"] + 1}',
                        fixable=False,
                        fix_type='indentation',
                        text_preview=self._get_text_preview(para['text'])
                    ))
                    indent_issues += 1
            elif abs(first_line - self.FIRST_LINE_INDENT) > 0.2:
                if indent_issues < 3:  # Limitar a 3 issues
                    self.issues.append(Issue(
                        title='Indentação de primeira linha incorreta',
                        description=f'Esperado: {self.FIRST_LINE_INDENT} cm | Encontrado: {first_line:.2f} cm',
                        severity='error',
                        location=f'Parágrafo {para["index"] + 1}',
                        fixable=False,
                        fix_type='indentation',
                        text_preview=self._get_text_preview(para['text'])
                    ))
                    indent_issues += 1

    def check_alignment(self):
        """Verifica alinhamento do texto"""
        paragraphs = self.document_info.get('paragraphs', [])
        align_issues = 0

        for para in paragraphs:
            if not para['text'].strip():
                continue

            alignment = para.get('alignment')

            # ABNT recomenda alinhamento justificado ou esquerda
            if alignment and alignment not in ['None', '0']:
                if align_issues < 2:  # Limitar a 2 issues
                    align_name = 'Centralizado' if 'CENTER' in str(alignment).upper() else 'Direita'
                    self.issues.append(Issue(
                        title=f'Alinhamento {align_name}',
                        description=f'Recomenda-se alinhamento justificado ou à esquerda | Encontrado: {align_name}',
                        severity='warning',
                        location=f'Parágrafo {para["index"] + 1}',
                        fixable=False,
                        fix_type='alignment',
                        text_preview=self._get_text_preview(para['text'])
                    ))
                    align_issues += 1

    def check_citacoes(self):
        """Verifica citações cruzadas"""
        try:
            paragraphs = self.document_info.get('paragraphs', [])
            if not paragraphs:
                return

            # Reconstruir texto completo
            texto_completo = '\n\n'.join([p['text'] for p in paragraphs])

            # Usar verificador de citações
            verificador = VerificadorCitacoes()
            problemas = verificador.verificar(texto_completo)

            # Adicionar problemas encontrados
            for problema in problemas:
                self.issues.append(Issue(
                    title=problema['titulo'],
                    description=problema['descricao'],
                    severity=problema['severity'],
                    location=problema.get('paragrafos', ['Texto'])[0] if 'paragrafos' in problema else 'Referências',
                    fixable=False,
                    fix_type='citation',
                    text_preview=None
                ))
        except Exception as e:
            # Silenciosamente ignorar erros de citação
            pass

    def check_sumario(self):
        """Verifica sumário contra títulos do documento"""
        try:
            paragraphs = self.document_info.get('paragraphs', [])
            if not paragraphs:
                return

            # Reconstruir texto completo
            texto_completo = '\n\n'.join([p['text'] for p in paragraphs])

            # Usar verificador de sumário
            verificador = VerificadorSumario(self.document_info)
            problemas = verificador.verificar(texto_completo)

            # Adicionar problemas encontrados
            for problema in problemas:
                self.issues.append(Issue(
                    title=problema['titulo'],
                    description=problema['descricao'],
                    severity=problema['severity'],
                    location='Sumário',
                    fixable=False,
                    fix_type='table_of_contents',
                    text_preview=None
                ))
        except Exception as e:
            # Silenciosamente ignorar erros de sumário
            pass

    def check_references_format(self):
        """Verifica formato da seção de REFERÊNCIAS"""
        try:
            paragraphs = self.document_info.get('paragraphs', [])
            if not paragraphs:
                return

            # Usar validador de referências
            validator = ReferencesValidator(paragraphs)
            ref_issues = validator.validate()

            # Converter para Issue
            for ref_issue in ref_issues:
                self.issues.append(Issue(
                    title=ref_issue.title,
                    description=ref_issue.description,
                    severity=ref_issue.severity,
                    location=ref_issue.location,
                    fixable=False,
                    fix_type='references',
                    text_preview=None
                ))
        except Exception as e:
            # Silenciosamente ignorar erros de referências
            pass
