# -*- coding: utf-8 -*-
from nicegui import ui
from theme import TEAL, TEAL_DARK, TEXT, TEXT_MUTED, BORDER, CARD, NAVY, OK, WARN, DANGER


def card(**style_extra):
    el = ui.column().classes("canoa-card").style("gap:8px;")
    for k, v in style_extra.items():
        el.style(f"{k.replace('_', '-')}:{v};")
    return el


def badge(texto, kind="ok"):
    cores = {
        "ok": ("#EAF7EE", OK),
        "warn": ("#FDF3E4", "#8A5A12"),
        "danger": ("#FBEAEA", DANGER),
        "muted": ("#EEF1F3", TEXT_MUTED),
    }
    bg, fg = cores.get(kind, cores["ok"])
    ui.label(texto).style(
        f"background:{bg}; color:{fg}; border-radius:999px; padding:3px 12px; "
        "font-size:12px; font-weight:600; display:inline-block;"
    )


def section_title(texto):
    ui.label(texto).style(f"color:{TEXT}; font-size:18px; font-weight:700; margin-top:8px;")


def page_title(texto, subtitulo=None):
    ui.label(texto).style(f"color:{NAVY}; font-size:26px; font-weight:800;")
    if subtitulo:
        ui.label(subtitulo).style(f"color:{TEXT_MUTED}; font-size:13px; margin-top:-8px;")
