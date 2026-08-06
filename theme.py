# -*- coding: utf-8 -*-
"""Tema visual do app — identidade Kalani Vaa Team.

Paleta reduzida a 5 tons (verde escuro, verde médio, verde claro, cinza
neutro, branco) + cores semânticas de status (erro/aviso/sucesso, que
não fazem parte da identidade, são só sinalização).
"""

# ---- Paleta (5 tons) ----
NAVY = "#0B1307"        # verde escuro — sidebar, textos fortes, títulos
TEAL = "#62A832"        # verde médio — cor primária (botões, links, destaque)
TEAL_DARK = "#497E25"   # verde médio escurecido — hover/estado ativo (variação do primário, não conta como tom novo)
TEAL_LIGHT = "#EAF6F4"  # verde claro — fundos suaves, cards de destaque
GRAY = "#5F6859"        # cinza neutro — texto secundário, bordas, ícones inativos
WHITE = "#FFFFFF"       # branco — fundo de cards, texto sobre fundo escuro

# Aliases mantidos para não quebrar imports existentes em outras telas
NAVY_DARK = NAVY
BG = "#CFD6C7"           # tom de fundo da página (tinta clara sobre o cinza neutro)
CARD = WHITE
BORDER = "#A7AFA0"       # variação clara do cinza neutro, só para linhas divisórias
TEXT = NAVY
TEXT_MUTED = GRAY

# Cores semânticas (status) — não fazem parte da identidade visual, só comunicam estado
DANGER = "#D9534F"
WARN = "#E6A23C"
OK = "#3FA35A"

# ---- Espaçamento em múltiplos de 8px ----
SPACE_XS = "8px"
SPACE_SM = "16px"
SPACE_MD = "24px"
SPACE_LG = "32px"
SPACE_XL = "40px"

# ---- Tipografia (4 estilos apenas) ----
# Use via .classes("kv-titulo" | "kv-subtitulo" | "kv-texto" | "kv-legenda")
FONTE_TITULO = "24px"
FONTE_SUBTITULO = "16px"
FONTE_TEXTO = "14px"
FONTE_LEGENDA = "12px"

SIDEBAR_W = "208px"
SIDEBAR_W_COLLAPSED = "52px"

APP_NAME = "Kalani Vaa Team"
LOGO_PATH = "/assets/logo_kalani.png"


def reais(centavos: int) -> str:
    return f"R$ {centavos / 100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


GLOBAL_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@700;800&display=swap');
body {{ background-color: {BG}; font-family: 'Inter', 'Segoe UI', Arial, sans-serif; margin: 0; }}
.nicegui-content {{ padding: 0 !important; gap: 0 !important; }}
.q-page {{ padding: 0 !important; }}
.kv-brand {{
    font-family: 'Baloo 2', 'Inter', sans-serif; font-weight: 800;
    text-transform: uppercase; letter-spacing: 0.8px;
}}
.canoa-card {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px;
    padding: {SPACE_SM}; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.canoa-badge {{ border-radius: 999px; padding: 3px 12px; font-size: {FONTE_LEGENDA}; font-weight: 600; }}
.canoa-badge-ok {{ background: #EAF7EE; color: {OK}; }}
.canoa-badge-warn {{ background: #FDF3E4; color: #8A5A12; }}
.canoa-badge-danger {{ background: #FBEAEA; color: {DANGER}; }}
.canoa-badge-muted {{ background: #EEF1F3; color: {TEXT_MUTED}; }}

/* Mobile: o público majoritário acessa por celular — reduz padding excessivo
   em telas estreitas nos containers principais (topo, conteúdo, landing). */
@media (max-width: 640px) {{
    .kv-main-content {{ padding: 16px !important; }}
    .kv-topbar {{ padding: 10px 16px !important; }}
    .kv-landing {{ padding: 24px 16px !important; }}
}}

/* Sistema tipográfico — 4 estilos apenas, conforme design system definido */
.kv-titulo {{ font-size: {FONTE_TITULO}; font-weight: 800; line-height: 1.2; color: {NAVY}; }}
.kv-subtitulo {{ font-size: {FONTE_SUBTITULO}; font-weight: 700; line-height: 1.25; color: {NAVY}; }}
.kv-texto {{ font-size: {FONTE_TEXTO}; font-weight: 400; line-height: 1.4; color: {TEXT}; }}
.kv-legenda {{ font-size: {FONTE_LEGENDA}; font-weight: 400; line-height: 1.3; color: {TEXT_MUTED}; }}

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
