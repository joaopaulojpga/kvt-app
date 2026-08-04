# -*- coding: utf-8 -*-
"""Tema visual do app — identidade Kalani Vaa Team."""

# Paleta oficial
TEAL = "#62A832"        # primária
TEAL_DARK = "#497E25"   # primária escurecida (hover/ativo)
NAVY = "#0B1307"        # secundária (sidebar, textos fortes)
NAVY_DARK = "#0B1307"
BG = "#CFD6C7"          # neutro claro (fundo das páginas)
CARD = "#FFFFFF"        # fundo dos cards (contraste sobre o fundo neutro)
BORDER = "#A7AFA0"      # neutro intermediário (bordas)
TEXT = "#0B1307"        # texto principal
TEXT_MUTED = "#5F6859"  # neutro escuro (texto secundário)
DANGER = "#D9534F"
WARN = "#E6A23C"
OK = "#3FA35A"

SIDEBAR_W = "230px"
SIDEBAR_W_COLLAPSED = "72px"

APP_NAME = "Kalani Vaa Team"
LOGO_PATH = "/assets/logo_kalani.png"


def reais(centavos: int) -> str:
    return f"R$ {centavos / 100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


GLOBAL_CSS = f"""
body {{ background-color: {BG}; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; }}
.canoa-card {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px;
    padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.canoa-badge {{ border-radius: 999px; padding: 3px 12px; font-size: 12px; font-weight: 600; }}
.canoa-badge-ok {{ background: #EAF7EE; color: {OK}; }}
.canoa-badge-warn {{ background: #FDF3E4; color: #8A5A12; }}
.canoa-badge-danger {{ background: #FBEAEA; color: {DANGER}; }}
.canoa-badge-muted {{ background: #EEF1F3; color: {TEXT_MUTED}; }}

/* Estilos pré-definidos para o campo "Head" da Newsletter (opção A: presets, sem editor livre) */
.kv-head-titulo-grande {{ font-size: 30px; font-weight: 800; line-height: 1.15; }}
.kv-head-destaque {{ font-size: 22px; font-weight: 700; line-height: 1.25; letter-spacing: 0.2px; }}
.kv-head-chamada {{ font-size: 17px; font-weight: 600; line-height: 1.3; text-transform: uppercase; letter-spacing: 0.6px; }}
"""

# Presets de estilo para o campo "Head" da Newsletter — usados tanto no
# formulário de criação (Configurações > Newsletter) quanto na
# renderização do carrossel.
HEAD_STYLES = {
    "Título grande": "kv-head-titulo-grande",
    "Destaque": "kv-head-destaque",
    "Chamada": "kv-head-chamada",
}
