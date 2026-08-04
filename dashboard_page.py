# -*- coding: utf-8 -*-
from nicegui import ui
import calendar
from datetime import date
from theme import NAVY, TEAL, TEXT, TEXT_MUTED, reais
from ui_helpers import page_title
from db import db

VALOR_AULA_CENTAVOS = 3500
MESES_ABREV = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
MESES_HISTORICO = 6


def _voltar_meses(ano, mes, n):
    """(ano, mes) resultante de voltar `n` meses a partir de (ano, mes)."""
    total = (ano * 12 + (mes - 1)) - n
    return total // 12, total % 12 + 1


def _faturamento_do_mes(conn, ano, mes):
    primeiro = date(ano, mes, 1).isoformat()
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    ultimo = date(ano, mes, ultimo_dia).isoformat()

    confirmadas = conn.execute(
        "SELECT c.id, "
        "  (SELECT COUNT(*) FROM reservations r WHERE r.class_id = c.id "
        "     AND r.status IN ('confirmada','presente','faltou')) AS n_remadores "
        "FROM classes c WHERE c.status = 'confirmada' AND c.data BETWEEN ? AND ?",
        (primeiro, ultimo),
    ).fetchall()
    payouts = conn.execute(
        "SELECT p.valor_centavos FROM payouts p JOIN classes c ON c.id = p.class_id "
        "WHERE c.data BETWEEN ? AND ?",
        (primeiro, ultimo),
    ).fetchall()

    bruto = sum(c["n_remadores"] for c in confirmadas) * VALOR_AULA_CENTAVOS
    liquido = bruto - sum(p["valor_centavos"] for p in payouts)
    return bruto, liquido


def render(user):
    page_title("Dashboard \u2014 Indicadores")
    hoje = date.today()
    inicio_mes = hoje.replace(day=1).isoformat()

    with db() as conn:
        confirmadas = conn.execute(
            "SELECT c.id, "
            "  (SELECT COUNT(*) FROM reservations r WHERE r.class_id = c.id "
            "     AND r.status IN ('confirmada','presente','faltou')) AS n_remadores "
            "FROM classes c WHERE c.status = 'confirmada' AND c.data >= ?",
            (inicio_mes,),
        ).fetchall()

        payouts = conn.execute(
            "SELECT p.*, u.nome AS instrutor_nome FROM payouts p "
            "JOIN classes c ON c.id = p.class_id JOIN users u ON u.id = p.instrutor_id "
            "WHERE c.data >= ?",
            (inicio_mes,),
        ).fetchall()

    n_turmas = len(confirmadas)
    media_alunos = (sum(c["n_remadores"] for c in confirmadas) / n_turmas) if n_turmas else 0
    faturamento_bruto = sum(c["n_remadores"] for c in confirmadas) * VALOR_AULA_CENTAVOS
    total_repasses = sum(p["valor_centavos"] for p in payouts)
    faturamento_liquido = faturamento_bruto - total_repasses

    with ui.row().style("gap:16px; width:100%; flex-wrap:wrap;"):
        for label, valor in [
            ("Média de alunos/turma", f"{media_alunos:.1f}"),
            ("Turmas confirmadas (mês)", str(n_turmas)),
            ("Faturamento bruto (mês)", reais(faturamento_bruto)),
            ("Faturamento líquido (mês)", reais(faturamento_liquido)),
        ]:
            with ui.column().classes("canoa-card").style("flex:1; min-width:200px; gap:4px;"):
                ui.label(label).style(f"color:{TEXT_MUTED}; font-size:11.5px; font-weight:700;")
                ui.label(valor).style(f"color:{NAVY}; font-size:24px; font-weight:800;")

    ui.label("Turmas por instrutor (mês)").style(f"color:{TEXT}; font-size:16px; font-weight:700; margin-top:8px;")
    if payouts:
        contagem = {}
        for p in payouts:
            contagem.setdefault(p["instrutor_nome"], set()).add(p["class_id"])
        dados = {nome: len(ids) for nome, ids in contagem.items()}
        with ui.column().classes("canoa-card").style("width:100%; gap:6px;"):
            chart = ui.echart({
                "xAxis": {"type": "value"},
                "yAxis": {"type": "category", "data": list(dados.keys())},
                "series": [{"type": "bar", "data": list(dados.values()), "itemStyle": {"color": TEAL}}],
                "grid": {"left": "25%"},
            }).style("height:220px; width:100%;")
    else:
        ui.label("Ainda não há turmas com baixa registrada neste mês.").style(f"color:{TEXT_MUTED};")

    ui.label("Faturamento mensal \u2014 bruto x líquido").style(
        f"color:{TEXT}; font-size:16px; font-weight:700; margin-top:8px;"
    )
    with db() as conn:
        historico = []
        for i in range(MESES_HISTORICO - 1, -1, -1):
            ano_h, mes_h = _voltar_meses(hoje.year, hoje.month, i)
            bruto_h, liquido_h = _faturamento_do_mes(conn, ano_h, mes_h)
            historico.append((f"{MESES_ABREV[mes_h]}/{str(ano_h)[-2:]}", bruto_h, liquido_h))

    with ui.column().classes("canoa-card").style("width:100%; gap:6px;"):
        ui.echart({
            "tooltip": {"trigger": "axis"},
            "legend": {"data": ["Bruto", "Líquido"], "top": 0},
            "grid": {"top": 40, "left": 60, "right": 20, "bottom": 30},
            "xAxis": {"type": "category", "data": [h[0] for h in historico]},
            "yAxis": {"type": "value", "axisLabel": {"formatter": "R$ {value}"}},
            "series": [
                {
                    "name": "Bruto", "type": "bar",
                    "data": [round(h[1] / 100, 2) for h in historico],
                    "itemStyle": {"color": TEAL},
                },
                {
                    "name": "Líquido", "type": "line", "smooth": True,
                    "data": [round(h[2] / 100, 2) for h in historico],
                    "itemStyle": {"color": NAVY},
                },
            ],
        }).style("height:260px; width:100%;")
