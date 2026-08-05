# -*- coding: utf-8 -*-
"""
"Dar baixa" na turma: o instrutor confirma o status da aula
(confirmada / suspensa por clima / suspensa por quórum), marca
presença/falta de cada inscrito e o sistema calcula e grava o repasse.

Regra: se a turma for suspensa (clima ou quórum) ou cancelada, todos
os créditos consumidos são devolvidos com +7 dias de validade e
NENHUM repasse é gerado. O repasse, quando gerado, é calculado sobre
os inscritos/pagantes — não muda com presença/falta.
"""
from db import db
import credits
from payouts import calcular_repasses_da_turma


class BaixaError(Exception):
    pass


def dar_baixa(class_id, status, presencas: dict, hoje=None):
    """
    status: 'confirmada' | 'suspensa_clima' | 'suspensa_quorum'
    presencas: {reservation_id: 'presente' | 'faltou'} — obrigatório
               apenas quando status == 'confirmada'.
    """
    if status not in ("confirmada", "suspensa_clima", "suspensa_quorum"):
        raise BaixaError("Status inválido.")

    with db() as conn:
        turma = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
        if turma is None:
            raise BaixaError("Turma não encontrada.")
        if turma["status"] not in ("agendada",):
            raise BaixaError("Esta turma já teve a baixa registrada.")

        reservas = conn.execute(
            "SELECT * FROM reservations WHERE class_id = ? AND status IN ('confirmada','presente','faltou')",
            (class_id,),
        ).fetchall()

        if status in ("suspensa_clima", "suspensa_quorum"):
            # devolve créditos de todos os inscritos com +7 dias, nenhum repasse é gerado
            for r in reservas:
                if r["credit_id"] is not None:
                    credits.devolver_credito(
                        r["credit_id"], motivo_extensao=True, hoje=hoje,
                        user_id=r["user_id"], reservation_id=r["id"],
                    )
            conn.execute("UPDATE classes SET status = ? WHERE id = ?", (status, class_id))
            return {"status": status, "repasses": []}

        # status == 'confirmada': marca presença/falta (crédito já foi consumido no check-in e
        # permanece consumido em ambos os casos — falta também consome o crédito)
        for r in reservas:
            marca = presencas.get(r["id"], "presente")
            if marca not in ("presente", "faltou"):
                marca = "presente"
            conn.execute("UPDATE reservations SET status = ? WHERE id = ?", (marca, r["id"]))

        total_remadores = len(reservas)
        calc = calcular_repasses_da_turma(total_remadores)

        payouts_gerados = []
        if calc["remadores_instrutor1"] > 0:
            conn.execute(
                "INSERT INTO payouts (class_id, instrutor_id, remadores_atribuidos, valor_centavos) "
                "VALUES (?, ?, ?, ?)",
                (class_id, turma["instrutor_resp_id"], calc["remadores_instrutor1"],
                 calc["repasse_instrutor1_centavos"]),
            )
            payouts_gerados.append(("instrutor1", calc["repasse_instrutor1_centavos"]))
        if calc["remadores_instrutor2"] > 0 and turma["instrutor2_id"]:
            conn.execute(
                "INSERT INTO payouts (class_id, instrutor_id, remadores_atribuidos, valor_centavos) "
                "VALUES (?, ?, ?, ?)",
                (class_id, turma["instrutor2_id"], calc["remadores_instrutor2"],
                 calc["repasse_instrutor2_centavos"]),
            )
            payouts_gerados.append(("instrutor2", calc["repasse_instrutor2_centavos"]))

        conn.execute("UPDATE classes SET status = 'confirmada' WHERE id = ?", (class_id,))
        return {"status": "confirmada", "repasses": payouts_gerados, "detalhe": calc}


def cancelar_turma_pelo_instrutor(class_id, hoje=None):
    """Cancelamento pela Agenda: mesma regra de devolução da suspensão (+7 dias, sem repasse)."""
    with db() as conn:
        turma = conn.execute("SELECT * FROM classes WHERE id = ?", (class_id,)).fetchone()
        if turma is None:
            raise BaixaError("Turma não encontrada.")
        reservas = conn.execute(
            "SELECT * FROM reservations WHERE class_id = ? AND status IN ('confirmada','presente','faltou')",
            (class_id,),
        ).fetchall()
        for r in reservas:
            if r["credit_id"] is not None:
                credits.devolver_credito(
                    r["credit_id"], motivo_extensao=True, hoje=hoje,
                    user_id=r["user_id"], reservation_id=r["id"],
                )
            conn.execute("UPDATE reservations SET status = 'cancelada' WHERE id = ?", (r["id"],))
        conn.execute("UPDATE classes SET status = 'cancelada' WHERE id = ?", (class_id,))
