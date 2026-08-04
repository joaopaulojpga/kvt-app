# -*- coding: utf-8 -*-
"""Newsletters exibidas no carrossel (página pública e Home do usuário logado)."""
from db import db, insert_returning_id

CTAS = {
    "abrir_modal": "Abrir card em tela cheia",
    "rolar_cadastro": "Rolar até o cadastro",
    "abrir_mapa": "Abrir mapa (localização)",
}


def listar_ativas():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM newsletters WHERE status = 'ativo' ORDER BY ordem, id"
        ).fetchall()
    return [dict(r) for r in rows]


def listar_todas():
    with db() as conn:
        rows = conn.execute("SELECT * FROM newsletters ORDER BY ordem, id").fetchall()
    return [dict(r) for r in rows]


def obter(newsletter_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM newsletters WHERE id = ?", (newsletter_id,)).fetchone()
    return dict(row) if row else None


def criar(titulo, head_texto, head_estilo, corpo_texto, imagem_url, imagem_posicao,
          botao_label, botao_cta, status="ativo", ordem=0):
    with db() as conn:
        return insert_returning_id(
            conn,
            "INSERT INTO newsletters (titulo, head_texto, head_estilo, corpo_texto, imagem_url, "
            "imagem_posicao, botao_label, botao_cta, status, ordem) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (titulo, head_texto, head_estilo, corpo_texto, imagem_url, imagem_posicao,
             botao_label, botao_cta, status, ordem),
        )


def atualizar(newsletter_id, **campos):
    campos_validos = {
        "titulo", "head_texto", "head_estilo", "corpo_texto", "imagem_url",
        "imagem_posicao", "botao_label", "botao_cta", "status", "ordem",
    }
    sets, valores = [], []
    for k, v in campos.items():
        if k in campos_validos:
            sets.append(f"{k} = ?")
            valores.append(v)
    if not sets:
        return
    valores.append(newsletter_id)
    with db() as conn:
        conn.execute(f"UPDATE newsletters SET {', '.join(sets)} WHERE id = ?", valores)
