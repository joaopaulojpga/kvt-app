# -*- coding: utf-8 -*-
"""
Regras de negócio de créditos.

Cobre: emissão de crédito na compra, validade de 30 dias corridos,
consumo no check-in/expansão, devolução com +7 dias quando a turma é
suspensa (clima/quórum) ou cancelada pelo instrutor.
"""
from datetime import date, timedelta
from db import db, get_param


def _validade_padrao(hoje=None):
    hoje = hoje or date.today()
    dias = get_param("validade_credito_dias", 30, int)
    return hoje + timedelta(days=dias)


def emitir_creditos(user_id, plano, purchase_id, quantidade, hoje=None):
    """Cria N créditos individuais para o usuário após uma compra confirmada."""
    validade = _validade_padrao(hoje)
    with db() as conn:
        for _ in range(quantidade):
            conn.execute(
                "INSERT INTO credits (user_id, origem, purchase_id, validade, status) "
                "VALUES (?, ?, ?, ?, 'disponivel')",
                (user_id, plano, purchase_id, validade.isoformat()),
            )


def saldo_disponivel(user_id, hoje=None):
    """Quantidade de créditos disponíveis e não vencidos."""
    hoje = (hoje or date.today()).isoformat()
    with db() as conn:
        expirar_creditos_vencidos(conn, hoje)
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM credits "
            "WHERE user_id = ? AND status = 'disponivel' AND validade >= ?",
            (user_id, hoje),
        ).fetchone()
    return row["n"]


def proxima_validade(user_id, hoje=None):
    hoje = (hoje or date.today()).isoformat()
    with db() as conn:
        row = conn.execute(
            "SELECT MIN(validade) AS v FROM credits "
            "WHERE user_id = ? AND status = 'disponivel' AND validade >= ?",
            (user_id, hoje),
        ).fetchone()
    return row["v"]


def expirar_creditos_vencidos(conn, hoje_iso):
    """Marca como 'expirado' créditos disponíveis cuja validade já passou."""
    conn.execute(
        "UPDATE credits SET status = 'expirado' "
        "WHERE status = 'disponivel' AND validade < ?",
        (hoje_iso,),
    )


def consumir_um_credito(user_id, hoje=None):
    """
    Consome o crédito de validade mais próxima (evita desperdício).
    Retorna o id do crédito consumido, ou None se não houver saldo.
    """
    hoje_iso = (hoje or date.today()).isoformat()
    with db() as conn:
        expirar_creditos_vencidos(conn, hoje_iso)
        row = conn.execute(
            "SELECT id FROM credits WHERE user_id = ? AND status = 'disponivel' AND validade >= ? "
            "ORDER BY validade ASC LIMIT 1",
            (user_id, hoje_iso),
        ).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE credits SET status = 'consumido' WHERE id = ?", (row["id"],))
        return row["id"]


def devolver_credito(credit_id, motivo_extensao=True, hoje=None):
    """
    Devolve um crédito consumido (cancelamento pelo instrutor ou turma
    suspensa por clima/quórum). Quando `motivo_extensao` é True, soma
    +7 dias de validade a partir de hoje (regra de negócio confirmada).
    """
    hoje = hoje or date.today()
    with db() as conn:
        if motivo_extensao:
            dias_extra = get_param("validade_extra_suspensao_dias", 7, int)
            nova_validade = hoje + timedelta(days=dias_extra)
            conn.execute(
                "UPDATE credits SET status = 'disponivel', validade = ? WHERE id = ?",
                (nova_validade.isoformat(), credit_id),
            )
        else:
            conn.execute("UPDATE credits SET status = 'disponivel' WHERE id = ?", (credit_id,))


def registrar_falta_consome_credito():
    """
    Documenta a regra: falta do aluno NÃO devolve o crédito.
    Nada a fazer aqui — o crédito já foi consumido no check-in e
    permanece 'consumido'. Função mantida por clareza de leitura do
    código (ver lib/attendance.py, que marca a reserva como 'faltou'
    sem tocar em lib/credits.py).
    """
    return None
