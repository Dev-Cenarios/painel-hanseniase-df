"""Pra senha nunca parar no git (já quase aconteceu no sinan)."""

from __future__ import annotations

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# têm que ficar vazias no .env.exemplo
CHAVES_SECRETAS = ("CENARIOS_HOST", "CENARIOS_USER", "CENARIOS_PASSWORD")


def _pares(arquivo: Path) -> dict[str, str]:
    pares = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = (p.strip() for p in linha.split("=", 1))
            pares[chave] = valor
    return pares


def test_o_modelo_de_env_nao_tem_credencial_preenchida() -> None:
    modelo = RAIZ / ".env.exemplo"
    assert modelo.is_file(), "o modelo sumiu — sem ele ninguém sabe o que preencher"
    pares = _pares(modelo)
    for chave in CHAVES_SECRETAS:
        assert not pares.get(chave), f"{chave} está preenchida em .env.exemplo, que é VERSIONADO"


def test_o_env_de_verdade_nao_e_versionado() -> None:
    linhas = (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in [linha.strip() for linha in linhas]


def test_nenhum_arquivo_do_codigo_carrega_senha() -> None:
    """Procura PASSWORD="..." perdido no código."""
    suspeitos = []
    for arquivo in [*RAIZ.glob("*.py"), *(RAIZ / "src").rglob("*.py"), *(RAIZ / "scripts").rglob("*.py")]:
        for numero, linha in enumerate(arquivo.read_text(encoding="utf-8").splitlines(), 1):
            limpa = linha.replace(" ", "").upper()
            if ("PASSWORD=\"" in limpa or "SENHA=\"" in limpa) and not limpa.endswith('=""'):
                suspeitos.append(f"{arquivo.name}:{numero}")
    assert not suspeitos, suspeitos
