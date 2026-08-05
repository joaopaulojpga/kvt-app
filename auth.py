# -*- coding: utf-8 -*-
"""
Autenticação simples baseada em usuário/senha com hash local.

Nota para quando migrarmos para o Supabase: o Supabase Auth resolve
isso de forma mais robusta e seria o recomendado em produção (troca de
senha, confirmação de e-mail, login social). Este módulo é suficiente
para o MVP funcionar de ponta a ponta enquanto essa conta não existe.
"""
import hashlib
import os
from db import db

_SALT = os.environ.get("CANOA_PASSWORD_SALT", "canoa-clube-mvp")


def _hash(senha: str) -> str:
    return hashlib.sha256((_SALT + senha).encode("utf-8")).hexdigest()


def cadastrar_usuario(nome, sexo, email, senha, cpf, celular, instagram=None, role="aluno"):
    with db() as conn:
        existente = conn.execute("SELECT id FROM users WHERE email = ? OR cpf = ?", (email, cpf)).fetchone()
        if existente:
            raise ValueError("Já existe um cadastro com este e-mail ou CPF.")
        conn.execute(
            "INSERT INTO users (nome, sexo, email, senha_hash, cpf, celular, instagram, role) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (nome, sexo, email, _hash(senha), cpf, celular, instagram, role),
        )
        user_id = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]
    import whatsapp
    whatsapp.notificar_cadastro(nome, celular)
    return user_id


def autenticar(email, senha):
    with db() as conn:
        row = conn.execute(
            "SELECT id, nome, role, senha_hash, ativo FROM users WHERE email = ?", (email,)
        ).fetchone()
    if row is None or row["senha_hash"] != _hash(senha) or not row["ativo"]:
        return None
    return {"id": row["id"], "nome": row["nome"], "role": row["role"]}


def atualizar_perfil(user_id, **campos):
    # "email" propositalmente fora daqui: o e-mail é o identificador de
    # login do usuário e não pode ser alterado por esta função, mesmo
    # que alguém passe email=... por engano em uma chamada futura.
    campos_validos = {
        "nome", "sexo", "cpf", "celular", "instagram", "foto_url",
        "data_nascimento", "cep", "endereco_numero",
    }
    sets, valores = [], []
    for k, v in campos.items():
        if k in campos_validos:
            sets.append(f"{k} = ?")
            valores.append(v)
    if not sets:
        return
    valores.append(user_id)
    with db() as conn:
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", valores)


def get_usuario(user_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None
