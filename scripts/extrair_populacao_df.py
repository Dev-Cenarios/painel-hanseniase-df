"""População do DF por ano, sexo e idade (public.pop_ibge) pra parquet.

Só o formato da pirâmide e o peso de 0–14 vêm daqui; o total do ano é o do
boletim (ver src/fonte_sinan.py).

    python -m scripts.extrair_populacao_df
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import banco  # noqa: E402

DESTINO = RAIZ / "data" / "origem" / "populacao_ibge_df.parquet"

# código IBGE de 7 dígitos, como está no pop_ibge
COD_MUN_DF = "5300108"

SQL = """
    SELECT ano::int AS ano,
           CASE sexo WHEN '1' THEN 'M' WHEN '2' THEN 'F' END AS sexo,
           idade::int AS idade,
           sum(populacao)::bigint AS populacao
    FROM public.pop_ibge
    WHERE cod_mun = %s
    GROUP BY 1, 2, 3
    ORDER BY 1, 2, 3
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destino", type=Path, default=DESTINO)
    a = p.parse_args()

    if not banco.configurado():
        raise SystemExit("Credenciais ausentes: copie .env.exemplo pra .env e preencha.")

    df = banco.consultar(SQL, params=[COD_MUN_DF])
    if df["sexo"].isna().any():
        raise SystemExit("sexo fora de 1/2 no pop_ibge — rever o CASE")
    a.destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(a.destino, index=False)
    print(f"{len(df)} linhas em {a.destino}")
    print(df.groupby("ano")["populacao"].sum().to_string())


if __name__ == "__main__":
    main()
