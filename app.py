# -*- coding: utf-8 -*-
import os
from fastapi import Request
from nicegui import ui, app

from db import init_db
from seed import seed_demo
from theme import GLOBAL_CSS
from pwa import PWA_HEAD_HTML, FAVICON_DATA_URI
import home_page, creditos_page, comprar_page, agenda_page, perfil_page, presenca_page, dashboard_page, configuracoes_page
import payments
import newsletters
from layout import shell

init_db()
if os.environ.get("CANOA_SEED_DEMO", "1") == "1":
    seed_demo()
newsletters.seed_newsletters_iniciais()


@app.post("/webhook/mercadopago")
async def webhook_mercadopago(request: Request):
    """Recebe a confirmação de pagamento do Mercado Pago (fonte confiável de verdade)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    query = dict(request.query_params)
    try:
        payments.processar_webhook(body, query)
    except Exception as e:
        # Nunca deixamos uma falha aqui derrubar a resposta ao Mercado Pago —
        # ele reenvia a notificação depois se não receber 200 OK.
        print(f"[webhook mercadopago] erro ao processar: {e}")
    return {"status": "ok"}


def _logged_in():
    return "id" in app.storage.user


def _require_role(*roles):
    return app.storage.user.get("role") in roles


@ui.page("/")
def pagina_home():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
    if _logged_in():
        ui.navigate.to("/creditos")
        return
    home_page.render()


@ui.page("/creditos")
def pagina_creditos():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/creditos", app.storage.user):
        creditos_page.render(app.storage.user)


@ui.page("/comprar")
def pagina_comprar():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/creditos", app.storage.user):
        comprar_page.render(app.storage.user)


@ui.page("/agenda")
def pagina_agenda():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/agenda", app.storage.user):
        agenda_page.render(app.storage.user)


@ui.page("/perfil")
def pagina_perfil():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/perfil", app.storage.user):
        perfil_page.render(app.storage.user)


@ui.page("/presenca")
def pagina_presenca():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
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
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/creditos")
        return
    with shell("/dashboard", app.storage.user):
        dashboard_page.render(app.storage.user)


@ui.page("/configuracoes")
def pagina_configuracoes():
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/creditos")
        return
    with shell("/configuracoes", app.storage.user):
        configuracoes_page.render(app.storage.user)


# A "storage_secret" assina o cookie de sessão do usuário — troque por um
# valor aleatório e secreto quando for para produção (pode vir de uma
# variável de ambiente, ex: os.environ["NICEGUI_STORAGE_SECRET"]).
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        title="Kalani Vaa Team",
        favicon=FAVICON_DATA_URI,
        storage_secret=os.environ.get("NICEGUI_STORAGE_SECRET", "troque-esta-chave-em-producao"),
        reload=False,
    )
