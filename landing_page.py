# -*- coding: utf-8 -*-
"""
Landing page institucional — kalanivaa.com.br (só prospecção, sem
login/cadastro embutido). Quem quer entrar/criar conta é redirecionado
pra app.kalanivaa.com.br pelos CTAs. Ver pagina_home() em app.py, que
decide qual página mostrar com base no header Host da requisição.
"""
import os
import re
import json
from datetime import date
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEAL_LIGHT, TEXT, TEXT_MUTED, DANGER, OK, APP_NAME
from logo_data import LOGO_KALANI_DATA_URI
from db import db
from carousel import MAPS_IFRAME
from whatsapp_bot import LINK_MAPS, LOCAL_CLUBE
from layout import INSTAGRAM_URL, WHATSAPP_URL

APP_URL = os.environ.get("APP_BASE_URL", "https://app.kalanivaa.com.br").rstrip("/")

# Foto real do herói (time remando ao pôr do sol) e vídeo institucional ainda
# não temos — deixei os dois como constantes únicas de troca. Sem foto, cai
# no gradiente da identidade; sem vídeo, o botão avisa que ainda não está
# disponível em vez de quebrar.
HERO_IMAGE_URL = None
VIDEO_URL = None

SECOES = [
    ("inicio", "Início"),
    ("como-funciona", "Como funciona"),
    ("horarios", "Horários"),
    ("depoimentos", "Depoimentos"),
    ("localizacao", "Localização"),
]

PASSOS = [
    ("account_circle", "Cadastre-se", "Crie sua conta em poucos segundos e venha fazer parte do Kalani Vaa Team."),
    ("event", "Escolha seu horário", "Confira nossa grade de turmas e escolha o melhor horário pra você remar."),
    ("directions_boat", "Reme e evolua", "Participe das remadas, melhore seu condicionamento e desfrute da experiência!"),
]

HORARIOS_SEMANA = [
    ("Terça", "06:00"), ("Quinta", "06:00"),
    ("Sábado", "06:00"), ("Sábado", "08:00"),
    ("Domingo", "07:00"), ("Domingo", "09:00"),
]

COMODIDADES = [
    ("groups", "Para todas as idades"),
    ("sentiment_satisfied", "Sem experiência? Sem problema!"),
    ("school", "Treinos guiados por instrutores"),
    ("favorite", "Comunidade e conexão"),
]

DEPOIMENTOS = [
    ("Mariana S.", "A canoa havaiana mudou minha vida! Mais saúde, disposição e amizades incríveis. Kalani é família!"),
    ("Lucas R.", "Instrutores incríveis, estrutura top e uma energia sensacional. Melhor decisão que tomei!"),
    ("Fernanda M.", "Além do treino, é um momento de conexão com a natureza e com pessoas incríveis!"),
]
DEPOIMENTOS_POR_PAGINA = 3
DEPOIMENTOS_MAX_PAGINAS = 3


def _ir_para_app():
    ui.navigate.to(f"{APP_URL}/")


def _scroll_para(id_secao):
    ui.run_javascript(f"document.getElementById('{id_secao}')?.scrollIntoView({{behavior:'smooth'}});")


def render():
    _cabecalho()
    _banner_principal()
    _como_funciona()
    _grade_horarios()
    _newsletter()
    _depoimentos()
    _banner_reforco()
    _localizacao()
    _instagram()
    _rodape()


def _cabecalho():
    with ui.row().style(
        "width:100%; padding:16px 24px; align-items:center; justify-content:space-between; "
        f"background:{NAVY}; position:relative; z-index:10;"
    ).props('id="inicio"'):
        with ui.row().style("align-items:center; gap:8px;"):
            ui.image(LOGO_KALANI_DATA_URI).style("width:34px; height:34px; border-radius:50%;")
            ui.label(APP_NAME).classes("kv-brand").style("color:white; font-size:14px;")
        with ui.button(icon="menu").props("flat round").style("color:white;"):
            with ui.menu():
                for id_secao, label in SECOES:
                    ui.menu_item(label, on_click=lambda i=id_secao: _scroll_para(i))
                ui.separator()
                ui.menu_item("Entrar / Cadastrar", on_click=_ir_para_app)


def _banner_principal():
    fundo = (
        f"background-image:linear-gradient(180deg, rgba(11,19,7,0.35), rgba(11,19,7,0.88)), url('{HERO_IMAGE_URL}'); "
        "background-size:cover; background-position:center;"
        if HERO_IMAGE_URL else
        f"background:linear-gradient(160deg, {NAVY} 0%, #1B3A0F 55%, {TEAL_DARK} 100%);"
    )
    with ui.column().style(f"width:100%; padding:48px 24px 56px; gap:18px; {fundo}"):
        with ui.column().style("max-width:640px; margin:0 auto; gap:14px; align-items:flex-start;"):
            ui.label("MAIS QUE UM ESPORTE,").style(
                "color:white; font-weight:800; font-size:22px; line-height:1.15;"
            )
            ui.html(
                f'<div style="color:white; font-weight:900; font-size:36px; line-height:1.05;">'
                f'UM ESTILO DE VIDA <span style="color:{TEAL}; font-style:italic;">VAA</span></div>'
            )
            ui.label(
                "Conecte-se com a natureza, fortaleça o corpo e a mente e faça parte de "
                "uma comunidade que rema junto."
            ).style("color:#D7E3CE; font-size:14.5px; line-height:1.5;")

            def abrir_video():
                if VIDEO_URL:
                    with ui.dialog() as dialog, ui.card().style("width:min(720px, 92vw); padding:0;"):
                        ui.html(
                            f'<iframe width="100%" height="405" src="{VIDEO_URL}" frameborder="0" '
                            'allowfullscreen style="display:block;"></iframe>'
                        )
                    dialog.open()
                else:
                    ui.notify("Vídeo em breve!", type="info")

            with ui.row().style("align-items:center; gap:10px; cursor:pointer;").on("click", abrir_video):
                with ui.row().style(
                    "width:38px; height:38px; border-radius:50%; background:rgba(255,255,255,0.15); "
                    "align-items:center; justify-content:center; border:1.5px solid white;"
                ):
                    ui.icon("play_arrow").style("color:white; font-size:20px;")
                ui.label("ASSISTA AO VÍDEO").style("color:white; font-weight:700; font-size:12.5px; letter-spacing:0.5px;")

            ui.button("Começar agora!", on_click=_ir_para_app).props("unelevated").style(
                f"background:{TEAL}; color:white; font-weight:800; font-size:16px; "
                "padding:14px 40px; border-radius:999px; margin-top:6px;"
            )
            with ui.row().style("align-items:center; gap:6px;"):
                ui.icon("lock", size="14px").style("color:#9FBE86;")
                ui.label("Processo rápido e seguro").style("color:#9FBE86; font-size:11.5px;")

        with ui.row().style(
            "max-width:640px; margin:20px auto 0; width:100%; gap:14px; flex-wrap:wrap; "
            "justify-content:space-between;"
        ):
            for icone, texto in COMODIDADES:
                with ui.row().style("align-items:center; gap:8px; flex:1; min-width:130px;"):
                    ui.icon(icone, size="18px").style(f"color:{TEAL};")
                    ui.label(texto).style("color:#D7E3CE; font-size:12px;")


def _titulo_secao(eyebrow, titulo):
    ui.label(eyebrow).style(
        f"color:{TEAL_DARK}; font-weight:800; font-size:11.5px; text-transform:uppercase; "
        "letter-spacing:1px; text-align:center; width:100%;"
    )
    ui.label(titulo).classes("kv-brand").style(
        f"color:{NAVY}; font-size:24px; text-align:center; width:100%; text-transform:none; letter-spacing:normal;"
    )


def _como_funciona():
    with ui.column().style(
        "width:100%; padding:48px 24px; gap:8px; align-items:center; background:white;"
    ).props('id="como-funciona"'):
        _titulo_secao("Como funciona", "3 passos para começar")
        with ui.column().style("max-width:480px; width:100%; gap:20px; margin-top:20px;"):
            for i, (icone, titulo, descricao) in enumerate(PASSOS, 1):
                with ui.row().style("gap:16px; align-items:flex-start; width:100%;"):
                    with ui.column().style("align-items:center; gap:4px;"):
                        with ui.row().style(
                            f"width:40px; height:40px; border-radius:50%; background:{TEAL}; "
                            "align-items:center; justify-content:center; flex-shrink:0;"
                        ):
                            ui.label(str(i)).style("color:white; font-weight:800; font-size:15px;")
                        ui.icon(icone, size="20px").style(f"color:{TEAL_LIGHT}; background:{NAVY}; "
                                                            "border-radius:50%; padding:6px;")
                    with ui.column().style("gap:2px;"):
                        ui.label(titulo).style(f"color:{NAVY}; font-weight:800; font-size:15px;")
                        ui.label(descricao).style(f"color:{TEXT_MUTED}; font-size:13px; line-height:1.4;")


def _grade_horarios():
    with ui.column().style(
        f"width:100%; padding:48px 24px; gap:8px; align-items:center; background:{TEAL_LIGHT};"
    ).props('id="horarios"'):
        _titulo_secao("Grade de horários", "Encontre o melhor horário pra você")
        with ui.column().style("max-width:520px; width:100%; gap:10px; margin-top:20px;"):
            for dia, horario in HORARIOS_SEMANA:
                with ui.row().style(
                    "background:white; border-radius:12px; padding:14px 18px; width:100%; "
                    "align-items:center; justify-content:space-between; box-shadow:0 1px 3px rgba(0,0,0,0.06);"
                ):
                    with ui.row().style("align-items:center; gap:10px;"):
                        ui.icon("event", size="18px").style(f"color:{TEAL};")
                        ui.label(dia).style(f"color:{NAVY}; font-weight:700; font-size:14px;")
                    ui.label(horario).style(
                        f"background:{TEAL}; color:white; font-weight:700; font-size:13px; "
                        "padding:5px 14px; border-radius:999px;"
                    )
        ui.button("Reservar agora!", on_click=_ir_para_app).props("unelevated").style(
            f"background:{NAVY}; color:white; font-weight:800; font-size:14.5px; "
            "padding:12px 36px; border-radius:999px; margin-top:20px;"
        )


def _newsletter():
    with ui.column().style(
        f"width:100%; padding:48px 24px; gap:10px; align-items:center; background:{NAVY};"
    ):
        ui.icon("mail", size="34px").style(f"color:{TEAL}; background:white; border-radius:50%; padding:12px;")
        ui.label("Fique por dentro das novidades").classes("kv-brand").style(
            "color:white; font-size:19px; text-align:center; text-transform:none; letter-spacing:normal;"
        )
        ui.label("Inscreva-se na nossa newsletter e receba novidades, dicas e convites exclusivos.").style(
            "color:#C9D9BE; font-size:13px; text-align:center; max-width:420px;"
        )

        with ui.column().style("max-width:380px; width:100%; gap:10px; margin-top:10px; align-items:center;"):
            celular = ui.input(placeholder="(21) 99999-9999").props("outlined dense").style(
                "width:100%; background:white; border-radius:8px;"
            )
            msg = ui.label("").style("font-size:12px;")

            def inscrever():
                digitos = re.sub(r"\D", "", celular.value or "")
                if len(digitos) < 10:
                    msg.set_text("Digite um número de WhatsApp válido, com DDD.")
                    msg.style(f"color:{DANGER}; font-size:12px;")
                    return
                with db() as conn:
                    conn.execute(
                        "INSERT INTO prospects (celular, origem) VALUES (?, 'landing_newsletter')",
                        (digitos,),
                    )
                celular.set_value("")
                msg.set_text("Prontinho! Você vai receber nossas novidades. \U0001F33A")
                msg.style(f"color:{TEAL}; font-size:12px; font-weight:700;")

            ui.button("Quero receber!", on_click=inscrever).props("unelevated").classes("w-full").style(
                f"background:{TEAL}; color:white; font-weight:800; padding:12px; border-radius:8px;"
            )


def _depoimentos():
    total_paginas = min(
        DEPOIMENTOS_MAX_PAGINAS,
        max(1, -(-len(DEPOIMENTOS) // DEPOIMENTOS_POR_PAGINA)),
    )
    with ui.column().style(
        "width:100%; padding:48px 24px; gap:8px; align-items:center; background:white;"
    ).props('id="depoimentos"'):
        _titulo_secao("Depoimentos", "Quem rema, recomenda")

        container = ui.column().style("max-width:480px; width:100%; gap:14px; margin-top:20px;")
        dots = ui.row().style("gap:6px; justify-content:center; width:100%; margin-top:14px;")
        estado = {"pagina": 0}

        def desenhar():
            container.clear()
            inicio = estado["pagina"] * DEPOIMENTOS_POR_PAGINA
            with container:
                for nome, texto in DEPOIMENTOS[inicio:inicio + DEPOIMENTOS_POR_PAGINA]:
                    with ui.column().classes("canoa-card").style("width:100%; gap:8px;"):
                        with ui.row().style("align-items:center; gap:10px;"):
                            with ui.row().style(
                                f"width:38px; height:38px; border-radius:50%; background:{TEAL_LIGHT}; "
                                "align-items:center; justify-content:center; flex-shrink:0;"
                            ):
                                ui.label(nome[0]).style(f"color:{TEAL_DARK}; font-weight:800;")
                            with ui.column().style("gap:0;"):
                                ui.label(nome).style(f"color:{NAVY}; font-weight:700; font-size:13.5px;")
                                ui.label("\u2605\u2605\u2605\u2605\u2605").style(f"color:{TEAL}; font-size:11px;")
                        ui.label(f"\u201C{texto}\u201D").style(f"color:{TEXT_MUTED}; font-size:13px; line-height:1.5; font-style:italic;")
            dots.clear()
            with dots:
                for i in range(total_paginas):
                    ativo = i == estado["pagina"]
                    ui.icon("circle", size="8px").style(
                        f"color:{TEAL if ativo else '#D8DED2'}; cursor:pointer;"
                    ).on("click", lambda i=i: ir_para(i))

        def ir_para(i):
            estado["pagina"] = i
            desenhar()

        desenhar()


def _banner_reforco():
    fundo = (
        f"background-image:linear-gradient(180deg, rgba(11,19,7,0.55), rgba(11,19,7,0.85)), url('{HERO_IMAGE_URL}'); "
        "background-size:cover; background-position:center;"
        if HERO_IMAGE_URL else
        f"background:linear-gradient(160deg, {NAVY} 0%, #1B3A0F 100%);"
    )
    with ui.column().style(f"width:100%; padding:52px 24px; gap:14px; align-items:center; {fundo}"):
        ui.label("PRONTO PARA VIVER ESSA EXPERIÊNCIA?").style(
            f"color:{TEAL}; font-weight:800; font-size:12px; letter-spacing:1px; text-align:center;"
        )
        ui.label("Sua próxima remada começa aqui!").classes("kv-brand").style(
            "color:white; font-size:26px; text-align:center; text-transform:none; letter-spacing:normal; max-width:420px;"
        )
        ui.button("Começar agora!", on_click=_ir_para_app).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:800; font-size:16px; "
            "padding:14px 40px; border-radius:999px; margin-top:6px;"
        )


def _localizacao():
    with ui.column().style(
        "width:100%; padding:48px 24px; gap:8px; align-items:center; background:white;"
    ).props('id="localizacao"'):
        _titulo_secao("Nossa localização", "Venha nos conhecer!")
        with ui.column().style("max-width:520px; width:100%; gap:14px; margin-top:20px;"):
            with ui.element("div").style(
                "width:100%; height:260px; border-radius:14px; overflow:hidden; "
                "box-shadow:0 1px 4px rgba(0,0,0,0.1);"
            ):
                ui.html(MAPS_IFRAME).style("width:100%; height:100%;")
            ui.label(f"{LOCAL_CLUBE} \u2014 Campos dos Goytacazes, RJ").style(
                f"color:{NAVY}; font-weight:700; font-size:14px; text-align:center;"
            )
            ui.label("Fácil acesso e estacionamento próximo.").style(
                f"color:{TEXT_MUTED}; font-size:12.5px; text-align:center;"
            )
            ui.button(
                "Como chegar", on_click=lambda: ui.navigate.to(LINK_MAPS, new_tab=True)
            ).props("outline").style(
                f"color:{TEAL_DARK}; border-color:{TEAL}; font-weight:700; align-self:center; "
                "padding:10px 28px; border-radius:999px;"
            )


def _instagram():
    with ui.column().style(
        f"width:100%; padding:48px 24px; gap:8px; align-items:center; background:{TEAL_LIGHT};"
    ):
        _titulo_secao("Siga nosso Instagram", "@kalani_vaa")
        with ui.row().style("max-width:520px; width:100%; gap:6px; flex-wrap:wrap; margin-top:20px; justify-content:center;"):
            for _ in range(6):
                with ui.column().style(
                    f"width:31%; aspect-ratio:1; background:{NAVY}; border-radius:8px; "
                    "align-items:center; justify-content:center;"
                ):
                    ui.icon("photo_camera", size="22px").style("color:#5E7A47;")
        ui.label("Fotos ilustrativas — substitua pelas fotos reais do perfil quando quiser.").style(
            f"color:{TEXT_MUTED}; font-size:10.5px; font-style:italic; margin-top:4px;"
        )
        ui.button(
            "Ver mais no Instagram", on_click=lambda: ui.navigate.to(INSTAGRAM_URL, new_tab=True)
        ).props("unelevated").style(
            f"background:{TEAL}; color:white; font-weight:800; padding:12px 32px; "
            "border-radius:999px; margin-top:10px;"
        )


def _rodape():
    with ui.column().style(f"width:100%; padding:36px 24px; gap:24px; background:{NAVY};"):
        with ui.row().style("max-width:900px; margin:0 auto; width:100%; gap:32px; flex-wrap:wrap; justify-content:space-between;"):
            with ui.column().style("gap:8px; max-width:280px;"):
                with ui.row().style("align-items:center; gap:8px;"):
                    ui.image(LOGO_KALANI_DATA_URI).style("width:30px; height:30px; border-radius:50%;")
                    ui.label(APP_NAME).classes("kv-brand").style("color:white; font-size:13px;")
                ui.label(
                    "Mais que um esporte, um estilo de vida. Junte-se a nós e reme pelo aprazível caminho da natureza."
                ).style("color:#9FBE86; font-size:12px; line-height:1.5;")
            with ui.column().style("gap:6px;"):
                ui.label("NAVEGAÇÃO").style(
                    f"color:{TEAL}; font-weight:800; font-size:11px; letter-spacing:0.8px; margin-bottom:4px;"
                )
                for id_secao, label in SECOES:
                    ui.label(label).style(
                        "color:#C9D9BE; font-size:12.5px; cursor:pointer;"
                    ).on("click", lambda i=id_secao: _scroll_para(i))
        ui.separator().style("background:#243318; opacity:0.5;")
        ui.label(f"\u00a9 {date.today().year} {APP_NAME} \u2014 Todos os direitos reservados.").style(
            "color:#5E7A47; font-size:11px; text-align:center;"
        )
