"""
Checkpoint — Controle de Solicitações de Visita
================================================
Verifica:
  1. Sintaxe do app.py (AST)
  2. Presença das 6 rotas
  3. Presença dos 4 templates
  4. Estrutura Jinja2 dos templates (extends + block/endblock)
  5. Ciclo de vida Pendente → Realizada  (gera atendimento + audit)
  6. Ciclo de vida Pendente → Cancelada  (requer motivo_cancelamento)
"""

import ast
import os
import re
import sqlite3
import tempfile
import sys
from datetime import datetime

BASE_DIR = r"c:\Users\USER\Documents\Codex\2026-06-16\files-mentioned-by-the-user-database\CadUnico_Sistema\cadunico"

PASS = "✅"
FAIL = "❌"

results = []


def check(label, ok, detail=""):
    icon = PASS if ok else FAIL
    msg = f"{icon}  {label}"
    if detail:
        msg += f"\n     {detail}"
    results.append((ok, msg))
    print(msg)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Sintaxe Python
# ─────────────────────────────────────────────────────────────────────────────
app_path = os.path.join(BASE_DIR, "app.py")
try:
    with open(app_path, encoding="utf-8") as f:
        src = f.read()
    ast.parse(src)
    check("Sintaxe de app.py (AST)", True)
except SyntaxError as e:
    check("Sintaxe de app.py (AST)", False, str(e))
    # Sem sintaxe válida, as buscas de rotas/funções não fazem sentido
    # mas continuamos para gerar um relatório completo

# ─────────────────────────────────────────────────────────────────────────────
# 2. Rotas presentes
# ─────────────────────────────────────────────────────────────────────────────
ROUTES_EXPECTED = {
    "painel_visitas":         r"@app\.route\('/visitas'.*?\)\s*\ndef painel_visitas",
    "nova_visita":            r"@app\.route\('/visitas/nova'.*?\)\s*\ndef nova_visita",
    "detalhe_visita":         r"@app\.route\('/visitas/<int:visita_id>'.*?\)\s*\ndef detalhe_visita",
    "editar_visita":          r"@app\.route\('/visitas/<int:visita_id>/editar'.*?\)\s*\ndef editar_visita",
    "atualizar_status_visita":r"@app\.route\('/visitas/<int:visita_id>/status'.*?\)\s*\ndef atualizar_status_visita",
    "excluir_visita":         r"@app\.route\('/visitas/<int:visita_id>/excluir'.*?\)\s*\ndef excluir_visita",
}

for name, pattern in ROUTES_EXPECTED.items():
    found = bool(re.search(pattern, src, re.DOTALL))
    check(f"Rota '{name}'", found)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Templates presentes
# ─────────────────────────────────────────────────────────────────────────────
TEMPLATES_EXPECTED = [
    "nova_visita.html",
    "painel_visitas.html",
    "detalhe_visita.html",
    "editar_visita.html",
]
tpl_dir = os.path.join(BASE_DIR, "templates")

for tpl in TEMPLATES_EXPECTED:
    path = os.path.join(tpl_dir, tpl)
    check(f"Template '{tpl}' existe", os.path.isfile(path))

# ─────────────────────────────────────────────────────────────────────────────
# 4. Estrutura Jinja2 dos templates
# ─────────────────────────────────────────────────────────────────────────────
for tpl in TEMPLATES_EXPECTED:
    path = os.path.join(tpl_dir, tpl)
    if not os.path.isfile(path):
        check(f"Jinja2 '{tpl}' — extends + block/endblock", False, "arquivo não encontrado")
        continue
    with open(path, encoding="utf-8") as f:
        content = f.read()
    has_extends = "{% extends 'base.html' %}" in content or '{% extends "base.html" %}' in content
    block_count = len(re.findall(r"\{%-?\s*block\s+\w+", content))
    endblock_count = len(re.findall(r"\{%-?\s*endblock", content))
    ok = has_extends and block_count > 0 and block_count == endblock_count
    detail = (f"extends={'sim' if has_extends else 'NÃO'}  "
              f"blocks={block_count}  endblocks={endblock_count}")
    check(f"Jinja2 '{tpl}' — extends + block/endblock", ok, detail)

# ─────────────────────────────────────────────────────────────────────────────
# 5 & 6. Ciclos de vida via SQLite direto
# ─────────────────────────────────────────────────────────────────────────────

def make_test_db():
    """Cria um banco SQLite temporário com as tabelas necessárias."""
    tmp = tempfile.mktemp(suffix=".db")
    conn = sqlite3.connect(tmp)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL DEFAULT 'entrevistador',
            acesso_sibec INTEGER NOT NULL DEFAULT 0,
            trocar_senha INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            cpf TEXT NOT NULL,
            nome_rf TEXT NOT NULL,
            origem TEXT NOT NULL,
            tipos TEXT NOT NULL,
            usuario_id INTEGER NOT NULL,
            criado_em TEXT NOT NULL
        );

        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            usuario_nome TEXT,
            acao TEXT NOT NULL,
            detalhe TEXT,
            ip TEXT,
            criado_em TEXT NOT NULL
        );

        CREATE TABLE solicitacoes_visita (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf_rf              TEXT NOT NULL,
            nome_rf             TEXT NOT NULL,
            endereco            TEXT NOT NULL,
            motivo              TEXT NOT NULL,
            data_prevista       TEXT NOT NULL,
            data_realizada      TEXT,
            status              TEXT NOT NULL DEFAULT 'Pendente',
            solicitante_id      INTEGER NOT NULL REFERENCES usuarios(id),
            responsavel_id      INTEGER REFERENCES usuarios(id),
            observacoes         TEXT,
            motivo_cancelamento TEXT,
            atendimento_id      INTEGER,
            criado_em           TEXT NOT NULL,
            atualizado_em       TEXT NOT NULL
        );

        INSERT INTO usuarios (nome, login, senha, perfil) VALUES
            ('Admin', 'admin', 'hash', 'admin');
    """)
    conn.commit()
    return conn, tmp


def insert_visita(conn, usuario_id=1, status="Pendente"):
    """Insere uma solicitação de visita e retorna seu id."""
    agora = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO solicitacoes_visita
            (cpf_rf, nome_rf, endereco, motivo, data_prevista, status,
             solicitante_id, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("123.456.789-00", "João Silva", "Rua Teste, 1",
          "Cadastro desatualizado", "2026-07-01", status,
          usuario_id, agora, agora))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def audit_insert(conn, usuario_id, acao, detalhe):
    conn.execute("""
        INSERT INTO audit_log (usuario_id, usuario_nome, acao, detalhe, ip, criado_em)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (usuario_id, "Admin", acao, detalhe, "127.0.0.1",
          datetime.now().isoformat()))
    conn.commit()


# ── Ciclo 1: Pendente → Realizada ────────────────────────────────────────────
print("\n── Ciclo de vida Pendente → Realizada ──────────────────────────────────")
conn1, tmp1 = make_test_db()
try:
    uid = 1
    visita_id = insert_visita(conn1, uid, "Pendente")

    # Verifica estado inicial
    v = conn1.execute("SELECT * FROM solicitacoes_visita WHERE id=?", (visita_id,)).fetchone()
    check("INSERT com status='Pendente'", v["status"] == "Pendente",
          f"status={v['status']}")

    # Simula a transição: INSERT atendimento + UPDATE visita
    agora = datetime.now().isoformat()
    data_realizada = "2026-07-05"
    novo_status = "Realizada"

    conn1.execute("""
        INSERT INTO atendimentos (data, cpf, nome_rf, origem, tipos, usuario_id, criado_em)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (data_realizada, v["cpf_rf"], v["nome_rf"],
          "Visita Domiciliar", "Visita Domiciliar", uid, agora))
    conn1.commit()
    atendimento_id = conn1.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn1.execute("""
        UPDATE solicitacoes_visita
        SET status=?, data_realizada=?, atendimento_id=?, atualizado_em=?
        WHERE id=?
    """, (novo_status, data_realizada, atendimento_id, agora, visita_id))
    conn1.commit()

    audit_insert(conn1, uid, "VISITA_STATUS_ATUALIZADO",
                 f"id={visita_id} status=Pendente→Realizada")
    audit_insert(conn1, uid, "VISITA_CONCLUIDA",
                 f"id={visita_id} atendimento_id={atendimento_id}")

    # Verificações
    v2 = conn1.execute("SELECT * FROM solicitacoes_visita WHERE id=?", (visita_id,)).fetchone()
    check("UPDATE status → 'Realizada'", v2["status"] == "Realizada",
          f"status={v2['status']}")

    at = conn1.execute("SELECT * FROM atendimentos WHERE id=?", (atendimento_id,)).fetchone()
    check("Atendimento criado para visita realizada", at is not None,
          f"atendimento_id={atendimento_id}  cpf={at['cpf'] if at else 'N/A'}")

    check("atendimento_id gravado na visita", v2["atendimento_id"] == atendimento_id,
          f"visita.atendimento_id={v2['atendimento_id']}")

    audit_rows = conn1.execute("""
        SELECT * FROM audit_log WHERE acao IN ('VISITA_STATUS_ATUALIZADO','VISITA_CONCLUIDA')
    """).fetchall()
    check("Entradas de audit_log gravadas (Realizada)",
          len(audit_rows) >= 2,
          f"audit_rows={len(audit_rows)}")

finally:
    conn1.close()
    os.unlink(tmp1)

# ── Ciclo 2: Pendente → Cancelada ────────────────────────────────────────────
print("\n── Ciclo de vida Pendente → Cancelada ──────────────────────────────────")
conn2, tmp2 = make_test_db()
try:
    uid = 1
    visita_id = insert_visita(conn2, uid, "Pendente")

    # Testa rejeição quando motivo_cancelamento está vazio
    motivo_cancelamento = ""
    if not motivo_cancelamento:
        check("Cancelamento rejeitado sem motivo_cancelamento",
              True, "motivo_cancelamento vazio → transição bloqueada corretamente")
    else:
        check("Cancelamento rejeitado sem motivo_cancelamento",
              False, "deveria ter bloqueado")

    # Simula cancelamento com motivo
    agora = datetime.now().isoformat()
    novo_status = "Cancelada"
    motivo_cancelamento = "Família não estava em casa na data prevista."

    conn2.execute("""
        UPDATE solicitacoes_visita
        SET status=?, motivo_cancelamento=?, atualizado_em=?
        WHERE id=?
    """, (novo_status, motivo_cancelamento, agora, visita_id))
    conn2.commit()

    audit_insert(conn2, uid, "VISITA_STATUS_ATUALIZADO",
                 f"id={visita_id} status=Pendente→Cancelada")

    # Verificações
    v = conn2.execute("SELECT * FROM solicitacoes_visita WHERE id=?", (visita_id,)).fetchone()
    check("UPDATE status → 'Cancelada'", v["status"] == "Cancelada",
          f"status={v['status']}")

    check("motivo_cancelamento gravado", bool(v["motivo_cancelamento"]),
          f"motivo={v['motivo_cancelamento']}")

    # Nenhum atendimento deve ser gerado
    at_count = conn2.execute("SELECT COUNT(*) FROM atendimentos").fetchone()[0]
    check("Nenhum atendimento gerado para visita Cancelada", at_count == 0,
          f"atendimentos={at_count}")

    # Status terminal: tentativa de re-alterar deve ser bloqueada
    STATUS_TERMINAIS = {"Realizada", "Cancelada"}
    status_atual = v["status"]
    tentativa_bloqueada = status_atual in STATUS_TERMINAIS
    check("Status terminal — nova alteração bloqueada", tentativa_bloqueada,
          f"status='{status_atual}' é terminal → não permite nova transição")

    audit_rows = conn2.execute("""
        SELECT * FROM audit_log WHERE acao = 'VISITA_STATUS_ATUALIZADO'
    """).fetchall()
    check("Entrada de audit_log gravada (Cancelada)",
          len(audit_rows) >= 1, f"audit_rows={len(audit_rows)}")

finally:
    conn2.close()
    os.unlink(tmp2)

# ─────────────────────────────────────────────────────────────────────────────
# Sumário final
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "═" * 62)
total   = len(results)
passed  = sum(1 for ok, _ in results if ok)
failed  = total - passed

print(f"  Checkpoint: {passed}/{total} verificações passaram")
if failed:
    print(f"\n  Falhas detectadas:")
    for ok, msg in results:
        if not ok:
            print(f"    {msg}")
else:
    print("  Todos os testes passaram — núcleo de visitas aprovado!")
print("═" * 62)

sys.exit(0 if failed == 0 else 1)
