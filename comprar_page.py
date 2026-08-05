# -*- coding: utf-8 -*-
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, DANGER, reais
from ui_helpers import page_title
from db import get_param
import auth
import payments
from payments import PagamentoError

PLANOS = {
    "avulsa": {"nome": "Remada avulsa", "creditos": 1, "param": "preco_avulsa_centavos"},
    "pacote4": {"nome": "Pacote 4 remadas", "creditos": 4, "param": "preco_pacote4_centavos"},
    "pacote6": {"nome": "Pacote 6 remadas", "creditos": 6, "param": "preco_pacote6_centavos"},
}


def render(user):
    page_title("Comprar Remadas")
    dados_user = auth.get_usuario(user["id"])
    tem_endereco = bool(dados_user.get("cep") and dados_user.get("endereco_numero"))

    ui.label(
        "Ao clicar em \"Comprar\", a tela de pagamento do Asaas abre aqui mesmo "
        f"({'Pix ou cartão' if tem_endereco else 'Pix'}). Suas remadas aparecem em "
        "\"Minhas Remadas\" assim que o pagamento for aprovado."
    ).style(f"color:{TEXT_MUTED}; font-size:12.5px; max-width:560px;")

    if not tem_endereco:
        ui.label(
            "Quer pagar com cartão de crédito? Preencha CEP e número em "
            "\"Meu Cadastro\" — por enquanto, só Pix está disponível pra você."
        ).style(f"color:{TEAL_DARK}; font-size:11.5px; max-width:560px;")

    msg = ui.label("")

    def _abrir_checkout(url):
        with ui.dialog().props("maximized") as dialog, ui.card().style(
            "padding:0; gap:0; width:100%; height:100%;"
        ):
            with ui.row().style(
                f"width:100%; padding:10px 16px; background:{NAVY}; "
                "align-items:center; justify-content:space-between; flex-shrink:0;"
            ):
                ui.label("Pagamento seguro \u2014 Asaas").style("color:white; font-weight:700; font-size:14px;")
                with ui.row().style("gap:8px; align-items:center;"):
                    ui.label("Não carregou?").style("color:#CDE8B8; font-size:11.5px;")
                    ui.button(
                        "Abrir em nova aba", on_click=lambda: ui.navigate.to(url, new_tab=True)
                    ).props("flat dense").style("color:white; font-size:11.5px; text-decoration:underline;")
                    ui.button(icon="close", on_click=dialog.close).props("flat dense round").style("color:white;")
            ui.html(
                f'<iframe src="{url}" style="width:100%; height:calc(100vh - 52px); '
                'border:0; display:block;" allow="payment"></iframe>'
            ).style("width:100%; flex:1;")
        dialog.open()

    def comprar(plano_key):
        plano = PLANOS[plano_key]
        preco = get_param(plano["param"], 0, int)
        try:
            dados = auth.get_usuario(user["id"])
            purchase_id = payments.criar_compra_pendente(user["id"], plano_key, preco)
            url = payments.criar_checkout(purchase_id, plano["nome"], preco, dados)
            _abrir_checkout(url)
            msg.set_text("")
        except PagamentoError as e:
            msg.set_text(f"Não foi possível iniciar o pagamento: {e}")
            msg.style(f"color:{DANGER}; font-size:13px;")

    with ui.row().style("gap:16px; width:100%; flex-wrap:wrap;"):
        for key, plano in PLANOS.items():
            preco = get_param(plano["param"], 0, int)
            destaque = key == "pacote6"
            with ui.column().classes("canoa-card").style(
                f"flex:1; min-width:220px; gap:6px; "
                f"{'border:2px solid ' + TEAL + ';' if destaque else ''}"
            ):
                if destaque:
                    ui.label("Melhor custo").style(
                        "background:#EAF7EE; color:#3FA35A; border-radius:999px; "
                        "padding:2px 10px; font-size:11px; font-weight:700; width:fit-content;"
                    )
                ui.label(plano["nome"]).style(f"color:{TEXT}; font-weight:700; font-size:14px;")
                ui.label(reais(preco)).style(f"color:{NAVY}; font-size:22px; font-weight:800;")
                if plano["creditos"] > 1:
                    ui.label(f"{plano['creditos']} remadas \u2022 {reais(preco // plano['creditos'])}/remada").style(
                        f"color:{TEXT_MUTED}; font-size:11.5px;"
                    )
                else:
                    ui.label("1 remada").style(f"color:{TEXT_MUTED}; font-size:11.5px;")
                ui.button(
                    "Comprar", on_click=lambda k=key: comprar(k)
                ).props("unelevated" if destaque else "outline").style(
                    (f"background:{TEAL}; color:white;" if destaque else f"color:{TEAL_DARK};")
                    + " font-weight:700; width:100%; margin-top:4px;"
                )
