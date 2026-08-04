# -*- coding: utf-8 -*-
"""
Camada de acesso ao banco de dados.

Se a variável de ambiente DATABASE_URL existir (connection string do
Postgres/Supabase), o app usa Postgres. Caso contrário, cai para um
arquivo SQLite local — útil para desenvolver e rodar os testes sem
precisar de nenhuma conta externa.

Todo o resto do código (credits.py, payouts.py, reservations.py etc.)
continua escrevendo consultas com `?` como marcador de parâmetro (estilo
SQLite) — este módulo traduz automaticamente para `%s` (estilo Postgres)
quando necessário, então nenhum desses arquivos precisou ser alterado.
"""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("CANOA_DB_PATH", os.path.join(os.path.dirname(__file__), "canoa.db"))
DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = bool(DATABASE_URL)


# =========================================================
# Schemas (um para cada backend — sintaxes de auto-incremento e
# "insere se não existir" diferem entre SQLite e Postgres)
# =========================================================

SCHEMA_SQLITE = """
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

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
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
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    plano           TEXT NOT NULL,
    valor_centavos  INTEGER NOT NULL,
    forma_pagamento TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pendente',
    payment_ref     TEXT,
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS credits (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    origem          TEXT NOT NULL,
    purchase_id     INTEGER REFERENCES purchases(id),
    validade        DATE NOT NULL,
    status          TEXT NOT NULL DEFAULT 'disponivel',
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classes (
    id                  SERIAL PRIMARY KEY,
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
    id              SERIAL PRIMARY KEY,
    class_id        INTEGER NOT NULL REFERENCES classes(id),
    user_id         INTEGER NOT NULL REFERENCES users(id),
    credit_id       INTEGER REFERENCES credits(id),
    status          TEXT NOT NULL DEFAULT 'confirmada',
    is_vaga_extra   INTEGER NOT NULL DEFAULT 0,
    criado_em       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(class_id, user_id)
);

CREATE TABLE IF NOT EXISTS payouts (
    id                  SERIAL PRIMARY KEY,
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

INSERT INTO params (chave, valor) VALUES
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
    ('preco_pacote6_centavos', '14500')
ON CONFLICT (chave) DO NOTHING;
"""


class _PGConnWrapper:
    """Faz uma conexão psycopg2 se comportar como a sqlite3.Connection
    que o resto do código já espera: `.execute(sql, params).fetchone()`,
    linhas acessíveis por nome de coluna, `.executescript()`, etc."""

    def __init__(self, raw_conn):
        self._conn = raw_conn

    def execute(self, query, params=()):
        import psycopg2.extras
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query.replace("?", "%s"), params)
        return cur

    def executescript(self, sql):
        cur = self._conn.cursor()
        cur.execute(sql)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def _ensure_sslmode(url):
    if "sslmode=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}sslmode=require"


def get_connection():
    if IS_POSTGRES:
        import psycopg2
        raw = psycopg2.connect(_ensure_sslmode(DATABASE_URL))
        return _PGConnWrapper(raw)
    else:
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
    schema = SCHEMA_POSTGRES if IS_POSTGRES else SCHEMA_SQLITE
    with db() as conn:
        conn.executescript(schema)


def get_param(chave, default=None, cast=str):
    with db() as conn:
        row = conn.execute("SELECT valor FROM params WHERE chave = ?", (chave,)).fetchone()
    if row is None:
        return default
    return cast(row["valor"])


def insert_returning_id(conn, query, params):
    """
    Executa um INSERT e devolve o id gerado — funciona tanto em SQLite
    quanto em Postgres (que não tem `cursor.lastrowid`).
    """
    if IS_POSTGRES:
        cur = conn.execute(query + " RETURNING id", params)
        return cur.fetchone()["id"]
    else:
        cur = conn.execute(query, params)
        return cur.lastrowid
