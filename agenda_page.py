# -*- coding: utf-8 -*-
from nicegui import ui
from datetime import date
import calendar
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, DANGER, WARN
from ui_helpers import page_title, badge
from db import db
import reservations, attendance, classes as turmas_mod, mailer as email_mod
import booking_modal
from reservations import ReservaError
from classes import TurmaError

DIAS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _turmas_do_mes(hoje):
    primeiro = hoje.replace(day=1)
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    ultimo = hoje.replace(day=ultimo_dia)
    with db() as conn:
        rows = conn.execute(
            "SELECT c.*, u.nome AS instrutor_nome, u2.nome AS instrutor2_nome, "
            "  (SELECT COUNT(*) FROM reservations r WHERE r.class_id = c.id "
            "     AND r.status IN ('confirmada','presente','faltou')) AS confirmados "
            "FROM classes c "
            "JOIN users u ON u.id = c.instrutor_resp_id "
            "LEFT JOIN users u2 ON u2.id = c.instrutor2_id "
            "WHERE c.data BETWEEN ? AND ? AND c.status != 'cancelada' "
            "ORDER BY c.data, c.horario",
            (primeiro.isoformat(), ultimo.isoformat()),
        ).fetchall()
    return [dict(r) for r in rows]


def render(user, hoje=None):
    hoje = hoje or date.today()
    page_title(f"Agenda de Turmas", hoje.strftime("%B/%Y").capitalize())
    ui.label("Datas anteriores não aparecem para reserva \u2022 mostrando apenas o mês vigente.").style(
        f"color:{TEXT_MUTED}; font-size:12px; margin-top:-8px;"
    )

    lista_container = ui.column().style("width:100%; gap:12px;")

    def recarregar():
        lista_container.clear()
        turmas = _turmas_do_mes(hoje)
        with lista_container:
            if not turmas:
                ui.label("Nenhuma turma cadastrada para este mês ainda.").style(f"color:{TEXT_MUTED};")
            for t in turmas:
                _linha_turma(t, user, hoje, recarregar)

    if user["role"] == "instrutor":
        _form_criar_turma(user, hoje, recarregar)

    recarregar()


def _form_editar_turma(t, on_done):
    instrutores = turmas_mod.listar_instrutores()
    nomes = [i["nome"] for i in instrutores]
    ids_por_nome = {i["nome"]: i["id"] for i in instrutores}
    nome_resp_atual = t["instrutor_nome"] if t["instrutor_nome"] in nomes else (nomes[0] if nomes else None)
    nome_extra_atual = t["instrutor2_nome"] if t["instrutor2_nome"] in nomes else "(nenhum)"

    with ui.column().classes("canoa-card").style(f"width:100%; border-color:{TEAL}; gap:10px; margin-top:4px;"):
        ui.label("Editar turma").style(f"color:{TEAL_DARK}; font-weight:700; font-size:13.5px;")
        data_edit = ui.input("Data (AAAA-MM-DD)", value=str(t["data"]))
        horario_edit = ui.input("Horário (HH:MM)", value=t["horario"])
        tipo_edit = ui.select(["treino", "passeio"], value=t["tipo"], label="Tipo")
        resp_edit = ui.select(nomes, value=nome_resp_atual, label="Instrutor responsável *")
        extra_edit = ui.select(
            ["(nenhum)"] + nomes, value=nome_extra_atual,
            label="Instrutor extra (opcional)",
        )
        erro = ui.label("").style(f"color:{DANGER}; font-size:13px;")

        def salvar_edicao():
            try:
                turmas_mod.atualizar_turma(
                    t["id"], data_edit.value, horario_edit.value, tipo_edit.value,
                    instrutor_resp_id=ids_por_nome.get(resp_edit.value),
                    instrutor2_id=ids_por_nome.get(extra_edit.value) if extra_edit.value != "(nenhum)" else None,
                )
                ui.notify("Turma atualizada.", type="positive")
                on_done()
            except TurmaError as e:
                erro.set_text(str(e))

        ui.button("Salvar alterações", on_click=salvar_edicao).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:fit-content;"
        )


def _form_criar_turma(user, hoje, on_done):
    instrutores = turmas_mod.listar_instrutores()
    nomes = [i["nome"] for i in instrutores]
    ids_por_nome = {i["nome"]: i["id"] for i in instrutores}

    with ui.expansion("\u2795 Criar nova turma", value=False).classes("canoa-card").style("width:100%;"):
        with ui.column().style("gap:10px; padding-top:8px;"):
            data_nova = ui.input("Data (AAAA-MM-DD)", value=hoje.isoformat())
            horario_novo = ui.input("Horário (HH:MM)", value="06:00")
            tipo_novo = ui.select(["treino", "passeio"], value="treino", label="Tipo")
            resp_nome = ui.select(nomes, value=user["nome"] if user["nome"] in nomes else (nomes[0] if nomes else None),
                                   label="Instrutor responsável *")
            extra_nome = ui.select(
                ["(nenhum)"] + nomes,
                value="(nenhum)",
                label="Instrutor extra (opcional \u2014 se já sabe que vai passar de 12 remadores)",
            )
            erro = ui.label("").style(f"color:{DANGER}; font-size:13px;")

            def criar():
                try:
                    turmas_mod.criar_turma(
                        data_nova.value, horario_novo.value, tipo_novo.value,
                        instrutor_resp_id=ids_por_nome.get(resp_nome.value),
                        instrutor2_id=ids_por_nome.get(extra_nome.value) if extra_nome.value != "(nenhum)" else None,
                    )
                    ui.notify("Turma criada.", type="positive")
                    on_done()
                except TurmaError as e:
                    erro.set_text(str(e))

            ui.button("Criar turma", on_click=criar).props("unelevated").style(
                f"background:{TEAL}; color:white; font-weight:700; width:fit-content;"
            )


def _linha_turma(t, user, hoje, on_done):
    data_turma = t["data"] if isinstance(t["data"], date) else date.fromisoformat(str(t["data"]))
    if data_turma < hoje:
        return
    dia_semana = DIAS_PT[data_turma.weekday()]
    vagas_base_turma = t["vagas_base"] or 12
    vagas_max_turma = t["vagas_max"] or 18
    limite_exibido = vagas_base_turma if t["confirmados"] <= vagas_base_turma else vagas_max_turma
    vagas_str = f"{t['confirmados']}/{limite_exibido}"

    with ui.expansion(
        f"{dia_semana}, {t['data']} \u2014 {t['horario']} \u2022 {t['tipo'].capitalize()} \u2022 "
        f"{vagas_str} vagas" + (f" \u2022 {t['status'].upper()}" if t["status"] != "agendada" else "")
    ).classes("canoa-card").style("width:100%;"):
        with ui.column().style("gap:10px; padding-top:8px;"):
            resp_txt = f"Instrutor responsável: {t['instrutor_nome']}"
            if t["instrutor2_nome"]:
                resp_txt += f" \u2022 Instrutor extra: {t['instrutor2_nome']}"
            ui.label(resp_txt).style(f"color:{TEXT_MUTED}; font-size:12px;")

            participantes = reservations.listar_participantes(t["id"])
            if participantes:
                ui.label("Participantes confirmados:").style(f"color:{TEXT}; font-weight:700; font-size:13px;")
                for i, p in enumerate(participantes, 1):
                    marca = " (aguardando aprovação)" if p["status"] == "pendente_aprovacao" else ""
                    ui.label(f"{i}. {p['nome']}{marca}").style(f"color:{TEXT_MUTED}; font-size:12.5px;")
            else:
                ui.label("Nenhum participante ainda.").style(f"color:{TEXT_MUTED}; font-size:12.5px;")

            ja_reservado = any(p.get("user_id") == user["id"] for p in participantes)
            msg = ui.label("")

            with ui.row().style("gap:10px;"):
                if t["status"] == "agendada" and not ja_reservado:
                    def reservar(class_id=t["id"]):
                        try:
                            resultado = reservations.reservar(user["id"], class_id)
                            if resultado["status"] == "confirmada":
                                booking_modal.mostrar_confirmacao(t["data"], t["horario"])
                            else:
                                ui.notify(
                                    "Turma no limite de vagas. Solicitação enviada para aprovação "
                                    "do instrutor responsável.", type="warning"
                                )
                                with db() as conn:
                                    instrutor = conn.execute(
                                        "SELECT nome, email FROM users WHERE id = ?", (t["instrutor_resp_id"],)
                                    ).fetchone()
                                if instrutor:
                                    email_mod.enviar_notificacao_expansao(
                                        instrutor["email"], instrutor["nome"], user["nome"],
                                        t["data"], t["horario"],
                                    )
                            on_done()
                        except ReservaError as e:
                            msg.set_text(str(e))
                            msg.style(f"color:{DANGER}; font-size:12.5px;")

                    ui.button("Reservar", on_click=reservar).props("unelevated").style(
                        f"background:{TEAL}; color:white; font-weight:700;"
                    )

                if user["role"] == "instrutor" and t["status"] == "agendada":
                    def cancelar(class_id=t["id"]):
                        attendance.cancelar_turma_pelo_instrutor(class_id)
                        ui.notify("Turma cancelada. Remadas devolvidas com +7 dias de validade.", type="warning")
                        on_done()

                    ui.button("Cancelar turma", on_click=cancelar).props("outline").style(
                        f"color:{DANGER}; font-weight:700;"
                    )

                    edit_container = ui.column().style("width:100%;")

                    def abrir_edicao():
                        edit_container.clear()
                        with edit_container:
                            _form_editar_turma(t, on_done)

                    ui.button("Editar turma", on_click=abrir_edicao).props("outline").style(
                        f"color:{TEAL_DARK}; font-weight:700;"
                    )

            if user["role"] == "instrutor" and t["status"] == "agendada":
                ui.separator()
                _form_editar_vagas(t, on_done)


def _form_editar_vagas(t, on_done):
    instrutores = [i for i in turmas_mod.listar_instrutores() if i["id"] != t["instrutor_resp_id"]]
    nomes = [i["nome"] for i in instrutores]
    ids_por_nome = {i["nome"]: i["id"] for i in instrutores}

    ui.label("Editar quantidade de vagas desta turma (pode aumentar ou diminuir).").style(
        f"color:{TEXT_MUTED}; font-size:12px;"
    )
    with ui.row().style("gap:12px; align-items:end; flex-wrap:wrap;"):
        vagas_input = ui.number("Vagas ofertadas", value=int(t["vagas_base"] or 12), min=1, max=30, step=1).style(
            "width:140px;"
        )
        extra_select = ui.select(nomes, label="Instrutor extra (obrigatório > 13 vagas)").style("width:260px;")
        extra_select.visible = (t["vagas_base"] or 12) > 13
        erro = ui.label("").style(f"color:{DANGER}; font-size:12.5px;")

        def on_vagas_change(e):
            extra_select.visible = (e.value or 0) > 13

        vagas_input.on_value_change(on_vagas_change)

        def salvar():
            try:
                instrutor2_id = ids_por_nome.get(extra_select.value) if extra_select.visible else None
                turmas_mod.atualizar_vagas_turma(t["id"], int(vagas_input.value), instrutor2_id)
                ui.notify("Vagas atualizadas.", type="positive")
                on_done()
            except TurmaError as e:
                erro.set_text(str(e))

        ui.button("Salvar vagas", on_click=salvar).props("outline").style(f"color:{TEAL_DARK}; font-weight:700;")
