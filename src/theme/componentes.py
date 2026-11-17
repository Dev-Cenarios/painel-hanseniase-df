"""A casca do hansepe: CSS e os pedaços de HTML (cabeçalho, cards, títulos)."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path

from . import cores, tokens


def css_base() -> str:
    """CSS dos cards e do básico. Injetar uma vez só."""
    return f"""
<style>
/* o fundo sai da cor do texto, aí funciona nos dois temas */
:root {{
  --fonte: {tokens.FONTE};
  --borda: {tokens.BORDA};
  --sombra: {tokens.SOMBRA_REPOUSO};
  --sombra-hover: {tokens.SOMBRA_HOVER};
  --sombra-ativo: {tokens.SOMBRA_ATIVO};
  --superficie: color-mix(in srgb, currentColor {tokens.MISTURA_CARD}, transparent);
  --superficie-topo: color-mix(in srgb, currentColor {tokens.MISTURA_CARD_TOPO}, transparent);
}}


.kpi-card {{
  --kpi-accent: #0F766E;
  position: relative;
  overflow: hidden;
  border-radius: {tokens.RAIO_CARD};
  border: var(--borda);
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: var(--sombra);
  color: inherit;
  font-family: var(--fonte);
  transition: transform .14s ease, box-shadow .14s ease, border-color .14s ease;
}}
.kpi-card::after {{
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: {tokens.RAIO_CARD};
  opacity: 0;
  pointer-events: none;
  transition: opacity .14s ease;
  background:
    radial-gradient(220px 120px at 15% 10%,
      color-mix(in srgb, var(--kpi-accent) 22%, transparent), transparent 65%),
    radial-gradient(220px 120px at 85% 0%,
      color-mix(in srgb, var(--kpi-accent) 8%, transparent), transparent 55%);
}}
.kpi-card:hover {{
  border-color: color-mix(in srgb, currentColor 24%, transparent);
  box-shadow: var(--sombra-hover);
}}
.kpi-card:hover::after {{ opacity: 1; }}
.kpi-card.is-selected {{
  border-color: color-mix(in srgb, var(--kpi-accent) 60%, transparent);
  box-shadow: var(--sombra-ativo),
              0 0 0 2px color-mix(in srgb, var(--kpi-accent) 28%, transparent);
}}
.kpi-card.is-selected::after {{ opacity: 1; }}
.kpi-card:focus-visible {{
  outline: none;
  border-color: color-mix(in srgb, var(--kpi-accent) 55%, transparent);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--kpi-accent) 35%, transparent),
              var(--sombra-hover);
}}

.kpi-inner {{
  position: relative;
  z-index: 1;
  display: flex;
  gap: {tokens.GAP};
  align-items: center;
  padding: {tokens.PADDING};
  min-width: 0;
}}
.kpi-accent {{
  flex: 0 0 auto;
  width: 9px;
  height: 46px;
  border-radius: {tokens.RAIO_PILL};
  background: var(--kpi-accent);
}}
.kpi-text {{ min-width: 0; flex: 1 1 auto; }}
/* disco do ícone, no canto do card */
.kpi-icon {{
  position: absolute;
  top: 10px;
  right: 10px;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--kpi-accent);
  background: color-mix(in srgb, var(--kpi-accent) 12%, transparent);
}}
.kpi-icon svg {{ width: 16px; height: 16px; }}
.kpi-card:has(.kpi-icon) .kpi-title {{ padding-right: 34px; }}
/* título do card sempre com 2 linhas, pra alinhar a fileira */
.kpi-title {{
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .74;
  margin-bottom: 3px;
  line-height: 1.25;
  min-height: 2.5em;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}}
/* no celular, 2 cards por linha */
@media (max-width: 639px) {{
  .kpi-title {{
    -webkit-line-clamp: 3;
    min-height: 3.75em;
  }}
}}
.kpi-value {{
  font-size: {tokens.TEXTO_XL};
  font-weight: 900;
  letter-spacing: -.2px;
  line-height: 1.03;
  color: color-mix(in srgb, var(--kpi-accent) 72%, currentColor 28%);
}}
.kpi-sub {{
  font-size: {tokens.TEXTO_XS};
  opacity: .70;
  margin-top: 3px;
  /* a linha do subtítulo existe mesmo vazia (alinha os cards) */
  line-height: 1.6;
  min-height: 1.6em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.kpi-delta {{ margin-top: 5px; font-size: {tokens.TEXTO_XS}; font-weight: 800; }}
.kpi-bom  {{ color: color-mix(in srgb, {tokens.BOM} 60%, currentColor); }}
.kpi-ruim {{ color: color-mix(in srgb, {tokens.RUIM} 60%, currentColor); }}
.kpi-igual {{ opacity: {tokens.NEUTRO_OPACIDADE}; }}

@media (prefers-reduced-motion: reduce) {{
  .kpi-card {{ transition: none !important; transform: none !important; }}
}}
</style>
"""


def formatar_inteiro(valor: float | None) -> str:
    if valor is None:
        return "—"
    return f"{valor:,.0f}".replace(",", ".")


def formatar_decimal(valor: float | None, casas: int = 2) -> str:
    if valor is None:
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def delta(
    atual: float | None,
    anterior: float | None,
    *,
    taxa: bool = False,
    bom_se_cai: bool = True,
    sufixo: str = "vs ano anterior",
) -> str:
    """Variação contra o ano anterior (verde ou vermelho conforme bom_se_cai)."""
    if atual is None or anterior is None:
        return ""

    diferenca = atual - anterior
    if abs(diferenca) < 1e-9:
        return f'<div class="kpi-delta kpi-igual">≈ sem variação {escape(sufixo)}</div>'

    caiu = diferenca < 0
    classe = "kpi-bom" if caiu == bom_se_cai else "kpi-ruim"
    seta = "↓" if caiu else "↑"
    texto = formatar_decimal(abs(diferenca)) if taxa else formatar_inteiro(abs(diferenca))
    return f'<div class="kpi-delta {classe}">{seta} {texto} {escape(sufixo)}</div>'


def kpi_card(
    titulo: str,
    valor: str,
    *,
    cor: str,
    subtitulo: str | None = None,
    badge_delta: str = "",
    selecionado: bool = False,
    ajuda: str = "",
    icone: str = "",
) -> str:
    """Card de KPI. ``icone`` é o miolo de um SVG 24x24; vazio, fica sem ícone."""
    classes = "kpi-card is-selected" if selecionado else "kpi-card"
    # a explicação aparece passando o mouse
    titulo_ajuda = f' title="{escape(ajuda)}"' if ajuda else ""
    # o subtítulo existe mesmo vazio, pra todos os cards terem a mesma altura
    sub = f'<div class="kpi-sub">{escape(subtitulo) if subtitulo else ""}</div>'
    # o SVG vem do pack, não do usuário
    glifo = (
        '<div class="kpi-icon"><svg viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{icone}</svg></div>'
        if icone
        else ""
    )

    return (
        f'<div class="{classes}" '
        f'style="--kpi-accent:{escape(cor)};'
        f'--kpi-accent-escuro:{escape(cores.para_fundo_escuro(cor))};"'
        f'{titulo_ajuda}>'
        f'<div class="kpi-inner">'
        f'<div class="kpi-accent"></div>'
        f'<div class="kpi-text">'
        f'<div class="kpi-title">{escape(titulo)}</div>'
        f'<div class="kpi-value">{escape(valor)}</div>'
        f"{sub}{badge_delta}"
        f"</div>{glifo}</div></div>"
    )

def css_layout() -> str:
    """CSS do layout (mexe em seletores internos do Streamlit, pode quebrar ao atualizar)."""
    return f"""
<style>
/* barra lateral, só quando tem espaço */
/* só esmaece se demorar */
[data-stale] {{
  transition: opacity .12s ease;
}}
[data-stale="true"] {{
  opacity: .45;
  transition-delay: .15s;
}}
@media (prefers-reduced-motion: reduce) {{
  [data-stale] {{ transition: none; }}
}}

/* o <style> injetado não ocupa espaço */
[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style:only-child) {{
  display: none;
}}

/* respiro da página */
[data-testid="stMainBlockContainer"] {{
  padding: {tokens.PAGINA_TOPO} {tokens.PAGINA_LADOS} {tokens.PAGINA_BASE} !important;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{
    padding-left: {tokens.PAGINA_LADOS_ESTREITO} !important;
    padding-right: {tokens.PAGINA_LADOS_ESTREITO} !important;
  }}
}}

/* deixa as colunas quebrarem em tela estreita */
.st-key-faixa-kpis [data-testid="stHorizontalBlock"] {{
  flex-wrap: wrap;
  /* espaço depois da faixa de KPIs */
  margin-bottom: 32px;
}}
.st-key-faixa-kpis [data-testid="stColumn"] {{
  /* 150px pra caberem os 6 lado a lado */
  min-width: 150px;
}}

/* título de painel */
.titulo-painel {{
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .85;
  line-height: 1.3;
  margin: 0 0 6px;
}}

.sinan-intro {{
  position: relative;
  overflow: hidden;
  display: grid;
  /* cabeçalho: bandeira · título · marca */
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  padding: {tokens.PADDING};
  margin-bottom: 6px;
  border-radius: {tokens.RAIO_PAINEL};
  border: var(--borda);
  /* cartão liso, como no painel de origem */
  background: var(--superficie);
  box-shadow: {tokens.SOMBRA_REPOUSO};
}}

.sinan-intro-texto {{
  min-width: 0;
  text-align: center;
}}

.sinan-intro-bandeira {{
  height: 58px;
  width: auto;
  flex-shrink: 0;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, .25);
}}
.sinan-procedencia {{
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin: 0 4px {tokens.GAP} 0;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XS};
  line-height: 1.35;
  text-align: right;
  opacity: .78;
}}
.sinan-procedencia b {{ font-weight: 700; }}
.sinan-procedencia-ajuda {{
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #0F9D8A;
  color: #fff;
  font-size: {tokens.TEXTO_XS};
  font-weight: 700;
  font-style: italic;
  cursor: help;
}}
/* sem bandeira, duas colunas */
.sinan-intro-sem-bandeira {{
  grid-template-columns: minmax(0, 1fr) auto;
}}

/* linha do recorte, embaixo do título */
.sinan-intro-escopo {{
  margin-top: 2px;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_SM};
  font-weight: 400;
  opacity: .68;
  line-height: 1.35;
}}

.sinan-intro h1.sinan-intro-titulo {{
  margin: 0;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_TITULO};
  font-weight: 900;
  line-height: 1.08;
  letter-spacing: -.015em;
  text-align: center;
  text-wrap: balance;
  color: inherit;
}}
/* no celular o cabeçalho vira duas faixas */
@media (max-width: 639px) {{
  .sinan-intro {{
    grid-template-columns: auto 1fr;
    gap: 12px;
    row-gap: 6px;
    align-items: center;
  }}
  .sinan-intro-bandeira {{ height: 40px; order: 1; }}
  .sinan-intro-marca {{ order: 2; }}
  .sinan-intro-texto {{
    grid-column: 1 / -1;
    order: 3;
    text-align: left;
  }}
  .sinan-intro h1.sinan-intro-titulo {{ text-align: left; }}
  .sinan-intro-escopo {{ text-align: left; }}
}}

/* a marca é texto, não imagem */
.sinan-intro-marca {{
  justify-self: end;
  align-self: center;
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XL};
  font-weight: 800;
  letter-spacing: -.005em;
  line-height: 1;
  white-space: nowrap;
  color: #0092C3;
}}
.sinan-intro-marca-mais {{
  color: #CA6F43;
  font-weight: 900;
}}
.indicador-programa {{
  padding: 14px 16px;
  border-radius: {tokens.RAIO_CARD};
  border: 1px solid color-mix(in srgb, currentColor 12%, transparent);
  background: color-mix(in srgb, currentColor 3%, transparent);
}}
.indicador-titulo {{
  font-size: {tokens.TEXTO_XS};
  font-weight: 600;
  opacity: .75;
  margin-bottom: 4px;
}}
.indicador-valor {{
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XL};
  font-weight: 800;
  line-height: 1.1;
  color: var(--ind-cor);
}}
.indicador-barra {{
  height: 6px;
  margin: 8px 0 6px;
  border-radius: 999px;
  background: color-mix(in srgb, currentColor 12%, transparent);
  overflow: hidden;
}}
.indicador-barra > span {{
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--ind-cor);
}}
.indicador-detalhe {{ font-size: {tokens.TEXTO_XS}; opacity: .65; }}


/* mapa à esquerda, gráficos à direita */
.sinan-painel {{
  border-radius: {tokens.RAIO_PAINEL};
  border: var(--borda);
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: {tokens.SOMBRA_REPOUSO};
  padding: {tokens.PADDING};
  color: inherit;
  font-family: var(--fonte);
}}
.sinan-painel-mapa {{ min-height: {tokens.ALTURA_MIN_MAPA}; }}
.sinan-painel-graficos {{ min-height: {tokens.ALTURA_MIN_PAINEL}; }}
/* legenda do mapa (o deck.gl não desenha uma) */
.mapa-legenda {{
  /* legenda em duas colunas */
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  align-content: start;
  gap: 5px 18px;
  /* embaixo do mapa, não por cima */
  position: relative;
  width: 100%;
  margin: 8px 0 4px 0;
  padding: 10px 14px;
  border-radius: {tokens.RAIO_PAINEL};
  border: 1px solid color-mix(in srgb, currentColor 14%, transparent);
  background: color-mix(in srgb, currentColor 5%, Canvas 95%);
  box-shadow: {tokens.SOMBRA_REPOUSO};
  backdrop-filter: blur(6px);
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XS};
  color: inherit;
}}
.mapa-legenda-n {{ opacity: .62; font-variant-numeric: tabular-nums; }}
.mapa-legenda-dica {{ font-weight: 400; opacity: .85; }}
.mapa-legenda-titulo {{
  display: flex;
  justify-content: space-between;
  gap: 16px;
  grid-column: 1 / -1;
  font-size: {tokens.TEXTO_SM};
  font-weight: 700;
  opacity: .74;
  margin-bottom: 2px;
}}
.mapa-legenda-item {{ display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }}
.mapa-legenda-item em {{ font-style: italic; opacity: .8; }}
/* --- Quadro de parâmetros ao lado do gráfico --- */
.quadro-parametros {{
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XS};
  line-height: 1.6;
  padding: 10px 12px;
  border-radius: {tokens.RAIO_PAINEL};
  border: 1px solid color-mix(in srgb, currentColor 14%, transparent);
  background: color-mix(in srgb, currentColor 4%, Canvas 96%);
}}
.quadro-parametros-titulo {{ font-weight: 700; margin-bottom: 4px; }}
.parametros-linha {{
  font-family: var(--fonte);
  font-size: {tokens.TEXTO_XS};
  opacity: .72;
  padding: 2px 0;
}}
.quadro-parametros ul {{ margin: 0; padding: 0; list-style: none; }}
.quadro-parametros-fonte {{ margin-top: 8px; opacity: .62; }}

.mapa-legenda-item i {{
  width: 14px;
  height: 14px;
  border-radius: 4px;
  border: 1px solid color-mix(in srgb, currentColor 18%, transparent);
}}

/* --- Controles com cara do painel de origem (pílulas) --- */

/* --- Espaçamento dos controles --- */
[data-testid="stWidgetLabel"] {{
  margin-bottom: 10px;
}}
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:not(:last-child):has([data-testid="stButtonGroup"]),
[data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:not(:last-child):has([data-testid="stSelectbox"]) {{
  margin-bottom: 14px;
}}

/* o ícone de ajuda não aumenta a linha do rótulo */
[data-testid="stWidgetLabel"] [data-testid="stTooltipIcon"] {{
  height: 1.6em;
  align-items: center;
}}

/* --- Abas: pílulas --- */
[data-testid="stTabs"] [role="tablist"] {{
  gap: 10px;
  border-bottom: none;
  margin-bottom: 0;
}}
[data-testid="stTabs"] [data-testid="stTab"] {{
  border: 1px solid color-mix(in srgb, currentColor 16%, transparent);
  border-radius: {tokens.RAIO_PILL};
  padding: 6px 18px;
  background: color-mix(in srgb, currentColor 4%, transparent);
  font-weight: 600;
}}
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] {{
  border-color: color-mix(in srgb, var(--intro-accent, #12346B) 55%, transparent);
  background: color-mix(in srgb, var(--intro-accent, #12346B) 12%, transparent);
  color: color-mix(in srgb, var(--intro-accent, #12346B) 50%, currentColor);
}}
/* sem o sublinhado da aba ativa */
[data-testid="stTabs"] .react-aria-SelectionIndicator {{ display: none; }}

/* --- Controle segmentado: pílulas --- */
[data-testid="stButtonGroup"] {{ gap: 8px; }}
[data-testid="stButtonGroup"] button {{
  border-radius: {tokens.RAIO_PILL} !important;
  border: 1px solid color-mix(in srgb, currentColor 16%, transparent) !important;
  padding: 5px 16px;
  font-weight: 600;
}}
/* no celular a pílula cresce pro dedo */
@media (max-width: 639px) {{
  [data-testid="stButtonGroup"] button[aria-checked],
  [data-testid="stButtonGroup"] button[aria-pressed] {{
    min-height: 44px;
  }}
}}
[data-testid="stButtonGroup"] button[aria-checked="true"],
[data-testid="stButtonGroup"] button[aria-pressed="true"] {{
  border-color: color-mix(in srgb, var(--intro-accent, #12346B) 55%, transparent) !important;
  background: color-mix(in srgb, currentColor 5%, transparent) !important;
}}

[data-testid="stMultiSelectTagsContainer"] span {{
  color: Canvas;
}}

/* --- Rótulo de widget: pílula --- */
[data-testid="stWidgetLabel"] > span {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  /* rótulo numa linha só */
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  border-radius: {tokens.RAIO_PILL};
  background: color-mix(in srgb, var(--intro-accent, #12346B) 11%, transparent);
  color: color-mix(in srgb, var(--intro-accent, #12346B) 50%, currentColor);
  font-weight: 700;
  font-size: {tokens.TEXTO_XS};
}}
[data-testid="stWidgetLabel"] p {{ margin: 0; font-weight: 700; }}

[data-testid="stElementContainer"]:has(.titulo-painel) {{
  min-height: 26px;
}}

/* o "i" de ajuda ao lado do título */
.titulo-painel-ajuda {{
  display: inline-grid;
  place-items: center;
  width: 17px;
  height: 17px;
  margin-left: 7px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--intro-accent, #12346B) 14%, transparent);
  color: var(--intro-accent, #12346B);
  font-size: 12px;
  font-weight: 700;
  font-style: italic;
  cursor: help;
  vertical-align: middle;
}}

/* --- Cada bloco no seu cartão (st.container(border=True, key="cartao-...")) --- */
[class*="st-key-cartao-"] {{
  border-radius: {tokens.RAIO_PAINEL} !important;
  border: var(--borda) !important;
  background: linear-gradient(180deg, var(--superficie-topo), var(--superficie));
  box-shadow: {tokens.SOMBRA_REPOUSO};
  padding: {tokens.PADDING};
  margin-bottom: 14px;
}}
/* respiro entre os controles do cartão */
[class*="st-key-cartao-controles"] [data-testid="stVerticalBlock"] {{ gap: 12px; }}
[class*="st-key-cartao-mapa"] [data-testid="stVerticalBlock"],
[class*="st-key-cartao-graficos"] [data-testid="stVerticalBlock"] {{ gap: 0; }}
[class*="st-key-cartao-"] > div > [data-testid="stElementContainer"]:last-child {{
  margin-bottom: 0;
}}

/* --- Botão "ver o território inteiro" --- */
.st-key-voltar_recife {{ margin: 12px 0 4px; }}
.st-key-voltar_recife button {{
  border-radius: {tokens.RAIO_PILL};
  border: 1.5px solid color-mix(in srgb, var(--intro-accent, #12346B) 45%, transparent);
  color: var(--intro-accent, #12346B);
  font-weight: 700;
  padding: 7px 20px;
  box-shadow: {tokens.SOMBRA_REPOUSO};
}}
.st-key-voltar_recife button:hover {{
  background: color-mix(in srgb, var(--intro-accent, #12346B) 10%, transparent);
  border-color: var(--intro-accent, #12346B);
}}

.sinan-painel-vazio {{
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: {tokens.TEXTO_SM};
  opacity: .55;
}}
</style>
"""


def titulo_painel(texto: str, ajuda: str = "") -> str:
    """Título de painel. Com ``ajuda``, ganha um "i" com a explicação."""
    marca = ""
    if ajuda:
        marca = (
            f'<span class="titulo-painel-ajuda" title="{escape(ajuda)}"'
            f' aria-label="{escape(ajuda)}" tabindex="0">i</span>'
        )
    return f'<div class="titulo-painel">{escape(texto)}{marca}</div>'


# bandeira embutida no HTML (sem o arquivo, fica sem)
_BANDEIRA = Path(__file__).resolve().parents[2] / "assets" / "bandeira_df.jpeg"


def _bandeira_data_uri() -> str | None:
    try:
        dados = _BANDEIRA.read_bytes()
    except OSError:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(dados).decode("ascii")


def faixa_intro(titulo: str, *, escopo: str, cor: str) -> str:
    """Cabeçalho: bandeira (se tiver), título no meio e Cenários+ à direita."""
    bandeira = _bandeira_data_uri()
    img = (
        f'<img class="sinan-intro-bandeira" src="{bandeira}" alt="Bandeira do Distrito Federal">'
        if bandeira
        else ""
    )
    classe = "sinan-intro" + ("" if bandeira else " sinan-intro-sem-bandeira")
    return (
        f'<div class="{classe}" style="--intro-accent:{escape(cor)};">'
        f"{img}"
        '<div class="sinan-intro-texto">'
        f'<h1 class="sinan-intro-titulo">{escape(titulo)}</h1>'
        f'<div class="sinan-intro-escopo">{escape(escopo)}</div>'
        "</div>"
        '<span class="sinan-intro-marca">Cenários'
        '<span class="sinan-intro-marca-mais">+</span></span>'
        "</div>"
    )


def procedencia(dados_ate: str, processado_em: str, *, ajuda: str = "") -> str:
    """Linha "Dados até … / Processado em …" embaixo do cabeçalho."""
    marcador = (
        f'<span class="sinan-procedencia-ajuda" title="{escape(ajuda)}">i</span>'
        if ajuda
        else ""
    )
    return (
        '<div class="sinan-procedencia"><div>'
        f"Dados até <b>{escape(dados_ate)}</b><br>"
        f"Processado em <b>{escape(processado_em)}</b></div>"
        f"{marcador}</div>"
    )


def painel_vazio(titulo: str, aviso: str, *, mapa: bool = False) -> str:
    """Espaço reservado de um painel que ainda não existe."""
    variante = "sinan-painel-mapa" if mapa else "sinan-painel-graficos"
    return (
        f'<div class="sinan-painel {variante} sinan-painel-vazio">'
        f"<div><strong>{escape(titulo)}</strong><br>{escape(aviso)}</div></div>"
    )


def _fatorar_unidade(titulo: str, linhas: tuple[str, ...]):
    """Tira a unidade repetida das linhas ("por 100 mil hab.") e põe uma vez no título."""
    if len(linhas) < 2:
        return titulo, linhas
    invertidas = [linha[::-1] for linha in linhas]
    comum = invertidas[0]
    for outra in invertidas[1:]:
        limite = min(len(comum), len(outra))
        corte = next(
            (i for i in range(limite) if comum[i] != outra[i]), limite
        )
        comum = comum[:corte]
    unidade = comum[::-1].strip()
    # só se o que repete for mesmo uma unidade
    if len(unidade) < 6 or not any(c.isalpha() for c in unidade):
        return titulo, linhas
    enxutas = tuple(linha[: len(linha) - len(comum)].rstrip(" /") for linha in linhas)
    rotulo = unidade.lstrip("/ ")
    if rotulo.startswith("100"):
        rotulo = f"por {rotulo}"
    return f"{titulo} ({rotulo})", enxutas


def titulo_legenda(titulo: str, unidade: str = "") -> str:
    """Título da legenda do mapa, explicando o número entre parênteses."""
    dica = (
        f'<span class="mapa-legenda-dica">({escape(unidade)} por faixa)</span>'
        if unidade else ""
    )
    return (
        f'<div class="mapa-legenda">'
        f'<div class="mapa-legenda-titulo">{escape(titulo)}{dica}</div></div>'
    )


def cores_das_faixas(chave: str, cores: list[str]) -> str:
    """Põe o quadradinho de cor em cada botão da legenda clicável (``chave`` = key do widget)."""
    regras = "\n".join(
        f'.st-key-{chave} [data-testid="stButtonGroup"] '
        f"button:nth-of-type({i + 1})::before {{ background: {cor}; }}"
        for i, cor in enumerate(cores)
    )
    return (
        "<style>\n"
        f'.st-key-{chave} [data-testid="stButtonGroup"] button::before {{\n'
        "  content: '';\n"
        "  display: inline-block;\n"
        "  width: 11px; height: 11px;\n"
        "  margin-right: 7px;\n"
        "  border-radius: 3px;\n"
        "  border: 1px solid color-mix(in srgb, currentColor 18%, transparent);\n"
        "}\n"
        f"{regras}\n"
        "</style>"
    )


def parametros_em_linha(titulo: str, linhas) -> str:
    """A régua do quadro de parâmetros numa linha só."""
    titulo, linhas = _fatorar_unidade(titulo, tuple(linhas))
    itens = " · ".join(escape(linha) for linha in linhas)
    return (
        f'<div class="parametros-linha">'
        f"<b>{escape(titulo)}</b> &nbsp;{itens}</div>"
    )


def quadro_parametros(titulo: str, linhas, fonte: str = "") -> str:
    """Caixinha com as faixas do indicador ao lado do gráfico, como no boletim."""
    titulo, linhas = _fatorar_unidade(titulo, tuple(linhas))
    itens = "".join(f"<li>{escape(linha)}</li>" for linha in linhas)
    rodape = (
        f'<div class="quadro-parametros-fonte">{escape(fonte)}</div>' if fonte else ""
    )
    return (
        f'<div class="quadro-parametros">'
        f'<div class="quadro-parametros-titulo">{escape(titulo)}</div>'
        f"<ul>{itens}</ul>{rodape}</div>"
    )
