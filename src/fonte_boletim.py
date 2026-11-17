"""Números por RA e Região de Saúde: a Tabela 1 dos boletins da SES-DF.

O SINAN do banco não tem RA, então casos novos e taxa por área saem do boletim
(ver scripts/extrair_boletim_ra.py), de 2020 a 2025. A malha das 35 RAs e das
7 Regiões é a do DFTB (IPEDF 2026).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import geopandas as gpd
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TABELA = RAIZ / "data" / "origem" / "boletim_ra.parquet"
GEO = RAIZ / "geo"

# nível da tela → nível da tabela
_NIVEL = {"RA": "RA", "RS": "REGIAO"}

# coluna pedida → coluna da tabela
_COLUNA = {"deteccao": "taxa", "casos": "casos"}


def disponivel() -> bool:
    return TABELA.is_file() and (GEO / "ra.parquet").is_file()


def nome_regiao(regiao: str) -> str:
    return regiao.removeprefix("Regiao ").strip()


@lru_cache(maxsize=1)
def _tabela() -> pd.DataFrame:
    t = pd.read_parquet(TABELA)
    # Região pelo nome curto ("Leste"), como na malha
    eh_regiao = t["nivel"] == "REGIAO"
    t.loc[eh_regiao, "chave"] = t.loc[eh_regiao, "chave"].map(nome_regiao)
    t["regiao"] = t["regiao"].map(lambda r: nome_regiao(r) if isinstance(r, str) else r)
    return t


@lru_cache(maxsize=1)
def ras() -> gpd.GeoDataFrame:
    malha = gpd.read_parquet(GEO / "ra.parquet")[["ra_chave", "ra_nome", "regiao_saude", "geometry"]]
    return malha.assign(regiao_saude=malha["regiao_saude"].map(nome_regiao))


@lru_cache(maxsize=1)
def regioes() -> gpd.GeoDataFrame:
    malha = gpd.read_parquet(GEO / "regioes_saude.parquet")[["regiao_saude", "geometry"]]
    return malha.assign(regiao_saude=malha["regiao_saude"].map(nome_regiao))


def anos() -> list[int]:
    return sorted(int(a) for a in _tabela()["ano"].unique())


def valores(nivel: str, coluna: str, ano: int) -> pd.Series:
    """A coluna por área (``ra_chave`` ou nome curto da Região)."""
    t = _tabela()
    linhas = t[(t["nivel"] == _NIVEL[nivel]) & (t["ano"] == ano)]
    return pd.Series(linhas[_COLUNA[coluna]].to_numpy(), index=linhas["chave"].to_numpy(), dtype=float)


def valor(nivel: str, chave: str, coluna: str, ano: int) -> float | None:
    v = valores(nivel, coluna, ano).get(chave)
    return None if v is None or v != v else float(v)


def do_df(coluna: str, ano: int) -> float | None:
    t = _tabela()
    linhas = t[(t["nivel"] == "DF") & (t["ano"] == ano)]
    return float(linhas[_COLUNA[coluna]].iloc[0]) if not linhas.empty else None
