"""O que o dados.py devolve e a distância até o boletim da SES-DF 2021–2025."""

from __future__ import annotations

import pytest

from src import dados, doencas

pytestmark = pytest.mark.dado

pack = doencas.carregar()

# boletim SES-DF 2021–2025 (Tabela 1 e Figuras 12 a 17)
BOLETIM = {
    "casos": {2021: 130, 2022: 158, 2023: 130, 2024: 113, 2025: 157},
    "abandono_pct": {2024: 8.2, 2025: 8.9},
    "contatos_pct": {2023: 71.6, 2024: 82.3, 2025: 91.0},
    "prop_grau2_pct": {2021: 23.9, 2022: 14.7, 2023: 12.2, 2024: 17.2, 2025: 7.9},
    "recidiva_pct": {2023: 8.1, 2024: 9.3, 2025: 20.4},
}

# quanto a silver pode se afastar (a extração da SES é outra)
TOLERANCIA = {"casos": 6, "abandono_pct": 0.5, "contatos_pct": 2.5, "prop_grau2_pct": 2.0,
              "recidiva_pct": 1.0}


def test_anos_fechados() -> None:
    assert dados.anos() == list(range(2010, 2026))


def test_kpis_do_df_tem_tudo_que_a_tela_pede() -> None:
    pedidas = set(pack.LAYOUT_KPI) | set(pack.INDICADORES_QUALIDADE)
    for fracao in pack.FRACAO_KPI.values():
        pedidas |= set(fracao)
    assert pedidas <= set(dados.kpis(2025))


@pytest.mark.parametrize("metrica", list(BOLETIM))
def test_perto_do_boletim(metrica: str) -> None:
    for ano, esperado in BOLETIM[metrica].items():
        valor = dados.kpis(ano)[metrica]
        assert valor is not None and abs(valor - esperado) <= TOLERANCIA[metrica], (ano, valor, esperado)


def test_deteccao_usa_a_populacao_do_boletim() -> None:
    assert dados.kpis(2025)["incid"] == pytest.approx(4.85, abs=0.01)


def test_grau2_some_com_pouco_gif_avaliado() -> None:
    for ano in dados.anos():
        k = dados.kpis(ano)
        if k["gif_avaliado_pct"] is not None and k["gif_avaliado_pct"] < 75:
            assert k["prop_grau2_pct"] is None, ano


def test_formas_dos_graficos() -> None:
    ano = 2025
    assert list(dados.serie_anual("incid").columns) == ["ano", "valor"]
    canal = dados.canal(ano)
    assert not canal.vazio and len(canal.anos) == 5
    epi = dados.epicurva(2016, ano)
    assert len(epi) == 120 and epi["casos"].sum() > 0
    for variavel in pack.VARIAVEIS_DESTAQUE:
        tabela = dados.composicao(variavel, ano)
        assert {"categoria", "n", "pct", "total"} <= set(tabela.columns) and not tabela.empty
        assert {"ano", "categoria", "n", "pct"} <= set(dados.serie_composicao(variavel).columns)
    pir = dados.piramide(ano)
    assert set(pir["sexo"]) == {"M", "F"} and (pir["pop"] > 0).all()
    assert {"contatos_pct", "gif_avaliado_pct", "grau2_pct", "cura_pct", "abandono_pct"} <= set(
        dados.serie_qualidade().columns)


# ---------------------------------------------------------------------------
# Por área (tabelas do boletim)
# ---------------------------------------------------------------------------

def test_mapa_cobre_as_35_ras_e_as_7_regioes() -> None:
    for ano in dados.anos_por_area():
        assert set(dados.valores_mapa("casos", ano, "RA").index) == set(dados.ras()["ra_chave"]), ano
        assert set(dados.valores_mapa("casos", ano, "RS").index) == set(dados.regioes()["regiao_saude"]), ano


def test_areas_somam_o_total_do_boletim() -> None:
    from src import fonte_boletim

    for ano in dados.anos_por_area():
        total = fonte_boletim.do_df("casos", ano)
        assert dados.valores_mapa("casos", ano, "RA").sum() == total, ano
        assert dados.valores_mapa("casos", ano, "RS").sum() == total, ano


def test_tabela_1_do_boletim() -> None:
    assert dados.valores_mapa("casos", 2025, "RA")["PLANO PILOTO"] == 11
    assert dados.valores_mapa("incid", 2025, "RA")["SIA"] == pytest.approx(37.14)
    assert dados.valores_mapa("casos", 2020, "RA")["PLANALTINA"] == 28
    assert dados.valores_mapa("incid", 2025, "RS")["Leste"] == pytest.approx(7.11)


def test_taxa_errada_do_boletim_foi_refeita() -> None:
    """Gama 2025 vem 1,44 no PDF com 6 casos (daria 417 mil hab.)."""
    assert dados.valores_mapa("incid", 2025, "RA")["GAMA"] == pytest.approx(4.13, abs=0.05)


def test_area_so_tem_casos_e_deteccao_enquanto_nao_houver_ra_no_sinan() -> None:
    assert not dados.tem_dado_por_area()
    k = dados.kpis(2025, ("RA", "PLANO PILOTO"))
    assert k == {"incid": pytest.approx(4.43), "casos": 11}
    assert dados.kpis(2015, ("RA", "PLANO PILOTO")) == {}
    assert dados.piramide(2025, ("RA", "PLANO PILOTO")).empty


def test_regiao_de_cada_ra_bate_com_a_malha() -> None:
    from src import fonte_boletim

    t = fonte_boletim._tabela()
    ras = t[t["nivel"] == "RA"].drop_duplicates("chave").set_index("chave")["regiao"]
    malha = dados.ras().set_index("ra_chave")["regiao_saude"]
    assert (ras == malha.reindex(ras.index)).all()
