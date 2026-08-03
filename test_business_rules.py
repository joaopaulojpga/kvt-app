# -*- coding: utf-8 -*-
"""Valida lib/payouts.py e lib/credits.py contra os exemplos já validados na planilha."""
import os
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

from db import init_db, db  # noqa: E402
from payouts import calcular_repasses_da_turma  # noqa: E402
import credits  # noqa: E402

init_db()


def approx(a, b):
    assert a == b, f"esperado {b}, obtido {a}"


# ---- Repasse: mesmos exemplos da planilha (PRD seção 4.3) ----
r = calcular_repasses_da_turma(6)
approx(r["repasse_instrutor1_centavos"], 5500)   # R$ 55,00
approx(r["repasse_instrutor2_centavos"], 0)
approx(r["faturamento_bruto_centavos"], 21000)   # R$ 210,00

r = calcular_repasses_da_turma(10)
approx(r["repasse_instrutor1_centavos"], 7500)   # R$ 75,00

r = calcular_repasses_da_turma(12)
approx(r["repasse_instrutor1_centavos"], 7500)   # R$ 75,00 (teto, não 25+5*12=85)
approx(r["faturamento_bruto_centavos"], 42000)   # 12 x R$ 35,00 = R$ 420,00
approx(r["margem_liquida_centavos"], 42000 - 7500)  # R$ 345,00

r = calcular_repasses_da_turma(18)
approx(r["remadores_instrutor1"], 12)
approx(r["repasse_instrutor1_centavos"], 7500)   # R$ 75,00
approx(r["remadores_instrutor2"], 6)
approx(r["repasse_instrutor2_centavos"], 5500)   # R$ 55,00
approx(r["total_repasse_centavos"], 13000)       # R$ 130,00

print("OK — cálculo de repasse bate com os exemplos da planilha (6, 10, 12 e 18 remadores).")

# ---- Créditos: emissão, saldo, consumo, validade, devolução ----
with db() as conn:
    conn.execute(
        "INSERT INTO users (nome, sexo, email, senha_hash, cpf, celular, role) "
        "VALUES ('Teste', 'F', 't@t.com', 'x', '000', '21999999999', 'aluno')"
    )
    user_id = conn.execute("SELECT id FROM users WHERE email='t@t.com'").fetchone()["id"]

hoje = date(2026, 8, 3)
credits.emitir_creditos(user_id, "pacote4", None, 4, hoje=hoje)
approx(credits.saldo_disponivel(user_id, hoje=hoje), 4)
approx(credits.proxima_validade(user_id, hoje=hoje), (hoje + timedelta(days=30)).isoformat())

cid = credits.consumir_um_credito(user_id, hoje=hoje)
approx(credits.saldo_disponivel(user_id, hoje=hoje), 3)

# devolução por suspensão de turma: +7 dias a partir de hoje, mesmo que a validade original fosse outra
credits.devolver_credito(cid, motivo_extensao=True, hoje=hoje)
approx(credits.saldo_disponivel(user_id, hoje=hoje), 4)

# crédito vencido não deve contar no saldo
hoje_futuro = hoje + timedelta(days=40)
approx(credits.saldo_disponivel(user_id, hoje=hoje_futuro), 0)

print("OK — créditos: emissão, consumo, devolução com +7 dias e expiração por validade.")
print("\nTodos os testes passaram.")
