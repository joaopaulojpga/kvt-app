# -*- coding: utf-8 -*-
from nicegui import ui, app
from theme import NAVY, TEAL, TEXT_MUTED, DANGER, APP_NAME
from logo_data import LOGO_KALANI_DATA_URI
import auth

PASSOS = [
    ("1", "Cadastre-se", "Crie sua conta com seus dados e comece."),
    ("2", "Compre Remadas", "Avulsa ou em pacotes com desconto"),
    ("3", "Reserve sua aula", "Escolha o dia na agenda e faça check-in."),
]


def render():
    with ui.column().style("max-width:900px; margin:0 auto; padding:40px 24px; gap:28px;").classes("kv-landing"):
        with ui.row().style("align-items:center; gap:10px;"):
            ui.image(LOGO_KALANI_DATA_URI).style("width:44px; height:44px; border-radius:50%;")
            ui.label(APP_NAME).classes("kv-brand").style(f"color:{NAVY}; font-size:24px;")

        _passos_grid()

        with ui.column().style("width:100%;"):
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


def _passos_grid():
    with ui.row().style("gap:10px; width:100%; flex-wrap:nowrap;"):
        for numero, titulo, descricao in PASSOS:
            with ui.column().classes("canoa-card").style(
                "flex:1; min-width:0; gap:6px; padding:14px 12px; align-items:flex-start;"
            ):
                with ui.row().style(
                    f"width:26px; height:26px; border-radius:50%; background:{TEAL}; "
                    "align-items:center; justify-content:center; margin:0;"
                ):
                    ui.label(numero).style("color:white; font-weight:800; font-size:13px;")
                ui.label(titulo).style(f"color:{NAVY}; font-weight:800; font-size:13px; line-height:1.2;")
                ui.label(descricao).style(f"color:{TEXT_MUTED}; font-size:11px; line-height:1.35;")


def _form_login():
    with ui.column().classes("canoa-card w-full").style("max-width:480px; width:100%; gap:12px;"):
        email = ui.input("E-mail").classes("w-full")
        senha = ui.input("Senha", password=True).classes("w-full")
        erro = ui.label("").style(f"color:{DANGER}; font-size:13px;")

        def entrar():
            user = auth.autenticar(email.value or "", senha.value or "")
            if user is None:
                erro.set_text("E-mail ou senha inválidos.")
                return
            app.storage.user.update({"id": user["id"], "nome": user["nome"], "role": user["role"]})
            ui.navigate.to("/home")

        ui.button("Entrar", on_click=entrar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:100%;"
        )


def _form_cadastro():
    with ui.column().classes("canoa-card w-full").style("max-width:480px; width:100%; gap:10px;"):
        nome = ui.input("Nome completo *").classes("w-full")
        sexo = ui.select(["Feminino", "Masculino", "Outro"], value="Feminino", label="Sexo *").classes("w-full")
        email_c = ui.input("E-mail *").classes("w-full")
        senha_c = ui.input("Senha *", password=True).classes("w-full")
        cpf = ui.input("CPF *").classes("w-full")
        celular = ui.input("Celular / WhatsApp *").classes("w-full")
        instagram = ui.input("Instagram (opcional)").classes("w-full")
        ui.label("Endereço (opcional \u2014 só é pedido se você pagar com cartão de crédito)").style(
            f"color:{TEXT_MUTED}; font-size:11.5px; margin-top:4px;"
        )
        with ui.row().style("gap:10px; width:100%;"):
            cep = ui.input("CEP").style("flex:1;")
            numero = ui.input("Número").style("flex:1;")
        erro = ui.label("").style(f"color:{DANGER}; font-size:13px;")

        def cadastrar():
            campos = [nome.value, sexo.value, email_c.value, senha_c.value, cpf.value, celular.value]
            if not all(campos):
                erro.set_text("Preencha todos os campos obrigatórios (*).")
                return
            try:
                user_id = auth.cadastrar_usuario(
                    nome.value, sexo.value, email_c.value, senha_c.value,
                    cpf.value, celular.value, instagram.value or None,
                    cep=cep.value or None, endereco_numero=numero.value or None,
                )
                app.storage.user.update({"id": user_id, "nome": nome.value, "role": "aluno"})
                ui.navigate.to("/home")
            except ValueError as e:
                erro.set_text(str(e))

        ui.button("Criar minha conta", on_click=cadastrar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:100%;"
        )
