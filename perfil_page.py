# -*- coding: utf-8 -*-
from nicegui import ui
from theme import TEAL, TEAL_DARK, TEXT, TEXT_MUTED, DANGER
from ui_helpers import page_title
import auth


def render(user):
    page_title("Meu Cadastro")
    dados = auth.get_usuario(user["id"])

    with ui.column().classes("canoa-card").style("max-width:560px; gap:14px;"):
        ui.input("E-mail (não pode ser alterado)", value=dados["email"]).props("readonly").classes("w-full")
        ui.label("Para trocar o e-mail cadastrado, fale com um instrutor.").style(
            f"color:{TEXT_MUTED}; font-size:11.5px; margin-top:-10px;"
        )

        nome = ui.input("Nome completo *", value=dados["nome"]).classes("w-full")
        sexo = ui.select(["Feminino", "Masculino", "Outro"],
                          value=dados["sexo"] if dados["sexo"] in ["Feminino", "Masculino", "Outro"] else "Feminino",
                          label="Sexo *").classes("w-full")
        cpf = ui.input("CPF *", value=dados["cpf"]).classes("w-full")
        celular = ui.input("Celular / WhatsApp *", value=dados["celular"]).classes("w-full")
        instagram = ui.input("Instagram (opcional)", value=dados["instagram"] or "").classes("w-full")
        erro = ui.label("").style(f"color:{DANGER}; font-size:13px;")

        def salvar():
            if not all([nome.value, sexo.value, cpf.value, celular.value]):
                erro.set_text("Preencha todos os campos obrigatórios (*).")
                return
            auth.atualizar_perfil(
                user["id"], nome=nome.value, sexo=sexo.value,
                cpf=cpf.value, celular=celular.value, instagram=instagram.value or None,
            )
            user["nome"] = nome.value
            ui.notify("Dados atualizados.", type="positive")

        ui.button("Salvar alterações", on_click=salvar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:fit-content;"
        )
