"""Medidas, fontes e cores base da casca (vindas do hansepe)."""

from __future__ import annotations

# --- Superfícies -----------------------------------------------------------
RAIO_PAINEL = "14px"
RAIO_CARD = RAIO_PAINEL
RAIO_PILL = "999px"

BORDA = "1px solid color-mix(in srgb, currentColor 14%, transparent)"
SOMBRA_REPOUSO = "0 10px 26px rgba(2,6,23,.08)"
SOMBRA_HOVER = "0 18px 44px rgba(2,6,23,.12)"
SOMBRA_ATIVO = "0 22px 56px rgba(2,6,23,.14)"

# o fundo do card sai da cor do texto, aí funciona no tema claro e no escuro
MISTURA_CARD = "4%"
MISTURA_CARD_TOPO = "7%"
# --- Tipografia ------------------------------------------------------------
FONTE = (
    "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, "
    "'Apple Color Emoji', 'Segoe UI Emoji', sans-serif"
)

TEXTO_XS = "12px"    # legenda, detalhe, rótulo de eixo, tooltip
TEXTO_SM = "14px"    # corpo
TEXTO_XL = "24px"    # valor de KPI e de indicador
# nunca menor que o número do KPI
TEXTO_TITULO = "clamp(24px, 2.1vw, 30px)"

# --- Semântica -------------------------------------------------------------
BOM = "#16A34A"
RUIM = "#B42318"
NEUTRO_OPACIDADE = ".74"

TEXTO_CLARO = "#0B1220"
TEXTO_ESCURO = "#E5E7EB"

# --- Espaçamento e layout --------------------------------------------------
GAP = "12px"
PADDING = "12px"

# respiro da página (o padrão do Streamlit é largo demais pra painel)
PAGINA_TOPO = "40px"
PAGINA_LADOS = "40px"
PAGINA_BASE = "56px"

PAGINA_LADOS_ESTREITO = "16px"

ALTURA_MIN_MAPA = "520px"
ALTURA_MIN_PAINEL = "560px"
