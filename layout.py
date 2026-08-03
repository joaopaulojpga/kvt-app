# -*- coding: utf-8 -*-
from contextlib import contextmanager
from nicegui import ui, app
from theme import NAVY, NAVY_DARK, TEAL, TEAL_DARK, BG, TEXT, TEXT_MUTED, SIDEBAR_W

MENU_BASE = [("Meus Créditos", "/creditos"), ("Agenda de Turmas", "/agenda")]
MENU_INSTRUTOR = [("Lista de Presença", "/presenca")]
MENU_GESTOR = [("Dashboard", "/dashboard")]


def _logout():
    app.storage.user.clear()
    ui.navigate.to("/")


def _menu_para(user):
    itens = list(MENU_BASE)
    if user["role"] == "instrutor":
        itens += MENU_INSTRUTOR
    if user["role"] == "gestor":
        itens += MENU_GESTOR
    itens.append(("Meu Cadastro", "/perfil"))
    return itens


@contextmanager
def shell(active_path, user):
    """Uso: `with shell('/agenda', user): <conteúdo da página>`"""
    with ui.row().classes("w-full no-wrap").style("min-height:100vh; margin:0; gap:0;"):
        # ---- Sidebar ----
        with ui.column().style(
            f"width:{SIDEBAR_W}; min-width:{SIDEBAR_W}; background:{NAVY}; "
            "min-height:100vh; padding:24px 0; gap:0;"
        ):
            ui.label("\U0001F6F6 Canoa Clube").style(
                "color:white; font-size:18px; font-weight:700; padding:0 24px 20px 24px;"
            )
            for label, path in _menu_para(user):
                ativo = path == active_path
                item = ui.row().style(
                    "padding:12px 24px; cursor:pointer; align-items:center; "
                    f"background:{TEAL_DARK if ativo else 'transparent'};"
                )
                with item:
                    ui.label(label).style(
                        f"color:{'white' if ativo else '#A9C2D2'}; "
                        f"font-weight:{'700' if ativo else '400'}; font-size:14px;"
                    )
                item.on("click", lambda p=path: ui.navigate.to(p))
            ui.space()
            ui.label("MVP \u2022 NiceGUI").style(
                "color:#6E93A8; font-size:11px; padding:16px 24px 0 24px;"
            )

        # ---- Área principal ----
        with ui.column().classes("flex-1").style(f"background:{BG}; min-height:100vh; gap:0;"):
            with ui.row().style(
                "width:100%; background:white; border-bottom:1px solid #E5E9EC; "
                "padding:14px 32px; align-items:center; justify-content:flex-end; gap:12px;"
            ):
                iniciais = "".join([p[0] for p in user["nome"].split()[:2]]).upper()
                with ui.row().style("align-items:center; gap:10px;"):
                    ui.label(iniciais).style(
                        f"background:#DCEDEA; color:{TEAL_DARK}; border-radius:50%; "
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
