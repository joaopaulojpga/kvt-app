# -*- coding: utf-8 -*-
import os
from fastapi import Request
from nicegui import ui, app

from db import init_db
from seed import seed_demo
from theme import GLOBAL_CSS, TEAL, NAVY, TEAL_DARK, OK, DANGER, WARN
from pwa import PWA_HEAD_HTML, FAVICON_DATA_URI
import home_page, creditos_page, comprar_page, agenda_page, perfil_page, presenca_page, dashboard_page, configuracoes_page
import historico_creditos_page, movimentacoes_page
import payments
import newsletters
from layout import shell

init_db()
if os.environ.get("CANOA_SEED_DEMO", "1") == "1":
    seed_demo()
newsletters.seed_newsletters_iniciais()

# Fotos do clube (ex: imagem de fundo da landing) — não é UI, é registro de
# rota no FastAPI por baixo, então pode ficar no escopo do módulo mesmo
# nesta versão do NiceGUI que restringe chamadas de ui.* no escopo global.
app.add_static_files("/img", "static")


def _aplicar_tema():
    """
    Injeta o CSS global + favicon PWA e define a paleta de marca do Quasar
    (afeta componentes nativos: foco de input, aba ativa, checkbox, switch,
    spinner, notify etc.). Chamado dentro de cada @ui.page — versões mais
    recentes do NiceGUI (3.x) não permitem chamadas de UI no escopo global
    do módulo quando o app usa @ui.page.
    """
    ui.add_head_html(f"<style>{GLOBAL_CSS}</style>{PWA_HEAD_HTML}")
    ui.colors(primary=TEAL, secondary=NAVY, accent=TEAL_DARK, positive=OK, negative=DANGER, warning=WARN)


@app.post("/webhook/asaas")
async def webhook_asaas(request: Request):
    """Recebe a confirmação de pagamento do Asaas (fonte confiável de verdade)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        payments.processar_webhook(body, dict(request.headers))
    except Exception as e:
        # Nunca deixamos uma falha aqui derrubar a resposta ao Asaas — ele
        # reenvia a notificação depois se não receber HTTP 2xx.
        print(f"[webhook asaas] erro ao processar: {e}")
    return {"status": "ok"}


def _logged_in():
    return "id" in app.storage.user


def _require_role(*roles):
    return app.storage.user.get("role") in roles


@ui.page("/")
def pagina_home():
    _aplicar_tema()
    if _logged_in():
        ui.navigate.to("/creditos")
        return
    home_page.render()


@ui.page("/creditos")
def pagina_creditos():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/creditos", app.storage.user):
        creditos_page.render(app.storage.user)


@ui.page("/comprar")
def pagina_comprar():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/creditos", app.storage.user):
        comprar_page.render(app.storage.user)


@ui.page("/creditos/historico")
def pagina_historico_creditos():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/creditos/historico", app.storage.user):
        historico_creditos_page.render(app.storage.user)


@ui.page("/creditos/movimentacoes")
def pagina_movimentacoes_creditos():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/creditos")
        return
    with shell("/creditos/movimentacoes", app.storage.user):
        movimentacoes_page.render(app.storage.user)


@ui.page("/agenda")
def pagina_agenda():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/agenda", app.storage.user):
        agenda_page.render(app.storage.user)


@ui.page("/perfil")
def pagina_perfil():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/perfil", app.storage.user):
        perfil_page.render(app.storage.user)


@ui.page("/presenca")
def pagina_presenca():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("instrutor", "gestor"):
        ui.navigate.to("/creditos")
        return
    with shell("/presenca", app.storage.user):
        presenca_page.render(app.storage.user)


@ui.page("/dashboard")
def pagina_dashboard():
    _aplicar_tema()
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
    _aplicar_tema()
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
