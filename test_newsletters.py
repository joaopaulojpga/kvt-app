# -*- coding: utf-8 -*-
"""Testa o CRUD de newsletters (Configurações > Newsletter e o carrossel)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["CANOA_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test_newsletters.db")

from db import init_db  # noqa: E402
import newsletters  # noqa: E402


def approx(a, b, msg=""):
    assert a == b, f"{msg} — esperado {b}, obtido {a}"


init_db()

# ---- criação e listagem ----
approx(newsletters.listar_ativas(), [], "não deveria haver newsletters ainda")

id1 = newsletters.criar(
    titulo="Bem-vindo", head_texto="Reme com a gente", head_estilo="Título grande",
    corpo_texto="Texto curto.", imagem_url=None, imagem_posicao="center",
    botao_label="Cadastre-se", botao_cta="rolar_cadastro", status="ativo",
)
id2 = newsletters.criar(
    titulo="Onde estamos", head_texto="Venha nos visitar", head_estilo="Destaque",
    corpo_texto="Texto bem mais longo " * 10, imagem_url=None, imagem_posicao="center",
    botao_label="Ver no mapa", botao_cta="abrir_mapa", status="inativo",
)

ativas = newsletters.listar_ativas()
approx(len(ativas), 1, "só a newsletter ativa deveria aparecer no carrossel")
approx(ativas[0]["id"], id1)

todas = newsletters.listar_todas()
approx(len(todas), 2, "a tela de gestão deveria listar todas, ativas e inativas")

# ---- edição ----
newsletters.atualizar(id2, status="ativo", botao_label="Como chegar")
item2 = newsletters.obter(id2)
approx(item2["status"], "ativo")
approx(item2["botao_label"], "Como chegar")
approx(len(newsletters.listar_ativas()), 2, "após ativar, as duas deveriam aparecer no carrossel")

# ---- e-mail/campos protegidos não existem aqui, mas confere que campo inválido é ignorado ----
newsletters.atualizar(id1, campo_que_nao_existe="xyz", titulo="Bem-vindo ao clube")
approx(newsletters.obter(id1)["titulo"], "Bem-vindo ao clube")

print("OK — CRUD de newsletters (criar, listar ativas/todas, editar, ativar/desativar).")

# ---- seed inicial (6 slides reais) ----
criados = newsletters.seed_newsletters_iniciais()
approx(criados, 0, "não deveria semear de novo — a tabela já tinha newsletters dos testes acima")

# limpa a tabela (via SQL direto) pra simular um banco novo e testar o seed de verdade
from db import db as _db
with _db() as conn:
    conn.execute("DELETE FROM newsletters")

criados2 = newsletters.seed_newsletters_iniciais()
approx(criados2, 6, "deveria criar os 6 slides iniciais em uma tabela vazia")
approx(len(newsletters.listar_ativas()), 6)

slide6 = next(n for n in newsletters.listar_todas() if n["titulo"] == "Faça parte da comunidade")
approx(slide6["botao_cta"], "abrir_link")
approx(slide6["link_url"], "https://www.instagram.com/kalani_vaa/")

# rodar de novo não duplica
criados3 = newsletters.seed_newsletters_iniciais()
approx(criados3, 0, "não deveria duplicar os slides num segundo boot")
approx(len(newsletters.listar_todas()), 6)
print("OK — seed dos 6 slides iniciais funciona e é idempotente (não duplica em redeploys).")

print("\nTodos os testes de newsletters passaram.")
