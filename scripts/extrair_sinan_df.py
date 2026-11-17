"""Extrai a hanseníase dos residentes no DF da `silver.hanseniase` pra parquet.

Vem tudo: todos os anos, todo modo de entrada e também "Erro diagnóstico".
Quem corta é a camada de dados, do jeito do boletim da SES-DF (ano do
diagnóstico, caso novo, sem erro diagnóstico) — recidiva e coorte de cura
precisam das outras linhas.

O que não está em COLUNAS não sai do banco.

    python -m scripts.extrair_sinan_df
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import banco  # noqa: E402

DESTINO = RAIZ / "data" / "origem" / "sinan_df_hans.parquet"

COLUNAS = (
    "sk_sinan_hans",
    # tempo
    "data_notificacao",
    "ano_notificacao",
    "data_diagnostico",
    "data_inicio_tratamento",
    "data_alta",
    # geografia (DF não tem RA na fonte)
    "estado_notificacao",
    "municipio_notificacao",
    "nome_unidade_notificadora",
    "estado_residencia",
    "municipio_residencia",
    # perfil
    "sexo",
    "idade_notificada",
    "ano_nascimento",
    "raca_cor",
    "escolaridade",
    "gestante",
    "ocupacao",
    # clínica no diagnóstico
    "modo_entrada",
    "modo_deteccao",
    "classificacao_operacional",
    "forma_clinica",
    "numero_lesoes",
    "nervos_afetados",
    "baciloscopia",
    "avaliacao_incapacidade_diagnostico",
    "esquema_inicial",
    # acompanhamento e desfecho
    "classificacao_operacional_atual",
    "avaliacao_incapacidade_atual",
    "esquema_atual",
    "doses_recebidas",
    "episodio_reacional",
    "contatos_examinados",
    "tipo_alta",
    "status_duplicidade",
)

SQL = f"""
    SELECT {", ".join(COLUNAS)}
    FROM silver.hanseniase
    WHERE estado_residencia = 'Distrito Federal'
"""


def extrair():
    return banco.consultar(SQL)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destino", type=Path, default=DESTINO)
    a = p.parse_args()

    if not banco.configurado():
        raise SystemExit("Credenciais ausentes: copie .env.exemplo pra .env e preencha.")

    df = extrair()
    if df["sk_sinan_hans"].duplicated().any():
        raise SystemExit("sk_sinan_hans repetida — a silver mudou, rever a extração")

    a.destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(a.destino, index=False, compression="zstd")

    ano = df["data_diagnostico"].map(lambda d: d.year if d is not None and d == d else None)
    novo = (df["modo_entrada"] == "Caso novo") & (df["tipo_alta"] != "Erro diagnóstico")
    print(f"{len(df)} linhas, {len(df.columns)} colunas em {a.destino}")
    print("casos novos por ano de diagnóstico:")
    print(ano[novo].value_counts().sort_index().astype(int).to_string())


if __name__ == "__main__":
    main()
