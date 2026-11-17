"""Lê a Tabela 1 dos boletins de hanseníase da SES-DF: casos novos e taxa por RA e Região de Saúde.

O SINAN do banco não tem RA, então o mapa sai do boletim. Ano que aparece nos
dois boletins fica com o mais novo.

    python -m scripts.extrair_boletim_ra

Precisa do pypdf (está no ../sinan/.venv).
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "data" / "origem" / "boletins"
DESTINO = RAIZ / "data" / "origem" / "boletim_ra.parquet"

# do mais velho pro mais novo (o mais novo sobrescreve)
BOLETINS = {
    "hans_2020_2024.pdf": "https://www.saude.df.gov.br/documents/d/saude/informativo_hanseniase_final",
    "hans_2021_2025.pdf": "https://www.saude.df.gov.br/documents/d/saude/informativo_hanseniase_2026-pdf",
}

REGIOES = {"CENTRAL": "Regiao Central", "CENTRO-SUL": "Regiao Centro-Sul", "LESTE": "Regiao Leste",
           "NORTE": "Regiao Norte", "OESTE": "Regiao Oeste", "SUDOESTE": "Regiao Sudoeste",
           "SUL": "Regiao Sul"}

# como o boletim chama → ra_chave da malha
NOMES_RA = {"RIACHO FUNDO I": "RIACHO FUNDO", "ESTRUTURAL": "SCIA"}

_NUM = r"(?:-|\d+(?:,\d+)?)"
_LINHA = re.compile(rf"^(?P<nome>\D.*?)(?P<nums>(?:\s+{_NUM}){{10}})\s*$")


def _chave(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().upper()


def _numero(token: str) -> float:
    return 0.0 if token == "-" else float(token.replace(",", "."))


def ler_tabela(texto: str) -> pd.DataFrame:
    """As linhas da Tabela 1: ``nivel``, ``nome``, ``regiao``, ``ano``, ``casos``, ``taxa``."""
    inicio = texto.index("Tabela 1 –")
    anos = [int(a) for a in re.findall(r"20\d\d", texto[inicio:inicio + 400])[2:7]]
    linhas, regiao = [], None
    for linha in texto[inicio:].splitlines():
        achou = _LINHA.match(linha.strip())
        if not achou:
            continue
        nome = re.sub(r"\s*\(RS\w\w\)$", "", achou["nome"]).strip()
        nums = [_numero(t) for t in achou["nums"].split()]
        chave = _chave(nome)
        if chave == "TOTAL":
            nivel, regiao_da_linha = "DF", None
        elif chave in REGIOES:
            regiao = regiao_da_linha = REGIOES[chave]
            nivel = "REGIAO"
        else:
            nivel, regiao_da_linha, chave = "RA", regiao, NOMES_RA.get(chave, chave)
        for k, ano in enumerate(anos):
            linhas.append({"nivel": nivel, "chave": chave if nivel == "RA" else regiao_da_linha or "DF",
                           "nome": nome, "regiao": regiao_da_linha, "ano": ano,
                           "casos": nums[2 * k], "taxa": nums[2 * k + 1]})
        if chave == "TOTAL":
            break
    return pd.DataFrame(linhas)


def corrigir_taxas(tabela: pd.DataFrame, limite: float = 0.5) -> pd.DataFrame:
    """Refaz a taxa que não fecha com a população dos outros anos.

    O boletim 2021–2025 traz Gama 2025 com 6 casos e taxa 1,44 (dá 417 mil hab.,
    contra ~145 mil nos outros anos) e a Região Sul com 2,00. Onde a população
    implícita (casos / taxa) foge mais de 50% da mediana da área, a taxa vira
    casos / mediana e ``taxa_boletim`` guarda a original.
    """
    tabela = tabela.copy()
    tabela["taxa_boletim"] = tabela["taxa"]
    pop = (tabela["casos"] / tabela["taxa"] * 1e5).where(tabela["casos"] > 0)
    mediana = pop.groupby([tabela["nivel"], tabela["chave"]]).transform("median")
    errada = (pop / mediana - 1).abs() > limite
    tabela.loc[errada, "taxa"] = (tabela["casos"] / mediana * 1e5)[errada].round(2)
    for _, linha in tabela[errada].iterrows():
        print(f"taxa refeita: {linha['nome']} {linha['ano']} {linha['taxa_boletim']} → {linha['taxa']}")
    return tabela


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--destino", type=Path, default=DESTINO)
    a = p.parse_args()

    import pypdf

    PASTA.mkdir(parents=True, exist_ok=True)
    tabelas = []
    for arquivo, url in BOLETINS.items():
        caminho = PASTA / arquivo
        if not caminho.is_file():
            urllib.request.urlretrieve(url, caminho)
        texto = "\n".join(pg.extract_text() or "" for pg in pypdf.PdfReader(caminho).pages)
        tabela = ler_tabela(texto).assign(boletim=arquivo)
        if (tabela["nivel"] == "RA").groupby(tabela["ano"]).sum().ne(35).any():
            raise SystemExit(f"{arquivo}: não achei as 35 RAs em todo ano — o PDF mudou?")
        tabelas.append(tabela)

    tudo = pd.concat(tabelas, ignore_index=True)
    # ano repetido fica com o boletim mais novo (o último da lista)
    tudo = tudo.drop_duplicates(["nivel", "chave", "ano"], keep="last").reset_index(drop=True)
    tudo = corrigir_taxas(tudo)
    a.destino.parent.mkdir(parents=True, exist_ok=True)
    tudo.to_parquet(a.destino, index=False)

    soma = tudo[tudo["nivel"] == "RA"].groupby("ano")["casos"].sum()
    total = tudo[tudo["nivel"] == "DF"].set_index("ano")["casos"]
    print(f"{len(tudo)} linhas em {a.destino}")
    print(pd.DataFrame({"soma_das_RAs": soma, "total_DF": total}).to_string())


if __name__ == "__main__":
    sys.exit(main())
