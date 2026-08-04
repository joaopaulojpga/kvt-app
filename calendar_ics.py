# -*- coding: utf-8 -*-
"""Gera um arquivo .ics simples (sem dependências externas) para o botão "Adicionar ao calendário"."""
from datetime import datetime, timedelta

DURACAO_PADRAO_MIN = 90


def gerar_ics(data_str, horario_str, titulo="Remada - Kalani Vaa Team", local="Lagoa de Cima"):
    inicio = datetime.strptime(f"{data_str} {horario_str}", "%Y-%m-%d %H:%M")
    fim = inicio + timedelta(minutes=DURACAO_PADRAO_MIN)
    fmt = "%Y%m%dT%H%M%S"
    uid = f"{inicio.strftime(fmt)}-kalanivaa@app"

    linhas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Kalani Vaa Team//Reserva//PT",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.utcnow().strftime(fmt)}Z",
        f"DTSTART:{inicio.strftime(fmt)}",
        f"DTEND:{fim.strftime(fmt)}",
        f"SUMMARY:{titulo}",
        f"LOCATION:{local}",
        "DESCRIPTION:Sua remada na Kalani Vaa Team. Chegue 15 minutos antes\\, "
        "leve sua garrafa de água e utilize protetor solar.",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return ("\r\n".join(linhas) + "\r\n").encode("utf-8")
