"""Cores: misturas, rampas e contraste."""

from __future__ import annotations

Rgb = tuple[float, float, float]

# Quanto misturar de branco (claros) e de preto (escuros) na rampa.
_CLAROS = (0.35, 0.55, 0.72)
_ESCUROS = (0.18, 0.34, 0.52)

BRANCO = "#FFFFFF"
PRETO = "#000000"

SEM_DADO = "#F3F4F6"


def hex_para_rgb(cor: str) -> Rgb:
    texto = str(cor or "").strip().lstrip("#")
    if len(texto) == 3:
        texto = "".join(c * 2 for c in texto)
    if len(texto) != 6:
        raise ValueError(f"Cor hexadecimal inválida: {cor!r}")
    return tuple(int(texto[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_para_hex(rgb: Rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


def misturar(a: str, b: str, t: float) -> str:
    """t=0 devolve a, t=1 devolve b."""
    ra, rb = hex_para_rgb(a), hex_para_rgb(b)
    return rgb_para_hex(  # type: ignore[arg-type]
        tuple(x + (y - x) * t for x, y in zip(ra, rb, strict=True))
    )


def rampa(base: str) -> list[str]:
    """7 tons: 3 mais claros, a base no meio, 3 mais escuros."""
    claros = [misturar(BRANCO, base, t) for t in _CLAROS]
    escuros = [misturar(base, PRETO, t) for t in _ESCUROS]
    return [*claros, base.upper(), *escuros]


FUNDO_ESCURO = "#0B1220"

# mínimo da WCAG pra texto grande
CONTRASTE_MINIMO = 3.0


def _luminancia(cor: str) -> float:
    canais = []
    for x in hex_para_rgb(cor):
        canais.append(x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4)
    r, g, b = canais
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    """Contraste entre duas cores (1 a 21)."""
    la, lb = _luminancia(a), _luminancia(b)
    claro, escuro = max(la, lb), min(la, lb)
    return (claro + 0.05) / (escuro + 0.05)


def para_fundo_escuro(cor: str, fundo: str = FUNDO_ESCURO, alvo: float = 3.5) -> str:
    """Clareia a cor até dar pra ler no fundo escuro."""
    if contraste(cor, fundo) >= alvo:
        return cor

    for passo in range(1, 21):
        candidato = misturar(cor, "#FFFFFF", passo / 20)
        if contraste(candidato, fundo) >= alvo:
            return candidato
    return "#FFFFFF"
