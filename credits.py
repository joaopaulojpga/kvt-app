# -*- coding: utf-8 -*-
"""
CreditService — único ponto autorizado a alterar o saldo de créditos.

Cobre: emissão de crédito (compra online OU lançamento manual do gestor —
mesma função, mesma lógica, sem caminhos duplicados), validade de 30 dias
corridos, consumo no check-in/expansão, devolução com +7 dias quando a
turma é suspensa (clima/quórum) ou cancelada pelo instrutor.

Toda alteração de saldo grava uma linha em `credit_transactions` (Ledger
imutável, nunca editado/apagado) na MESMA transação de banco que altera
`credits` — nenhuma função fora deste módulo escreve nessas duas tabelas.
O saldo em si continua sendo calculado a partir de `credits` (cada linha =
1 crédito individual, com sua própria validade — é o que permite o FIFO de
expiração); o Ledger existe para auditoria e histórico, não substitui essa
contagem.
"""
from datetime import date, timedelta
from db import db, get_param


def _validade_padrao(hoje=None):
    hoje = hoje or date.today()
    dias = get_param("validade_credito_dias", 30, int)
    return hoje + timedelta(days=dias)


def _saldo_disponivel_conn(conn, user_id, hoje_iso):
    """Igual a saldo_disponivel(), mas reaproveitando uma conexão já aberta
    — usado internamente para ler o saldo_anterior/posterior na MESMA
    transação da escrita, sem correr risco de leitura fora de sincronia."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM credits WHERE user_id = ? AND status = 'disponivel' AND validade >= ?",
        (user_id, hoje_iso),
    ).fetchone()
    return row["n"]


def _registrar_transacao(conn, user_id, tipo_movimentacao, tipo_operacao, quantidade,
                          saldo_anterior, saldo_posterior, purchase_id=None, reservation_id=None,
                          forma_pagamento=None, usuario_responsavel_id=None, observacoes=None):
    conn.execute(
        "INSERT INTO credit_transactions (user_id, tipo_movimentacao, tipo_operacao, "
        "quantidade_creditos, saldo_anterior, saldo_posterior, purchase_id, reservation_id, "
        "forma_pagamento, usuario_responsavel_id, observacoes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (user_id, tipo_movimentacao, tipo_operacao, quantidade, saldo_anterior, saldo_posterior,
         purchase_id, reservation_id, forma_pagamento, usuario_responsavel_id, observacoes),
    )


def emitir_creditos(user_id, plano, purchase_id, quantidade, hoje=None,
                     tipo_movimentacao="compra_online", forma_pagamento=None,
                     usuario_responsavel_id=None, observacoes=None):
    """
    Único ponto de entrada para CONCEDER créditos — usado tanto pela
    confirmação de pagamento online (webhook do Asaas, `tipo_movimentacao`
    padrão "compra_online") quanto pelo lançamento manual do gestor em
    "Movimentações" (venda_offline, cortesia, reposicao, reagendamento,
    ajuste_manual). Mesma função, mesma lógica — nunca duplicar este
    caminho. Sempre grava uma linha no Ledger.
    """
    hoje = hoje or date.today()
    hoje_iso = hoje.isoformat()
    validade = _validade_padrao(hoje)
    with db() as conn:
        expirar_creditos_vencidos(conn, hoje_iso)
        saldo_antes = _saldo_disponivel_conn(conn, user_id, hoje_iso)
        for _ in range(quantidade):
            conn.execute(
                "INSERT INTO credits (user_id, origem, purchase_id, validade, status) "
                "VALUES (?, ?, ?, ?, 'disponivel')",
                (user_id, plano, purchase_id, validade.isoformat()),
            )
        saldo_depois = saldo_antes + quantidade
        _registrar_transacao(
            conn, user_id, tipo_movimentacao, "entrada", quantidade, saldo_antes, saldo_depois,
            purchase_id=purchase_id, forma_pagamento=forma_pagamento,
            usuario_responsavel_id=usuario_responsavel_id, observacoes=observacoes,
        )


def saldo_disponivel(user_id, hoje=None):
    """Quantidade de créditos disponíveis e não vencidos."""
    hoje = (hoje or date.today()).isoformat()
    with db() as conn:
        expirar_creditos_vencidos(conn, hoje)
        return _saldo_disponivel_conn(conn, user_id, hoje)


def proxima_validade(user_id, hoje=None):
    hoje = (hoje or date.today()).isoformat()
    with db() as conn:
        row = conn.execute(
            "SELECT MIN(validade) AS v FROM credits "
            "WHERE user_id = ? AND status = 'disponivel' AND validade >= ?",
            (user_id, hoje),
        ).fetchone()
    return row["v"]


def expirar_creditos_vencidos(conn, hoje_iso):
    """Marca como 'expirado' créditos disponíveis cuja validade já passou."""
    conn.execute(
        "UPDATE credits SET status = 'expirado' "
        "WHERE status = 'disponivel' AND validade < ?",
        (hoje_iso,),
    )


def consumir_um_credito(user_id, hoje=None, reservation_id=None):
    """
    Consome o crédito de validade mais próxima (evita desperdício).
    Retorna o id do crédito consumido, ou None se não houver saldo.
    """
    hoje_iso = (hoje or date.today()).isoformat()
    with db() as conn:
        expirar_creditos_vencidos(conn, hoje_iso)
        saldo_antes = _saldo_disponivel_conn(conn, user_id, hoje_iso)
        row = conn.execute(
            "SELECT id FROM credits WHERE user_id = ? AND status = 'disponivel' AND validade >= ? "
            "ORDER BY validade ASC LIMIT 1",
            (user_id, hoje_iso),
        ).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE credits SET status = 'consumido' WHERE id = ?", (row["id"],))
        _registrar_transacao(
            conn, user_id, "reserva", "saida", 1, saldo_antes, saldo_antes - 1,
            reservation_id=reservation_id,
        )
        return row["id"]


def devolver_credito(credit_id, motivo_extensao=True, hoje=None, user_id=None, reservation_id=None):
    """
    Devolve um crédito consumido (cancelamento pelo instrutor ou turma
    suspensa por clima/quórum). Quando `motivo_extensao` é True, soma
    +7 dias de validade a partir de hoje (regra de negócio confirmada).
    `user_id` é usado só para o registro no Ledger — se não vier, é
    buscado a partir do próprio crédito.
    """
    hoje = hoje or date.today()
    hoje_iso = hoje.isoformat()
    with db() as conn:
        if user_id is None:
            linha = conn.execute("SELECT user_id FROM credits WHERE id = ?", (credit_id,)).fetchone()
            user_id = linha["user_id"] if linha else None

        saldo_antes = _saldo_disponivel_conn(conn, user_id, hoje_iso) if user_id else None

        if motivo_extensao:
            dias_extra = get_param("validade_extra_suspensao_dias", 7, int)
            nova_validade = hoje + timedelta(days=dias_extra)
            conn.execute(
                "UPDATE credits SET status = 'disponivel', validade = ? WHERE id = ?",
                (nova_validade.isoformat(), credit_id),
            )
        else:
            conn.execute("UPDATE credits SET status = 'disponivel' WHERE id = ?", (credit_id,))

        if user_id:
            _registrar_transacao(
                conn, user_id, "estorno", "entrada", 1, saldo_antes, saldo_antes + 1,
                reservation_id=reservation_id,
            )


def listar_movimentacoes(user_id, limite=None):
    """Ledger completo (mais recente primeiro) de um aluno — usado nas
    telas 'Histórico' (autoatendimento) e 'Movimentações' (gestor)."""
    sql = (
        "SELECT ct.*, u.nome AS responsavel_nome FROM credit_transactions ct "
        "LEFT JOIN users u ON u.id = ct.usuario_responsavel_id "
        "WHERE ct.user_id = ? ORDER BY ct.criado_em DESC, ct.id DESC"
    )
    if limite:
        sql += f" LIMIT {int(limite)}"
    with db() as conn:
        rows = conn.execute(sql, (user_id,)).fetchall()
    return [dict(r) for r in rows]


def registrar_falta_consome_credito():
    """
    Documenta a regra: falta do aluno NÃO devolve o crédito.
    Nada a fazer aqui — o crédito já foi consumido no check-in e
    permanece 'consumido'. Função mantida por clareza de leitura do
    código (ver lib/attendance.py, que marca a reserva como 'faltou'
    sem tocar em lib/credits.py).
    """
    return None
