# -*- coding: utf-8 -*-
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED
from ui_helpers import page_title, badge, section_title
from db import db
import credits
import carousel


def render(user):
    page_title("Home")

    section_title("Meus Créditos")
    saldo = credits.saldo_disponivel(user["id"])
    validade = credits.proxima_validade(user["id"])

    with ui.row().style("gap:16px; width:100%; flex-wrap:wrap;"):
        with ui.column().style(
            f"background:{NAVY}; border-radius:14px; padding:24px; gap:6px; min-width:320px; flex:1;"
        ):
            ui.label("Créditos disponíveis").style("color:#BFD6E2; font-size:13px;")
            with ui.row().style("align-items:baseline; gap:8px;"):
                ui.label(str(saldo)).style("color:white; font-size:42px; font-weight:800;")
                ui.label("remadas").style("color:#CFE3EC; font-size:15px;")
            if validade:
                ui.label(f"Validade do próximo crédito: {validade}").style(
                    "color:#9FC1D3; font-size:11.5px;"
                )
            if saldo == 0:
                ui.label("Você não tem créditos disponíveis.").style(
                    "color:#F5C6A5; font-size:12.5px; margin-top:4px;"
                )
            ui.button("Comprar créditos", on_click=lambda: ui.navigate.to("/comprar")).props(
                "unelevated"
            ).style(f"background:{TEAL}; color:white; font-weight:700; margin-top:6px; width:fit-content;")

        with ui.column().style(
            "background:#EAF6F4; border:1px solid #0F9D8C; border-radius:14px; "
            "padding:24px; gap:6px; min-width:320px; flex:1;"
        ):
            ui.label("Pronto para remar?").style(f"color:{TEAL_DARK}; font-weight:700; font-size:15px;")
            ui.label("Veja as turmas disponíveis na agenda do mês e faça seu check-in.").style(
                f"color:{TEXT}; font-size:12.5px;"
            )
            ui.button("Reservar aula \u2192", on_click=lambda: ui.navigate.to("/agenda")).props(
                "unelevated"
            ).style(f"background:{TEAL}; color:white; font-weight:700; margin-top:6px; width:fit-content;")

    section_title("Novidades do clube")
    carousel.render_carousel()

    section_title("Histórico de remadas")

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
        "faltou": ("Faltou (crédito consumido)", "danger"),
        "confirmada": ("Reservado (aguardando a aula)", "muted"),
        "cancelada": ("Cancelada", "muted"),
        "pendente_aprovacao": ("Aguardando aprovação de vaga", "warn"),
    }
    with ui.column().classes("canoa-card").style("gap:4px; width:100%;"):
        for r in rows:
            texto, kind = label_kind.get(r["status"], (r["status"], "muted"))
            if r["status_turma"] in ("suspensa_clima", "suspensa_quorum"):
                texto, kind = "Suspensa \u2014 crédito devolvido", "muted"
            with ui.row().style(
                "justify-content:space-between; align-items:center; padding:8px 0; "
                "border-bottom:1px solid #EEF1F3; width:100%;"
            ):
                ui.label(f"{r['data']} \u00b7 {r['horario']} \u00b7 {r['tipo'].capitalize()}").style(
                    f"color:{TEXT}; font-size:13px;"
                )
                badge(texto, kind)
