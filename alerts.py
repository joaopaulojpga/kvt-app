# -*- coding: utf-8 -*-
"""
Central de Alertas — calculada "ao vivo" a cada abertura do sino, sem
depender de um agendador em segundo plano (o app roda como um único
processo web, sem worker/cron separado). Quase todo alerta aqui é uma
pergunta "isso é verdade agora?" respondida por uma consulta simples —
não um evento disparado uma vez e esquecido/persistido. É suficiente
para os casos abaixo, com uma exceção: "nova turma atribuída na
escala", que usa o timestamp `atribuido_em` (ver classes.py) porque
não dá pra saber se uma atribuição é "recente" só olhando o estado
atual — precisa de um "quando mudou".

Push, e-mail e WhatsApp ficam pra uma fase futura (combinado à parte);
isso aqui é só o alerta dentro do próprio app (sino no topo).
"""
from datetime import datetime, timedelta
from db import db

JANELA_ATRIBUICAO_RECENTE_HORAS = 48
JANELA_EXPIRACAO_CREDITOS_DIAS = 7
JANELA_SEM_INSTRUTOR_DIAS = 7
JANELA_LEMBRETE_HORAS = 24
JANELA_BAIXA_APOS_HORAS = 2


def _horas_ate(data_str, horario_str, agora):
    inicio = datetime.fromisoformat(f"{data_str} {horario_str}")
    return (inicio - agora).total_seconds() / 3600


def _texto_prazo(horas_restantes):
    if horas_restantes <= 2:
        return "em menos de 2 horas"
    if horas_restantes <= 12:
        return "em menos de 12 horas"
    return "em menos de 24 horas"


def alertas_aluno(user_id, agora=None):
    agora = agora or datetime.now()
    hoje = agora.date()
    alertas = []

    with db() as conn:
        venc = conn.execute(
            "SELECT COUNT(*) AS n, MIN(validade) AS proxima FROM credits "
            "WHERE user_id = ? AND status = 'disponivel' AND validade BETWEEN ? AND ?",
            (user_id, hoje.isoformat(), (hoje + timedelta(days=JANELA_EXPIRACAO_CREDITOS_DIAS)).isoformat()),
        ).fetchone()
    if venc["n"] > 0:
        plural = "s" if venc["n"] > 1 else ""
        alertas.append({
            "icone": "schedule",
            "mensagem": f"Você tem {venc['n']} remada{plural} vencendo até {venc['proxima']}.",
            "rota": "/home",
            "urgencia": "warn",
        })

    with db() as conn:
        proximas = conn.execute(
            "SELECT c.data, c.horario FROM reservations r JOIN classes c ON c.id = r.class_id "
            "WHERE r.user_id = ? AND r.status = 'confirmada' AND c.status = 'agendada' AND c.data >= ? "
            "ORDER BY c.data, c.horario",
            (user_id, hoje.isoformat()),
        ).fetchall()
    for turma in proximas:
        horas = _horas_ate(str(turma["data"]), turma["horario"], agora)
        if 0 < horas <= JANELA_LEMBRETE_HORAS:
            alertas.append({
                "icone": "directions_boat",
                "mensagem": f"Sua remada de {turma['horario']} do dia {turma['data']} é "
                            f"{_texto_prazo(horas)}.",
                "rota": "/agenda",
                "urgencia": "info",
            })
            break  # só a mais próxima, pra não empilhar lembrete de várias remadas ao mesmo tempo

    return alertas


def alertas_instrutor(user_id, agora=None):
    agora = agora or datetime.now()
    hoje = agora.date()
    alertas = []

    with db() as conn:
        proximas = conn.execute(
            "SELECT data, horario FROM classes WHERE instrutor_resp_id = ? AND status = 'agendada' "
            "AND data >= ? ORDER BY data, horario",
            (user_id, hoje.isoformat()),
        ).fetchall()
    for turma in proximas:
        horas = _horas_ate(str(turma["data"]), turma["horario"], agora)
        if 0 < horas <= JANELA_LEMBRETE_HORAS:
            alertas.append({
                "icone": "directions_boat",
                "mensagem": f"Você é o instrutor responsável pela remada de {turma['horario']} do dia "
                            f"{turma['data']} \u2014 {_texto_prazo(horas)}.",
                "rota": "/agenda",
                "urgencia": "info",
            })
            break

    with db() as conn:
        rows = conn.execute(
            "SELECT data, horario FROM classes WHERE instrutor_resp_id = ? AND status = 'agendada' "
            "AND data <= ? ORDER BY data, horario",
            (user_id, hoje.isoformat()),
        ).fetchall()
    pendentes_baixa = [
        t for t in rows if _horas_ate(str(t["data"]), t["horario"], agora) <= -JANELA_BAIXA_APOS_HORAS
    ]
    if pendentes_baixa:
        plural = "s" if len(pendentes_baixa) > 1 else ""
        alertas.append({
            "icone": "fact_check",
            "mensagem": f"{len(pendentes_baixa)} turma{plural} já passou{'aram' if plural else ''} do "
                        "horário e está esperando você dar baixa (presença/falta).",
            "rota": "/presenca",
            "urgencia": "warn",
        })

    limite = (agora - timedelta(hours=JANELA_ATRIBUICAO_RECENTE_HORAS)).isoformat(sep=" ")
    with db() as conn:
        novas = conn.execute(
            "SELECT COUNT(*) AS n FROM classes WHERE instrutor_resp_id = ? AND status = 'agendada' "
            "AND data >= ? AND atribuido_em IS NOT NULL AND atribuido_em >= ?",
            (user_id, hoje.isoformat(), limite),
        ).fetchone()
    if novas["n"] > 0:
        plural = "s" if novas["n"] > 1 else ""
        alertas.append({
            "icone": "event_available",
            "mensagem": f"Você foi escalado(a) para {novas['n']} nova{plural} turma{plural} recentemente.",
            "rota": "/configuracoes",
            "urgencia": "info",
        })

    return alertas


def alertas_gestor(agora=None):
    agora = agora or datetime.now()
    hoje = agora.date()
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM classes WHERE instrutor_resp_id IS NULL AND status = 'agendada' "
            "AND data BETWEEN ? AND ?",
            (hoje.isoformat(), (hoje + timedelta(days=JANELA_SEM_INSTRUTOR_DIAS)).isoformat()),
        ).fetchone()
    if row["n"] == 0:
        return []
    plural = "s" if row["n"] > 1 else ""
    return [{
        "icone": "warning",
        "mensagem": f"{row['n']} aula{plural} nos próximos {JANELA_SEM_INSTRUTOR_DIAS} dias ainda sem "
                    f"instrutor responsável definido.",
        "rota": "/configuracoes",
        "urgencia": "danger",
    }]


def alertas_para(user, agora=None):
    """Dispatcher único usado pelo sino da topbar."""
    if user["role"] == "aluno":
        return alertas_aluno(user["id"], agora)
    if user["role"] == "instrutor":
        return alertas_instrutor(user["id"], agora)
    if user["role"] == "gestor":
        return alertas_gestor(agora)
    return []
