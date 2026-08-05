# -*- coding: utf-8 -*-
import json
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED
from ui_helpers import page_title
import whatsapp


def render(user):
    page_title("Mensagens WhatsApp")
    ui.label(
        "Gere o texto pronto e cole manualmente no grupo do clube. Assim que tivermos o número "
        "de WhatsApp Business configurado, isso pode virar envio automático."
    ).style(f"color:{TEXT_MUTED}; font-size:12.5px; max-width:640px;")

    with ui.row().style("gap:16px; width:100%; flex-wrap:wrap; align-items:flex-start; margin-top:8px;"):
        _card_lista_semana()
        _card_convite()
        _card_informativo()


def _caixa_texto_copiavel(texto):
    with ui.column().style("gap:8px; width:100%;"):
        area = ui.textarea(value=texto).props("readonly").classes("w-full").style("font-size:12.5px;")

        def copiar():
            ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(texto)})")
            ui.notify("Texto copiado! Cole no grupo do WhatsApp.", type="positive")

        ui.button("Copiar texto", icon="content_copy", on_click=copiar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700;"
        )


def _card_lista_semana():
    with ui.column().classes("canoa-card").style("flex:1; min-width:300px; gap:10px;"):
        ui.label("Lista de turmas da semana").style(f"color:{NAVY}; font-weight:800; font-size:14px;")
        ui.label("Turmas com instrutor definido nos próximos 7 dias.").style(
            f"color:{TEXT_MUTED}; font-size:11.5px;"
        )
        container = ui.column().style("width:100%;")

        def gerar():
            container.clear()
            with container:
                _caixa_texto_copiavel(whatsapp.gerar_texto_lista_semana())

        ui.button("Gerar", on_click=gerar).props("outline").style(f"color:{TEAL_DARK}; font-weight:700;")
        container


def _card_convite():
    with ui.column().classes("canoa-card").style("flex:1; min-width:300px; gap:10px;"):
        ui.label("Convite para remada").style(f"color:{NAVY}; font-weight:800; font-size:14px;")
        ui.label("Chamada padrão convidando pra reservar.").style(f"color:{TEXT_MUTED}; font-size:11.5px;")
        container = ui.column().style("width:100%;")

        def gerar():
            container.clear()
            with container:
                _caixa_texto_copiavel(whatsapp.gerar_texto_convite_remada())

        ui.button("Gerar", on_click=gerar).props("outline").style(f"color:{TEAL_DARK}; font-weight:700;")
        container


def _card_informativo():
    with ui.column().classes("canoa-card").style("flex:1; min-width:300px; gap:10px;"):
        ui.label("Informativo (eventos, orientações)").style(f"color:{NAVY}; font-weight:800; font-size:14px;")
        titulo = ui.input("Título").classes("w-full")
        corpo = ui.textarea("Mensagem").classes("w-full")
        container = ui.column().style("width:100%;")

        def gerar():
            if not (titulo.value and corpo.value):
                ui.notify("Preencha título e mensagem.", type="warning")
                return
            container.clear()
            with container:
                _caixa_texto_copiavel(whatsapp.gerar_texto_informativo(titulo.value, corpo.value))

        ui.button("Gerar", on_click=gerar).props("outline").style(f"color:{TEAL_DARK}; font-weight:700;")
        container
