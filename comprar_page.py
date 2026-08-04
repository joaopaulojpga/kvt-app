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
    ui.label(
        "Ao clicar em \"Comprar\", você será redirecionado para o ambiente seguro "
        "do Mercado Pago para pagar via Pix ou cartão. Suas remadas aparecem em "
        "\"Minhas Remadas\" assim que o pagamento for aprovado."
    ).style(f"color:{TEXT_MUTED}; font-size:12.5px; max-width:560px;")

    msg = ui.label("")

    def comprar(plano_key):
        plano = PLANOS[plano_key]
        preco = get_param(plano["param"], 0, int)
        try:
            dados = auth.get_usuario(user["id"])
            purchase_id = payments.criar_compra_pendente(user["id"], plano_key, preco)
            url = payments.criar_preferencia(purchase_id, plano["nome"], preco, dados["email"])
            ui.navigate.to(url, new_tab=True)
            msg.set_text(
                "Abrimos uma nova aba para você concluir o pagamento no Mercado Pago. "
                "Depois de pagar, suas remadas aparecem em \"Minhas Remadas\" em poucos instantes."
            )
            msg.style(f"color:{TEAL_DARK}; font-size:13px; font-weight:600;")
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
