# -*- coding: utf-8 -*-
from nicegui import ui, app
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, APP_NAME
from logo_data import LOGO_KALANI_DATA_URI
import auth


def render():
    with ui.column().style("max-width:900px; margin:0 auto; padding:48px 24px; gap:24px;"):
        with ui.row().style("align-items:center; gap:10px;"):
            ui.image(LOGO_KALANI_DATA_URI).style("width:40px; height:40px; border-radius:50%;")
            ui.label(APP_NAME).style(f"color:{NAVY}; font-size:26px; font-weight:800;")

        with ui.column().style(
            f"background:{NAVY}; border-radius:16px; padding:32px; gap:8px;"
        ):
            ui.label("Como funcionam nossas aulas").style(
                "color:white; font-size:22px; font-weight:800;"
            )
            ui.label(
                "Turmas de terça a domingo, reserva por crédito, remos e coletes inclusos. "
                "Compre seus créditos, confira a agenda do mês e garanta sua vaga."
            ).style("color:#CFE3EC; font-size:14px; max-width:560px;")

        with ui.row().style("gap:16px; width:100%;"):
            for titulo, desc in [
                ("1. Cadastre-se", "Crie sua conta com seus dados e comece."),
                ("2. Compre créditos", "Avulso ou em pacotes, com desconto."),
                ("3. Reserve sua aula", "Escolha o dia na agenda e faça check-in."),
            ]:
                with ui.column().classes("canoa-card").style("flex:1; gap:6px;"):
                    ui.label(titulo).style(f"color:{TEXT}; font-weight:700; font-size:14px;")
                    ui.label(desc).style(f"color:{TEXT_MUTED}; font-size:12.5px;")

        with ui.column().style(
            "background:#EAF6F4; border-radius:12px; padding:18px 22px; gap:2px;"
        ):
            ui.label("Grade principal").style(f"color:{TEAL_DARK}; font-weight:700; font-size:14px;")
            ui.label(
                "Terça 6h \u2022 Quinta 6h \u2022 Sábado 6h e 8h \u2022 Domingo 7h e 9h "
                "\u2014 vagas de 12, expansíveis até 18."
            ).style(f"color:{TEXT}; font-size:13px;")

        with ui.tabs().classes("w-full") as tabs:
            tab_login = ui.tab("Entrar")
            tab_cadastro = ui.tab("Cadastrar")
        with ui.tab_panels(tabs, value=tab_login).classes("w-full").style(
            "background:transparent;"
        ):
            with ui.tab_panel(tab_login):
                _form_login()
            with ui.tab_panel(tab_cadastro):
                _form_cadastro()


def _form_login():
    with ui.column().classes("canoa-card").style("max-width:420px; gap:12px;"):
        email = ui.input("E-mail").classes("w-full")
        senha = ui.input("Senha", password=True).classes("w-full")
        erro = ui.label("").style("color:#D9534F; font-size:13px;")

        def entrar():
            user = auth.autenticar(email.value or "", senha.value or "")
            if user is None:
                erro.set_text("E-mail ou senha inválidos.")
                return
            app.storage.user.update({"id": user["id"], "nome": user["nome"], "role": user["role"]})
            ui.navigate.to("/creditos")

        ui.button("Entrar", on_click=entrar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700;"
        )


def _form_cadastro():
    with ui.column().classes("canoa-card").style("max-width:480px; gap:10px;"):
        nome = ui.input("Nome completo *").classes("w-full")
        sexo = ui.select(["Feminino", "Masculino", "Outro"], value="Feminino", label="Sexo *").classes("w-full")
        email_c = ui.input("E-mail *").classes("w-full")
        senha_c = ui.input("Senha *", password=True).classes("w-full")
        cpf = ui.input("CPF *").classes("w-full")
        celular = ui.input("Celular / WhatsApp *").classes("w-full")
        instagram = ui.input("Instagram (opcional)").classes("w-full")
        erro = ui.label("").style("color:#D9534F; font-size:13px;")

        def cadastrar():
            campos = [nome.value, sexo.value, email_c.value, senha_c.value, cpf.value, celular.value]
            if not all(campos):
                erro.set_text("Preencha todos os campos obrigatórios (*).")
                return
            try:
                user_id = auth.cadastrar_usuario(
                    nome.value, sexo.value, email_c.value, senha_c.value,
                    cpf.value, celular.value, instagram.value or None,
                )
                app.storage.user.update({"id": user_id, "nome": nome.value, "role": "aluno"})
                ui.navigate.to("/creditos")
            except ValueError as e:
                erro.set_text(str(e))

        ui.button("Criar minha conta", on_click=cadastrar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700;"
        )
