"""Painel de Monitoramento da Hanseníase do DF — a tela do hansepe, com os dados do DF.

Mesmas seções e na mesma ordem: KPIs, controles, mapa com proporções e abas,
indicadores de qualidade, tópicos de interesse e séries anuais. Aqui só monta a
tela; as contas ficam em src/.

O SINAN do banco ainda não tem RA: por área só há casos novos e detecção (Tabela 1
do boletim), e o resto da tela fica no DF inteiro. Quando o dado
georreferenciado chegar, `dados.tem_dado_por_area()` vira True e tudo segue a área.
"""

from __future__ import annotations

import contextlib

import pandas as pd
import pydeck
import streamlit as st
from cenarios_core import grafico_componente, mapa, mapa_componente, resiliencia

from src import config, dados, doencas, estilo
from src.theme import componentes as ui

pack = doencas.carregar()

st.set_page_config(page_title=config.TITULO_PAINEL, layout="wide", initial_sidebar_state="collapsed")

# os cinco da faixa; as proporções vão pra coluna da direita
KPIS_FAIXA = tuple(m for m in pack.LAYOUT_KPI if m not in pack.FRACAO_KPI)
KPIS_PROPORCAO = tuple(m for m in pack.LAYOUT_KPI if m in pack.FRACAO_KPI)

RECORTES = ("RA", "RS")
ROTULO_RECORTE = {"RA": "Regiões Administrativas", "RS": "Regiões de Saúde"}
UNIDADE_RECORTE = {"RA": "RAs", "RS": "regiões de saúde"}

ROTULO_CLASSIFICACAO = {"NATURAL": "Quebras naturais", "QUARTIL": "Quintis", "FIXA": "Endemicidade"}
AJUDA_CLASSIFICACAO = """Como as cores repartem os valores.

**Quebras naturais** agrupam áreas parecidas e separam as diferentes.

**Quintis** põem um quinto das áreas em cada cor. A régua muda a cada ano.

**Endemicidade** usa os parâmetros oficiais: Baixo (< 2), Médio (2,00–9,99), Alto (10,00–19,99), Muito alto (20,00–39,99) e Hiperendêmico (≥ 40 por 100 mil). Só nas taxas de detecção."""
CLASSIFICACAO_SEM_REGUA = "NATURAL"

TODO_O_DF = "— todo o DF —"
FONTE_DADOS = "Fonte: Sinan/SES-DF; população IPEDF"

ALTURA_MAPA = 520
ALTURA_LINHA_1 = ALTURA_MAPA

# divisa das Regiões de Saúde por cima das RAs
COR_REGIAO = [18, 52, 107, 230]
LARGURA_REGIAO = 2.2

JANELAS = (5, 10, 15)
JANELA_PADRAO = 10

# gráfico | calha com a régua, como o boletim
CALHA = [7, 3]

AVISO_CANAL = ("A faixa é o intervalo entre o 1º e o 3º quartil dos {n} anos anteriores ({anos}). "
               "Mês acima da faixa está acima do que o DF costuma ter naquele mês.")

TTL = 24 * 3600


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

@st.cache_data(ttl=TTL, show_spinner=False)
def _kpis(ano: int, area):
    return dados.kpis(ano, area)


@st.cache_resource(show_spinner=False)
def _camada(recorte: str):
    return dados.ras() if recorte == "RA" else dados.regioes()


@st.cache_resource(show_spinner=False)
def _geojson(recorte: str):
    return mapa.geometrias_geojson(_camada(recorte))


@st.cache_resource(show_spinner=False)
def _divisas_regioes():
    return dados.regioes().__geo_interface__


@st.cache_data(ttl=TTL, show_spinner=False)
def _valores_mapa(metrica: str, ano: int, recorte: str):
    return dados.valores_mapa(metrica, ano, recorte)


@st.cache_data(ttl=TTL, show_spinner=False)
def _nomes_ras() -> dict[str, str]:
    camada = dados.ras()
    return dict(zip(camada["ra_chave"], camada["ra_nome"], strict=True))


@st.cache_data(ttl=TTL, show_spinner=False)
def _regiao_da_ra() -> dict[str, str]:
    camada = dados.ras()
    return dict(zip(camada["ra_chave"], camada["regiao_saude"], strict=True))


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------

anos = dados.anos()
anos_area = dados.anos_por_area()
st.session_state.setdefault("ano", anos[-1])
st.session_state.setdefault("metrica", pack.METRICAS_MAPA[0])
st.session_state.setdefault("recorte", "RA")
st.session_state.setdefault("area", None)


def _ao_mudar_metrica() -> None:
    # aplica antes do rerun, pros cards de cima já verem a métrica nova
    escolhida = st.session_state.get("metrica_sel")
    if escolhida:
        st.session_state["metrica"] = escolhida


def _ao_clicar_na_legenda() -> None:
    st.session_state["faixa_realcada"] = st.session_state.get("faixa_legenda")


def _ao_mudar_recorte() -> None:
    if escolhido := st.session_state.get("recorte_sel"):
        st.session_state["recorte"] = escolhido
        st.session_state["area"] = None
        st.session_state["faixa_realcada"] = None


def _ao_buscar() -> None:
    escolha = st.session_state.get("busca")
    if escolha in (None, TODO_O_DF):
        st.session_state["area"] = None
    else:
        st.session_state.update(area=("RA", escolha), recorte="RA")


# lê os cliques antes de desenhar (mapa e ranking), clicar de novo volta pro DF
for _comp, _nonce, _ler in (
    ("mapa", "clique_mapa", mapa_componente.alvo_do_clique),
    ("ranking", "clique_ranking", grafico_componente.alvo_do_clique),
):
    _alvo, _novo = _ler(st.session_state.get(_comp), st.session_state.get(_nonce))
    if _novo:
        st.session_state[_nonce] = _novo
    if _alvo:
        clicada = (st.session_state["recorte"], str(_alvo))
        st.session_state["area"] = None if clicada == st.session_state["area"] else clicada

# os widgets seguem o estado, nunca o contrário
st.session_state["metrica_sel"] = st.session_state["metrica"]
st.session_state["recorte_sel"] = st.session_state["recorte"]

ano: int = st.session_state["ano"] if st.session_state["ano"] in anos else anos[-1]
metrica: str = st.session_state["metrica"]
recorte: str = st.session_state["recorte"]
area = st.session_state["area"]
# o resto da tela só segue a área quando o SINAN tiver RA
area_dados = area if dados.tem_dado_por_area() else None


def _local(com_area: bool = True) -> str:
    return dados.nome_area(area if com_area else area_dados)


st.markdown(estilo.css(), unsafe_allow_html=True)
st.markdown(f"<style>:root{{--intro-accent:{pack.CORES['primary']};}}</style>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cabeçalho e faixa de KPIs
# ---------------------------------------------------------------------------

if area is None:
    onde = None
elif area[0] == "RS":
    onde = f"Região {area[1]}"
else:
    onde = f"{dados.nome_area(area)} (Região {_regiao_da_ra().get(area[1])})"
trilha = " • ".join(p for p in ("Distrito Federal", onde, f"Ano de diagnóstico: {ano}") if p)
st.markdown(ui.faixa_intro(f"Painel de Monitoramento da {pack.TITULO} do DF", escopo=trilha,
                           cor=pack.CORES["primary"]), unsafe_allow_html=True)


def _quadro(m: str) -> None:
    """A régua do boletim ao lado do gráfico."""
    if texto := pack.texto_parametros(m):
        st.markdown(ui.quadro_parametros(*texto), unsafe_allow_html=True)


def _janela() -> int:
    return int(st.session_state.get("janela") or JANELA_PADRAO)


def _recortar(tabela: pd.DataFrame) -> pd.DataFrame:
    if tabela.empty or "ano" not in tabela:
        return tabela
    return tabela[(tabela["ano"] <= ano) & (tabela["ano"] > ano - _janela())]


def _com_calha(titulo: str, *, ajuda: str = ""):
    st.markdown(ui.titulo_painel(titulo, ajuda=ajuda), unsafe_allow_html=True)
    return st.columns(CALHA, vertical_alignment="top")


def _calha_base(tabela: pd.DataFrame, *, universo: int = 0) -> None:
    """Quantos casos sustentam a distribuição."""
    if tabela.empty:
        return
    total = int(tabela["total"].iloc[0])
    if universo and total <= universo:
        linha = (f"{ui.formatar_inteiro(total)} de {ui.formatar_inteiro(universo)} casos novos com o "
                 f"campo preenchido ({ui.formatar_decimal(total / universo * 100, 1)}%)")
    else:
        linha = f"{ui.formatar_inteiro(total)} casos novos com o campo preenchido"
    st.markdown(ui.quadro_parametros("Base do cálculo", (linha,), fonte=FONTE_DADOS), unsafe_allow_html=True)


def _card(m: str, atual: dict, anterior: dict, local: str) -> None:
    proporcao = m in pack.FRACAO_KPI
    valor, antes = atual.get(m), anterior.get(m)
    taxa = m in pack.TAXAS
    sub = f"{local} • {ano}"
    if (fracao := pack.FRACAO_KPI.get(m)) and valor is not None:
        num, den = (atual.get(c) for c in fracao)
        if num is not None and den:
            sub += f" • {ui.formatar_inteiro(num)} de {ui.formatar_inteiro(den)}"
    if classe := pack.classe_de(m, valor):
        sub += f" • {classe}"
    st.markdown(ui.kpi_card(
        pack.rotulo(m) if proporcao else pack.rotulo_card(m),
        ui.formatar_decimal(valor) if taxa else ui.formatar_inteiro(valor),
        cor=pack.cor(m), subtitulo=sub,
        selecionado=(not proporcao) and m == metrica,
        badge_delta=ui.delta(valor, antes, taxa=taxa, bom_se_cai=m in pack.BOM_SE_CAI),
        ajuda=" — ".join(p for p in (pack.rotulo(m), pack.descricao(m)) if p),
        icone="" if proporcao else pack.icone(m),
    ), unsafe_allow_html=True)


def _anterior(a) -> dict:
    return _kpis(ano - 1, a) if ano - 1 in anos else {}


with resiliencia.painel("Indicadores"), st.container(key="faixa-kpis"):
    atual = _kpis(ano, area)
    for coluna, m in zip(st.columns(len(KPIS_FAIXA)), KPIS_FAIXA, strict=True):
        with coluna:
            _card(m, atual, _anterior(area), _local())
if area and not dados.tem_dado_por_area():
    st.caption(f"Por área o boletim só traz casos novos e detecção ({anos_area[0]}–{anos_area[-1]}). "
               "O resto do painel segue o DF inteiro até o SINAN georreferenciado chegar.")


# ---------------------------------------------------------------------------
# Controles
# ---------------------------------------------------------------------------

with resiliencia.painel("Controles"), st.container(border=True, key="cartao-controles"):
    col_ano, col_metrica, col_recorte, col_cores, col_busca = st.columns(
        [1.1, 2.6, 3.2, 3.6, 2.6], vertical_alignment="top")
    col_ano.selectbox("Ano", anos, key="ano")
    col_metrica.segmented_control(
        "Métrica", pack.METRICAS_MAPA, format_func=pack.rotulo_curto, key="metrica_sel",
        on_change=_ao_mudar_metrica, help="O que o mapa pinta e o ranking ordena.",
    )
    col_recorte.segmented_control(
        "Nível do mapa", RECORTES, format_func=ROTULO_RECORTE.get, key="recorte_sel",
        on_change=_ao_mudar_recorte, help="Por RA ou somado por Região de Saúde.",
    )
    with col_cores:
        com_regua = pack.tem_regua_oficial(metrica)
        opcoes = [c for c in mapa.CLASSIFICACOES if c != "FIXA" or com_regua]
        preferida = st.session_state.get("classificacao", "FIXA")
        forcada = preferida not in opcoes
        escolhida = CLASSIFICACAO_SEM_REGUA if forcada else preferida
        classificacao = st.segmented_control(
            "Cores", opcoes, format_func=ROTULO_CLASSIFICACAO.get, default=escolhida, help=AJUDA_CLASSIFICACAO,
        )
        if classificacao and not (forcada and classificacao == CLASSIFICACAO_SEM_REGUA):
            st.session_state["classificacao"] = classificacao
        classificacao = classificacao or escolhida
    nomes_ras = _nomes_ras()
    opcoes_busca = [TODO_O_DF, *sorted(nomes_ras, key=nomes_ras.get)]
    st.session_state["busca"] = area[1] if area and area[0] == "RA" else TODO_O_DF
    col_busca.selectbox("Buscar RA", opcoes_busca, key="busca", on_change=_ao_buscar,
                        format_func=lambda c: c if c == TODO_O_DF else nomes_ras[c])


# ---------------------------------------------------------------------------
# Linha 1: mapa à esquerda, proporções e abas à direita
# ---------------------------------------------------------------------------

esquerda, direita = st.columns([5, 6], gap="medium")
escala = None

with esquerda, resiliencia.painel("Mapa"), st.container(border=True, key="cartao-mapa"):
    serie_mapa = _valores_mapa(metrica, ano, recorte)
    if serie_mapa.dropna().empty:
        st.markdown(ui.painel_vazio(
            "Mapa", f"Por área o boletim só traz {anos_area[0]} a {anos_area[-1]}. Escolha um desses anos.",
            mapa=True), unsafe_allow_html=True)
    else:
        chave, nome = ("ra_chave", "ra_nome") if recorte == "RA" else ("regiao_saude", "regiao_saude")
        notas = (pd.Series(_regiao_da_ra()).map(lambda r: f"Região {r}") if recorte == "RA" else None)
        desenho, escala = mapa.deck(
            _camada(recorte), serie_mapa, chave=chave, coluna_nome=nome,
            rampa=pack.rampa_mapa(metrica), rotulo_metrica=pack.rotulo(metrica),
            decimais=1 if metrica in pack.TAXAS else 0, altura=ALTURA_MAPA, geometrias=_geojson(recorte),
            destacado=area[1] if area and area[0] == recorte else None, metodo=classificacao,
            cortes_fixos=pack.cortes_fixos(metrica), nomes_fixos=pack.nomes_fixos(metrica),
            casas_regua=pack.casas_regua(metrica), faixa_realcada=st.session_state.get("faixa_realcada"),
            notas=notas, quadro_ilhas=False,
        )
        if recorte == "RA":
            desenho.layers.append(pydeck.Layer(
                "GeoJsonLayer", id="regioes-saude", data=_divisas_regioes(), stroked=True, filled=False,
                get_line_color=COR_REGIAO, line_width_min_pixels=LARGURA_REGIAO, pickable=False,
            ))
            # o deck sai do core já serializado; sem refazer, a camada nova não vai (falta parâmetro no core)
            vars(desenho).pop("to_json", None)
            mapa._compactar(desenho)
        mapa_componente.desenhar(desenho, altura=ALTURA_MAPA, key="mapa",
                                 titulo=f"Mapa do Distrito Federal: {pack.rotulo(metrica)}")

        contagem = mapa.classificar(serie_mapa, escala).value_counts()
        faixas = [r for r in escala.rotulos if r in escala.cores]
        nomes_faixa = pack.nomes_fixos(metrica) if classificacao == "FIXA" else None

        def _rotulo_faixa(r: str, _nomes=nomes_faixa, _faixas=faixas) -> str:
            i = _faixas.index(r) if r in _faixas else -1
            nome_faixa = f"  {_nomes[i]}" if _nomes and 0 <= i < len(_nomes) else ""
            return f"{r}{nome_faixa}  ({int(contagem.get(r, 0))})"

        st.markdown(ui.titulo_legenda(pack.rotulo_mapa(metrica), UNIDADE_RECORTE[recorte].capitalize()),
                    unsafe_allow_html=True)
        st.markdown(ui.cores_das_faixas("faixa_legenda", [escala.cores[r] for r in faixas]),
                    unsafe_allow_html=True)
        st.pills("Faixa em destaque", faixas, format_func=_rotulo_faixa, selection_mode="single",
                 key="faixa_legenda", on_change=_ao_clicar_na_legenda, label_visibility="collapsed")
        st.caption(("Divisas grossas: as 7 Regiões de Saúde. " if recorte == "RA" else "")
                   + "Por área: Tabela 1 dos boletins de hanseníase da SES-DF.")
    if area:
        st.button("Ver o DF inteiro", key="voltar_df", on_click=lambda: st.session_state.update(area=None))


with direita:
    with resiliencia.painel("Proporções"):
        proporcoes = _kpis(ano, area_dados)
        for coluna, m in zip(st.columns(len(KPIS_PROPORCAO)), KPIS_PROPORCAO, strict=True):
            with coluna:
                _card(m, proporcoes, _anterior(area_dados), _local(com_area=False))

    with st.container(border=True, key="cartao-graficos"):
        aba_evolucao, aba_ranking, aba_piramide = st.tabs(
            ["Evolução temporal", f"Ranking de {UNIDADE_RECORTE[recorte]}", "Pirâmide etária"])

        with aba_evolucao, resiliencia.painel("Evolução temporal"):
            c_h, c_g = st.columns([3, 2], vertical_alignment="bottom")
            horizonte = c_h.radio("Horizonte", ["Meses do ano", "Todos os anos"], horizontal=True,
                                  label_visibility="collapsed")
            mensal = horizonte == "Meses do ano"
            rodape = ""
            if mensal:
                escolha = c_g.selectbox("Grau de incapacidade", ["Todos os graus", *dados.GRAUS_SERIE])
                canal = dados.canal(ano, area_dados, None if escolha == "Todos os graus" else escolha)
                figura = grafico_componente.canal_endemico(canal, rotulo=pack.rotulo("incid"),
                                                           cor=pack.cor("incid"), anos_agrupados=True)
                titulo_serie = f"Canal endêmico — {_local(com_area=False)}"
                if canal.anos:
                    rodape = AVISO_CANAL.format(n=len(canal.anos), anos=", ".join(str(a) for a in canal.anos))
                    if acima := int((dados.meses_fora_da_faixa(canal)["posicao"] == "acima").sum()):
                        rodape += f" Em {ano}, **{acima} de 12 meses** ficaram acima da faixa."
            else:
                figura = grafico_componente.evolucao_anual(
                    _recortar(dados.serie_anual("incid", area)), rotulo=pack.rotulo("incid"),
                    cor=pack.cor("incid"), ano=ano)
                titulo_serie = f"Taxa de detecção por ano — {_local()}"
            st.markdown(ui.titulo_painel(titulo_serie, ajuda=rodape), unsafe_allow_html=True)
            colunas = None if mensal else st.columns([7, 3], vertical_alignment="top")
            with contextlib.nullcontext() if mensal else colunas[0]:
                grafico_componente.desenhar(figura, altura=ALTURA_LINHA_1 - 250,
                                            key="canal" if mensal else "anual")
            if not mensal:
                with colunas[1]:
                    _quadro("incid")

            titulo_epi, botoes_epi = st.columns([4, 6], vertical_alignment="center")
            titulo_epi.markdown(ui.titulo_painel(
                "Epicurva por mês", ajuda="Casos novos por mês de diagnóstico, em série contínua. "
                                          "A janela vale também para as demais séries da página."),
                unsafe_allow_html=True)
            botoes_epi.segmented_control("Janela", JANELAS, format_func=lambda j: f"{j}a",
                                         default=st.session_state.get("janela", JANELA_PADRAO),
                                         key="janela", label_visibility="collapsed")
            grafico_componente.desenhar(
                grafico_componente.epicurva(
                    dados.epicurva(max(ano - _janela() + 1, anos[0]), ano, area_dados),
                    rotulo="Casos novos", rotulo_x="Mês de diagnóstico", cor=pack.cor("casos"),
                    ano_em_foco=ano, area=True),
                altura=200, key="epicurva",
            )

        with aba_ranking, resiliencia.painel("Ranking"):
            top_n = (st.slider("Quantos exibir", 5, 35, 15, step=5, key="top_n") if recorte == "RA" else 7)
            tabela = dados.ranking(metrica, ano, recorte, top_n)
            if recorte == "RA" and not tabela.empty:
                tabela["nome"] = tabela["nome"] + " (" + tabela["chave"].map(_regiao_da_ra()) + ")"
            grafico_componente.desenhar(
                grafico_componente.ranking(
                    tabela, rotulo=pack.rotulo(metrica), cor=pack.cor(metrica), escala=escala,
                    selecionado=area[1] if area and area[0] == recorte else None,
                    largura_rotulo=210, rotulos_valor=True, casas=1 if metrica in pack.TAXAS else 0,
                ),
                altura=max(grafico_componente.ALTURA_MIN_RANKING,
                           grafico_componente.ALTURA_BARRA_RANKING * len(tabela)
                           + grafico_componente.ALTURA_EIXO_RANKING),
                key="ranking",
            )

        with aba_piramide, resiliencia.painel("Pirâmide etária"):
            por_100mil = st.toggle("Taxa de detecção por 100 mil habitantes",
                                   help="Casos da faixa ÷ população da faixa × 100.000.")
            st.markdown(ui.titulo_painel(f"Casos novos por sexo e idade — {_local(com_area=False)}, {ano}"),
                        unsafe_allow_html=True)
            grafico_componente.desenhar(
                grafico_componente.piramide(dados.piramide(ano, area_dados), rotulo="Casos novos",
                                            por_100mil=por_100mil),
                altura=max(ALTURA_LINHA_1 - 160, 280), key="piramide",
            )


# ---------------------------------------------------------------------------
# Linha 2: indicadores de qualidade do programa
# ---------------------------------------------------------------------------

AJUDA_QUALIDADE = ("Indicadores de acompanhamento do programa, nos parâmetros do boletim. Cura, abandono e "
                   "contatos são da **coorte** do ano, como o boletim: paucibacilares diagnosticados no ano "
                   "anterior e multibacilares dois anos antes.")

with resiliencia.painel("Indicadores de qualidade"), st.container(border=True, key="cartao-qualidade"):
    qualidade = _kpis(ano, area_dados)
    st.markdown(ui.titulo_painel(f"Indicadores de qualidade do programa — {_local(com_area=False)}",
                                 ajuda=AJUDA_QUALIDADE), unsafe_allow_html=True)
    for coluna, m in zip(st.columns(len(pack.INDICADORES_QUALIDADE)), pack.INDICADORES_QUALIDADE,
                         strict=True):
        with coluna:
            _card(m, qualidade, _anterior(area_dados), _local(com_area=False))
    if qualidade.get("coorte_aberta"):
        st.caption(f"Cura, abandono e contatos não aparecem em {ano}: a coorte ainda não fechou.")


# ---------------------------------------------------------------------------
# Linha 3: tópicos de interesse
# ---------------------------------------------------------------------------

ALTURA_TOPICO_COLUNA = 260
VISTAS_TOPICO = {"ANO": "Ano selecionado", "SERIE": "Série histórica"}
INDICADORES_EM_SERIE = {
    "contatos_pct": "Contatos examinados (%)",
    "gif_avaliado_pct": "GIF avaliado no diagnóstico (%)",
    "grau2_pct": "GIF II no diagnóstico (%)",
    "cura_abandono": "Cura e abandono (%)",
}
AJUDA_TOPICOS = ("Distribuição de cada variável da ficha entre os casos novos do ano, e os indicadores do "
                 "programa por ano. Abaixo de cinco casos o percentual não é publicável e só a contagem aparece.")


def _desenhar_topico(variavel: str, rotulo: str) -> None:
    local = _local(com_area=False)
    if st.session_state.get("vista_topicos", "ANO") == "SERIE":
        tabela = dados.serie_composicao(variavel, area_dados)
        grafico, calha = _com_calha(f"Proporção de casos novos segundo {rotulo.lower()} por ano — {local}")
        with grafico:
            grafico_componente.desenhar(grafico_componente.composicao_por_ano(tabela, cor=pack.COR_BOLETIM),
                                        altura=ALTURA_TOPICO_COLUNA, key=f"topico-serie-{variavel}")
        with calha:
            if not tabela.empty:
                por_ano = tabela.groupby("ano")["n"].sum()
                st.markdown(ui.quadro_parametros("Base do cálculo", (
                    f"{int(por_ano.index.min())} a {int(por_ano.index.max())}, "
                    f"{ui.formatar_inteiro(float(por_ano.sum()))} casos novos com o campo preenchido",
                    "Cada coluna soma 100%: o que se compara é a composição.",
                ), fonte=FONTE_DADOS), unsafe_allow_html=True)
        return
    tabela = dados.composicao(variavel, ano, area_dados)
    orientacao = pack.orientacao_topico(variavel, tabela.get("categoria", []))
    altura = (ALTURA_TOPICO_COLUNA if orientacao == "coluna"
              else max(grafico_componente.altura_composicao(len(tabela)), 175))
    grafico, calha = _com_calha(f"Proporção de casos novos segundo {rotulo.lower()} — {local}, {ano}")
    with grafico:
        grafico_componente.desenhar(
            grafico_componente.composicao(tabela, rotulo="", cor=pack.COR_BOLETIM, largura_rotulo=150,
                                          ordem_dos_dados=True, orientacao=orientacao),
            altura=altura, key=f"topico-{variavel}",
        )
    with calha:
        _calha_base(tabela, universo=dados.total_de_casos(ano, area_dados))


def _desenhar_indicador(chave: str, serie: pd.DataFrame) -> None:
    if chave == "cura_abandono":
        grafico, calha = _com_calha("Proporção de cura e de abandono de tratamento",
                                    ajuda="Curas e abandonos sobre a coorte do ano (PB do ano anterior, "
                                          "MB de dois anos antes), sem as transferências.")
        with grafico:
            grafico_componente.desenhar(grafico_componente.comparativo_anual(serie, series={
                "cura_pct": ("% Cura", pack.COR_BOLETIM),
                "abandono_pct": ("% Abandono", pack.COR_BOLETIM_SECUNDARIA),
            }), altura=300, key="cura-abandono")
        with calha:
            _quadro("cura_pct")
            _quadro("abandono_pct")
        return
    titulo, ajuda, m, tipo = {
        "contatos_pct": ("Proporção de contatos examinados entre os registrados",
                         "Contatos examinados sobre registrados dos casos novos da coorte.",
                         "contatos_pct", "linha"),
        "gif_avaliado_pct": ("Proporção de casos com grau de incapacidade avaliado no diagnóstico",
                             "Casos novos com grau 0, I ou II sobre o total. Mede preenchimento, não gravidade.",
                             "gif_avaliado_pct", "barra"),
        "grau2_pct": ("Proporção de casos com grau de incapacidade física II no diagnóstico",
                      "Grau II sobre os avaliados. Em branco quando menos de 75% foram avaliados.",
                      "prop_grau2_pct", "barra"),
    }[chave]
    grafico, calha = _com_calha(titulo, ajuda=ajuda)
    with grafico:
        grafico_componente.desenhar(grafico_componente.indicador_anual(
            serie, coluna=chave, rotulo="Proporção (%)", cor=pack.COR_BOLETIM, ano=ano, tipo=tipo,
        ), altura=260, key=f"indicador-{chave}")
    with calha:
        _quadro(m)


with resiliencia.painel("Tópicos de interesse"), st.container(border=True, key="cartao-composicao"):
    st.markdown(ui.titulo_painel("Tópicos de interesse", ajuda=AJUDA_TOPICOS), unsafe_allow_html=True)
    planas = pack.variaveis_planas()
    escolhidas = st.multiselect(
        "O que exibir", [*INDICADORES_EM_SERIE, *planas],
        default=[*INDICADORES_EM_SERIE, *pack.VARIAVEIS_DESTAQUE],
        format_func=lambda c: INDICADORES_EM_SERIE.get(c) or planas[c],
        label_visibility="collapsed", placeholder="Escolha os indicadores e as variáveis a exibir",
    )
    st.segmented_control("Vista", list(VISTAS_TOPICO), format_func=VISTAS_TOPICO.get, default="ANO",
                         key="vista_topicos", label_visibility="collapsed")
    if not escolhidas:
        st.caption("Nada escolhido. Use o campo acima para trazer o que interessa.")
    serie_indicadores = (_recortar(dados.serie_qualidade(area_dados))
                         if any(c in INDICADORES_EM_SERIE for c in escolhidas) else pd.DataFrame())
    for escolha in escolhidas:
        if escolha in INDICADORES_EM_SERIE:
            _desenhar_indicador(escolha, serie_indicadores)
        else:
            _desenhar_topico(escolha, planas[escolha])


# ---------------------------------------------------------------------------
# Linha 4: séries anuais
# ---------------------------------------------------------------------------

with resiliencia.painel("Séries anuais"), st.container(border=True, key="cartao-series"):
    grafico_mb, calha_mb = _com_calha(
        f"Classificação operacional por ano — {_local(com_area=False)}",
        ajuda="Casos novos PB e MB por ano de diagnóstico; a linha é a proporção de multibacilares.")
    with grafico_mb:
        grafico_componente.desenhar(grafico_componente.barras_empilhadas_com_linha(
            _recortar(dados.serie_classificacao(area_dados)),
            barras={"pb": "PB - Paucibacilar", "mb": "MB - Multibacilar"}, linha="prop_mb",
            rotulo_linha="Proporção MB (%)", cores={"pb": "#B9AFD6", "mb": pack.COR_BOLETIM},
            cor_linha=pack.COR_BOLETIM_SECUNDARIA,
        ), altura=300, key="classificacao-operacional")
    with calha_mb:
        st.markdown(ui.quadro_parametros("Base do cálculo", ("Casos novos com classificação operacional "
                                                             "preenchida",), fonte=FONTE_DADOS),
                    unsafe_allow_html=True)

    grafico_014, calha_014 = _com_calha(
        f"Casos de 0 a 14 anos por ano — {_local(com_area=False)}",
        ajuda="Casos novos em menores de 15 anos por ano de diagnóstico; a linha é a taxa por 100 mil "
              "habitantes dessa faixa.")
    with grafico_014:
        grafico_componente.desenhar(grafico_componente.barras_empilhadas_com_linha(
            _recortar(dados.serie_0_14(area_dados)), barras={"casos": "Casos (0 a 14)"}, linha="taxa",
            rotulo_linha="Taxa de detecção 0–14 (por 100 mil)", cores={"casos": pack.COR_BOLETIM},
            cor_linha=pack.COR_BOLETIM_SECUNDARIA, casas_linha=2, rotulos=True,
        ), altura=300, key="casos-0-14")
    with calha_014:
        _quadro("taxa_det_0_14")


st.caption(
    f"Fonte: Sinan-Net, hanseníase em residentes no DF (cenarios_ai, extraído em {dados.extraido_em()}); "
    f"população IPEDF, como no boletim (antes de 2020, IBGE na mesma escala). Série: {anos[0]}–{anos[-1]}. "
    "Por RA e Região de Saúde: Tabela 1 dos boletins de hanseníase da SES-DF (2020–2025). "
    "Indicadores e parâmetros do boletim da SES-DF e do Ministério da Saúde."
)
