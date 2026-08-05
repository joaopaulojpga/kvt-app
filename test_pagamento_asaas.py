# -*- coding: utf-8 -*-
"""Testa a integração de pagamento com o Asaas: criação de compra, webhook
(idempotência, filtro de eventos, validação de token) — sem chamadas de
rede de verdade (payments.consultar_pagamento é substituída por um stub)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_pagamento_asaas.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import payments  # noqa: E402
import credits  # noqa: E402

init_db()


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


aluno = cadastrar_usuario("Fernanda Reis", "F", "fernanda_pay@t.com", "1", "payasaas1", "21900009999")

# ---- criar_compra_pendente ----
purchase_id = payments.criar_compra_pendente(aluno, "pacote4", 10500)
with db() as conn:
    compra = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
approx(compra["forma_pagamento"], "asaas", "forma_pagamento deveria ser 'asaas'")
approx(compra["status"], "pendente")
print("OK — criar_compra_pendente grava forma_pagamento='asaas' e status pendente.")

# ---- stub de consultar_pagamento (sem rede) ----
_original_consultar = payments.consultar_pagamento


def _stub_consultar(payment_id):
    return {"id": payment_id, "externalReference": str(purchase_id), "status": "RECEIVED"}


payments.consultar_pagamento = _stub_consultar

# ---- evento que não é de pagamento confirmado: não credita ----
payments.processar_webhook({"event": "PAYMENT_CREATED", "payment": {"id": "pay_1"}}, {})
approx(credits.saldo_disponivel(aluno), 0, "PAYMENT_CREATED não deveria creditar nada")
print("OK — eventos fora de EVENTOS_PAGO são ignorados (nenhum crédito emitido).")

# ---- token de webhook inválido (quando configurado): não credita ----
payments.ASAAS_WEBHOOK_TOKEN = "segredo-forte-de-teste-1234567890"
payments.processar_webhook(
    {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
    {"asaas-access-token": "token-errado"},
)
approx(credits.saldo_disponivel(aluno), 0, "token inválido não deveria creditar nada")
print("OK — webhook com asaas-access-token inválido é rejeitado.")

# ---- evento válido com token correto: credita ----
payments.processar_webhook(
    {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
    {"asaas-access-token": "segredo-forte-de-teste-1234567890"},
)
approx(credits.saldo_disponivel(aluno), 4, "deveria creditar as 4 remadas do pacote4")
with db() as conn:
    compra = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
approx(compra["status"], "pago")
approx(compra["payment_ref"], "pay_1")
print("OK — PAYMENT_RECEIVED com token válido credita as remadas e marca a compra como paga.")

# ---- idempotência: mesmo evento de novo não credita duas vezes ----
payments.processar_webhook(
    {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1"}},
    {"asaas-access-token": "segredo-forte-de-teste-1234567890"},
)
approx(credits.saldo_disponivel(aluno), 4, "reprocessar o mesmo evento não deveria creditar de novo")
print("OK — reenvio do mesmo evento (idempotência) não duplica o crédito.")

payments.consultar_pagamento = _original_consultar
payments.ASAAS_WEBHOOK_TOKEN = None

print("\nTodos os testes de pagamento (Asaas) passaram.")
