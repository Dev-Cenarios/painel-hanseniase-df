# Imagem do painel. O mesmo jeito de subir dos irmãos da família Cenários.
FROM python:3.13-slim

WORKDIR /app

# curl → healthcheck · libgomp1 → DuckDB usa OpenMP
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Do lock, não do requirements.txt: dois builds do mesmo commit sobem as
# mesmas versões. O lock aponta para o wheel do cenarios-core em `vendor/`,
# que vem antes do `pip install` — o build não precisa de rede para o core.
COPY requirements.lock.txt .
COPY vendor/ vendor/
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY app.py .
COPY src/ src/
COPY .streamlit/ .streamlit/
# A malha das RAs (versionada). O dado (fora do git) não entra: o compose monta data/.
COPY geo/ geo/
COPY assets/ assets/

ENV PYTHONUNBUFFERED=1 \
    SINAN_DOENCA=hanseniase \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    BASE_URL_PATH=""

EXPOSE 8501

# O caminho do healthcheck inclui o subcaminho: sob `baseUrlPath`, a raiz
# responde 404. E o healthcheck mente: responde mesmo com o script quebrado —
# depois de todo deploy, abra a página e confira um número conhecido.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail "http://localhost:8501/${BASE_URL_PATH:+$BASE_URL_PATH/}_stcore/health" || exit 1

ENTRYPOINT ["sh", "-c", "exec streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.baseUrlPath=\"$BASE_URL_PATH\" \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true \
    --browser.gatherUsageStats=false"]
