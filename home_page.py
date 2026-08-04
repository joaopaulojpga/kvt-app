# -*- coding: utf-8 -*-
from nicegui import ui, app
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, APP_NAME
from logo_data import LOGO_KALANI_DATA_URI
import auth
import carousel


def render():
    with ui.column().style("max-width:900px; margin:0 auto; padding:48px 24px; gap:24px;"):
        with ui.row().style("align-items:center; gap:10px;"):
            ui.image(LOGO_KALANI_DATA_URI).style("width:40px; height:40px; border-radius:50%;")
            ui.label(APP_NAME).style(f"color:{NAVY}; font-size:26px; font-weight:800;")

        carousel.render_carousel()

        ui.button("COMEÇAR AGORA", on_click=lambda: ui.run_javascript(
            "document.getElementById('cadastro-section')?.scrollIntoView({behavior:'smooth'});"
        )).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:800; font-size:16px; "
            "width:100%; padding:16px; border-radius:12px; letter-spacing:0.5px;"
        )

        _grade_horarios_chips()

        with ui.column().style("width:100%;").props('id="cadastro-section"'):
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


def _grade_horarios_chips():
    with ui.column().style(
        "background:#EAF6F4; border-radius:12px; padding:20px 22px; gap:10px; width:100%;"
    ):
        ui.label("Grade principal").style(f"color:{TEAL_DARK}; font-weight:700; font-size:14px;")
        dias = [
            ("Terça", ["06:00"]), ("Quinta", ["06:00"]),
            ("Sábado", ["06:00", "08:00"]), ("Domingo", ["07:00", "09:00"]),
        ]
        with ui.row().style("gap:20px; flex-wrap:wrap;"):
            for dia, horarios in dias:
                with ui.column().style("gap:6px; min-width:100px;"):
                    ui.label(dia).style(f"color:{TEXT}; font-weight:700; font-size:12.5px;")
                    with ui.row().style("gap:6px; flex-wrap:wrap;"):
                        for h in horarios:
                            ui.label(h).style(
                                f"background:{TEAL}; color:white; font-weight:700; font-size:12px; "
                                "padding:5px 12px; border-radius:999px;"
                            )
        ui.label("Vagas de 12, expansíveis até 18.").style(f"color:{TEXT_MUTED}; font-size:11.5px; margin-top:2px;")


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
