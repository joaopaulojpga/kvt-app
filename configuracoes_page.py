# -*- coding: utf-8 -*-
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, BORDER, DANGER
from ui_helpers import page_title, badge
import auth
import students


def render(user):
    page_title("Configurações")

    aba_container = ui.column().style("width:100%; gap:16px;")

    def mostrar(aba):
        aba_container.clear()
        with aba_container:
            with ui.row().style("gap:8px; margin-bottom:4px;"):
                ui.button("Lista de Alunos", on_click=lambda: mostrar("alunos")).props(
                    "unelevated" if aba == "alunos" else "outline"
                ).style(
                    (f"background:{TEAL}; color:white;" if aba == "alunos" else f"color:{TEAL_DARK};")
                    + " font-weight:700;"
                )
                ui.button("Relatórios", on_click=lambda: mostrar("relatorios")).props(
                    "unelevated" if aba == "relatorios" else "outline"
                ).style(
                    (f"background:{TEAL}; color:white;" if aba == "relatorios" else f"color:{TEAL_DARK};")
                    + " font-weight:700;"
                )
            if aba == "alunos":
                _secao_lista_alunos()
            else:
                _secao_relatorio_alunos()

    mostrar("alunos")


def _secao_lista_alunos():
    lista_container = ui.column().style("width:100%; gap:10px;")

    def recarregar():
        lista_container.clear()
        alunos = students.listar_alunos()
        with lista_container:
            if not alunos:
                ui.label("Nenhum aluno cadastrado ainda.").style(f"color:{TEXT_MUTED};")
                return
            for aluno in alunos:
                _linha_aluno(aluno, recarregar)

    recarregar()


def _linha_aluno(aluno, on_done):
    with ui.column().classes("canoa-card").style("width:100%; gap:8px;"):
        edit_container = ui.column().style("width:100%; order:2;")

        with ui.row().style("justify-content:space-between; align-items:center; width:100%; flex-wrap:wrap; gap:8px; order:1;"):
            with ui.column().style("gap:0;"):
                ui.label(aluno["nome"]).style(f"color:{TEXT}; font-weight:700; font-size:14px;")
                ui.label(f"{aluno['email']} \u2022 {aluno['celular']}").style(
                    f"color:{TEXT_MUTED}; font-size:12px;"
                )
            with ui.row().style("gap:8px;"):
                def promover(uid=aluno["id"]):
                    students.promover_para_instrutor(uid)
                    ui.notify(f"{aluno['nome']} agora é instrutor.", type="positive")
                    on_done()

                ui.button("Promover a instrutor", on_click=promover).props("outline").style(
                    f"color:{TEAL_DARK}; font-weight:700; font-size:12.5px;"
                )

                def abrir_edicao(a=aluno):
                    edit_container.clear()
                    with edit_container:
                        _form_editar_aluno(a, on_done)

                ui.button("Editar cadastro", on_click=abrir_edicao).props("flat dense").style(
                    f"color:{TEXT_MUTED}; font-weight:700; font-size:12.5px;"
                )


def _form_editar_aluno(aluno, on_done):
    dados = auth.get_usuario(aluno["id"])
    with ui.column().style(f"border-top:1px solid {BORDER}; padding-top:10px; gap:8px; width:100%;"):
        nome = ui.input("Nome completo *", value=dados["nome"]).classes("w-full")
        sexo = ui.select(["Feminino", "Masculino", "Outro"],
                          value=dados["sexo"] if dados["sexo"] in ["Feminino", "Masculino", "Outro"] else "Feminino",
                          label="Sexo *").classes("w-full")
        cpf = ui.input("CPF *", value=dados["cpf"]).classes("w-full")
        celular = ui.input("Celular / WhatsApp *", value=dados["celular"]).classes("w-full")
        nascimento = ui.input("Data de nascimento (AAAA-MM-DD)", value=dados["data_nascimento"] or "").classes("w-full")
        instagram = ui.input("Instagram (opcional)", value=dados["instagram"] or "").classes("w-full")
        erro = ui.label("").style(f"color:{DANGER}; font-size:12.5px;")

        def salvar():
            if not all([nome.value, sexo.value, cpf.value, celular.value]):
                erro.set_text("Preencha todos os campos obrigatórios (*).")
                return
            auth.atualizar_perfil(
                aluno["id"], nome=nome.value, sexo=sexo.value, cpf=cpf.value,
                celular=celular.value, instagram=instagram.value or None,
                data_nascimento=nascimento.value or None,
            )
            ui.notify("Cadastro atualizado.", type="positive")
            on_done()

        ui.button("Salvar", on_click=salvar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:fit-content;"
        )


def _secao_relatorio_alunos():
    linhas = students.relatorio_alunos()
    with ui.column().classes("canoa-card").style("width:100%; gap:0; overflow-x:auto;"):
        headers = ["Nome", "Status", "Aulas presentes", "Última aula", "Nascimento", "WhatsApp"]
        with ui.row().style(f"border-bottom:2px solid {BORDER}; padding-bottom:8px; gap:0; width:100%;"):
            larguras = ["26%", "12%", "14%", "16%", "16%", "16%"]
            for h, w in zip(headers, larguras):
                ui.label(h).style(f"width:{w}; color:{TEXT_MUTED}; font-weight:700; font-size:11.5px;")

        if not linhas:
            ui.label("Nenhum aluno cadastrado ainda.").style(f"color:{TEXT_MUTED}; padding-top:10px;")

        for linha in linhas:
            with ui.row().style("padding:8px 0; gap:0; width:100%; border-bottom:1px solid #EEF1F3;"):
                ui.label(linha["nome"]).style(f"width:26%; color:{TEXT}; font-size:12.5px;")
                with ui.row().style("width:12%;"):
                    badge(linha["status"], "ok" if linha["status"] == "Ativo" else "muted")
                ui.label(str(linha["aulas_reservadas"])).style(f"width:14%; color:{TEXT}; font-size:12.5px;")
                ui.label(linha["ultima_aula"] or "\u2014").style(f"width:16%; color:{TEXT}; font-size:12.5px;")
                ui.label(linha["data_nascimento"] or "\u2014").style(f"width:16%; color:{TEXT}; font-size:12.5px;")
                ui.label(linha["celular"]).style(f"width:16%; color:{TEXT}; font-size:12.5px;")
