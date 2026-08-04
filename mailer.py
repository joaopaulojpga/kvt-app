# -*- coding: utf-8 -*-
"""
Envio de e-mails transacionais via Resend.

Toda falha de envio é silenciada (só registrada no log) — um e-mail que
não sai não pode nunca derrubar o fluxo principal do app (a compra já
foi paga e os créditos já foram emitidos antes de tentarmos avisar por
e-mail; se o e-mail falhar, o crédito continua lá, só o aviso que não
chegou).
"""
import os
import json
import urllib.request
import urllib.error

RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
RESEND_FROM = os.environ.get("RESEND_FROM", "Kalani Vaa Team <onboarding@resend.dev>")
RESEND_API_BASE = "https://api.resend.com"


def _enviar(destinatario, assunto, html):
    if not RESEND_API_KEY:
        print(f"[email] RESEND_API_KEY ausente — e-mail para {destinatario} não enviado.")
        return False
    payload = {
        "from": RESEND_FROM,
        "to": [destinatario],
        "subject": assunto,
        "html": html,
    }
    req = urllib.request.Request(
        f"{RESEND_API_BASE}/emails",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True
    except urllib.error.HTTPError as e:
        print(f"[email] Resend recusou o envio para {destinatario} ({e.code}): {e.read().decode(errors='replace')}")
        return False
    except urllib.error.URLError as e:
        print(f"[email] Falha de conexão ao enviar para {destinatario}: {e}")
        return False


def enviar_confirmacao_compra(destinatario, nome, plano_nome, quantidade_creditos):
    html = f"""
    <div style="font-family:Arial,sans-serif; color:#2B3640;">
      <h2 style="color:#123B57;">Compra confirmada! \U0001F6F6</h2>
      <p>Oi, {nome}!</p>
      <p>Seu pagamento do <b>{plano_nome}</b> foi aprovado e
      <b>{quantidade_creditos} remada(s)</b> já estão disponíveis na
      sua conta do Kalani Vaa Team.</p>
      <p>Bons remos!</p>
    </div>
    """
    return _enviar(destinatario, "Compra confirmada \u2014 Kalani Vaa Team", html)


def enviar_notificacao_expansao(destinatario_instrutor, nome_instrutor, aluno_nome, data, horario):
    html = f"""
    <div style="font-family:Arial,sans-serif; color:#2B3640;">
      <h2 style="color:#123B57;">Solicitação de expansão de vaga</h2>
      <p>Oi, {nome_instrutor}!</p>
      <p><b>{aluno_nome}</b> pediu uma vaga extra na turma de
      <b>{data} às {horario}</b>, que já está no limite de 12 vagas.</p>
      <p>Entre no Kalani Vaa Team, na tela "Lista de Presença", para aprovar
      ou recusar essa solicitação.</p>
    </div>
    """
    return _enviar(destinatario_instrutor, "Vaga extra pendente de aprovação \u2014 Kalani Vaa Team", html)
