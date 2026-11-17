"""A extração sem banco: recorte e lista de colunas."""

from __future__ import annotations

from scripts import extrair_sinan_df as ex


def test_so_residentes_do_df() -> None:
    assert "estado_residencia = 'Distrito Federal'" in ex.SQL


def test_nao_puxa_select_estrela() -> None:
    assert "*" not in ex.SQL
    assert len(ex.COLUNAS) == len(set(ex.COLUNAS))


def test_tem_o_que_o_boletim_usa() -> None:
    precisa = {
        "data_diagnostico", "modo_entrada", "tipo_alta", "classificacao_operacional",
        "avaliacao_incapacidade_diagnostico", "avaliacao_incapacidade_atual",
        "contatos_examinados", "idade_notificada", "sexo", "raca_cor",
    }
    assert precisa <= set(ex.COLUNAS)
