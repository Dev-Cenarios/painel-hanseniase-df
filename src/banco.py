"""Conexão só leitura com o cenarios_ai (só pros scripts; o app lê parquet).

Mesmo do DFTB: credenciais no .env, readonly na sessão e no servidor.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]


def _carregar_env() -> None:
    caminho = RAIZ / ".env"
    if not caminho.is_file():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


def configurado() -> bool:
    _carregar_env()
    return bool(
        os.environ.get("CENARIOS_HOST")
        and os.environ.get("CENARIOS_USER")
        and os.environ.get("CENARIOS_PASSWORD")
    )


@contextmanager
def conectar():
    import psycopg2  # só os scripts precisam

    if not configurado():
        raise RuntimeError(
            "Credenciais ausentes: preencha CENARIOS_HOST, CENARIOS_USER e CENARIOS_PASSWORD no .env"
        )

    conexao = psycopg2.connect(
        host=os.environ["CENARIOS_HOST"],
        port=int(os.environ.get("CENARIOS_PORT", "5432")),
        dbname=os.environ.get("CENARIOS_DB", "cenarios_ai"),
        user=os.environ["CENARIOS_USER"],
        password=os.environ["CENARIOS_PASSWORD"],
        connect_timeout=10,
        options="-c default_transaction_read_only=on",
    )
    try:
        conexao.set_session(readonly=True, autocommit=True)
        yield conexao
    finally:
        conexao.close()


def consultar(sql: str, params: list | None = None) -> pd.DataFrame:
    import warnings

    with conectar() as conexao, warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # pandas reclama de DBAPI sem SQLAlchemy
        return pd.read_sql_query(sql, conexao, params=params)
