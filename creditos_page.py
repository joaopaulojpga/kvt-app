# -*- coding: utf-8 -*-
from nicegui import ui
from datetime import date
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED
from ui_helpers import page_title, badge, section_title
from db import db
import credits
import reservations
import carousel

DIAS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def render(user):
    primeiro_nome = user["nome"].split()[0]
    ui.label(f"Bem-vindo de volta, {primeiro_nome}.").style(
        f"color:{NAVY}; font-size:22px; font-weight:800;"
    )

    frequencia = reservations.contagem_remadas_mes(user["id"])
    if frequencia > 0:
        ui.label(f"Você remou {frequencia}x este mês \U0001F525").style(
            f"color:{TEAL_DARK}; font-size:13px; font-weight:700; margin-top:-12px;"
        )

    _card_proxima_remada(user)

    section_title("Minhas Remadas")
    _card_remadas(user)

    section_title("Novidades do clube")
    carousel.render_carousel()

    section_title("Histórico de remadas")
    _historico(user)


def _card_proxima_remada(user):
    prox = reservations.proxima_reserva(user["id"])
    if prox:
        data_fmt = str(prox["data"])
        try:
            d = date.fromisoformat(data_fmt)
            data_fmt = f"{DIAS_PT[d.weekday()]}, {d.strftime('%d/%m/%Y')}"
        except ValueError:
            pass
        with ui.column().style(
            f"background:{NAVY}; border-radius:14px; padding:24px; gap:6px; width:100%;"
        ):
            ui.label("Sua próxima remada").style("color:#BFD6E2; font-size:13px; font-weight:700;")
            ui.label(f"\U0001F4C5 {data_fmt}").style("color:white; font-size:16px; font-weight:700;")
            ui.label(f"\U0001F550 {prox['horario']}  \u00b7  \U0001F4CD Lagoa de Cima").style(
                "color:#CFE3EC; font-size:13.5px;"
            )
            ui.label("Estamos te esperando! \U0001F33A").style("color:#9FC1D3; font-size:12.5px; margin-top:2px;")
            ui.button("Ver detalhes", on_click=lambda: ui.navigate.to("/agenda")).props(
                "outline"
            ).style("color:white; border-color:white; font-weight:700; margin-top:8px; width:fit-content;")
    else:
        with ui.column().style(
            "background:#EAF6F4; border:1px solid #62A832; border-radius:14px; "
            "padding:24px; gap:6px; width:100%;"
        ):
            ui.label("Você ainda não possui nenhuma remada agendada.").style(
                f"color:{TEAL_DARK}; font-weight:700; font-size:15px;"
            )
            ui.label("Que tal escolher um horário e garantir sua vaga?").style(
                f"color:{TEXT}; font-size:12.5px;"
            )
            ui.button("Reservar agora", on_click=lambda: ui.navigate.to("/agenda")).props(
                "unelevated"
            ).style(f"background:{TEAL}; color:white; font-weight:700; margin-top:6px; width:fit-content;")


def _card_remadas(user):
    saldo = credits.saldo_disponivel(user["id"])
    validade = credits.proxima_validade(user["id"])
    with ui.column().classes("canoa-card").style("gap:6px; width:100%;"):
        ui.label("Remadas disponíveis").style(f"color:{TEXT_MUTED}; font-size:13px;")
        with ui.row().style("align-items:baseline; gap:8px;"):
            ui.label(str(saldo)).style(f"color:{NAVY}; font-size:42px; font-weight:800;")
            ui.label("remadas").style(f"color:{TEXT_MUTED}; font-size:15px;")
        if validade:
            ui.label(f"Validade da próxima a vencer: {validade}").style(
                f"color:{TEXT_MUTED}; font-size:11.5px;"
            )
        if saldo == 0:
            ui.label("Você não tem remadas disponíveis no momento.").style(
                "color:#B5651D; font-size:12.5px; margin-top:2px;"
            )
        ui.button("Comprar remadas", on_click=lambda: ui.navigate.to("/comprar")).props(
            "unelevated"
        ).style(f"background:{TEAL}; color:white; font-weight:700; margin-top:6px; width:fit-content;")


def _historico(user):
    with db() as conn:
        rows = conn.execute(
            "SELECT c.data, c.horario, c.tipo, r.status, c.status AS status_turma "
            "FROM reservations r JOIN classes c ON c.id = r.class_id "
            "WHERE r.user_id = ? ORDER BY c.data DESC, c.horario DESC",
            (user["id"],),
        ).fetchall()

    if not rows:
        ui.label("Nenhuma remada ainda. Que tal reservar sua primeira turma?").style(
            f"color:{TEXT_MUTED}; font-size:13px;"
        )
        return

    label_kind = {
        "presente": ("Compareceu", "ok"),
        "faltou": ("Faltou (remada consumida)", "danger"),
        "confirmada": ("Reservado (aguardando a aula)", "muted"),
        "cancelada": ("Cancelada", "muted"),
        "pendente_aprovacao": ("Aguardando aprovação de vaga", "warn"),
    }
    with ui.column().classes("canoa-card").style("gap:4px; width:100%;"):
        for r in rows:
            texto, kind = label_kind.get(r["status"], (r["status"], "muted"))
            if r["status_turma"] in ("suspensa_clima", "suspensa_quorum"):
                texto, kind = "Suspensa \u2014 remada devolvida", "muted"
            with ui.row().style(
                "justify-content:space-between; align-items:center; padding:8px 0; "
                "border-bottom:1px solid #EEF1F3; width:100%;"
            ):
                ui.label(f"{r['data']} \u00b7 {r['horario']} \u00b7 {r['tipo'].capitalize()}").style(
                    f"color:{TEXT}; font-size:13px;"
                )
                badge(texto, kind)
