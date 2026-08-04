# -*- coding: utf-8 -*-
from contextlib import contextmanager
from nicegui import ui, app
from theme import NAVY, TEAL, TEAL_DARK, BG, TEXT, TEXT_MUTED, SIDEBAR_W, SIDEBAR_W_COLLAPSED, APP_NAME
from logo_data import LOGO_KALANI_DATA_URI
import auth
import credits

MENU_BASE = [("Home", "/creditos", "home"), ("Agenda de Turmas", "/agenda", "event")]
MENU_INSTRUTOR = [("Lista de Presença", "/presenca", "fact_check")]
MENU_GESTOR = [("Dashboard", "/dashboard", "insights"), ("Configurações", "/configuracoes", "settings")]
ITEM_CADASTRO = ("Meu Cadastro", "/perfil", "person")

WHATSAPP_URL = "https://chat.whatsapp.com/CuvzGubexylGgxp6Npu6Mt"
INSTAGRAM_URL = "https://www.instagram.com/kalani_vaa/"


def _logout():
    app.storage.user.clear()
    ui.navigate.to("/")


def _abrir_ajuda():
    with ui.dialog() as dialog, ui.card().style("width:min(360px, 90vw); padding:20px; gap:10px;"):
        ui.label("Precisa de ajuda?").style(f"color:{NAVY}; font-weight:800; font-size:16px;")
        ui.label("Fale com a gente pelo grupo do WhatsApp ou siga o Instagram do clube.").style(
            f"color:{TEXT_MUTED}; font-size:13px;"
        )
        ui.button("Abrir WhatsApp", on_click=lambda: ui.navigate.to(WHATSAPP_URL, new_tab=True)).props(
            "unelevated"
        ).classes("w-full").style(f"background:{TEAL}; color:white; font-weight:700;")
        ui.button("Abrir Instagram", on_click=lambda: ui.navigate.to(INSTAGRAM_URL, new_tab=True)).props(
            "outline"
        ).classes("w-full").style(f"color:{TEAL_DARK}; font-weight:700;")
        ui.button("Fechar", on_click=dialog.close).props("flat").style(f"color:{TEXT_MUTED}; align-self:flex-end;")
    dialog.open()


def _menu_para(user):
    itens = list(MENU_BASE)
    if user["role"] == "instrutor":
        itens += MENU_INSTRUTOR
    if user["role"] == "gestor":
        itens += MENU_GESTOR
    itens.append(ITEM_CADASTRO)
    return itens


@ui.refreshable
def _sidebar(active_path, user):
    collapsed = bool(user.get("sidebar_collapsed", True))
    largura = SIDEBAR_W_COLLAPSED if collapsed else SIDEBAR_W

    def alternar_sidebar():
        user["sidebar_collapsed"] = not collapsed
        _sidebar.refresh(active_path, user)

    with ui.column().style(
        f"width:{largura}; min-width:{largura}; background:{NAVY}; "
        "min-height:100vh; padding:16px 0; gap:0; transition:width 0.12s ease; flex-shrink:0;"
    ):
        # Cabeçalho: logo + nome (se expandido) e botão de recolher, lado a lado
        with ui.row().style(
            f"align-items:center; gap:8px; padding:0 {'0' if collapsed else '16'}px 16px "
            f"{'0' if collapsed else '16'}px; "
            f"justify-content:{'center' if collapsed else 'space-between'};"
        ):
            with ui.row().style("align-items:center; gap:8px;"):
                ui.image(LOGO_KALANI_DATA_URI).style("width:32px; height:32px; border-radius:50%; flex-shrink:0;")
                if not collapsed:
                    ui.label(APP_NAME).style(
                        "color:white; font-size:15px; font-weight:800; line-height:1.15;"
                    )
            if not collapsed:
                ui.button(icon="menu_open", on_click=alternar_sidebar).props(
                    "flat dense round"
                ).style("color:#9FBE86;").tooltip("Recolher")

        if collapsed:
            with ui.row().style("justify-content:center; padding-bottom:8px;"):
                ui.button(icon="menu", on_click=alternar_sidebar).props(
                    "flat dense round"
                ).style("color:#9FBE86;").tooltip("Expandir")
        ui.separator().style("background:#243318; opacity:0.5;")

        # Itens de menu — ícone sempre, texto só quando expandido
        with ui.column().style("gap:0; margin-top:8px;"):
            for label, path, icone in _menu_para(user):
                ativo = path == active_path
                item = ui.row().style(
                    f"padding:12px {'0' if collapsed else '20'}px; cursor:pointer; align-items:center; "
                    f"justify-content:{'center' if collapsed else 'flex-start'}; gap:12px; "
                    f"background:{TEAL_DARK if ativo else 'transparent'};"
                )
                with item:
                    ui.icon(icone).style(
                        f"color:{'white' if ativo else '#CDE8B8'}; font-size:20px;"
                    )
                    if not collapsed:
                        ui.label(label).style(
                            f"color:{'white' if ativo else '#CDE8B8'}; "
                            f"font-weight:{'700' if ativo else '400'}; font-size:13.5px;"
                        )
                if collapsed:
                    item.tooltip(label)
                item.on("click", lambda p=path: ui.navigate.to(p))

        ui.space()

        ui.separator().style("background:#243318; opacity:0.5;")
        for label, icone, acao in [("Ajuda", "help_outline", _abrir_ajuda), ("Sair", "logout", _logout)]:
            item = ui.row().style(
                f"padding:12px {'0' if collapsed else '20'}px; cursor:pointer; align-items:center; "
                f"justify-content:{'center' if collapsed else 'flex-start'}; gap:12px; margin-top:4px;"
            )
            with item:
                ui.icon(icone).style("color:#9FBE86; font-size:19px;")
                if not collapsed:
                    ui.label(label).style("color:#CDE8B8; font-weight:400; font-size:13.5px;")
            if collapsed:
                item.tooltip(label)
            item.on("click", acao)


@contextmanager
def shell(active_path, user):
    """Uso: `with shell('/agenda', user): <conteúdo da página>`"""
    with ui.row().classes("w-full no-wrap").style("min-height:100vh; margin:0; gap:0;"):
        # ---- Sidebar (componente independente, recolhe/expande sem reload de página) ----
        _sidebar(active_path, user)

        # ---- Área principal ----
        with ui.column().classes("flex-1").style(f"background:{BG}; min-height:100vh; gap:0;"):
            with ui.row().style(
                "width:100%; background:white; "
                "padding:14px 32px; align-items:center; justify-content:flex-end; gap:16px;"
            ).classes("kv-topbar"):
                if user["role"] == "aluno":
                    saldo = credits.saldo_disponivel(user["id"])
                    with ui.column().style(
                        "background:#F4F8F0; border:1px solid #C9D3BE; border-radius:12px; "
                        "padding:4px 18px; align-items:center; gap:0;"
                    ):
                        ui.label("Créditos").style(f"color:{TEXT_MUTED}; font-size:10px; font-weight:700;")
                        ui.label(str(saldo)).style(f"color:{NAVY}; font-size:20px; font-weight:800; line-height:1.1;")
                        ui.label("remadas").style(f"color:{TEXT_MUTED}; font-size:10px;")

                dados = auth.get_usuario(user["id"])
                foto = dados.get("foto_url") if dados else None
                with ui.row().style("align-items:center; gap:10px;"):
                    if foto:
                        ui.image(foto).style(
                            f"width:34px; height:34px; border-radius:50%; object-fit:cover; "
                            f"border:1.5px solid {TEAL};"
                        )
                    else:
                        iniciais = "".join([p[0] for p in user["nome"].split()[:2]]).upper()
                        ui.label(iniciais).style(
                            f"background:#E3EEDA; color:{TEAL_DARK}; border-radius:50%; "
                            "width:34px; height:34px; display:flex; align-items:center; "
                            "justify-content:center; font-weight:700; font-size:13px;"
                        )
                    with ui.column().style("gap:0; line-height:1.1;"):
                        ui.label(user["nome"].split()[0]).style(
                            f"color:{TEXT}; font-weight:700; font-size:13px;"
                        )
                        ui.label(user["role"].capitalize()).style(
                            f"color:{TEXT_MUTED}; font-size:11px;"
                        )

            with ui.column().style("padding:32px; gap:16px; flex:1;").classes("kv-main-content") as content:
                yield content
