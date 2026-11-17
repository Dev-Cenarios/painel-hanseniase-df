"""O app inteiro rodando no AppTest.

Confere também que não tem aviso: o resiliencia.painel esconde erro de bloco
atrás de um aviso, e o app "sobe" mesmo com gráfico quebrado.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import doencas

APP = str(Path(__file__).resolve().parents[1] / "app.py")
LIMITE = 120

pytestmark = pytest.mark.dado

pack = doencas.carregar()


def _rodar(**estado) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=LIMITE)
    for chave, valor in estado.items():
        at.session_state[chave] = valor
    return at.run()


def _conferir(at: AppTest) -> None:
    assert not at.exception, [e.value for e in at.exception]
    assert not at.warning, [w.value for w in at.warning]


def _cards(at: AppTest) -> list[str]:
    return [m.value for m in at.markdown if 'class="kpi-card' in m.value]


def _mapas(at: AppTest) -> list[str]:
    return [c.proto.json_args for c in at.get("component_instance") if '"spec"' in c.proto.json_args]


def test_sobe_com_as_secoes_do_hansepe() -> None:
    at = _rodar()
    _conferir(at)
    # 5 da faixa, 2 proporções e 4 de qualidade
    assert len(_cards(at)) == 11
    texto = " ".join(m.value for m in at.markdown)
    for secao in ("Indicadores de qualidade do programa", "Tópicos de interesse",
                  "Classificação operacional por ano", "Casos de 0 a 14 anos por ano"):
        assert secao in texto, secao


def test_mapa_por_ra_com_as_divisas_das_regioes() -> None:
    mapas = _mapas(_rodar())
    assert len(mapas) == 1 and "regioes-saude" in mapas[0]


def test_mapa_por_regiao_de_saude() -> None:
    at = _rodar(recorte="RS")
    _conferir(at)
    assert len(_mapas(at)) == 1


@pytest.mark.parametrize("metrica", pack.METRICAS_MAPA)
def test_toda_metrica_do_mapa_desenha(metrica: str) -> None:
    _conferir(_rodar(metrica=metrica))


def test_ra_escolhida_muda_os_cards_e_avisa() -> None:
    geral, ra = _rodar(), _rodar(area=("RA", "PLANO PILOTO"))
    _conferir(ra)
    assert _cards(geral)[:5] != _cards(ra)[:5]
    assert any("Plano Piloto" in m.value for m in ra.markdown)
    assert any("SINAN georreferenciado" in c.value for c in ra.caption)


def test_ano_sem_ra_nao_quebra() -> None:
    at = _rodar(ano=2015)
    _conferir(at)
    assert not _mapas(at)
