"""Filtro "Mostrar só corrigíveis" na página de resultados, num navegador real.

Roda a página public/index.html no Edge (headless) com um conjunto pequeno de achados
sintéticos e lê o resultado das verificações no DOM. Pula se o Edge não estiver instalado.
"""
import json
import pathlib
import re
import subprocess

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
HTML = RAIZ / 'public' / 'index.html'
EDGE = pathlib.Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')

ACHADOS = [
    {'title': 'Fonte errada', 'location': 'Capítulo 4', 'severity': 'error', 'fixable': True,
     'categoria': 'Fonte', 'esperado': '12 pt', 'encontrado': '10 pt'},
    {'title': 'Fonte manual', 'location': 'Capítulo 2', 'severity': 'error', 'fixable': False,
     'categoria': 'Fonte', 'esperado': None, 'encontrado': None},
    {'title': 'Referência fora de ordem', 'location': 'Referências', 'severity': 'error', 'fixable': False,
     'categoria': 'Referências', 'esperado': None, 'encontrado': None},
    {'title': 'Organização manual', 'location': 'Capítulo 1', 'severity': 'warning', 'fixable': False,
     'categoria': 'Organização', 'esperado': None, 'encontrado': None},
    {'title': 'Recuo corrigível', 'location': 'Capítulo 3', 'severity': 'warning', 'fixable': True,
     'categoria': 'Recuo', 'esperado': '1,25 cm', 'encontrado': '0 cm'},
]

# Verificações no navegador. Cada uma grava um valor em "resultado" para o teste ler.
VERIFICACOES = r"""
(function () {
  const r = {};
  const itens = () => Array.from(document.querySelectorAll('#issuesList [data-issue-idx]'));
  const grupos = () => Array.from(document.querySelectorAll('#issuesList .res-group'));
  const visivel = el => el.style.display !== 'none';
  const abertos = () => grupos().filter(g => g.classList.contains('is-open')).map(g => g.dataset.categoria).sort();
  const clicarGrupo = nome => grupos().find(g => g.dataset.categoria === nome)
      .querySelector('.res-group-toggle').click();
  const filtro = document.getElementById('filterCorrigiveis');

  // Estado inicial: o usuário abre Organização e fecha Fonte.
  if (abertos().includes('Fonte')) clicarGrupo('Fonte');
  if (!abertos().includes('Organização')) clicarGrupo('Organização');
  const estadoUsuario = abertos();

  // 1) Ligar o filtro esconde os itens não corrigíveis.
  filtro.checked = true;
  filtro.dispatchEvent(new Event('change'));
  r.naoCorrigiveisEscondidos = itens().filter(el => !visivel(el)).length;
  r.soCorrigiveisVisiveis = itens().filter(visivel).every(el =>
      el.querySelector('.res-tag.acao').textContent.trim() === 'Corrigível automaticamente');
  r.visiveisComFiltro = itens().filter(visivel).length;

  // 2) Grupos sem itens visíveis ficam escondidos; os demais abrem.
  r.gruposVisiveis = grupos().filter(visivel).map(g => g.dataset.categoria).sort();
  r.gruposComItensAbertos = grupos().filter(visivel).every(g => g.classList.contains('is-open'));
  r.contador = grupos().filter(visivel).map(g => g.querySelector('.res-group-count').textContent.trim());

  // 3) Desligar o filtro restaura a lista e o estado de cada grupo.
  filtro.checked = false;
  filtro.dispatchEvent(new Event('change'));
  r.todosVisiveisAposDesligar = itens().every(visivel);
  r.estadoRestaurado = JSON.stringify(abertos()) === JSON.stringify(estadoUsuario);
  r.contadorAposDesligar = grupos().map(g => g.querySelector('.res-group-count').textContent.trim());

  document.getElementById('saida').textContent = JSON.stringify(r);
})();
"""


def _pagina(achados):
    html = HTML.read_text(encoding='utf-8')
    html = html.replace('https://vlibras.gov.br/app/vlibras-plugin.js', 'file:///nao-existe/vlibras.js')
    dados = json.dumps({'status': 'success', 'issues': achados}, ensure_ascii=False)
    gancho = (
        '<pre id="saida" hidden></pre>'
        f'<script>displayResults({dados});</script>'
        f'<script>{VERIFICACOES}</script></body>'
    )
    return html.replace('</body>', gancho, 1)


@pytest.mark.skipif(not EDGE.exists(), reason='Microsoft Edge não encontrado')
def test_filtro_corrigiveis_filtra_abre_e_restaura(tmp_path):
    pagina = tmp_path / 'filtro.html'
    pagina.write_text(_pagina(ACHADOS), encoding='utf-8')
    saida = subprocess.run(
        [str(EDGE), '--headless=new', '--disable-gpu', '--dump-dom', pagina.as_uri()],
        capture_output=True, timeout=120,
    ).stdout.decode('utf-8', errors='replace')
    casamento = re.search(r'<pre id="saida"[^>]*>(.*?)</pre>', saida, re.S)
    assert casamento, 'a página não gravou o resultado das verificações'
    r = json.loads(casamento.group(1))

    # Filtro ligado esconde os não corrigíveis (3 dos 5 achados)
    assert r['naoCorrigiveisEscondidos'] == 3
    assert r['soCorrigiveisVisiveis'] is True
    assert r['visiveisComFiltro'] == 2

    # Só os grupos com corrigíveis aparecem, e todos abrem
    assert r['gruposVisiveis'] == ['Fonte', 'Recuo']
    assert r['gruposComItensAbertos'] is True
    assert r['contador'] == ['1 de 2', '1 de 1']

    # Desligado: tudo volta e cada grupo volta ao estado que o usuário tinha
    assert r['todosVisiveisAposDesligar'] is True
    assert r['estadoRestaurado'] is True
    assert r['contadorAposDesligar'] == ['2', '1', '1', '1']
