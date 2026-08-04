# -*- coding: utf-8 -*-
import base64
import io
from nicegui import ui, events
from theme import TEAL, TEAL_DARK, TEXT, TEXT_MUTED, DANGER
from ui_helpers import page_title
import auth

AVATAR_MAX_PX = 256


def render(user):
    page_title("Meu Cadastro")
    dados = auth.get_usuario(user["id"])

    with ui.column().classes("canoa-card").style("max-width:560px; gap:14px;"):
        with ui.row().style("align-items:center; gap:16px;"):
            avatar = ui.image(dados["foto_url"] or _iniciais_svg(dados["nome"])).style(
                "width:72px; height:72px; border-radius:50%; object-fit:cover; "
                f"border:2px solid {TEAL};"
            )

            def ao_enviar(e: events.UploadEventArguments):
                try:
                    from PIL import Image
                    img = Image.open(e.content).convert("RGBA")
                    img.thumbnail((AVATAR_MAX_PX, AVATAR_MAX_PX))
                    buf = io.BytesIO()
                    img.save(buf, format="PNG", optimize=True)
                    data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
                    auth.atualizar_perfil(user["id"], foto_url=data_uri)
                    avatar.set_source(data_uri)
                    ui.notify("Foto atualizada.", type="positive")
                except Exception as ex:
                    ui.notify(f"Não foi possível usar essa imagem: {ex}", type="negative")

            with ui.column().style("gap:2px;"):
                ui.upload(on_upload=ao_enviar, auto_upload=True, max_file_size=5_000_000).props(
                    'accept=".jpg,.jpeg,.png" label="Trocar foto"'
                ).classes("w-full").style("max-width:220px;")
                ui.label("JPG ou PNG, até 5MB").style(f"color:{TEXT_MUTED}; font-size:11px;")

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
        nascimento = ui.input("Data de nascimento (AAAA-MM-DD)", value=dados["data_nascimento"] or "").classes("w-full")
        instagram = ui.input("Instagram (opcional)", value=dados["instagram"] or "").classes("w-full")
        erro = ui.label("").style(f"color:{DANGER}; font-size:13px;")

        def salvar():
            if not all([nome.value, sexo.value, cpf.value, celular.value]):
                erro.set_text("Preencha todos os campos obrigatórios (*).")
                return
            auth.atualizar_perfil(
                user["id"], nome=nome.value, sexo=sexo.value,
                cpf=cpf.value, celular=celular.value, instagram=instagram.value or None,
                data_nascimento=nascimento.value or None,
            )
            user["nome"] = nome.value
            ui.notify("Dados atualizados.", type="positive")

        ui.button("Salvar alterações", on_click=salvar).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:700; width:fit-content;"
        )


def _iniciais_svg(nome):
    """Avatar padrão (iniciais) em SVG, usado enquanto o aluno não envia uma foto."""
    iniciais = "".join([p[0] for p in nome.split()[:2]]).upper() or "?"
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72">'
        f'<rect width="72" height="72" rx="36" fill="#E3EEDA"/>'
        f'<text x="36" y="44" font-family="Arial" font-size="26" font-weight="700" '
        f'fill="#497E25" text-anchor="middle">{iniciais}</text></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
