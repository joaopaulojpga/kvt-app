# -*- coding: utf-8 -*-
"""Tema visual do app (mesma paleta usada nos protótipos do PRD)."""

NAVY = "#123B57"
NAVY_DARK = "#0C2A3E"
TEAL = "#0F9D8C"
TEAL_DARK = "#0B7A6C"
BG = "#F4F6F8"
CARD = "#FFFFFF"
BORDER = "#D7DEE3"
TEXT = "#2B3640"
TEXT_MUTED = "#7A8791"
DANGER = "#D9534F"
WARN = "#E6A23C"
OK = "#3FA35A"

SIDEBAR_W = "230px"


def reais(centavos: int) -> str:
    return f"R$ {centavos / 100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


GLOBAL_CSS = f"""
body {{ background-color: {BG}; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; }}
.canoa-card {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px;
    padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.canoa-badge {{ border-radius: 999px; padding: 3px 12px; font-size: 12px; font-weight: 600; }}
.canoa-badge-ok {{ background: #EAF7EE; color: {OK}; }}
.canoa-badge-warn {{ background: #FDF3E4; color: #8A5A12; }}
.canoa-badge-danger {{ background: #FBEAEA; color: {DANGER}; }}
.canoa-badge-muted {{ background: #EEF1F3; color: {TEXT_MUTED}; }}
"""
