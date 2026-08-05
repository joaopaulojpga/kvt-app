# -*- coding: utf-8 -*-
"""Testa o módulo whatsapp.py: geração de textos (rotinas), o gancho de
lembrete de véspera com dedup, e o comportamento gracioso sem credenciais."""
import os
import sys
import tempfile
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_whatsapp.db")

from db import init_db, db  # noqa: E402
from auth import cadastrar_usuario  # noqa: E402
import classes as turmas_mod, reservations, credits, whatsapp  # noqa: E402

init_db()
HOJE = date(2026, 8, 5)


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b!r}, obtido {a!r}"


# ---- sem credenciais: não quebra, só não envia ----
assert whatsapp.WHATSAPP_TOKEN is None, "teste pressupõe ambiente sem credenciais configuradas"
ok = whatsapp._enviar_mensagem("21999999999", "teste")
approx(ok, False, "sem credenciais, _enviar_mensagem deveria retornar False sem lançar erro")
print("OK — sem credenciais configuradas, o envio não quebra o fluxo (retorna False).")

# ---- _limpar_telefone: sempre garante o código do país ----
approx(whatsapp._limpar_telefone("(21) 90000-9999"), "5521900009999")
approx(whatsapp._limpar_telefone("+55 21 90000-9999"), "5521900009999")
approx(whatsapp._limpar_telefone("5521900009999"), "5521900009999")
print("OK — _limpar_telefone normaliza com código do país em qualquer formato de entrada.")

# ---- automações não quebram o fluxo principal mesmo sem credenciais ----
aluno = cadastrar_usuario("Duda Zap", "F", "duda_zap@t.com", "1", "zap1", "21900001111")
instrutor = cadastrar_usuario("Zeca Zap", "M", "zeca_zap@t.com", "1", "zap2", "21900002222")
with db() as conn:
    conn.execute("UPDATE users SET role='instrutor' WHERE id=?", (instrutor,))
turmas_mod.criar_turma(HOJE.isoformat(), "06:00", "treino", instrutor_resp_id=instrutor)
with db() as conn:
    turma_id = conn.execute("SELECT id FROM classes WHERE data=?", (HOJE.isoformat(),)).fetchone()["id"]

credits.emitir_creditos(aluno, "avulsa", None, 1, hoje=HOJE)
resultado = reservations.reservar(aluno, turma_id, hoje=HOJE)
approx(resultado["status"], "confirmada", "a notificação não deveria impedir a reserva de acontecer")
print("OK — reservar() completa normalmente mesmo com o WhatsApp não configurado.")

# ---- gerar_texto_lista_semana: reflete a grade real, no novo formato ----
texto = whatsapp.gerar_texto_lista_semana(hoje=HOJE)
assert "06:00" in texto and "Zeca Zap" in texto, "o texto deveria citar o horário e o instrutor da turma"
assert "\U0001F4C5" in texto and "\U0001F550" in texto, "deveria usar os emojis no lugar de marcadores de texto"
assert "1. Duda Zap" in texto, "deveria listar o aluno que reservou, numerado"
print("OK — gerar_texto_lista_semana lista as turmas reais, com emojis e alunos numerados.")

texto_sem_alunos = whatsapp.gerar_texto_lista_semana(hoje=HOJE, incluir_alunos=False)
assert "Duda Zap" not in texto_sem_alunos, "com incluir_alunos=False não deveria citar nomes"
assert "06:00" in texto_sem_alunos, "mas ainda deveria trazer os dados da turma"
print("OK — gerar_texto_lista_semana(incluir_alunos=False) omite os nomes, mantendo o resto do formato.")

texto_vazio = whatsapp.gerar_texto_lista_semana(hoje=HOJE + timedelta(days=30))
assert "Nenhuma turma" in texto_vazio
print("OK — gerar_texto_lista_semana avisa quando não há turmas futuras.")

# ---- gerar_texto_convite_remada / informativo: geram texto não vazio ----
assert len(whatsapp.gerar_texto_convite_remada()) > 10
assert "Manutenção" in whatsapp.gerar_texto_informativo("Manutenção", "Sábado não teremos aula.")
print("OK — geradores de convite e informativo produzem o texto esperado.")

# ---- verificar_lembretes_vespera: só notifica quem está na janela de 12h, sem duplicar ----
turmas_mod.criar_turma((HOJE + timedelta(days=1)).isoformat(), "06:00", "treino", instrutor_resp_id=instrutor)
with db() as conn:
    turma_amanha_id = conn.execute(
        "SELECT id FROM classes WHERE data=?", ((HOJE + timedelta(days=1)).isoformat(),)
    ).fetchone()["id"]
credits.emitir_creditos(aluno, "avulsa", None, 1, hoje=HOJE)
reservations.reservar(aluno, turma_amanha_id, hoje=HOJE)

agora_longe = datetime(HOJE.year, HOJE.month, HOJE.day, 10, 0)  # >12h antes das 06:00 de amanhã
n = whatsapp.verificar_lembretes_vespera(agora=agora_longe)
approx(n, 0, "fora da janela de 12h não deveria notificar")

agora_perto = datetime(HOJE.year, HOJE.month, HOJE.day + 1, 0, 0)  # 6h antes das 06:00 de amanhã
n2 = whatsapp.verificar_lembretes_vespera(agora=agora_perto)
approx(n2, 0, "sem credenciais o envio falha, então não conta como enviado")
with db() as conn:
    log = conn.execute("SELECT COUNT(*) AS n FROM notification_log WHERE tipo='lembrete_vespera'").fetchone()
approx(log["n"], 1, "mesmo falhando o envio, deveria registrar no log pra não tentar de novo (evita duplicar quando configurar)")

n3 = whatsapp.verificar_lembretes_vespera(agora=agora_perto)
with db() as conn:
    log2 = conn.execute("SELECT COUNT(*) AS n FROM notification_log WHERE tipo='lembrete_vespera'").fetchone()
approx(log2["n"], 1, "chamar de novo não deveria duplicar o registro de log")
print("OK — verificar_lembretes_vespera só considera a janela de 12h e nunca duplica o registro.")

print("\nTodos os testes do módulo WhatsApp passaram.")
