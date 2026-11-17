"""O que o build e o deploy precisam (sem rodar o Docker)."""

from __future__ import annotations

import fnmatch
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _ignorados() -> list[str]:
    linhas = (RAIZ / ".dockerignore").read_text(encoding="utf-8").splitlines()
    return [linha.strip().rstrip("/") for linha in linhas if linha.strip() and not linha.startswith("#")]


def _barrado(caminho: str) -> bool:
    return any(fnmatch.fnmatch(caminho, p) or caminho.startswith(p + "/") for p in _ignorados())


def test_o_wheel_do_core_entra_no_contexto_e_o_lock_aponta_para_ele() -> None:
    wheels = sorted((RAIZ / "vendor").glob("cenarios_core-*.whl"))
    assert len(wheels) == 1, wheels
    assert not _barrado(f"vendor/{wheels[0].name}")
    lock = (RAIZ / "requirements.lock.txt").read_text(encoding="utf-8")
    assert f"./vendor/{wheels[0].name}" in lock
    assert f"./vendor/{wheels[0].name}" in (RAIZ / "requirements.txt").read_text(encoding="utf-8")


def test_o_dockerfile_copia_vendor_antes_de_instalar() -> None:
    texto = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    assert texto.index("COPY vendor/") < texto.index("RUN pip install")


def test_o_compose_recusa_subir_sem_porta() -> None:
    """Sem .env o compose não pode subir (já derrubou o DFTB)."""
    texto = (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${PORTA:?" in texto
    assert "${BASE_URL_PATH?" in texto


def test_o_modelo_de_env_traz_o_que_o_compose_exige() -> None:
    chaves = {linha.split("=", 1)[0].strip()
              for linha in (RAIZ / ".env.exemplo").read_text(encoding="utf-8").splitlines()
              if "=" in linha and not linha.lstrip().startswith("#")}
    assert {"PORTA", "BASE_URL_PATH", "SINAN_DOENCA"} <= chaves


def test_o_que_o_app_precisa_nao_e_barrado() -> None:
    for caminho in ("app.py", "src/dados.py", ".streamlit/config.toml", "geo/ra.parquet", "geo/regioes_saude.parquet"):
        assert (RAIZ / caminho).exists(), caminho
        assert not _barrado(caminho), f"{caminho} barrado pelo .dockerignore"


def test_o_healthcheck_inclui_o_subcaminho() -> None:
    """O healthcheck precisa do subcaminho (sem ele dá 404)."""
    texto = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    assert "${BASE_URL_PATH:+$BASE_URL_PATH/}_stcore/health" in texto


def test_o_compose_monta_os_dados() -> None:
    """data/ fica fora da imagem, então o compose tem que montar."""
    assert "./data:/app/data:ro" in (RAIZ / "docker-compose.yml").read_text(encoding="utf-8")
