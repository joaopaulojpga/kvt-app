# -*- coding: utf-8 -*-
import os
from nicegui import ui, app

from db import init_db
from seed import seed_demo
from theme import GLOBAL_CSS
import home_page, creditos_page, comprar_page, agenda_page, perfil_page, presenca_page, dashboard_page
from layout import shell

init_db()
if os.environ.get("CANOA_SEED_DEMO", "1") == "1":
    seed_demo()


def _logged_in():
    return "id" in app.storage.user


def _require_role(*roles):
    return app.storage.user.get("role") in roles


@ui.page("/")
def pagina_home():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    if _logged_in():
        ui.navigate.to("/creditos")
        return
    home_page.render()


@ui.page("/creditos")
def pagina_creditos():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/creditos", app.storage.user):
        creditos_page.render(app.storage.user)


@ui.page("/comprar")
def pagina_comprar():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/creditos", app.storage.user):
        comprar_page.render(app.storage.user)


@ui.page("/agenda")
def pagina_agenda():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/agenda", app.storage.user):
        agenda_page.render(app.storage.user)


@ui.page("/perfil")
def pagina_perfil():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/perfil", app.storage.user):
        perfil_page.render(app.storage.user)


@ui.page("/presenca")
def pagina_presenca():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("instrutor"):
        ui.navigate.to("/creditos")
        return
    with shell("/presenca", app.storage.user):
        presenca_page.render(app.storage.user)


@ui.page("/dashboard")
def pagina_dashboard():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>")
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/creditos")
        return
    with shell("/dashboard", app.storage.user):
        dashboard_page.render(app.storage.user)


# A "storage_secret" assina o cookie de sessão do usuário — troque por um
# valor aleatório e secreto quando for para produção (pode vir de uma
# variável de ambiente, ex: os.environ["NICEGUI_STORAGE_SECRET"]).
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        title="Canoa Clube",
        storage_secret=os.environ.get("NICEGUI_STORAGE_SECRET", "troque-esta-chave-em-producao"),
        reload=False,
    )
