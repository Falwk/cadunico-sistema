"""
Gera static/css/m3-tokens.css com a paleta Material Design 3 (tema claro e escuro)
a partir das cores oficiais do Manual de Marca do Cadastro Unico 25 Anos.

  primaria   = verde   #00883A
  secundaria = roxo    #783DB2
  terciaria  = amarelo #FAB614

Uso:  python scripts/gerar_tokens_m3.py
Requer: pip install materialyoucolor
"""
import os
from materialyoucolor.hct import Hct
from materialyoucolor.palettes.tonal_palette import TonalPalette

SEEDS = {
    "primary": 0xFF00883A,
    "secondary": 0xFF783DB2,
    "tertiary": 0xFFFAB614,
    "error": 0xFFB3261E,
}


def pal(argb):
    return TonalPalette.from_hct(Hct.from_int(argb))


primary_hue = Hct.from_int(SEEDS["primary"]).hue
P = {k: pal(v) for k, v in SEEDS.items()}
# Neutros levemente tingidos de verde (como no M3 Expressive)
P["neutral"] = TonalPalette.from_hue_and_chroma(primary_hue, 6.0)
P["neutral_variant"] = TonalPalette.from_hue_and_chroma(primary_hue, 10.0)


def hx(argb):
    return "#{:06X}".format(argb & 0xFFFFFF)


def role(pname, tone):
    return hx(P[pname].tone(tone))


def scheme(dark):
    T = (lambda l, d: d) if dark else (lambda l, d: l)
    r = {}
    for name in ("primary", "secondary", "tertiary", "error"):
        r[name] = role(name, T(40, 80))
        r[f"on-{name}"] = role(name, T(100, 20))
        r[f"{name}-container"] = role(name, T(90, 30))
        r[f"on-{name}-container"] = role(name, T(10, 90))
    r["surface"] = role("neutral", T(98, 6))
    r["surface-dim"] = role("neutral", T(87, 6))
    r["surface-bright"] = role("neutral", T(98, 24))
    r["surface-container-lowest"] = role("neutral", T(100, 4))
    r["surface-container-low"] = role("neutral", T(96, 10))
    r["surface-container"] = role("neutral", T(94, 12))
    r["surface-container-high"] = role("neutral", T(92, 17))
    r["surface-container-highest"] = role("neutral", T(90, 22))
    r["on-surface"] = role("neutral", T(10, 90))
    r["on-surface-variant"] = role("neutral_variant", T(30, 80))
    r["outline"] = role("neutral_variant", T(50, 60))
    r["outline-variant"] = role("neutral_variant", T(80, 30))
    r["inverse-surface"] = role("neutral", T(20, 90))
    r["inverse-on-surface"] = role("neutral", T(95, 20))
    r["inverse-primary"] = role("primary", T(80, 40))
    r["scrim"] = "#000000"
    r["shadow"] = "#000000"
    # Cores de status (sucesso/aviso) harmonizadas com a marca
    r["success"] = role("primary", T(40, 80))
    r["success-container"] = role("primary", T(90, 30))
    r["on-success-container"] = role("primary", T(10, 90))
    r["warning"] = role("tertiary", T(40, 80))
    r["warning-container"] = role("tertiary", T(90, 30))
    r["on-warning-container"] = role("tertiary", T(10, 90))
    return r


def block(selector, r, comment):
    linhas = [f"  /* {comment} */"]
    linhas += [f"  --md-sys-color-{k}: {v};" for k, v in r.items()]
    return f"{selector} {{\n" + "\n".join(linhas) + "\n}\n"


css = (
    "/* ARQUIVO GERADO por scripts/gerar_tokens_m3.py - nao editar manualmente.\n"
    "   Paleta Material Design 3 a partir do Manual de Marca Cadastro Unico 25 Anos. */\n\n"
)
css += block(":root,\n:root[data-theme=\"light\"]", scheme(False), "Tema claro")
css += "\n"
css += block(":root[data-theme=\"dark\"]", scheme(True), "Tema escuro")
css += "\n@media (prefers-color-scheme: dark) {\n"
css += block(":root:not([data-theme=\"light\"])", scheme(True), "Tema escuro automatico (preferencia do sistema)").replace("\n  ", "\n    ").replace("{\n    /*", "{\n    /*")
css += "}\n"

destino = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "css", "m3-tokens.css")
os.makedirs(os.path.dirname(destino), exist_ok=True)
with open(destino, "w", encoding="utf-8") as f:
    f.write(css)
print("Gerado:", destino, f"({len(css)} bytes)")
