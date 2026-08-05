# -*- coding: utf-8 -*-
"""
Central de Eventos do WhatsApp — único módulo autorizado a enviar
mensagens de WhatsApp. Toda automação (reserva, compra, cancelamento
etc.) chama uma função daqui; nenhuma outra parte do código monta ou
envia mensagem diretamente.

Mesma filosofia do mailer.py: se as credenciais não estiverem
configuradas, a função não quebra o fluxo principal — só registra no
log que não foi enviada. Uma reserva confirmada continua confirmada
mesmo que o aviso não saia.

IMPORTANTE — textos são RASCUNHO: os scripts abaixo foram escritos
para deixar toda a infraestrutura pronta, mas o texto final de cada
mensagem deve ser validado com o cliente antes de ir pra produção
(ver conversa sobre "vamos validando os scripts juntos").

Sobre templates: o envio abaixo manda mensagem de texto livre. Isso
funciona hoje (inclusive com o número de teste que a Meta libera antes
da aprovação do app), mas mensagens que a gente INICIA (não é resposta
a algo que o usuário mandou) exigem um Template aprovado pela Meta
pra funcionar fora da janela de 24h em produção — passo que ainda
precisa ser feito quando o número estiver configurado.
"""
import os
import re
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

from db import db

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")
WHATSAPP_API_BASE = "https://graph.facebook.com/v20.0"
APP_BASE_URL = os.environ.get("APP_BASE_URL", "").rstrip("/")

# Número do gestor pra onde vão as "Rotinas" (ele cola manualmente no
# grupo, por decisão do cliente — evita a limitação da API oficial de
# não conseguir postar num grupo comum já existente).
GESTOR_WHATSAPP = os.environ.get("GESTOR_WHATSAPP")

JANELA_LEMBRETE_VESPERA_HORAS = 12


def _limpar_telefone(texto):
    digitos = re.sub(r"\D", "", texto or "")
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        return digitos
    return "55" + digitos  # a API da Meta exige código do país


def _enviar_mensagem(telefone, texto):
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_ID):
        print(f"[whatsapp] credenciais ausentes — mensagem para {telefone} não enviada:\n{texto}")
        return False
    if not telefone:
        print("[whatsapp] destinatário sem celular cadastrado — mensagem não enviada.")
        return False

    payload = {
        "messaging_product": "whatsapp",
        "to": _limpar_telefone(telefone),
        "type": "text",
        "text": {"body": texto},
    }
    req = urllib.request.Request(
        f"{WHATSAPP_API_BASE}/{WHATSAPP_PHONE_ID}/messages",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        return True
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"[whatsapp] falha ao enviar para {telefone}: {e}")
        return False


def responder_mensagem(telefone, texto):
    """Envio de resposta a uma mensagem recebida (Fase 2 — Scripts). Mesmo
    mecanismo de envio das automações, só um nome mais claro pro chamador."""
    return _enviar_mensagem(telefone, texto)


def _ja_notificado(conn, tipo, referencia_id):
    row = conn.execute(
        "SELECT 1 FROM notification_log WHERE tipo = ? AND referencia_id = ?",
        (tipo, referencia_id),
    ).fetchone()
    return row is not None


def _marcar_notificado(conn, tipo, referencia_id):
    conn.execute(
        "INSERT INTO notification_log (tipo, referencia_id) VALUES (?, ?)",
        (tipo, referencia_id),
    )


# ---------------------------------------------------------------------
# Automações — 1:1, disparadas no momento do evento
# ---------------------------------------------------------------------

def notificar_cadastro(nome, celular):
    texto = (
        f"Oi, {nome.split()[0]}! \U0001F33A\n\n"
        "Seu cadastro na Kalani Vaa Team foi concluído com sucesso!\n"
        "Agora é só comprar suas remadas e reservar sua primeira aula pelo app."
    )
    return _enviar_mensagem(celular, texto)


def notificar_compra(nome, celular, plano_nome, quantidade_creditos):
    texto = (
        f"Pagamento confirmado, {nome.split()[0]}! \u2705\n\n"
        f"{plano_nome} ({quantidade_creditos} remada{'s' if quantidade_creditos > 1 else ''}) já está disponível "
        "na sua conta. Bora reservar sua próxima remada?"
    )
    return _enviar_mensagem(celular, texto)


def notificar_reserva_confirmada(nome, celular, data, horario):
    texto = (
        f"Reserva confirmada, {nome.split()[0]}! \U0001F6F6\n\n"
        f"\U0001F4C5 {data} \u2022 \U0001F550 {horario}\n"
        "Chegue 15 minutos antes, leve água e protetor solar.\n"
        "Nos vemos na água!\n\n"
        "\u2615 Ah, e fazemos um café comunitário lá na Lagoa pra socializar depois da remada "
        "\u2014 sinta-se à vontade pra levar algo pra compartilhar!"
    )
    return _enviar_mensagem(celular, texto)


def notificar_reserva_pendente(nome, celular, data, horario):
    texto = (
        f"Recebemos seu pedido, {nome.split()[0]}!\n\n"
        f"A turma de {data} às {horario} já está no limite padrão de vagas — sua reserva ficou "
        "pendente de aprovação do instrutor responsável. Te avisamos assim que for confirmada."
    )
    return _enviar_mensagem(celular, texto)


def notificar_reserva_cancelada(nome, celular, data, horario):
    texto = (
        f"Sua reserva de {data} às {horario} foi cancelada, {nome.split()[0]}.\n"
        "Sua remada já voltou pra sua conta."
    )
    return _enviar_mensagem(celular, texto)


def notificar_aula_cancelada(participantes, data, horario):
    """`participantes` é uma lista de dicts/linhas com 'nome' e 'celular'."""
    enviados = 0
    for p in participantes:
        texto = (
            f"Oi, {p['nome'].split()[0]}. A remada de {data} às {horario} foi cancelada/suspensa.\n"
            "Sua remada já voltou pra sua conta, com validade estendida em +7 dias. "
            "Sentimos muito pelo transtorno!"
        )
        if _enviar_mensagem(p["celular"], texto):
            enviados += 1
    return enviados


def notificar_escala_atribuida(nome_instrutor, celular_instrutor, data, horario):
    texto = (
        f"Fala, {nome_instrutor.split()[0]}! Você foi escalado(a) como instrutor responsável:\n\n"
        f"\U0001F4C5 {data} \u2022 \U0001F550 {horario}\n\n"
        "Confira a Escala completa no app."
    )
    return _enviar_mensagem(celular_instrutor, texto)


def verificar_lembretes_vespera(agora=None):
    """
    Varre as reservas confirmadas cuja remada começa em até 12h e ainda
    não teve lembrete enviado. Feito pra ser chamado periodicamente por
    um agendador externo gratuito (ver decisão de infraestrutura), não
    por um processo interno — evita duplicar envio em restarts.
    """
    agora = agora or datetime.now()
    limite = (agora + timedelta(hours=JANELA_LEMBRETE_VESPERA_HORAS)).isoformat(sep=" ")
    agora_iso = agora.isoformat(sep=" ")
    enviados = 0
    with db() as conn:
        proximas = conn.execute(
            "SELECT r.id AS reservation_id, u.nome, u.celular, c.data, c.horario "
            "FROM reservations r "
            "JOIN users u ON u.id = r.user_id "
            "JOIN classes c ON c.id = r.class_id "
            "WHERE r.status = 'confirmada' AND c.status = 'agendada' "
            "AND (c.data || ' ' || c.horario) BETWEEN ? AND ?",
            (agora_iso, limite),
        ).fetchall()
        for row in proximas:
            if _ja_notificado(conn, "lembrete_vespera", row["reservation_id"]):
                continue
            texto = (
                f"Lembrete: sua remada é amanhã/hoje! \U0001F3D4\uFE0F\n\n"
                f"\U0001F4C5 {row['data']} \u2022 \U0001F550 {row['horario']}\n"
                "Chegue 15 minutos antes, leve água e protetor solar."
            )
            if _enviar_mensagem(row["celular"], texto):
                enviados += 1
            _marcar_notificado(conn, "lembrete_vespera", row["reservation_id"])
    return enviados


# ---------------------------------------------------------------------
# Rotinas — geram o texto pra você revisar e colar manualmente no
# grupo do clube (decisão combinada, evita a limitação da API oficial
# de não postar em grupos comuns já existentes)
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# Rotinas — geram o texto pra você revisar e colar manualmente no
# grupo do clube (decisão combinada, evita a limitação da API oficial
# de não postar em grupos comuns já existentes)
# ---------------------------------------------------------------------

TURMAS_NA_LISTA = 4  # sempre as 4 próximas — não uma janela fixa de dias


def _proximas_turmas_para_lista(hoje, limite=TURMAS_NA_LISTA):
    """
    As N turmas futuras mais próximas com instrutor definido — nunca as
    que já baixaram (status muda pra 'confirmada'/'suspensa_*' ao dar
    baixa), então a lista se atualiza sozinha conforme as aulas
    acontecem, sem precisar filtrar por data de "fim da semana".
    """
    with db() as conn:
        rows = conn.execute(
            "SELECT c.id, c.data, c.horario, c.tipo, c.vagas_base, u.nome AS instrutor_nome, "
            "  (SELECT COUNT(*) FROM reservations r WHERE r.class_id = c.id "
            "     AND r.status IN ('confirmada','presente','faltou')) AS confirmados "
            "FROM classes c JOIN users u ON u.id = c.instrutor_resp_id "
            "WHERE c.data >= ? AND c.status = 'agendada' "
            "ORDER BY c.data, c.horario LIMIT ?",
            (hoje.isoformat(), limite),
        ).fetchall()
    return [dict(r) for r in rows]


def _nomes_participantes(class_id):
    with db() as conn:
        rows = conn.execute(
            "SELECT u.nome FROM reservations r JOIN users u ON u.id = r.user_id "
            "WHERE r.class_id = ? AND r.status IN ('confirmada','presente','faltou') "
            "ORDER BY r.criado_em",
            (class_id,),
        ).fetchall()
    return [r["nome"] for r in rows]


def _bloco_turma(t, incluir_alunos):
    linhas = [
        f"\U0001F4C5 {t['data']}",
        f"\U0001F550 {t['horario']}",
        f"\U0001F9D1\u200D\U0001F3EB Instrutor: {t['instrutor_nome']}",
        f"\U0001F3F7\uFE0F Tipo: {t['tipo'].capitalize()}",
        f"\U0001F465 {t['confirmados']}/{t['vagas_base'] or 12} vagas",
    ]
    if incluir_alunos:
        nomes = _nomes_participantes(t["id"])
        if nomes:
            linhas += [f"{i}. {nome}" for i, nome in enumerate(nomes, 1)]
        else:
            linhas.append("Nenhum aluno reservado ainda.")
    return "\n".join(linhas)


def gerar_texto_lista_semana(hoje=None, incluir_alunos=True):
    from datetime import date

    hoje = hoje or date.today()
    turmas = _proximas_turmas_para_lista(hoje)

    partes = ["\U0001F3D4\uFE0F *Turmas da semana \u2014 Kalani Vaa Team*", ""]
    if not turmas:
        partes.append("Nenhuma turma futura com instrutor definido ainda.")
    else:
        blocos = [_bloco_turma(t, incluir_alunos) for t in turmas]
        partes.append("\n\n".join(blocos))
    if APP_BASE_URL:
        partes += ["", f"Reserve pelo app: {APP_BASE_URL}/agenda"]
    return "\n".join(partes)


def gerar_texto_convite_remada():
    link = f"{APP_BASE_URL}/agenda" if APP_BASE_URL else ""
    return (
        "\U0001F33A Bora remar? \U0001F6F6\n\n"
        "Ainda dá tempo de garantir sua vaga nas próximas remadas da semana!\n"
        f"Reserve pelo app: {link}"
    )


def gerar_texto_informativo(titulo, corpo):
    return f"\U0001F4E2 *{titulo}*\n\n{corpo}"
