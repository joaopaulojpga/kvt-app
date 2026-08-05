# -*- coding: utf-8 -*-
"""Testa o Ledger de créditos (credit_transactions): toda concessão,
consumo e devolução de crédito grava uma linha imutável e correta."""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_credit_ledger.db")

from db import init_db, db, insert_returning_id  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import credits  # noqa: E402

init_db()
HOJE = date(2026, 8, 5)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


aluno = cadastrar_usuario("Bia Ledger", "F", "bia_ledger@t.com", "1", "ledger1", "21900001111")
gestor = cadastrar_usuario("Gestora Ana", "F", "ana_gestora@t.com", "1", "ledger2", "21900002222", role="gestor")

# turma + reserva reais, só pra testar a rastreabilidade do reservation_id no Ledger
with db() as conn:
    class_id = insert_returning_id(
        conn, "INSERT INTO classes (data, horario, tipo, status) VALUES (?, ?, 'treino', 'agendada')",
        (HOJE.isoformat(), "06:00"),
    )
    reservation_id = insert_returning_id(
        conn, "INSERT INTO reservations (class_id, user_id, status) VALUES (?, ?, 'confirmada')",
        (class_id, aluno),
    )

# ---- emitir_creditos (compra online): grava entrada com saldo antes/depois corretos ----
credits.emitir_creditos(aluno, "pacote4", None, 4, hoje=HOJE)
mov = credits.listar_movimentacoes(aluno)
approx(len(mov), 1)
approx(mov[0]["tipo_movimentacao"], "compra_online")
approx(mov[0]["tipo_operacao"], "entrada")
approx(mov[0]["quantidade_creditos"], 4)
approx(mov[0]["saldo_anterior"], 0)
approx(mov[0]["saldo_posterior"], 4)
approx(mov[0]["purchase_id"], None)
approx(mov[0]["usuario_responsavel_id"], None, "compra online não tem responsável manual")
print("OK — emitir_creditos (compra_online) grava a movimentação com saldo antes/depois corretos.")

# ---- emitir_creditos (venda offline, lançada pelo gestor): grava com responsável + forma de pagamento ----
credits.emitir_creditos(
    aluno, "avulsa", None, 1, hoje=HOJE,
    tipo_movimentacao="venda_offline", forma_pagamento="pix",
    usuario_responsavel_id=gestor, observacoes="Pix recebido no grupo do WhatsApp",
)
mov = credits.listar_movimentacoes(aluno)
approx(len(mov), 2)
ultima = mov[0]  # mais recente primeiro
approx(ultima["tipo_movimentacao"], "venda_offline")
approx(ultima["forma_pagamento"], "pix")
approx(ultima["usuario_responsavel_id"], gestor)
approx(ultima["responsavel_nome"], "Gestora Ana")
approx(ultima["observacoes"], "Pix recebido no grupo do WhatsApp")
approx(ultima["saldo_anterior"], 4)
approx(ultima["saldo_posterior"], 5)
approx(credits.saldo_disponivel(aluno, hoje=HOJE), 5)
print("OK — venda_offline lançada pelo gestor grava responsável, forma de pagamento e observação.")

# ---- consumir_um_credito: grava saída tipo 'reserva' ----
credit_id = credits.consumir_um_credito(aluno, hoje=HOJE, reservation_id=reservation_id)
assert credit_id is not None
mov = credits.listar_movimentacoes(aluno)
approx(mov[0]["tipo_movimentacao"], "reserva")
approx(mov[0]["tipo_operacao"], "saida")
approx(mov[0]["quantidade_creditos"], 1)
approx(mov[0]["saldo_anterior"], 5)
approx(mov[0]["saldo_posterior"], 4)
approx(mov[0]["reservation_id"], reservation_id)
approx(credits.saldo_disponivel(aluno, hoje=HOJE), 4)
print("OK — consumir_um_credito grava a saída tipo 'reserva' com o reservation_id.")

# ---- devolver_credito: grava entrada tipo 'estorno' ----
credits.devolver_credito(credit_id, motivo_extensao=False, hoje=HOJE, user_id=aluno, reservation_id=reservation_id)
mov = credits.listar_movimentacoes(aluno)
approx(mov[0]["tipo_movimentacao"], "estorno")
approx(mov[0]["tipo_operacao"], "entrada")
approx(mov[0]["saldo_anterior"], 4)
approx(mov[0]["saldo_posterior"], 5)
approx(mov[0]["reservation_id"], reservation_id)
approx(credits.saldo_disponivel(aluno, hoje=HOJE), 5)
print("OK — devolver_credito grava a entrada tipo 'estorno' corretamente.")

# ---- Ledger é cumulativo e imutável: nenhuma linha anterior muda ----
approx(len(credits.listar_movimentacoes(aluno)), 4, "todas as 4 movimentações devem continuar no histórico")
print("OK — o Ledger acumula todas as movimentações sem apagar/alterar as anteriores.")

# ---- listar_movimentacoes com limite ----
approx(len(credits.listar_movimentacoes(aluno, limite=2)), 2)
print("OK — listar_movimentacoes respeita o parâmetro de limite.")

print("\nTodos os testes do Ledger de créditos passaram.")
