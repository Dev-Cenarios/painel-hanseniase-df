# Publicação na VM

Passo a passo para pôr o hansedf em
`https://painel.cenarios.unb.br/cenarios/hansedf/`. É o mesmo caminho do
tbbrasil e do hansepe.

| | |
|---|---|
| Público | `https://painel.cenarios.unb.br/cenarios/hansedf/` |
| Direto, por VPN | porta **8523** na VM (`ssh cenarios-vm`) — livre em 28/out/2026 |
| Container | `dashboard-hansedf` (imagem `dashboard-hansedf:latest`, construída na VM) |
| Pasta na VM | `~/hansedf` |
| Repo | `Dev-Cenarios/painel-hanseniase-df` (público). Até nov/2026 era `Mcardosor/hansedf`, privado, com deploy key |
| Variáveis | `~/hansedf/.env`: `PORTA=8523`, `BASE_URL_PATH=cenarios/hansedf` |
| Dados | `~/hansedf/data/origem` (parquets), por `tar` — fora do git e da imagem |

Tudo abaixo precisa da **VPN ligada**: sem ela nem o GitHub nem a VM
respondem.

## 0. Conferir antes

```bash
ssh cenarios-vm 'docker ps --format "{{.Names}} {{.Ports}}" | grep 8523'
```

Não pode sair nada. Se sair, escolha outra porta e troque em todo lugar
abaixo onde aparece 8523.

## 1. Repositório

O código está em `Dev-Cenarios/painel-hanseniase-df`, público. Mudança entra
por commit e push lá. Antes de commitar, `git status`: `.env` e `data/` **não**
podem aparecer.

## 2. Clone na VM

Como o repositório é público, a VM clona e faz `git pull` sem chave:

```bash
ssh cenarios-vm 'git clone https://github.com/Dev-Cenarios/painel-hanseniase-df.git ~/hansedf'
```

Na VM onde o painel já estava, clonado do repositório antigo, basta trocar o
endereço e tirar a chave de deploy:

```bash
ssh cenarios-vm 'cd ~/hansedf && git remote set-url origin https://github.com/Dev-Cenarios/painel-hanseniase-df.git && git config --unset core.sshCommand'
```

## 3. `.env` na VM

Sem `.env` o compose recusa subir — de propósito. Na VM só vão porta e
subcaminho; as credenciais do banco ficam na máquina de trabalho, onde rodam
os scripts de extração.

```bash
ssh cenarios-vm 'cd ~/hansedf && printf "PORTA=8523\nBASE_URL_PATH=cenarios/hansedf\nSINAN_DOENCA=hanseniase\n" > .env && cat .env'
```

## 4. Dados

Da máquina de trabalho, em `paineis/hansedf`. Os PDFs dos boletins não vão:
o painel lê o `boletim_ra.parquet` já extraído.

```bash
ssh cenarios-vm 'mkdir -p ~/hansedf/data/origem'
tar -C data/origem --exclude='boletins' --exclude='*.csv' -cf - . | ssh cenarios-vm 'tar -C ~/hansedf/data/origem -xf -'
ssh cenarios-vm 'ls -la ~/hansedf/data/origem'
```

Têm que chegar `sinan_df_hans.parquet`, `populacao_ibge_df.parquet` e
`boletim_ra.parquet`.

## 5. Subir o container

```bash
ssh cenarios-vm 'cd ~/hansedf && docker compose up -d --build'
ssh cenarios-vm 'curl -s http://localhost:8523/cenarios/hansedf/_stcore/health'
```

O `curl` tem que responder `ok`. O primeiro build leva alguns minutos.

## 6. Rota no nginx (`painel.cenarios.unb.br`)

O domínio é um só, servido pelo nginx da VM; cada painel é um bloco
`location` em `/etc/nginx/sites-available/telessaude`. Esse arquivo é do
`matheusrodrigues` e `nginx -t`/`systemctl reload nginx` são NOPASSWD — dá
pra rodar sem senha. Se pedir senha, quem tem sudo roda o mesmo script.

Crie `~/nginx/scripts/aplicar-rota-hansedf.sh` na VM:

```bash
#!/usr/bin/env bash
# Põe o hansedf em /cenarios/hansedf (8523). Backup, teste, e só recarrega se passar. Idempotente.
set -euo pipefail
ARQ=/etc/nginx/sites-available/telessaude
cp "$ARQ" ~/nginx/backups/telessaude.bak-$(date +%Y%m%d-%H%M)
python3 - "$ARQ" <<"PY"
import sys
arq = sys.argv[1]; s = open(arq, encoding="utf-8").read()
if "location /cenarios/hansedf {" not in s:
    ancora = "    location /cenarios/tbbrasil {"
    bloco = """    location /cenarios/hansedf {
        proxy_pass         http://localhost:8523;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection $connection_upgrade;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

"""
    s = s.replace(ancora, bloco + ancora, 1)
    open(arq, "w", encoding="utf-8").write(s)
PY
sudo -n /usr/sbin/nginx -t
sudo -n /usr/bin/systemctl reload nginx
echo "pronto: /cenarios/hansedf/ -> 8523"
```

```bash
ssh cenarios-vm 'bash ~/nginx/scripts/aplicar-rota-hansedf.sh'
```

**Sem barra final** em `location` e em `proxy_pass`: o container espera
receber o prefixo `/cenarios/hansedf`. Os cabeçalhos `Upgrade`/`Connection`
são o websocket do Streamlit — sem eles a página fica carregando para
sempre.

## 7. Conferir de fora

Abra `https://painel.cenarios.unb.br/cenarios/hansedf/` (com a VPN
desligada, de preferência, pra ver o que o público vê) e confira um número
conhecido: **157 casos novos em 2025**, igual ao boletim. O healthcheck
responde `ok` mesmo com o script quebrado — só a página prova o deploy.

## 8. Cartão na página inicial

A rota sozinha não anuncia o painel. A grade de `https://painel.cenarios.unb.br/`
é o HTML solto `/var/www/frontpage/index.html`:

```bash
ssh cenarios-vm 'cp /var/www/frontpage/index.html ~/frontpage-index.bak-$(date +%Y%m%d-%H%M)'
```

e acrescente, antes do `</div>` que fecha a grade (logo depois do cartão do
tbbrasil):

```html
    <a class="card" href="/cenarios/hansedf/">
      <div class="icon">🩺</div>
      <h2>Hanseníase no DF</h2>
      <p>Casos novos, cura, abandono e grau 2 de incapacidade no Distrito Federal — mapa por Região Administrativa, Regiões de Saúde e evolução anual, na régua do boletim da SES-DF. Fonte: SINAN</p>
      <span class="tag new">Novo</span>
    </a>
```

Publica na hora, sem recarregar o nginx. Confira com `?v=1` na URL — sem
isso o navegador pode devolver a versão em cache.

## 9. Registrar

Acrescente o hansedf nas duas tabelas do `INDEX.md` (porta 8523, pasta
`~/hansedf`, repo `hansedf` privado com deploy key, container
`dashboard-hansedf`).

## Atualizar depois

Código:

```bash
git push
ssh cenarios-vm 'cd ~/hansedf && git pull && docker compose up -d --build'
```

Dados: refaça o passo 4 e reinicie (`docker compose restart`) — o dado é
volume, não precisa de build.
