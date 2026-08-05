# -*- coding: utf-8 -*-
from nicegui import ui
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED
from ui_helpers import page_title, badge
import credits

TIPO_LABEL = {
    "compra_online": ("Compra online", "shopping_cart", "ok"),
    "venda_offline": ("Venda offline", "point_of_sale", "ok"),
    "cortesia": ("Cortesia", "redeem", "ok"),
    "reposicao": ("Reposição", "history", "ok"),
    "reagendamento": ("Reagendamento", "event_repeat", "ok"),
    "ajuste_manual": ("Ajuste manual", "tune", "muted"),
    "reserva": ("Reserva de remada", "directions_boat", "muted"),
    "estorno": ("Estorno", "replay", "warn"),
}
FORMA_PAGAMENTO_LABEL = {"pix": "Pix", "dinheiro": "Dinheiro", "cartao": "Cartão", "transferencia": "Transferência"}


def render(user):
    page_title("Histórico de Créditos")

    saldo = credits.saldo_disponivel(user["id"])
    validade = credits.proxima_validade(user["id"])
    with ui.row().style("gap:16px; width:100%; flex-wrap:wrap; margin-bottom:4px;"):
        with ui.column().classes("canoa-card").style("flex:1; min-width:180px; gap:2px;"):
            ui.label("Saldo atual").style(f"color:{TEXT_MUTED}; font-size:12px;")
            ui.label(f"{saldo} remadas").style(f"color:{NAVY}; font-size:22px; font-weight:800;")
        if validade:
            with ui.column().classes("canoa-card").style("flex:1; min-width:180px; gap:2px;"):
                ui.label("Próxima validade a vencer").style(f"color:{TEXT_MUTED}; font-size:12px;")
                ui.label(validade).style(f"color:{NAVY}; font-size:16px; font-weight:700;")

    movimentacoes = credits.listar_movimentacoes(user["id"])
    if not movimentacoes:
        ui.label("Nenhuma movimentação de créditos ainda.").style(f"color:{TEXT_MUTED}; font-size:13px;")
        return

    with ui.column().classes("canoa-card").style("width:100%; gap:0;"):
        for mov in movimentacoes:
            _linha_movimentacao(mov)


def _linha_movimentacao(mov):
    label, icone, kind = TIPO_LABEL.get(mov["tipo_movimentacao"], (mov["tipo_movimentacao"], "swap_horiz", "muted"))
    sinal = "+" if mov["tipo_operacao"] == "entrada" else "\u2212"
    cor_valor = TEAL_DARK if mov["tipo_operacao"] == "entrada" else "#D9534F"

    with ui.row().style(
        "justify-content:space-between; align-items:center; padding:10px 0; "
        "border-bottom:1px solid #EEF1F3; width:100%; gap:10px; flex-wrap:wrap;"
    ):
        with ui.row().style("align-items:center; gap:10px; flex:1; min-width:200px;"):
            ui.icon(icone).style(f"color:{TEAL_DARK}; font-size:18px;")
            with ui.column().style("gap:0;"):
                ui.label(label).style(f"color:{TEXT}; font-weight:700; font-size:13px;")
                detalhe = str(mov["criado_em"])[:16].replace("T", " \u00b7 ")
                if mov["responsavel_nome"]:
                    detalhe += f" \u2022 lançado por {mov['responsavel_nome']}"
                if mov["forma_pagamento"]:
                    detalhe += f" \u2022 {FORMA_PAGAMENTO_LABEL.get(mov['forma_pagamento'], mov['forma_pagamento'])}"
                ui.label(detalhe).style(f"color:{TEXT_MUTED}; font-size:11px;")
                if mov["observacoes"]:
                    ui.label(mov["observacoes"]).style(f"color:{TEXT_MUTED}; font-size:11px; font-style:italic;")
        ui.label(f"{sinal}{mov['quantidade_creditos']}").style(
            f"color:{cor_valor}; font-weight:800; font-size:15px;"
        )
