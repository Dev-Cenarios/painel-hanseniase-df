"""Contatos registrados e examinados dos residentes no DF (public.sinan_hans) pra parquet.

A silver não tem contatos registrados, que é o denominador do indicador; o
SINAN bruto tem. Só o que a conta precisa sai do banco.

    python -m scripts.extrair_contatos_df
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import banco  # noqa: E402

DESTINO = RAIZ / "data" / "origem" / "sinan_df_contatos.parquet"

# código de 6 dígitos de Brasília no SINAN
MUN_DF = "530010"

SQL = """
    SELECT dt_diag, classopera, modoentr, tpalta_n, contreg, contexam
    FROM public.sinan_hans
    WHERE id_mn_resi = %s
"""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destino", type=Path, default=DESTINO)
    a = p.parse_args()

    if not banco.configurado():
        raise SystemExit("Credenciais ausentes: copie .env.exemplo pra .env e preencha.")

    df = banco.consultar(SQL, params=[MUN_DF])
    a.destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(a.destino, index=False)
    print(f"{len(df)} linhas em {a.destino}")


if __name__ == "__main__":
    main()
