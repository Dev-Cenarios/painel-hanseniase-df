"""Tudo que o app.py pede de dado passa por aqui.

``area`` é o recorte: ``None`` é o DF inteiro, ``("RS", "Leste")`` uma Região
de Saúde e ``("RA", "PLANO PILOTO")`` uma RA (a chave da malha).

Hoje o SINAN do banco não tem RA, então:

- DF inteiro: tudo do SINAN (fonte_sinan.py)
- RA e Região de Saúde: só casos novos e detecção, da Tabela 1 do boletim
  (fonte_boletim.py, 2020–2025); o resto vem vazio

Quando o SINAN georreferenciado chegar, é só calcular por área no
fonte_sinan.py e trocar as funções de baixo — a tela não muda.

- sem dado é None/NaN, nunca zero
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from src import fonte_boletim as _boletim
from src import fonte_sinan as _fonte

GRAUS_SERIE = _fonte.GRAUS_SERIE

# o que o boletim dá por área
_POR_AREA = {"incid": "deteccao", "casos": "casos"}


def disponivel() -> bool:
    """Se os parquets estão lá (sem eles os testes de dado são pulados)."""
    return _fonte.disponivel() and _boletim.disponivel()


def tem_dado_por_area() -> bool:
    """Se o SINAN já tem RA. Enquanto não tiver, área só tem casos e detecção."""
    return False


def extraido_em() -> str:
    return _fonte.extraido_em()


def anos() -> list[int]:
    return _fonte.anos()


def anos_por_area() -> list[int]:
    """Anos em que há número por RA e Região de Saúde."""
    return _boletim.anos()


# ---------------------------------------------------------------------------
# Geografia
# ---------------------------------------------------------------------------

def ras() -> gpd.GeoDataFrame:
    """``ra_chave``, ``ra_nome``, ``regiao_saude``, ``geometry``."""
    return _boletim.ras()


def regioes() -> gpd.GeoDataFrame:
    """``regiao_saude``, ``geometry``."""
    return _boletim.regioes()


def nome_area(area: tuple[str, str] | None) -> str:
    if area is None:
        return "DF"
    nivel, chave = area
    if nivel == "RA":
        return ras().set_index("ra_chave")["ra_nome"].get(chave, chave)
    return f"Região {chave}"


# ---------------------------------------------------------------------------
# Números
# ---------------------------------------------------------------------------

def kpis(ano: int, area: tuple[str, str] | None = None) -> dict:
    """Cada métrica do pack no ano, com numerador e denominador das proporções."""
    if area is None:
        return _fonte.kpis(ano)
    nivel, chave = area
    if ano not in _boletim.anos():
        return {}
    return {m: _boletim.valor(nivel, chave, coluna, ano) for m, coluna in _POR_AREA.items()}


def valores_mapa(metrica: str, ano: int, nivel: str = "RA") -> pd.Series:
    """A métrica por RA (``ra_chave``) ou Região de Saúde (nome curto)."""
    if metrica not in _POR_AREA or ano not in _boletim.anos():
        return pd.Series(dtype=float, name=metrica)
    return _boletim.valores(nivel, _POR_AREA[metrica], ano).rename(metrica)


def ranking(metrica: str, ano: int, nivel: str = "RA", top_n: int | None = None) -> pd.DataFrame:
    """``chave``, ``nome``, ``valor``, do maior pro menor."""
    serie = valores_mapa(metrica, ano, nivel).dropna().sort_values(ascending=False)
    if nivel == "RA":
        nomes = ras().set_index("ra_chave")["ra_nome"].reindex(serie.index).to_numpy()
    else:
        nomes = serie.index.to_numpy()
    tabela = pd.DataFrame({"chave": serie.index, "nome": nomes, "valor": serie.to_numpy()})
    return tabela.head(top_n) if top_n else tabela


def serie_anual(metrica: str, area: tuple[str, str] | None = None) -> pd.DataFrame:
    """``ano``, ``valor``."""
    if area is None:
        return _fonte.serie_anual(metrica)
    if metrica not in _POR_AREA:
        return pd.DataFrame(columns=["ano", "valor"])
    nivel, chave = area
    return pd.DataFrame([{"ano": a, "valor": _boletim.valor(nivel, chave, _POR_AREA[metrica], a)}
                         for a in _boletim.anos()])


def _so_df(area, vazio: pd.DataFrame, calcular):
    """O que só existe pro DF inteiro, enquanto o SINAN não tem RA."""
    return calcular() if area is None else vazio


def canal(ano: int, area=None, grau: str | None = None):
    vazio = _fonte.Canal(pd.DataFrame(columns=["mes", "mes_nome", "q1", "q3"]),
                         pd.DataFrame(columns=["mes", "mes_nome", "ano", "valor"]),
                         pd.DataFrame(columns=["mes", "mes_nome", "valor"]), ())
    return _so_df(area, vazio, lambda: _fonte.canal(ano, grau))


def meses_fora_da_faixa(c) -> pd.DataFrame:
    return _fonte.meses_fora_da_faixa(c)


def epicurva(ano_min: int, ano_max: int, area=None) -> pd.DataFrame:
    return _so_df(area, pd.DataFrame(columns=["ano_mes", "ano", "mes", "casos"]),
                  lambda: _fonte.epicurva(ano_min, ano_max))


def piramide(ano: int, area=None) -> pd.DataFrame:
    return _so_df(area, pd.DataFrame(columns=["sexo", "faixa_ord", "faixa_etaria", "valor", "pop"]),
                  lambda: _fonte.piramide(ano))


def composicao(variavel: str, ano: int, area=None) -> pd.DataFrame:
    return _so_df(area, pd.DataFrame(columns=["categoria", "n", "pct", "total"]),
                  lambda: _fonte.composicao(variavel, ano))


def serie_composicao(variavel: str, area=None) -> pd.DataFrame:
    return _so_df(area, pd.DataFrame(columns=["ano", "categoria", "n", "pct"]),
                  lambda: _fonte.serie_composicao(variavel))


def total_de_casos(ano: int, area=None) -> int:
    return _fonte.total_de_casos(ano) if area is None else 0


def serie_qualidade(area=None) -> pd.DataFrame:
    return _so_df(area, pd.DataFrame(columns=["ano"]), _fonte.serie_qualidade)


def serie_classificacao(area=None) -> pd.DataFrame:
    return _so_df(area, pd.DataFrame(columns=["ano", "pb", "mb", "prop_mb"]), _fonte.serie_classificacao)


def serie_0_14(area=None) -> pd.DataFrame:
    return _so_df(area, pd.DataFrame(columns=["ano", "casos", "taxa"]), _fonte.serie_0_14)
