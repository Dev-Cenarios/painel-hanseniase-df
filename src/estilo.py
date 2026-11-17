"""A cara do painel, usando as peças do hansepe (src/theme/).

Aqui só tem o que o hansepe não tem: a frase do retrato, o aviso, o rodapé
e a legenda de chips.
"""

from __future__ import annotations

from html import escape

from cenarios_core import formato

from src.theme import componentes as ui

# laranja do hansepe/tbpe
ACENTO = "#C1440A"

OK = "#16A34A"
CRITICO = "#B42318"
AZUL = "#1E73BE"


def css() -> str:
    """CSS do hansepe + o nosso."""
    return ui.css_base() + ui.css_layout() + """
<style>
.frase { border-left: 4px solid var(--cor); padding: 4px 0 4px 16px; margin: 6px 0 14px; }
.frase-numero {
  font-weight: 800; font-size: clamp(2.2rem, 4vw, 3.2rem); line-height: 1;
  color: var(--cor); font-variant-numeric: tabular-nums;
}
.frase-texto { font-weight: 700; font-size: 1.05rem; margin-top: 6px; line-height: 1.35; }
.frase-apoio { font-size: .9rem; opacity: .8; margin-top: 6px; }
.aviso {
  background: color-mix(in srgb, currentColor 5%, transparent);
  border: 1px solid color-mix(in srgb, currentColor 14%, transparent);
  border-left: 3px solid """ + ACENTO + """; border-radius: 14px;
  padding: 14px 18px; margin: 8px 0 14px; font-size: .9rem;
}
.sobre { font-size: .9rem; line-height: 1.55; opacity: .92; }
.sobre h4 { font-size: .95rem; margin: 14px 0 4px; }
.rodape {
  border-top: 1px solid color-mix(in srgb, currentColor 14%, transparent);
  margin-top: 28px; padding: 10px 4px; font-size: 12px; opacity: .72;
  display: flex; justify-content: space-between; gap: 14px; flex-wrap: wrap;
}
</style>
"""


def cabecalho(titulo: str, subtitulo: str, contexto: str | None = None) -> str:
    """Cabeçalho do hansepe, sem bandeira (painel nacional)."""
    return ui.faixa_intro(titulo, escopo=subtitulo, cor=ACENTO)


def rodape(fonte: str) -> str:
    """Fonte do dado e assinatura."""
    return (f'<div class="rodape"><span>{escape(fonte)}</span>'
            f'<span>Projeto Cenários+ · UnB</span></div>')


def formatar(valor: float | None, casas: int) -> str:
    if valor is None:
        return "—"
    return formato.formatar_inteiro(valor) if casas == 0 else formato.formatar_decimal(valor, casas)


def card(rotulo: str, valor: float | None, casas: int, cor: str,
         anterior: float | None = None, bom_se_cai: bool = True, ano_anterior: int | None = None,
         subtitulo: str | None = None, icone: str = "", ajuda: str = "") -> str:
    """Card de KPI com a variação contra o ano anterior."""
    variacao = ui.delta(valor, anterior, taxa=casas > 0, bom_se_cai=bom_se_cai,
                        sufixo=f"vs {ano_anterior}" if ano_anterior else "vs ano anterior")
    return ui.kpi_card(rotulo, formatar(valor, casas), cor=cor, subtitulo=subtitulo,
                       badge_delta=variacao, icone=icone, ajuda=ajuda or rotulo)


def card_texto(rotulo: str, texto: str | None, cor: str, nota: str | None = None) -> str:
    """Card com texto no lugar do número."""
    return ui.kpi_card(rotulo, texto or "—", cor=cor, subtitulo=nota, ajuda=rotulo)


def card_numero(rotulo: str, valor: float | None, casas: int, cor: str, nota: str | None = None) -> str:
    """Card de número sem variação, com uma nota embaixo."""
    return ui.kpi_card(rotulo, formatar(valor, casas), cor=cor, subtitulo=nota, ajuda=rotulo)


def aviso(titulo: str, texto: str) -> str:
    """Caixinha de aviso."""
    return f'<div class="aviso"><b>{escape(titulo)}</b> {escape(texto)}</div>'


def legenda_cores(cores: dict[str, str], titulo: str) -> str:
    """Legenda de chips, igual à do mapa."""
    itens = "".join(f'<span class="mapa-legenda-item"><i style="background:{escape(c)}"></i>'
                    f'{escape(r)}</span>' for r, c in cores.items())
    return (f'<div class="mapa-legenda"><div class="mapa-legenda-titulo">{escape(titulo)}</div>'
            f'{itens}</div>')


def frase(numero: str, texto: str, apoio: str | None, cor: str) -> str:
    """A frase grande da aba Município."""
    apoio_html = f'<div class="frase-apoio">{escape(apoio)}</div>' if apoio else ""
    return (f'<div class="frase" style="--cor:{escape(cor)}">'
            f'<div class="frase-numero">{escape(numero)}</div>'
            f'<div class="frase-texto">{escape(texto)}</div>{apoio_html}</div>')


def titulo_bloco(texto: str, ajuda: str = "") -> str:
    """Título de painel (com o "i" de ajuda se tiver)."""
    return ui.titulo_painel(texto, ajuda=ajuda)
