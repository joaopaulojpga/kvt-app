# -*- coding: utf-8 -*-
"""
Camada de acesso ao banco de dados.

Hoje aponta para um arquivo SQLite local (bom para desenvolver e testar
sem depender de nenhuma conta externa). Quando a conta do Supabase for
criada, basta trocar a implementação de `get_connection()` para usar
psycopg2/SQLAlchemy apontando para a connection string do Postgres —
o restante do código (os outros arquivos .py) não muda, porque só fala
com este módulo.
"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("CANOA_DB_PATH", os.path.join(os.path.dirname(__file__), "canoa.db"))

# Schema embutido aqui (em vez de um arquivo .sql separado) para que o
# projeto inteiro funcione com uma estrutura de pastas totalmente plana
# — importante porque uploads de pasta pelo navegador (GitHub) às vezes
# não preservam subpastas corretamente.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nome            TEXT NOT NULL,
    sexo            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    senha_hash      TEXT NOT NULL,
    cpf             TEXT NOT NULL UNIQUE,
    celular         TEXT NOT NULL,
    instagram       TEXT,
    foto_url        TEXT,
    role            TEXT NOT NULL DEFAULT 'aluno',
    ativo           INTEGER NOT NULL DEFAULT 1,
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    plano           TEXT NOT NULL,
    valor_centavos  INTEGER NOT NULL,
    forma_pagamento TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pendente',
    payment_ref     TEXT,
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS credits (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    origem          TEXT NOT NULL,
    purchase_id     INTEGER REFERENCES purchases(id),
    validade        DATE NOT NULL,
    status          TEXT NOT NULL DEFAULT 'disponivel',
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    data                DATE NOT NULL,
    horario             TEXT NOT NULL,
    tipo                TEXT NOT NULL DEFAULT 'treino',
    vagas_base          INTEGER NOT NULL DEFAULT 12,
    vagas_max           INTEGER NOT NULL DEFAULT 18,
    instrutor_resp_id   INTEGER NOT NULL REFERENCES users(id),
    instrutor2_id       INTEGER REFERENCES users(id),
    status              TEXT NOT NULL DEFAULT 'agendada',
    criado_em           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reservations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id        INTEGER NOT NULL REFERENCES classes(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    credit_id       INTEGER REFERENCES credits(id),
    status          TEXT NOT NULL DEFAULT 'confirmada',
    is_vaga_extra   INTEGER NOT NULL DEFAULT 0,
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_id, user_id)
);

CREATE TABLE IF NOT EXISTS payouts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id            INTEGER NOT NULL REFERENCES classes(id),
    instrutor_id        INTEGER NOT NULL REFERENCES users(id),
    remadores_atribuidos INTEGER NOT NULL,
    valor_centavos      INTEGER NOT NULL,
    criado_em           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS params (
    chave   TEXT PRIMARY KEY,
    valor   TEXT NOT NULL
);

INSERT OR IGNORE INTO params (chave, valor) VALUES
    ('valor_aula_centavos', '3500'),
    ('taxa_fixa_instrutor_centavos', '2500'),
    ('taxa_por_remador_centavos', '500'),
    ('teto_remadores_calculo', '10'),
    ('limite_remadores_por_instrutor', '12'),
    ('vagas_base', '12'),
    ('vagas_max', '18'),
    ('validade_credito_dias', '30'),
    ('validade_extra_suspensao_dias', '7'),
    ('horas_limite_cancelamento', '12'),
    ('preco_avulsa_centavos', '3500'),
    ('preco_pacote4_centavos', '10500'),
    ('preco_pacote6_centavos', '14500');
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Cria as tabelas se ainda não existirem (idempotente)."""
    with db() as conn:
        conn.executescript(SCHEMA_SQL)


def get_param(chave, default=None, cast=str):
    with db() as conn:
        row = conn.execute("SELECT valor FROM params WHERE chave = ?", (chave,)).fetchone()
    if row is None:
        return default
    return cast(row["valor"])
