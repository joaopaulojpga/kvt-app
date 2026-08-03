# -*- coding: utf-8 -*-
"""Popula dados de exemplo para você testar o app antes de ter usuários reais."""
from datetime import date, timedelta
from db import db, init_db
import auth


def seed_demo(hoje=None):
    hoje = hoje or date.today()
    init_db()
    with db() as conn:
        ja_tem = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    if ja_tem > 0:
        return  # já foi populado antes, não duplica

    joao = auth.cadastrar_usuario("João Souza", "M", "joao@canoaclube.com", "123456",
                                   "111.111.111-11", "(21) 99999-0001", role="instrutor")
    ana = auth.cadastrar_usuario("Ana Lima", "F", "ana@canoaclube.com", "123456",
                                  "222.222.222-22", "(21) 99999-0002", role="instrutor")
    marcos = auth.cadastrar_usuario("Marcos Reis", "M", "marcos@canoaclube.com", "123456",
                                     "333.333.333-33", "(21) 99999-0003", role="instrutor")
    auth.cadastrar_usuario("Gestor Clube", "F", "gestor@canoaclube.com", "123456",
                            "444.444.444-44", "(21) 99999-0004", role="gestor")

    # grade da semana corrente: terça/quinta 6h, sábado 6h/8h, domingo 7h/9h
    grade = [
        (1, "06:00", joao), (3, "06:00", ana),
        (5, "06:00", joao), (5, "08:00", marcos),
        (6, "07:00", ana), (6, "09:00", joao),
    ]  # weekday: 0=segunda ... 6=domingo
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    with db() as conn:
        for weekday, horario, instrutor_id in grade:
            data_turma = inicio_semana + timedelta(days=weekday)
            if data_turma < hoje:
                data_turma += timedelta(days=7)
            conn.execute(
                "INSERT INTO classes (data, horario, tipo, instrutor_resp_id, status) "
                "VALUES (?, ?, 'treino', ?, 'agendada')",
                (data_turma.isoformat(), horario, instrutor_id),
            )
