# -*- coding: utf-8 -*-
from contextlib import contextmanager
from nicegui import ui, app
from theme import NAVY, TEAL, TEAL_DARK, BG, TEXT, TEXT_MUTED, SIDEBAR_W, SIDEBAR_W_COLLAPSED, APP_NAME
from logo_data import LOGO_KALANI_DATA_URI
import auth

MENU_BASE = [("Meus Créditos", "/creditos", "home"), ("Agenda de Turmas", "/agenda", "event")]
MENU_INSTRUTOR = [("Lista de Presença", "/presenca", "fact_check")]
MENU_GESTOR = [("Dashboard", "/dashboard", "insights"), ("Configurações", "/configuracoes", "settings")]
ITEM_CADASTRO = ("Meu Cadastro", "/perfil", "person")


def _logout():
    app.storage.user.clear()
    ui.navigate.to("/")


def _menu_para(user):
    itens = list(MENU_BASE)
    if user["role"] == "instrutor":
        itens += MENU_INSTRUTOR
    if user["role"] == "gestor":
        itens += MENU_GESTOR
    itens.append(ITEM_CADASTRO)
    return itens


@contextmanager
def shell(active_path, user):
    """Uso: `with shell('/agenda', user): <conteúdo da página>`"""
    collapsed = bool(user.get("sidebar_collapsed", False))
    largura = SIDEBAR_W_COLLAPSED if collapsed else SIDEBAR_W

    def alternar_sidebar():
        user["sidebar_collapsed"] = not collapsed
        ui.navigate.to(active_path)

    with ui.row().classes("w-full no-wrap").style("min-height:100vh; margin:0; gap:0;"):
        # ---- Sidebar ----
        with ui.column().style(
            f"width:{largura}; min-width:{largura}; background:{NAVY}; "
            "min-height:100vh; padding:16px 0; gap:0; transition:width 0.15s ease;"
        ):
            # Botão de recolher/expandir — fixo no topo
            with ui.row().style(
                f"padding:0 {'0' if collapsed else '16'}px 12px {'0' if collapsed else '16'}px; "
                f"justify-content:{'center' if collapsed else 'flex-end'};"
            ):
                ui.button(icon="menu" if collapsed else "menu_open", on_click=alternar_sidebar).props(
                    "flat dense round"
                ).style("color:#9FBE86;").tooltip("Expandir" if collapsed else "Recolher")

            # Cabeçalho: logo (+ nome, se expandido)
            with ui.row().style(
                f"align-items:center; gap:10px; padding:0 {'0' if collapsed else '20'}px 16px "
                f"{'0' if collapsed else '20'}px; justify-content:{'center' if collapsed else 'flex-start'};"
            ):
                ui.image(LOGO_KALANI_DATA_URI).style("width:36px; height:36px; border-radius:50%; flex-shrink:0;")
                if not collapsed:
                    ui.label(APP_NAME).style(
                        "color:white; font-size:15px; font-weight:800; line-height:1.15;"
                    )
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

            if not collapsed:
                ui.label("MVP \u2022 NiceGUI").style(
                    "color:#5E7A47; font-size:10.5px; padding:8px 20px 0 20px;"
                )

        # ---- Área principal ----
        with ui.column().classes("flex-1").style(f"background:{BG}; min-height:100vh; gap:0;"):
            with ui.row().style(
                "width:100%; background:white; border-bottom:1px solid #C3CBB8; "
                "padding:14px 32px; align-items:center; justify-content:flex-end; gap:12px;"
            ):
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
                    ui.button("Sair", on_click=_logout).props("flat dense").style(
                        f"color:{TEXT_MUTED}; font-size:12px;"
                    )

            with ui.column().style("padding:32px; gap:16px; flex:1;") as content:
                yield content
