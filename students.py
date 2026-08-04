# -*- coding: utf-8 -*-
"""Gestão de alunos — usado em Configurações > Lista de Alunos e no Relatório de Alunos."""
from db import db
import credits


def listar_alunos():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, nome, email, celular, data_nascimento, role FROM users "
            "WHERE role = 'aluno' ORDER BY nome"
        ).fetchall()
    return [dict(r) for r in rows]


def promover_para_instrutor(user_id):
    with db() as conn:
        conn.execute("UPDATE users SET role = 'instrutor' WHERE id = ?", (user_id,))


def relatorio_alunos():
    """
    Uma linha por aluno, com:
    - status: 'Ativo' se tem crédito disponível, 'Inativo' se não tem
    - aulas_reservadas: quantas vezes esteve PRESENTE (não conta faltas nem reservas futuras)
    - ultima_aula: data da última aula em que esteve presente
    """
    with db() as conn:
        alunos = conn.execute(
            "SELECT id, nome, celular, data_nascimento FROM users "
            "WHERE role = 'aluno' ORDER BY nome"
        ).fetchall()
        linhas = []
        for a in alunos:
            aulas_reservadas = conn.execute(
                "SELECT COUNT(*) AS n FROM reservations WHERE user_id = ? AND status = 'presente'",
                (a["id"],),
            ).fetchone()["n"]
            ultima = conn.execute(
                "SELECT MAX(c.data) AS d FROM reservations r JOIN classes c ON c.id = r.class_id "
                "WHERE r.user_id = ? AND r.status = 'presente'",
                (a["id"],),
            ).fetchone()["d"]
            linhas.append({
                "id": a["id"],
                "nome": a["nome"],
                "celular": a["celular"],
                "data_nascimento": a["data_nascimento"],
                "aulas_reservadas": aulas_reservadas,
                "ultima_aula": ultima,
            })
    for linha in linhas:
        linha["status"] = "Ativo" if credits.saldo_disponivel(linha["id"]) > 0 else "Inativo"
    return linhas
