# -*- coding: utf-8 -*-
"""
Deixa o app instalável na tela inicial do celular (PWA de verdade, não
só um site responsivo). O manifest é gerado em memória e embutido como
data URI — mesma técnica usada para a logo — para não depender de uma
pasta de arquivos estáticos separada (evita o mesmo problema de upload
de pastas que já tivemos no GitHub).
"""
import json
import base64
from logo_data import LOGO_KALANI_B64
from theme import APP_NAME, BG, NAVY

_ICON_DATA_URI = "data:image/png;base64," + LOGO_KALANI_B64

_MANIFEST = {
    "name": APP_NAME,
    "short_name": "Kalani Vaa",
    "description": "Reserve suas remadas, acompanhe seus créditos e as novidades do clube.",
    "start_url": "/",
    "scope": "/",
    "display": "standalone",
    "background_color": BG,
    "theme_color": NAVY,
    "icons": [
        {"src": _ICON_DATA_URI, "sizes": "160x160", "type": "image/png", "purpose": "any maskable"},
    ],
}
_MANIFEST_B64 = base64.b64encode(json.dumps(_MANIFEST).encode("utf-8")).decode("ascii")

PWA_HEAD_HTML = f"""
<link rel="manifest" href="data:application/manifest+json;base64,{_MANIFEST_B64}">
<link rel="icon" href="{_ICON_DATA_URI}">
<link rel="apple-touch-icon" href="{_ICON_DATA_URI}">
<meta name="theme-color" content="{NAVY}">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Kalani Vaa">
"""
