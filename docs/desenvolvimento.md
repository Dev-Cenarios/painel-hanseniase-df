# Guia de desenvolvimento

Para quem vai mexer no código: comandos, arquitetura e as regras que já
custaram uma investigação. O que o painel mostra está no README.

Painel **Hanseníase no DF**, em Streamlit. Filho do `modelo`, neto do
**`cenarios-core`** (`../cenarios-core`), de onde vêm mapa, gráficos e
contenção de falha, instalado do wheel em `vendor/` em versão fixa. Nasceu
em 28/out/2026; no mesmo dia ligou no SINAN (`silver.hanseniase`). A régua é o
boletim da SES-DF "Situação Epidemiológica da Hanseníase no DF, 2021 a 2025".

**A tela é a do hansepe** (mesmas seções, cards, réguas e o pack copiado de
lá, com os mesmos nomes de métrica). O SINAN do banco ainda não tem RA: por RA e
Região de Saúde só há casos novos e detecção, da Tabela 1 dos boletins
(2020–2025), e o resto fica no DF inteiro. Quando o SINAN georreferenciado
chegar: calcular por área no `src/fonte_sinan.py`, fazer
`dados.tem_dado_por_area()` devolver True e pôr as outras métricas em
`METRICAS_MAPA` — a tela já segue a área.

Documentação, código, commits e comentários em português. A receita da
família é `../sinan/docs/como-fazer.md`.

- Mudança que serve a outros painéis vai para o core, não para cá.

## Comandos

Ambiente: `../sinan/.venv` (Python 3.13), com o core instalado.

```bash
python -m scripts.extrair_sinan_df        # silver.hanseniase → data/origem (VPN)
python -m scripts.extrair_populacao_df    # pop_ibge → data/origem (VPN)
python -m scripts.extrair_boletim_ra      # Tabela 1 dos boletins → data/origem (baixa os PDFs)
python -m scripts.extrair_contatos_df     # contatos do public.sinan_hans → data/origem (VPN)
streamlit run app.py
pytest
ruff check --select F app.py src tests scripts
docker compose up -d --build              # exige .env (copie de .env.exemplo)
```

## Arquitetura

`app.py` (composição, cópia adaptada da do hansepe) → `src/dados.py` (fachada,
recorte por `area`) → `src/fonte_sinan.py` (DF inteiro) e `src/fonte_boletim.py`
(RA e Região de Saúde); `src/doencas/hanseniase.py` é o pack do hansepe.

- **`src/fonte_sinan.py`** conta como o boletim: caso novo por **ano do
  diagnóstico**, sem "Erro diagnóstico"; cura, abandono e contatos na **coorte
  do MS** (PB de A−1, MB de A−2, sem transferências); grau 2 sobre os avaliados
  e só com GIF avaliado ≥ 75%. Contatos registrados vêm do SINAN bruto
  (`public.sinan_hans`), porque a silver não tem. População = a do boletim
  (casos / taxa, 2020–2025) e, antes, o IBGE na mesma escala.
  `tests/test_dados.py` confere a distância ao boletim.
- **Casca = a do hansepe** (a família de TB e hanseníase se reconhece por
  ela). `src/theme/` é cópia do `src/theme/` do hansepe (tokens, cores,
  componentes); `src/estilo.py` é a ponte — `cabecalho`, `card`,
  `titulo_bloco`… desenhando com as peças de lá. Painéis por
  `st.container(border=True, key="cartao-…")`, cards em `key="faixa-kpis"`,
  ícone de cada card no pack (`ICONES_KPI`). Só modo claro.
- Dados em `data/origem/` (fora do git e da imagem; o compose monta `./data`).
  A malha das RAs e Regiões (`geo/`, a do DFTB) é versionada.
- As divisas das Regiões são uma camada que o `app.py` põe no deck do core e
  reserializa com `mapa._compactar` — falta parâmetro no core pra isso.
- `extrair_boletim_ra` refaz taxa que não fecha com a população dos outros
  anos (Gama e Região Sul em 2025, erro do PDF); a original fica em `taxa_boletim`.

## Regras

- Não importe o `app.py` em teste: use o `AppTest` (`tests/test_aplicacao.py`).
  E confira ausência de **aviso**, não só de exceção — `resiliencia.painel`
  engole falha de bloco.
- Capture `Exception`, nunca `BaseException` (`st.rerun()` atravessa por ela).
- O que o painel desenha diferente do core entra por **parâmetro** do core,
  nunca por cópia do código dele. Faltou parâmetro: é versão nova do core.
