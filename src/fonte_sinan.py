"""Os números do DF inteiro: SINAN de hanseníase contado como o boletim da SES-DF.

- caso novo = modo de entrada "Caso novo", sem "Erro diagnóstico", pelo ano do diagnóstico
- cura, abandono e contatos na coorte do MS: PB diagnosticados em A−1 e MB em A−2, sem transferências
- grau 2 sobre os avaliados (regra do MS), e só com GIF avaliado em 75% ou mais
- população = a do boletim (IPEDF) e, antes de 2020, a do IBGE na mesma escala

Os nomes das métricas são os do hansepe. Tudo aqui é do DF inteiro: o SINAN
do banco não tem RA (o recorte por área fica no dados.py).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ORIGEM = Path(__file__).resolve().parents[1] / "data" / "origem"
SINAN = ORIGEM / "sinan_df_hans.parquet"
CONTATOS = ORIGEM / "sinan_df_contatos.parquet"
POP_IBGE = ORIGEM / "populacao_ibge_df.parquet"

# pop_ibge começa em 2010; 2026 ainda tá aberto
ANOS = tuple(range(2010, 2026))

MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro")

# População do IPEDF que o boletim usa, tirada de casos / taxa (Tabela 1, duas casas).
# 2020 vem do boletim 2020–2024. Troque pela tabela do IPEDF quando tiver.
POPULACAO_BOLETIM = {
    2020: round(204 / 6.68 * 1e5),
    2021: round(130 / 4.20 * 1e5),
    2022: round(158 / 5.05 * 1e5),
    2023: round(130 / 4.10 * 1e5),
    2024: round(113 / 3.53 * 1e5),
    2025: round(157 / 4.85 * 1e5),
}

# abaixo disso a proporção é ruído e vira sem dado
MINIMO_PARA_PERCENTUAL = 5

# o MS só lê o grau 2 com GIF avaliado em pelo menos 75%
MINIMO_GIF_AVALIADO = 75

# coorte com mais que isso sem alta ainda não fechou
MAXIMO_SEM_ALTA = 0.25

# quantos anos anteriores fazem a faixa do canal endêmico (o hansepe usa 5)
ANOS_REFERENCIA = 5

GRAUS_SERIE = ("Grau zero", "Grau I", "Grau II", "Não avaliado", "Não informado")

IGNORADO = "Ignorado/em branco"
_IGNORADOS = {"Ignorado", "Não informado", "Nao informado", None}

FAIXAS = (("0 a 4", 0, 4), ("5 a 9", 5, 9), ("10 a 14", 10, 14), ("15 a 19", 15, 19),
          ("20 a 29", 20, 29), ("30 a 39", 30, 39), ("40 a 49", 40, 49), ("50 a 59", 50, 59),
          ("60 a 69", 60, 69), ("70 a 79", 70, 79), ("80 e mais", 80, 200))

# variável da ficha (código do hansepe) → coluna da silver e a ordem das categorias
TOPICOS: dict[str, tuple[str, tuple[str, ...]]] = {
    "CLASSOPERA": ("classificacao_operacional", ("PB - Paucibacilar", "MB - Multibacilar")),
    "FORMACLINI": ("forma_clinica", ("I - Indeterminada", "T - Tuberculóide", "D - Dimorfa",
                                     "V - Virchowiana", "Não classificado")),
    "AVALIA_N": ("avaliacao_incapacidade_diagnostico", ("Grau zero", "Grau I", "Grau II", "Não avaliado")),
    "BACILOSCOP": ("baciloscopia", ("Positiva", "Negativa", "Não realizada")),
    "NERVOSAFET": ("nervos_afetados", ()),
    "EPIS_RACIO": ("episodio_reacional", ("Reação tipo 1", "Reação tipo 2", "Reação tipo 1 e 2")),
    "MODOENTR": ("modo_entrada", ("Caso novo", "Transferência do mesmo município (outra unidade)",
                                  "Transferência de outro município (mesma UF)",
                                  "Transferência de outro estado", "Transferência de outro país",
                                  "Recidiva", "Outros reingressos")),
    "MODODETECT": ("modo_deteccao", ("Encaminhamento", "Demanda espontânea", "Exame de coletividade",
                                     "Exame de contatos", "Outros modos")),
    "ESQ_INI_N": ("esquema_inicial", ("PQT/PB/6 doses", "PQT/MB/12 doses", "Outros Esquemas Substitutos")),
    "DOSE_RECEB": ("doses_recebidas", ()),
    "TPALTA_N": ("tipo_alta", ("Cura", "Transferência p/ mesmo município", "Transferência p/ outro município",
                               "Transferência p/ outro estado", "Transferência p/ outro país",
                               "Transferência não especificada", "Óbito", "Abandono")),
    "CS_RACA": ("raca_cor", ("Branca", "Preta", "Amarela", "Parda", "Indigena")),
    "CS_ESCOL_N": ("escolaridade", ("Analfabeto", "1a a 4a serie incompleta do EF", "4a serie completa do EF",
                                    "5a a 8a serie incompleta do EF", "Ensino fundamental completo",
                                    "Ensino medio incompleto", "Ensino medio completo",
                                    "Educacao superior incompleta", "Educacao superior completa",
                                    "Nao se aplica")),
    "CS_GESTANT": ("gestante", ("1o Trimestre", "2o Trimestre", "3o Trimestre", "Idade gestacional ignorada",
                                "Nao", "Nao se aplica")),
}

# como a categoria aparece (sem acento na fonte, ou com o código na frente)
_NOMES = {
    "PB - Paucibacilar": "Paucibacilar", "MB - Multibacilar": "Multibacilar",
    "I - Indeterminada": "Indeterminada", "T - Tuberculóide": "Tuberculoide", "D - Dimorfa": "Dimorfa",
    "V - Virchowiana": "Virchowiana", "Não classificado": "Não classificada",
    "Grau zero": "Grau 0", "Grau I": "Grau I", "Grau II": "Grau II",
    "Indigena": "Indígena", "Nao se aplica": "Não se aplica", "Nao": "Não",
    "Analfabeto": "Analfabeto", "1a a 4a serie incompleta do EF": "1ª a 4ª série incompleta",
    "4a serie completa do EF": "4ª série completa", "5a a 8a serie incompleta do EF": "5ª a 8ª série incompleta",
    "Ensino fundamental completo": "Fundamental completo", "Ensino medio incompleto": "Médio incompleto",
    "Ensino medio completo": "Médio completo", "Educacao superior incompleta": "Superior incompleto",
    "Educacao superior completa": "Superior completo",
    "Transferência do mesmo município (outra unidade)": "Transf. mesmo município",
    "Transferência de outro município (mesma UF)": "Transf. outro município",
    "Transferência de outro estado": "Transf. outro estado", "Transferência de outro país": "Transf. outro país",
}

# variáveis em que o valor é a quantidade
NUMERICAS = frozenset({"NERVOSAFET", "DOSE_RECEB"})


def disponivel() -> bool:
    return SINAN.is_file() and POP_IBGE.is_file() and CONTATOS.is_file()


def anos() -> list[int]:
    return list(ANOS)


def extraido_em() -> str:
    return datetime.date.fromtimestamp(SINAN.stat().st_mtime).strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Bases
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _notificacoes() -> pd.DataFrame:
    """Todas as notificações sem erro diagnóstico, com ano/mês do diagnóstico e idade."""
    df = pd.read_parquet(SINAN)
    df = df[df["tipo_alta"].fillna("") != "Erro diagnóstico"].copy()
    diag = pd.to_datetime(df["data_diagnostico"], errors="coerce")
    df["ano"] = diag.dt.year.astype("Int64")
    df["mes"] = diag.dt.month.astype("Int64")
    df["idade"] = pd.to_numeric(df["idade_notificada"].str[:3], errors="coerce")
    df["novo"] = df["modo_entrada"] == "Caso novo"
    df["mb"] = df["classificacao_operacional"].str.startswith("MB", na=False)
    return df


def _casos_novos(ano: int | None = None) -> pd.DataFrame:
    df = _notificacoes()
    df = df[df["novo"]]
    return df if ano is None else df[df["ano"] == ano]


@lru_cache(maxsize=1)
def _contatos() -> pd.DataFrame:
    """SINAN bruto, só pros contatos: casos novos sem erro diagnóstico."""
    df = pd.read_parquet(CONTATOS)
    df = df[(df["modoentr"].astype(str) == "1") & (df["tpalta_n"].astype(str) != "8")].copy()
    df["ano"] = pd.to_datetime(df["dt_diag"], errors="coerce").dt.year
    df["mb"] = df["classopera"].astype(str) == "2"
    df["transferencia"] = df["tpalta_n"].astype(str).isin(["2", "3", "4", "5", "9"])
    for c in ("contreg", "contexam"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@lru_cache(maxsize=1)
def _pop_ibge() -> pd.DataFrame:
    return pd.read_parquet(POP_IBGE)


def _escala(ano: int) -> float:
    """Quanto multiplicar o IBGE do ano pra chegar no total do boletim."""
    pop = _pop_ibge()
    if ano in POPULACAO_BOLETIM:
        return POPULACAO_BOLETIM[ano] / pop.loc[pop["ano"] == ano, "populacao"].sum()
    # antes de 2020: o IBGE na escala de 2020, pra não ter degrau na série
    primeiro = min(POPULACAO_BOLETIM)
    return POPULACAO_BOLETIM[primeiro] / pop.loc[pop["ano"] == primeiro, "populacao"].sum()


def populacao(ano: int, idade_max: int | None = None) -> float | None:
    pop = _pop_ibge()
    linhas = pop[pop["ano"] == ano]
    if linhas.empty:
        return None
    if idade_max is not None:
        linhas = linhas[linhas["idade"] <= idade_max]
    return float(linhas["populacao"].sum()) * _escala(ano)


def _div(parte, total, fator: float = 100, minimo: int = 0) -> float | None:
    if parte is None or total is None or total <= 0 or total < minimo:
        return None
    return parte / total * fator


def _coorte(cn: pd.DataFrame, ano: int, transferencia: pd.Series) -> pd.DataFrame:
    """Coorte do MS pro ano de avaliação, sem transferências."""
    linhas = cn[((~cn["mb"]) & (cn["ano"] == ano - 1)) | (cn["mb"] & (cn["ano"] == ano - 2))]
    return linhas[~transferencia.reindex(linhas.index).fillna(False).astype(bool)]


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

def kpis(ano: int) -> dict[str, float | bool | None]:
    """Todas as métricas do pack no ano, com numerador e denominador das proporções."""
    cn = _casos_novos(ano)
    casos = float(len(cn))
    menores = float((cn["idade"] < 15).sum())
    pop, pop_0_14 = populacao(ano), populacao(ano, idade_max=14)

    classificados = float(cn["classificacao_operacional"].str[:2].isin(["PB", "MB"]).sum())
    multibacilares = float(cn["mb"].sum())

    gif = cn["avaliacao_incapacidade_diagnostico"].fillna("")
    avaliados = float(gif.str.startswith("Grau").sum())
    grau2 = float((gif == "Grau II").sum())
    gif_aval = _div(avaliados, casos, minimo=MINIMO_PARA_PERCENTUAL)
    prop_grau2 = _div(grau2, avaliados, minimo=MINIMO_PARA_PERCENTUAL)
    if gif_aval is None or gif_aval < MINIMO_GIF_AVALIADO:
        prop_grau2 = None

    todos = _casos_novos()
    coorte = _coorte(todos, ano, todos["tipo_alta"].fillna("").str.startswith("Transf"))
    alta = coorte["tipo_alta"].fillna("Não informado")
    n_coorte = float(len(coorte))
    sem_alta = float(alta.isin(["Não informado", ""]).sum())
    aberta = n_coorte > 0 and sem_alta / n_coorte > MAXIMO_SEM_ALTA
    curas, abandonos = float((alta == "Cura").sum()), float((alta == "Abandono").sum())

    brutos = _contatos()
    coorte_contatos = _coorte(brutos, ano, brutos["transferencia"])
    registrados = float(coorte_contatos["contreg"].sum())
    examinados = float(coorte_contatos["contexam"].sum())

    notif = _notificacoes()
    notif = notif[notif["ano"] == ano]

    return {
        "casos": casos,
        "pop": pop,
        "incid": _div(casos, pop, 1e5),
        "casos_0_14": menores,
        "pop_0_14": pop_0_14,
        "taxa_det_0_14": _div(menores, pop_0_14, 1e5),
        "cura": curas,
        "prop_mb_pct": _div(multibacilares, classificados, minimo=MINIMO_PARA_PERCENTUAL),
        "multibacilares": multibacilares,
        "classificados": classificados,
        "prop_grau2_pct": prop_grau2,
        "grau2": grau2,
        "avaliacao_base": avaliados,
        "gif_avaliado_pct": gif_aval,
        "gif_avaliados": avaliados,
        "gif_base": casos,
        "cura_pct": None if aberta else _div(curas, n_coorte, minimo=MINIMO_PARA_PERCENTUAL),
        "cura_encerrada": curas,
        "encerramentos": n_coorte,
        "abandono_pct": None if aberta else _div(abandonos, n_coorte, minimo=MINIMO_PARA_PERCENTUAL),
        "abandonos": abandonos,
        "saidas": n_coorte,
        "contatos_pct": None if aberta else _div(examinados, registrados, minimo=MINIMO_PARA_PERCENTUAL),
        "contatos_examinados": examinados,
        "contatos_registrados": registrados,
        "recidiva_pct": _div(float((notif["modo_entrada"] == "Recidiva").sum()), float(len(notif)),
                             minimo=MINIMO_PARA_PERCENTUAL),
        "coorte_aberta": aberta,
        "cobertura_saidas": 1 - sem_alta / n_coorte if n_coorte else None,
    }


@lru_cache(maxsize=1)
def kpis_todos() -> pd.DataFrame:
    return pd.DataFrame([{"ano": a, **kpis(a)} for a in ANOS])


def serie_anual(metrica: str) -> pd.DataFrame:
    tabela = kpis_todos()
    return pd.DataFrame({"ano": tabela["ano"], "valor": tabela[metrica]})


def serie_qualidade() -> pd.DataFrame:
    """Os indicadores dos tópicos, por ano: ``contatos_pct``, ``gif_avaliado_pct``, ``grau2_pct``…"""
    t = kpis_todos()
    return pd.DataFrame({"ano": t["ano"], "contatos_pct": t["contatos_pct"],
                         "gif_avaliado_pct": t["gif_avaliado_pct"], "grau2_pct": t["prop_grau2_pct"],
                         "cura_pct": t["cura_pct"], "abandono_pct": t["abandono_pct"]})


def serie_classificacao() -> pd.DataFrame:
    """``ano``, ``pb``, ``mb``, ``prop_mb``."""
    t = kpis_todos()
    return pd.DataFrame({"ano": t["ano"], "pb": t["classificados"] - t["multibacilares"],
                         "mb": t["multibacilares"], "prop_mb": t["prop_mb_pct"]})


def serie_0_14() -> pd.DataFrame:
    """``ano``, ``casos``, ``taxa``."""
    t = kpis_todos()
    return pd.DataFrame({"ano": t["ano"], "casos": t["casos_0_14"], "taxa": t["taxa_det_0_14"]})


# ---------------------------------------------------------------------------
# Mês: canal endêmico e epicurva
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Canal:
    """As camadas do canal endêmico, no formato do core (o mesmo do hansepe)."""

    faixa: pd.DataFrame
    referencia: pd.DataFrame
    atual: pd.DataFrame
    anos: tuple[int, ...]

    @property
    def vazio(self) -> bool:
        return self.atual.empty or self.faixa.empty


def _incidencia_mensal(ano: int, grau: str | None) -> pd.DataFrame:
    cn = _casos_novos(ano)
    if grau:
        cn = cn[cn["avaliacao_incapacidade_diagnostico"].fillna("Não informado") == grau]
    pop = populacao(ano)
    por_mes = cn["mes"].value_counts().reindex(range(1, 13), fill_value=0)
    return pd.DataFrame({"mes": por_mes.index, "mes_nome": [MESES[m - 1] for m in por_mes.index],
                         "valor": por_mes.to_numpy() / pop * 1e5 if pop else np.nan})


def canal(ano: int, grau: str | None = None) -> Canal:
    """O ano contra a faixa interquartil dos anos anteriores (a regra do hansepe)."""
    atual = _incidencia_mensal(ano, grau)
    anteriores = [_incidencia_mensal(a, grau).assign(ano=a)
                  for a in range(ano - ANOS_REFERENCIA, ano) if a in ANOS]
    meses = atual[["mes", "mes_nome"]]
    if not anteriores:
        return Canal(meses.assign(q1=np.nan, q3=np.nan),
                     pd.DataFrame(columns=["mes", "mes_nome", "ano", "valor"]), atual, ())
    historico = pd.concat(anteriores, ignore_index=True)
    quartis = historico.groupby("mes")["valor"].agg(
        q1=lambda s: float(np.quantile(s, 0.25)), q3=lambda s: float(np.quantile(s, 0.75)),
    ).reset_index()
    return Canal(meses.merge(quartis, on="mes", how="left"), historico[["mes", "mes_nome", "ano", "valor"]],
                 atual, tuple(sorted(historico["ano"].unique())))


def meses_fora_da_faixa(c: Canal) -> pd.DataFrame:
    if c.vazio:
        return pd.DataFrame(columns=["mes", "valor", "q1", "q3", "posicao"])
    j = c.atual.merge(c.faixa[["mes", "q1", "q3"]], on="mes")
    fora = j[(j["valor"] > j["q3"]) | (j["valor"] < j["q1"])].copy()
    fora["posicao"] = np.where(fora["valor"] > fora["q3"], "acima", "abaixo")
    return fora


def epicurva(ano_min: int, ano_max: int) -> pd.DataFrame:
    """Casos novos por mês em série contínua: ``ano_mes``, ``ano``, ``mes``, ``casos``."""
    cn = _casos_novos()
    cn = cn[(cn["ano"] >= ano_min) & (cn["ano"] <= ano_max)]
    idx = pd.MultiIndex.from_product([range(ano_min, ano_max + 1), range(1, 13)], names=["ano", "mes"])
    serie = cn.groupby(["ano", "mes"]).size().reindex(idx, fill_value=0).rename("casos").reset_index()
    serie["ano_mes"] = serie["ano"].astype(str) + "-" + serie["mes"].astype(str).str.zfill(2)
    return serie[["ano_mes", "ano", "mes", "casos"]]


# ---------------------------------------------------------------------------
# Perfil
# ---------------------------------------------------------------------------

def piramide(ano: int) -> pd.DataFrame:
    """``sexo``, ``faixa_ord``, ``faixa_etaria``, ``valor``, ``pop`` (a do core)."""
    cn = _casos_novos(ano)
    pop = _pop_ibge()
    pop = pop[pop["ano"] == ano]
    escala = _escala(ano) if not pop.empty else 0
    sexo = cn["sexo"].map({"Masculino": "M", "Feminino": "F"})
    registros = []
    for s in ("M", "F"):
        for ordem, (nome, de, ate) in enumerate(FAIXAS):
            casos = ((sexo == s) & cn["idade"].between(de, ate)).sum()
            p = pop[(pop["sexo"] == s) & pop["idade"].between(de, ate)]["populacao"].sum() * escala
            registros.append({"sexo": s, "faixa_ord": ordem, "faixa_etaria": nome,
                              "valor": float(casos), "pop": float(p)})
    return pd.DataFrame(registros)


def _categorias(variavel: str, linhas: pd.DataFrame) -> pd.Series:
    """A categoria de cada caso, já no nome da tela; ``None`` pra campo vazio."""
    coluna, _ = TOPICOS[variavel]
    valores = linhas[coluna]
    if variavel in NUMERICAS:
        return pd.to_numeric(valores, errors="coerce").astype("Int64").astype(str).where(valores.notna())
    return valores.map(lambda v: None if v in _IGNORADOS or v != v else _NOMES.get(v, v))


def _ordem(variavel: str, presentes) -> list[str]:
    _, ordem = TOPICOS[variavel]
    if variavel in NUMERICAS:
        return sorted(presentes, key=lambda c: int(c))
    conhecidas = [_NOMES.get(c, c) for c in ordem]
    return [c for c in conhecidas if c in presentes] + sorted(c for c in presentes if c not in conhecidas)


def total_de_casos(ano: int) -> int:
    return len(_casos_novos(ano))


def composicao(variavel: str, ano: int) -> pd.DataFrame:
    """``categoria``, ``n``, ``pct``, ``total`` dos casos novos com o campo preenchido."""
    cat = _categorias(variavel, _casos_novos(ano)).dropna()
    n = cat.value_counts()
    n = n.reindex(_ordem(variavel, set(n.index)))
    total = float(n.sum())
    pct = (n / total * 100).to_numpy() if total >= MINIMO_PARA_PERCENTUAL else [None] * len(n)
    return pd.DataFrame({"categoria": n.index, "n": n.to_numpy().astype(float), "pct": pct, "total": total})


def serie_composicao(variavel: str) -> pd.DataFrame:
    """``ano``, ``categoria``, ``n``, ``pct`` (cada ano soma 100%)."""
    cn = _casos_novos()
    cn = cn[cn["ano"].isin(ANOS)]
    tabela = pd.DataFrame({"ano": cn["ano"].astype(int), "categoria": _categorias(variavel, cn)}).dropna()
    n = tabela.groupby(["ano", "categoria"]).size().rename("n").reset_index()
    n["pct"] = n["n"] / n.groupby("ano")["n"].transform("sum") * 100
    ordem = {c: i for i, c in enumerate(_ordem(variavel, set(n["categoria"])))}
    return n.sort_values(["ano", "categoria"], key=lambda s: s.map(ordem) if s.name == "categoria" else s)
