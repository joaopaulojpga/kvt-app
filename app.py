# -*- coding: utf-8 -*-
import os
from fastapi import Request
from fastapi.responses import PlainTextResponse
from nicegui import ui, app

from db import init_db
from seed import seed_demo
from theme import GLOBAL_CSS, TEAL, NAVY, TEAL_DARK, OK, DANGER, WARN
from pwa import PWA_HEAD_HTML, FAVICON_DATA_URI
import home_page, creditos_page, comprar_page, agenda_page, perfil_page, presenca_page, dashboard_page, configuracoes_page
import historico_creditos_page, movimentacoes_page, mensagens_page
import landing_page
import payments
import newsletters
from layout import shell

import whatsapp
import whatsapp_bot

init_db()
if os.environ.get("CANOA_SEED_DEMO", "1") == "1":
    seed_demo()
newsletters.seed_newsletters_iniciais()


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


@app.get("/webhook/whatsapp")
async def verificar_webhook_whatsapp(request: Request):
    """
    Meta chama isso UMA VEZ (GET) quando você configura a URL do webhook
    no painel, só pra confirmar que o endpoint é seu de verdade.
    """
    modo = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    desafio = request.query_params.get("hub.challenge") or ""
    if modo == "subscribe" and token == os.environ.get("WHATSAPP_VERIFY_TOKEN"):
        return PlainTextResponse(desafio)
    return PlainTextResponse("token de verificação inválido", status_code=403)


@app.post("/webhook/whatsapp")
async def receber_whatsapp(request: Request):
    """Recebe mensagens que os usuários mandam pro número do clube (Scripts — Fase 2)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        whatsapp_bot.processar_webhook_recebido(body)
    except Exception as e:
        print(f"[webhook whatsapp] erro ao processar: {e}")
    return {"status": "ok"}


@app.post("/tasks/lembretes-vespera")
async def tarefa_lembretes_vespera(request: Request):
    """
    Chamado periodicamente por um agendador EXTERNO gratuito (GitHub
    Actions ou cron-job.org) — não por um Cron Job do Render, que é
    pago. Protegido por um token simples via query string.
    """
    token_esperado = os.environ.get("TASKS_TOKEN")
    if token_esperado and request.query_params.get("token") != token_esperado:
        return {"status": "erro", "motivo": "token inválido"}
    try:
        enviados = whatsapp.verificar_lembretes_vespera()
    except Exception as e:
        print(f"[tasks] erro ao verificar lembretes de véspera: {e}")
        return {"status": "erro", "detalhe": str(e)}
    return {"status": "ok", "enviados": enviados}


def _logged_in():
    return "id" in app.storage.user


def _require_role(*roles):
    return app.storage.user.get("role") in roles


@ui.page("/")
def pagina_home(request: Request):
    _aplicar_tema()
    if _logged_in():
        ui.navigate.to("/home")
        return
    # kalanivaa.com.br (domínio raiz) = landing institucional, só
    # prospecção; qualquer outro host (app.kalanivaa.com.br, o domínio
    # antigo do Render, localhost etc.) mostra a página de acesso ao
    # sistema (login/cadastro).
    host = (request.headers.get("host") or "").split(":")[0].lower()
    if host == "kalanivaa.com.br":
        landing_page.render()
    else:
        home_page.render()


@ui.page("/home")
def pagina_creditos():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/home", app.storage.user):
        creditos_page.render(app.storage.user)


@ui.page("/comprar")
def pagina_comprar():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    with shell("/comprar", app.storage.user):
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
        ui.navigate.to("/home")
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
        ui.navigate.to("/home")
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
        ui.navigate.to("/home")
        return
    with shell("/dashboard", app.storage.user):
        dashboard_page.render(app.storage.user)


@ui.page("/configuracoes")
def pagina_configuracoes():
    # rota antiga (favoritos salvos, links já compartilhados) — redireciona
    # pro primeiro item do submenu em vez de quebrar.
    ui.navigate.to("/configuracoes/alunos")


@ui.page("/configuracoes/alunos")
def pagina_configuracoes_alunos():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/home")
        return
    with shell("/configuracoes/alunos", app.storage.user):
        configuracoes_page.render_alunos(app.storage.user)


@ui.page("/configuracoes/relatorios")
def pagina_configuracoes_relatorios():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/home")
        return
    with shell("/configuracoes/relatorios", app.storage.user):
        configuracoes_page.render_relatorios(app.storage.user)


@ui.page("/configuracoes/newsletter")
def pagina_configuracoes_newsletter():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/home")
        return
    with shell("/configuracoes/newsletter", app.storage.user):
        configuracoes_page.render_newsletter(app.storage.user)


@ui.page("/configuracoes/escala")
def pagina_configuracoes_escala():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/home")
        return
    with shell("/configuracoes/escala", app.storage.user):
        configuracoes_page.render_escala(app.storage.user)


@ui.page("/configuracoes/mensagens")
def pagina_configuracoes_mensagens():
    _aplicar_tema()
    if not _logged_in():
        ui.navigate.to("/")
        return
    if not _require_role("gestor"):
        ui.navigate.to("/home")
        return
    with shell("/configuracoes/mensagens", app.storage.user):
        mensagens_page.render(app.storage.user)


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
