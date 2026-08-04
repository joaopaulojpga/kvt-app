# -*- coding: utf-8 -*-
from nicegui import ui
from datetime import date
import calendar
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, DANGER, WARN
from ui_helpers import page_title, badge
from db import db
import reservations, attendance, classes as turmas_mod, mailer as email_mod, credits
import booking_modal
from reservations import ReservaError
from classes import TurmaError

from reports import MESES_PT

DIAS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
LOCAL_CLUBE = "Lagoa de Cima"
TURMAS_POR_PAGINA = 6  # grade 2 colunas x 3 linhas

_CAMPOS_TURMA = (
    "c.*, u.nome AS instrutor_nome, u2.nome AS instrutor2_nome, "
    "(SELECT COUNT(*) FROM reservations r WHERE r.class_id = c.id "
    "   AND r.status IN ('confirmada','presente','faltou')) AS confirmados"
)
_FROM_TURMA = (
    "FROM classes c "
    "JOIN users u ON u.id = c.instrutor_resp_id "  # INNER JOIN: só turmas com instrutor responsável definido
    "LEFT JOIN users u2 ON u2.id = c.instrutor2_id "
)


def _proximas_turmas(hoje, limite=6):
    """A remada mais próxima + as N-1 seguintes, independente do mês."""
    with db() as conn:
        rows = conn.execute(
            f"SELECT {_CAMPOS_TURMA} {_FROM_TURMA}"
            "WHERE c.data >= ? AND c.status != 'cancelada' "
            "ORDER BY c.data, c.horario LIMIT ?",
            (hoje.isoformat(), limite),
        ).fetchall()
    return [dict(r) for r in rows]


def _turmas_do_mes(ano, mes):
    primeiro = date(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    ultimo = date(ano, mes, ultimo_dia)
    with db() as conn:
        rows = conn.execute(
            f"SELECT {_CAMPOS_TURMA} {_FROM_TURMA}"
            "WHERE c.data BETWEEN ? AND ? AND c.status != 'cancelada' "
            "ORDER BY c.data, c.horario",
            (primeiro.isoformat(), ultimo.isoformat()),
        ).fetchall()
    return [dict(r) for r in rows]


def render(user, hoje=None):
    hoje = hoje or date.today()
    page_title("Agenda de Turmas")

    estado = {"modo": "proximas", "ano": hoje.year, "mes": hoje.month}
    corpo = ui.column().style("width:100%; gap:12px;")

    def ir_proximas():
        estado["modo"] = "proximas"
        redesenhar()

    def ir_mes(delta):
        estado["modo"] = "mes"
        total = estado["ano"] * 12 + (estado["mes"] - 1) + delta
        novo_ano, novo_mes = total // 12, total % 12 + 1
        # não navega para meses anteriores ao vigente (mesma regra já aplicada em Escala/Relatórios)
        if (novo_ano, novo_mes) >= (hoje.year, hoje.month):
            estado["ano"], estado["mes"] = novo_ano, novo_mes
        redesenhar()

    def redesenhar():
        corpo.clear()
        with corpo:
            with ui.row().style("gap:8px; flex-wrap:wrap; align-items:center;"):
                ui.button("Próximas remadas", on_click=ir_proximas).props(
                    "unelevated" if estado["modo"] == "proximas" else "outline"
                ).style(
                    (f"background:{TEAL}; color:white;" if estado["modo"] == "proximas" else f"color:{TEAL_DARK};")
                    + " font-weight:700;"
                )
                ui.button("Ver por mês", on_click=lambda: ir_mes(0)).props(
                    "unelevated" if estado["modo"] == "mes" else "outline"
                ).style(
                    (f"background:{TEAL}; color:white;" if estado["modo"] == "mes" else f"color:{TEAL_DARK};")
                    + " font-weight:700;"
                )

            if estado["modo"] == "proximas":
                ui.label("Sua próxima remada e as 5 seguintes, considerando a grade padrão.").style(
                    f"color:{TEXT_MUTED}; font-size:12px;"
                )
                turmas = _proximas_turmas(hoje)
            else:
                no_mes_vigente = (estado["ano"], estado["mes"]) == (hoje.year, hoje.month)
                with ui.row().style("gap:6px; align-items:center;"):
                    ui.button(icon="chevron_left", on_click=lambda: ir_mes(-1)).props(
                        "flat dense round"
                    ).style(f"color:{TEAL_DARK};").set_enabled(not no_mes_vigente)
                    ui.label(f"{MESES_PT[estado['mes']].capitalize()}/{estado['ano']}").style(
                        f"color:{TEXT}; font-weight:700; font-size:14px; min-width:120px; text-align:center;"
                    )
                    ui.button(icon="chevron_right", on_click=lambda: ir_mes(1)).props(
                        "flat dense round"
                    ).style(f"color:{TEAL_DARK};")
                turmas = [t for t in _turmas_do_mes(estado["ano"], estado["mes"])
                          if date.fromisoformat(str(t["data"])) >= hoje]

            if not turmas:
                ui.label("Nenhuma turma encontrada.").style(f"color:{TEXT_MUTED};")
            else:
                _grade_turmas(turmas, user, hoje, redesenhar)

    if user["role"] == "instrutor":
        _form_criar_turma(user, hoje, redesenhar)

    redesenhar()


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


def _grade_turmas(turmas, user, hoje, on_done):
    estado_pg = {"pagina": 0}
    total_paginas = max(1, -(-len(turmas) // TURMAS_POR_PAGINA))  # ceil
    grade_container = ui.column().style("width:100%; gap:12px;")

    def desenhar_pagina():
        grade_container.clear()
        inicio = estado_pg["pagina"] * TURMAS_POR_PAGINA
        pagina_turmas = turmas[inicio:inicio + TURMAS_POR_PAGINA]
        with grade_container:
            with ui.element("div").style(
                "display:grid; grid-template-columns:repeat(2, 1fr); gap:14px; width:100%;"
            ):
                for t in pagina_turmas:
                    _card_turma(t, user, hoje, on_done)

            if total_paginas > 1:
                with ui.row().style("gap:10px; align-items:center; justify-content:center; width:100%; margin-top:4px;"):
                    ui.button(icon="chevron_left", on_click=lambda: mudar_pagina(-1)).props(
                        "flat dense round"
                    ).style(f"color:{TEAL_DARK};").set_enabled(estado_pg["pagina"] > 0)
                    ui.label(f"Página {estado_pg['pagina'] + 1} de {total_paginas}").style(
                        f"color:{TEXT_MUTED}; font-size:12.5px;"
                    )
                    ui.button(icon="chevron_right", on_click=lambda: mudar_pagina(1)).props(
                        "flat dense round"
                    ).style(f"color:{TEAL_DARK};").set_enabled(estado_pg["pagina"] < total_paginas - 1)

    def mudar_pagina(delta):
        estado_pg["pagina"] = max(0, min(total_paginas - 1, estado_pg["pagina"] + delta))
        desenhar_pagina()

    desenhar_pagina()


def _card_turma(t, user, hoje, on_done):
    data_turma = t["data"] if isinstance(t["data"], date) else date.fromisoformat(str(t["data"]))
    dia_semana = DIAS_PT[data_turma.weekday()]
    vagas_base_turma = t["vagas_base"] or 12
    vagas_max_turma = t["vagas_max"] or 18
    limite_exibido = vagas_base_turma if t["confirmados"] <= vagas_base_turma else vagas_max_turma

    participantes = reservations.listar_participantes(t["id"])
    minha_reserva = next((p for p in participantes if p.get("user_id") == user["id"]), None)
    ja_reservado = minha_reserva is not None

    with ui.column().classes("canoa-card").style("width:100%; gap:10px; padding:16px;"):
        with ui.row().style("justify-content:space-between; align-items:flex-start; width:100%;"):
            with ui.row().style("gap:8px; align-items:center;"):
                ui.icon("event", size="22px").style(f"color:{TEAL};")
                with ui.column().style("gap:0;"):
                    ui.label(data_turma.strftime("%d/%m")).style(
                        f"color:{NAVY}; font-size:20px; font-weight:800; line-height:1.1;"
                    )
                    ui.label(dia_semana).style(f"color:{TEXT_MUTED}; font-size:12px;")
            with ui.column().style(
                f"background:#EAF6F4; border-radius:50%; width:52px; height:52px; "
                "align-items:center; justify-content:center; gap:0; flex-shrink:0;"
            ):
                ui.label(f"{t['confirmados']}/{limite_exibido}").style(
                    f"color:{TEAL_DARK}; font-weight:800; font-size:12px; line-height:1.1;"
                )
                ui.label("vagas").style(f"color:{TEAL_DARK}; font-size:8.5px;")

        with ui.column().style("gap:3px; width:100%;"):
            with ui.row().style("gap:6px; align-items:center;"):
                ui.icon("schedule", size="14px").style(f"color:{TEXT_MUTED};")
                ui.label(f"às {t['horario']}").style(f"color:{TEXT}; font-size:12.5px;")
            with ui.row().style("gap:6px; align-items:center;"):
                ui.icon("sports", size="14px").style(f"color:{TEXT_MUTED};")
                ui.label(f"Instrutor: {t['instrutor_nome']}").style(f"color:{TEXT}; font-size:12.5px;")
            with ui.row().style("gap:6px; align-items:center;"):
                ui.icon("place", size="14px").style(f"color:{TEXT_MUTED};")
                ui.label(LOCAL_CLUBE).style(f"color:{TEXT}; font-size:12.5px;")

        if t["status"] != "agendada":
            badge(t["status"].replace("_", " ").upper(), "muted")
        elif ja_reservado:
            badge(
                "Aguardando aprovação" if minha_reserva["status"] == "pendente_aprovacao" else "Você está inscrito(a)",
                "warn" if minha_reserva["status"] == "pendente_aprovacao" else "ok",
            )

        msg = ui.label("").style(f"color:{DANGER}; font-size:11.5px;")

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

        def desfazer(res_id=minha_reserva["id"] if minha_reserva else None):
            try:
                reservations.cancelar_reserva(res_id)
                ui.notify("Reserva desfeita. Sua remada foi devolvida.", type="positive")
                on_done()
            except ReservaError as e:
                msg.set_text(str(e))

        if t["status"] == "agendada" and not ja_reservado:
            ui.button("Reservar", icon="chevron_right", on_click=reservar).props(
                "unelevated"
            ).classes("w-full").style(f"background:{TEAL}; color:white; font-weight:700;")
        elif t["status"] == "agendada" and ja_reservado and minha_reserva["status"] != "pendente_aprovacao":
            ui.button("Desfazer reserva", on_click=desfazer).props("outline").classes("w-full").style(
                f"color:{DANGER}; font-weight:700;"
            ).tooltip("Permitido até 12h antes do início da aula")

        ui.label("Ver detalhes").style(
            f"color:{TEAL_DARK}; font-size:12px; font-weight:700; text-decoration:underline; "
            "cursor:pointer; align-self:center;"
        ).on("click", lambda: _abrir_detalhes_turma(t, user, on_done))


def _abrir_detalhes_turma(t, user, on_done):
    with ui.dialog() as dialog, ui.card().style("width:min(520px, 92vw); padding:20px; gap:10px;"):
        data_turma = t["data"] if isinstance(t["data"], date) else date.fromisoformat(str(t["data"]))
        dia_semana = DIAS_PT[data_turma.weekday()]
        ui.label(f"{dia_semana}, {t['data']} \u2014 {t['horario']}").style(
            f"color:{NAVY}; font-weight:800; font-size:16px;"
        )
        resp_txt = f"Instrutor responsável: {t['instrutor_nome']}"
        if t["instrutor2_nome"]:
            resp_txt += f" \u2022 Instrutor extra: {t['instrutor2_nome']}"
        ui.label(resp_txt).style(f"color:{TEXT_MUTED}; font-size:12px;")

        def fechar_e_atualizar():
            dialog.close()
            on_done()

        participantes = reservations.listar_participantes(t["id"])
        if participantes:
            ui.label("Participantes confirmados:").style(f"color:{TEXT}; font-weight:700; font-size:13px;")
            for i, p in enumerate(participantes, 1):
                marca = " (aguardando aprovação)" if p["status"] == "pendente_aprovacao" else ""
                with ui.row().style("align-items:center; gap:8px;"):
                    ui.label(f"{i}. {p['nome']}{marca}").style(f"color:{TEXT_MUTED}; font-size:12.5px;")
                    if user["role"] == "instrutor":
                        def remover(res_id=p["id"], nome=p["nome"]):
                            try:
                                reservations.remover_aluno(res_id)
                                ui.notify(f"{nome} removido(a) da turma \u2014 crédito devolvido.", type="positive")
                                fechar_e_atualizar()
                            except ReservaError as e:
                                ui.notify(str(e), type="negative")

                        ui.icon("close", size="16px").style(
                            f"color:{DANGER}; cursor:pointer;"
                        ).tooltip("Remover aluno (devolve o crédito)").on("click", remover)
        else:
            ui.label("Nenhum participante ainda.").style(f"color:{TEXT_MUTED}; font-size:12.5px;")

        if user["role"] == "instrutor" and t["status"] == "agendada":
            ui.separator()
            with ui.row().style("gap:10px;"):
                def cancelar(class_id=t["id"]):
                    attendance.cancelar_turma_pelo_instrutor(class_id)
                    ui.notify("Turma cancelada. Remadas devolvidas com +7 dias de validade.", type="warning")
                    fechar_e_atualizar()

                ui.button("Cancelar turma", on_click=cancelar).props("outline").style(
                    f"color:{DANGER}; font-weight:700;"
                )

                edit_container = ui.column().style("width:100%;")

                def abrir_edicao():
                    edit_container.clear()
                    with edit_container:
                        _form_editar_turma(t, fechar_e_atualizar)

                ui.button("Editar turma", on_click=abrir_edicao).props("outline").style(
                    f"color:{TEAL_DARK}; font-weight:700;"
                )

            ui.separator()
            _form_editar_vagas(t, fechar_e_atualizar)

        ui.button("Fechar", on_click=dialog.close).props("flat").style(
            f"color:{TEXT_MUTED}; align-self:flex-end;"
        )
    dialog.open()


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
