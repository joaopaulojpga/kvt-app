# -*- coding: utf-8 -*-
from nicegui import ui
from datetime import date as date_cls
from theme import NAVY, TEAL, TEAL_DARK, TEXT, TEXT_MUTED
from calendar_ics import gerar_ics

DIAS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def mostrar_confirmacao(data_str, horario_str):
    try:
        d = date_cls.fromisoformat(str(data_str))
        data_fmt = f"{DIAS_PT[d.weekday()]}, {d.strftime('%d/%m/%Y')}"
    except ValueError:
        data_fmt = str(data_str)

    with ui.dialog() as dialog, ui.card().style(
        "max-width:420px; padding:28px; gap:12px; border-radius:16px;"
    ):
        ui.label("\U0001F389 Remada reservada com sucesso!").style(
            f"color:{NAVY}; font-size:19px; font-weight:800;"
        )
        ui.label("Sua próxima experiência na água já está garantida.").style(
            f"color:{TEXT_MUTED}; font-size:13px;"
        )

        with ui.column().style(
            "background:#EAF6F4; border-radius:12px; padding:14px 16px; gap:4px; width:100%;"
        ):
            ui.label(f"\U0001F4C5 {data_fmt}").style(f"color:{TEAL_DARK}; font-weight:700; font-size:14px;")
            ui.label(f"\U0001F550 {horario_str}").style(f"color:{TEAL_DARK}; font-weight:700; font-size:14px;")
            ui.label("\U0001F4CD Lagoa de Cima").style(f"color:{TEAL_DARK}; font-weight:700; font-size:14px;")

        ui.label("Orientações rápidas:").style(f"color:{TEXT}; font-weight:700; font-size:12.5px; margin-top:4px;")
        for dica in ["Chegue 15 minutos antes", "Leve sua garrafa de água", "Utilize protetor solar"]:
            ui.label(f"\u2022 {dica}").style(f"color:{TEXT_MUTED}; font-size:12.5px;")

        with ui.row().style("gap:10px; width:100%; margin-top:8px; flex-wrap:wrap;"):
            def baixar_ics():
                ics_bytes = gerar_ics(str(data_str), horario_str)
                ui.download(ics_bytes, "remada-kalani-vaa.ics")

            ui.button("Adicionar ao calendário", on_click=baixar_ics).props("outline").style(
                f"color:{TEAL_DARK}; font-weight:700;"
            )
            ui.button("Fechar", on_click=dialog.close).props("unelevated").style(
                f"background:{TEAL}; color:white; font-weight:700;"
            )

    dialog.open()
