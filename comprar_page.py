# -*- coding: utf-8 -*-
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED, reais
from ui_helpers import page_title
from db import db, get_param
import credits

PLANOS = {
    "avulsa": {"nome": "Remada avulsa", "creditos": 1, "param": "preco_avulsa_centavos"},
    "pacote4": {"nome": "Pacote 4 remadas", "creditos": 4, "param": "preco_pacote4_centavos"},
    "pacote6": {"nome": "Pacote 6 remadas", "creditos": 6, "param": "preco_pacote6_centavos"},
}


def _registrar_compra_paga(user_id, plano_key, forma_pagamento):
    """Simula o retorno de sucesso do gateway (Mercado Pago) — troca pela API real depois."""
    plano = PLANOS[plano_key]
    valor = get_param(plano["param"], 0, int)
    with db() as conn:
        conn.execute(
            "INSERT INTO purchases (user_id, plano, valor_centavos, forma_pagamento, status) "
            "VALUES (?, ?, ?, ?, 'pago')",
            (user_id, plano_key, valor, forma_pagamento),
        )
        purchase_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    credits.emitir_creditos(user_id, plano_key, purchase_id, plano["creditos"])
    return valor


def render(user):
    page_title("Comprar Remadas")
    ui.label("Escolha uma opção de crédito").style(f"color:{TEXT}; font-size:15px; font-weight:700;")

    checkout_container = ui.column().style("width:100%;")

    def abrir_checkout(plano_key):
        checkout_container.clear()
        plano = PLANOS[plano_key]
        preco = get_param(plano["param"], 0, int)
        with checkout_container:
            with ui.column().classes("canoa-card").style(f"border:2px dashed {TEAL}; gap:12px; margin-top:8px;"):
                ui.label(f"Checkout \u2014 {plano['nome']} \u2022 {reais(preco)}").style(
                    f"color:{TEAL_DARK}; font-weight:700; font-size:14px;"
                )
                forma = ui.radio(["Pix", "Cartão de crédito"], value="Pix").props("inline")
                resultado = ui.label("")

                def confirmar():
                    valor = _registrar_compra_paga(user["id"], plano_key, (forma.value or "pix").lower())
                    resultado.set_text(
                        f"\u2705 Pagamento confirmado! {plano['creditos']} crédito(s) adicionados. "
                        f"Um e-mail de confirmação foi enviado."
                    )
                    resultado.style(f"color:{TEAL_DARK}; font-weight:600; font-size:13px;")

                ui.button("Confirmar pagamento", on_click=confirmar).props("unelevated").style(
                    f"background:{TEAL}; color:white; font-weight:700; width:fit-content;"
                )

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
                    ui.label(f"{plano['creditos']} créditos \u2022 {reais(preco // plano['creditos'])}/remada").style(
                        f"color:{TEXT_MUTED}; font-size:11.5px;"
                    )
                else:
                    ui.label("1 crédito").style(f"color:{TEXT_MUTED}; font-size:11.5px;")
                ui.button(
                    "Comprar", on_click=lambda k=key: abrir_checkout(k)
                ).props("unelevated" if destaque else "outline").style(
                    (f"background:{TEAL}; color:white;" if destaque else f"color:{TEAL_DARK};")
                    + " font-weight:700; width:100%; margin-top:4px;"
                )
