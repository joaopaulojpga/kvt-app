# -*- coding: utf-8 -*-
from nicegui import ui
from datetime import date
from theme import TEAL, TEAL_DARK, TEXT, TEXT_MUTED, DANGER, WARN, reais
from ui_helpers import page_title
from db import db
import expansion, attendance, reservations
from attendance import BaixaError
from expansion import ExpansaoError


def render(user):
    page_title("Lista de Presença")

    pendentes_container = ui.column().style("width:100%; gap:10px;")
    turmas_container = ui.column().style("width:100%; gap:12px;")

    def recarregar():
        pendentes_container.clear()
        turmas_container.clear()
        _render_pendentes(user, pendentes_container, recarregar)
        _render_turmas_para_baixa(user, turmas_container, recarregar)

    recarregar()


def _render_pendentes(user, container, on_done):
    pendentes = expansion.listar_pendentes(instrutor_id=user["id"])
    if not pendentes:
        return
    with container:
        ui.label(f"\u26A0\uFE0F {len(pendentes)} solicitação(ões) de expansão de vaga pendente(s)").style(
            f"color:#8A5A12; font-weight:700; font-size:14px;"
        )
        with db() as conn:
            outros_instrutores = conn.execute(
                "SELECT id, nome FROM users WHERE role = 'instrutor' AND id != ?", (user["id"],)
            ).fetchall()
        nomes = {o["nome"]: o["id"] for o in outros_instrutores}

        for p in pendentes:
            with ui.row().classes("canoa-card").style(
                "width:100%; align-items:center; gap:16px; background:#FDF3E4; border-color:#E6A23C;"
            ):
                ui.label(f"{p['aluno_nome']} pediu vaga extra \u2014 {p['data']} {p['horario']}").style(
                    "flex:1; color:#8A5A12; font-size:13px;"
                )
                escolha = ui.select(list(nomes.keys()) or ["(nenhum instrutor)"], label="2\u00ba instrutor").style(
                    "width:200px;"
                )

                def aprovar(reservation_id=p["reservation_id"], escolha_ref=escolha):
                    try:
                        expansion.aprovar_expansao(reservation_id, nomes.get(escolha_ref.value))
                        ui.notify("Expansão aprovada.", type="positive")
                        on_done()
                    except ExpansaoError as e:
                        ui.notify(str(e), type="negative")

                def recusar(reservation_id=p["reservation_id"]):
                    expansion.recusar_expansao(reservation_id)
                    ui.notify("Solicitação recusada.", type="info")
                    on_done()

                ui.button("Aprovar", on_click=aprovar).props("unelevated").style(
                    f"background:{TEAL}; color:white; font-weight:700;"
                )
                ui.button("Recusar", on_click=recusar).props("outline").style(f"color:{DANGER};")
        ui.separator()


def _render_turmas_para_baixa(user, container, on_done):
    with db() as conn:
        turmas = conn.execute(
            "SELECT c.*, u.nome AS instrutor_nome FROM classes c "
            "JOIN users u ON u.id = c.instrutor_resp_id "
            "WHERE c.status = 'agendada' AND (c.instrutor_resp_id = ? OR c.instrutor2_id = ?) "
            "AND c.data <= ? ORDER BY c.data, c.horario",
            (user["id"], user["id"], date.today().isoformat()),
        ).fetchall()

    with container:
        ui.label("Turmas para dar baixa").style(f"color:{TEXT}; font-size:16px; font-weight:700;")
        if not turmas:
            ui.label("Nenhuma turma aguardando baixa (só aparecem turmas com data já iniciada).").style(
                f"color:{TEXT_MUTED}; font-size:13px;"
            )
            return

        for t in turmas:
            _linha_dar_baixa(dict(t), on_done)


def _linha_dar_baixa(t, on_done):
    participantes = reservations.listar_participantes(t["id"])
    confirmados = [p for p in participantes if p["status"] in ("confirmada", "presente", "faltou")]

    with ui.column().classes("canoa-card").style("width:100%; gap:10px;"):
        ui.label(f"{t['data']} \u2014 {t['horario']} \u2022 {len(confirmados)} inscritos").style(
            f"color:{TEXT}; font-weight:700; font-size:14px;"
        )
        status_radio = ui.radio(["Confirmada", "Suspensa \u2013 Clima", "Suspensa \u2013 Quórum"], value="Confirmada").props("inline")

        presencas_checks = {}
        presencas_container = ui.row().style("gap:16px; flex-wrap:wrap;")

        def montar_presencas():
            presencas_container.clear()
            presencas_checks.clear()
            if status_radio.value == "Confirmada":
                with presencas_container:
                    for p in confirmados:
                        presencas_checks[p["id"]] = ui.checkbox(p["nome"], value=True)

        status_radio.on_value_change(lambda _: montar_presencas())
        montar_presencas()

        erro = ui.label("").style(f"color:{DANGER}; font-size:12.5px;")

        def dar_baixa():
            mapa_status = {
                "Confirmada": "confirmada",
                "Suspensa \u2013 Clima": "suspensa_clima",
                "Suspensa \u2013 Quórum": "suspensa_quorum",
            }
            presencas = {rid: ("presente" if chk.value else "faltou") for rid, chk in presencas_checks.items()}
            try:
                resultado = attendance.dar_baixa(t["id"], mapa_status[status_radio.value], presencas)
                if resultado["status"] == "confirmada":
                    detalhe = resultado["detalhe"]
                    msg = f"Baixa registrada. Repasse instrutor 1: {reais(detalhe['repasse_instrutor1_centavos'])}"
                    if detalhe["remadores_instrutor2"] > 0:
                        msg += f" \u2022 Repasse instrutor 2: {reais(detalhe['repasse_instrutor2_centavos'])}"
                    ui.notify(msg, type="positive")
                else:
                    ui.notify("Turma marcada como suspensa. Créditos devolvidos com +7 dias de validade.", type="warning")
                on_done()
            except BaixaError as e:
                erro.set_text(str(e))

        ui.button("Dar baixa", on_click=dar_baixa).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:fit-content;"
        )
