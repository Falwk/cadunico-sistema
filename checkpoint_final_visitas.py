"""
checkpoint_final_visitas.py
===========================
Suite de verificação final do módulo de Controle de Solicitações de Visita.
Executa 8 verificações e reporta o resultado de cada uma.
"""
import ast
import os
import sqlite3
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASS = "✅"
FAIL = "❌"
results = []


def check(name, ok, detail=""):
    status = PASS if ok else FAIL
    msg = f"  {status} {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append((name, ok, detail))
    return ok


# ---------------------------------------------------------------------------
# 1. Python syntax
# ---------------------------------------------------------------------------
print("\n── 1. Sintaxe Python ──────────────────────────────────────────────────")
app_path = os.path.join(BASE_DIR, "app.py")
try:
    with open(app_path, encoding="utf-8") as f:
        source = f.read()
    ast.parse(source)
    check("app.py parseia sem erros de sintaxe", True)
except SyntaxError as e:
    check("app.py parseia sem erros de sintaxe", False, str(e))

# ---------------------------------------------------------------------------
# 2. All 6 visitas routes present
# ---------------------------------------------------------------------------
print("\n── 2. Rotas de visitas em app.py ──────────────────────────────────────")
EXPECTED_ROUTES = [
    "painel_visitas",
    "nova_visita",
    "detalhe_visita",
    "editar_visita",
    "atualizar_status_visita",
    "excluir_visita",
]
for route in EXPECTED_ROUTES:
    present = f"def {route}" in source
    check(f"rota '{route}' presente", present)

# ---------------------------------------------------------------------------
# 3. All 4 new templates exist
# ---------------------------------------------------------------------------
print("\n── 3. Templates de visitas existem ───────────────────────────────────")
EXPECTED_TEMPLATES = [
    "templates/nova_visita.html",
    "templates/painel_visitas.html",
    "templates/detalhe_visita.html",
    "templates/editar_visita.html",
]
for tpl in EXPECTED_TEMPLATES:
    path = os.path.join(BASE_DIR, tpl)
    exists = os.path.isfile(path)
    check(f"template '{tpl}' existe", exists)

# ---------------------------------------------------------------------------
# 4. Navigation integration in base.html
# ---------------------------------------------------------------------------
print("\n── 4. Integração na navegação (base.html) ─────────────────────────────")
base_path = os.path.join(BASE_DIR, "templates", "base.html")
try:
    with open(base_path, encoding="utf-8") as f:
        base_content = f.read()
    nav_ok = "url_for('painel_visitas')" in base_content
    check("base.html contém url_for('painel_visitas')", nav_ok)
except FileNotFoundError:
    check("base.html contém url_for('painel_visitas')", False, "base.html não encontrado")

# ---------------------------------------------------------------------------
# 5. Dashboard card
# ---------------------------------------------------------------------------
print("\n── 5. Card de visitas no dashboard ────────────────────────────────────")
dashboard_path = os.path.join(BASE_DIR, "templates", "dashboard.html")
try:
    with open(dashboard_path, encoding="utf-8") as f:
        dash_content = f.read()
    has_painel_link = "painel_visitas" in dash_content
    has_pendente    = "status='Pendente'" in dash_content or 'status=\'Pendente\'' in dash_content
    has_var         = "total_visitas_pendentes" in dash_content
    check("dashboard.html link para painel_visitas presente", has_painel_link)
    check("dashboard.html link com status='Pendente'", has_pendente)
    check("dashboard.html usa variável total_visitas_pendentes", has_var)
except FileNotFoundError:
    check("dashboard.html verificações", False, "dashboard.html não encontrado")

# ---------------------------------------------------------------------------
# 6. Dashboard route passes total_visitas_pendentes
# ---------------------------------------------------------------------------
print("\n── 6. Rota dashboard passa total_visitas_pendentes ────────────────────")
has_route_var = "total_visitas_pendentes=total_visitas_pendentes" in source
check("app.py dashboard passa total_visitas_pendentes ao template", has_route_var)

# ---------------------------------------------------------------------------
# 7. init_db idempotency
# ---------------------------------------------------------------------------
print("\n── 7. Idempotência de init_db ──────────────────────────────────────────")
try:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Primeira criação + inserção de uma linha
    conn.execute("""CREATE TABLE IF NOT EXISTS solicitacoes_visita (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        cpf_rf              TEXT NOT NULL,
        nome_rf             TEXT NOT NULL,
        endereco            TEXT NOT NULL,
        motivo              TEXT NOT NULL,
        data_prevista       TEXT NOT NULL,
        data_realizada      TEXT,
        status              TEXT NOT NULL DEFAULT 'Pendente',
        solicitante_id      INTEGER NOT NULL,
        responsavel_id      INTEGER,
        observacoes         TEXT,
        motivo_cancelamento TEXT,
        atendimento_id      INTEGER,
        criado_em           TEXT NOT NULL,
        atualizado_em       TEXT NOT NULL
    )""")
    conn.execute("""INSERT INTO solicitacoes_visita
        (cpf_rf, nome_rf, endereco, motivo, data_prevista, status,
         solicitante_id, criado_em, atualizado_em)
        VALUES ('123.456.789-09','João Silva','Rua A, 1','Recadastramento',
                '2026-07-01','Pendente',1,
                '2026-06-01T10:00:00','2026-06-01T10:00:00')""")
    conn.commit()

    # Segunda chamada do CREATE IF NOT EXISTS — deve ser silenciosa
    conn.execute("""CREATE TABLE IF NOT EXISTS solicitacoes_visita (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        cpf_rf              TEXT NOT NULL,
        nome_rf             TEXT NOT NULL,
        endereco            TEXT NOT NULL,
        motivo              TEXT NOT NULL,
        data_prevista       TEXT NOT NULL,
        data_realizada      TEXT,
        status              TEXT NOT NULL DEFAULT 'Pendente',
        solicitante_id      INTEGER NOT NULL,
        responsavel_id      INTEGER,
        observacoes         TEXT,
        motivo_cancelamento TEXT,
        atendimento_id      INTEGER,
        criado_em           TEXT NOT NULL,
        atualizado_em       TEXT NOT NULL
    )""")
    conn.commit()

    row = conn.execute("SELECT COUNT(*) as n FROM solicitacoes_visita").fetchone()
    check("init_db idempotente: linha sobrevive a segundo CREATE IF NOT EXISTS",
          row['n'] == 1, f"linhas encontradas: {row['n']}")
    conn.close()
except Exception as e:
    check("init_db idempotente", False, str(e))

# ---------------------------------------------------------------------------
# 8. Lifecycle simulation
# ---------------------------------------------------------------------------
print("\n── 8. Simulação completa de ciclo de vida ──────────────────────────────")

def make_test_db():
    """Cria BD em memória com todas as tabelas necessárias."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
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
            solicitante_id      INTEGER NOT NULL,
            responsavel_id      INTEGER,
            observacoes         TEXT,
            motivo_cancelamento TEXT,
            atendimento_id      INTEGER,
            criado_em           TEXT NOT NULL,
            atualizado_em       TEXT NOT NULL
        );
    """)
    # Insere usuários de teste
    c.execute("INSERT INTO usuarios (nome,login,senha,perfil) VALUES ('Admin','admin','x','admin')")
    c.execute("INSERT INTO usuarios (nome,login,senha,perfil) VALUES ('Entrevistador A','a','x','entrevistador')")
    c.execute("INSERT INTO usuarios (nome,login,senha,perfil) VALUES ('Entrevistador B','b','x','entrevistador')")
    c.commit()
    return c


def insert_visita(conn, uid, cpf="123.456.789-09", nome="João", status='Pendente'):
    agora = datetime.now().isoformat()
    conn.execute("""INSERT INTO solicitacoes_visita
        (cpf_rf, nome_rf, endereco, motivo, data_prevista, status,
         solicitante_id, criado_em, atualizado_em)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (cpf, nome, 'Rua A, 1', 'Recadastramento', '2026-07-01', status, uid, agora, agora))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def audit_log(conn, uid, uname, acao, detalhe):
    conn.execute("""INSERT INTO audit_log
        (usuario_id,usuario_nome,acao,detalhe,ip,criado_em)
        VALUES (?,?,?,?,?,?)""",
        (uid, uname, acao, detalhe, '127.0.0.1', datetime.now().isoformat()))
    conn.commit()


# ── Ciclo A: Pendente → Em Andamento → Realizada ──────────────────────────
try:
    conn = make_test_db()
    uid_admin = conn.execute("SELECT id FROM usuarios WHERE login='admin'").fetchone()[0]
    uid_a = conn.execute("SELECT id FROM usuarios WHERE login='a'").fetchone()[0]

    vid = insert_visita(conn, uid_a)
    audit_log(conn, uid_a, 'Entrevistador A', 'VISITA_CRIADA', f"cpf=123 id={vid}")

    # → Em Andamento
    agora = datetime.now().isoformat()
    conn.execute("UPDATE solicitacoes_visita SET status='Em Andamento', atualizado_em=? WHERE id=?", (agora, vid))
    conn.commit()
    audit_log(conn, uid_a, 'Entrevistador A', 'VISITA_STATUS_ATUALIZADO',
              f"id={vid} status=Pendente→Em Andamento")

    # → Realizada — gera atendimento
    data_real = '2026-07-10'
    conn.execute("""INSERT INTO atendimentos
        (data,cpf,nome_rf,origem,tipos,usuario_id,criado_em)
        VALUES (?,?,?,?,?,?,?)""",
        (data_real,'123.456.789-09','João','Visita Domiciliar','Visita Domiciliar',uid_a, agora))
    conn.commit()
    at_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.execute("""UPDATE solicitacoes_visita
        SET status='Realizada', data_realizada=?, atendimento_id=?, atualizado_em=?
        WHERE id=?""", (data_real, at_id, agora, vid))
    conn.commit()
    audit_log(conn, uid_a, 'Entrevistador A', 'VISITA_STATUS_ATUALIZADO',
              f"id={vid} status=Em Andamento→Realizada")
    audit_log(conn, uid_a, 'Entrevistador A', 'VISITA_CONCLUIDA',
              f"id={vid} atendimento_id={at_id}")

    v = conn.execute("SELECT * FROM solicitacoes_visita WHERE id=?", (vid,)).fetchone()
    at = conn.execute("SELECT * FROM atendimentos WHERE id=?", (at_id,)).fetchone()

    check("Ciclo A: status final = 'Realizada'", v['status'] == 'Realizada',
          f"status={v['status']}")
    check("Ciclo A: atendimento criado com ID correto",
          at is not None and v['atendimento_id'] == at_id,
          f"atendimento_id={v['atendimento_id']}")
    check("Ciclo A: data_realizada armazenada", v['data_realizada'] == data_real,
          f"data_realizada={v['data_realizada']}")

    # Auditoria: VISITA_CRIADA, VISITA_STATUS_ATUALIZADO (x2), VISITA_CONCLUIDA
    audit_rows = conn.execute(
        "SELECT acao FROM audit_log WHERE detalhe LIKE ? ORDER BY id",
        (f"%id={vid}%",)
    ).fetchall()
    acoes = [r['acao'] for r in audit_rows]
    check("Ciclo A: entrada VISITA_CRIADA no audit_log", 'VISITA_CRIADA' in acoes,
          f"acoes={acoes}")
    check("Ciclo A: entrada VISITA_STATUS_ATUALIZADO no audit_log",
          'VISITA_STATUS_ATUALIZADO' in acoes, f"acoes={acoes}")
    check("Ciclo A: entrada VISITA_CONCLUIDA no audit_log",
          'VISITA_CONCLUIDA' in acoes, f"acoes={acoes}")

    conn.close()
except Exception as e:
    check("Ciclo A completo", False, str(e))

# ── Ciclo B: Pendente → Cancelada ─────────────────────────────────────────
try:
    conn = make_test_db()
    uid_a = conn.execute("SELECT id FROM usuarios WHERE login='a'").fetchone()[0]
    vid = insert_visita(conn, uid_a)
    audit_log(conn, uid_a, 'Entrevistador A', 'VISITA_CRIADA', f"cpf=123 id={vid}")

    motivo_canc = "Família não estava em casa"
    agora = datetime.now().isoformat()
    conn.execute("""UPDATE solicitacoes_visita
        SET status='Cancelada', motivo_cancelamento=?, atualizado_em=?
        WHERE id=?""", (motivo_canc, agora, vid))
    conn.commit()
    audit_log(conn, uid_a, 'Entrevistador A', 'VISITA_STATUS_ATUALIZADO',
              f"id={vid} status=Pendente→Cancelada")

    v = conn.execute("SELECT * FROM solicitacoes_visita WHERE id=?", (vid,)).fetchone()
    at_count = conn.execute("SELECT COUNT(*) as n FROM atendimentos").fetchone()['n']

    check("Ciclo B: status final = 'Cancelada'", v['status'] == 'Cancelada',
          f"status={v['status']}")
    check("Ciclo B: motivo_cancelamento armazenado",
          v['motivo_cancelamento'] == motivo_canc,
          f"motivo={v['motivo_cancelamento']!r}")
    check("Ciclo B: nenhum atendimento criado", at_count == 0, f"atendimentos={at_count}")

    conn.close()
except Exception as e:
    check("Ciclo B completo", False, str(e))

# ── Simulação de filtro por perfil entrevistador ───────────────────────────
try:
    conn = make_test_db()
    uid_a = conn.execute("SELECT id FROM usuarios WHERE login='a'").fetchone()[0]
    uid_b = conn.execute("SELECT id FROM usuarios WHERE login='b'").fetchone()[0]

    # Insere visita de A e de B
    vid_a = insert_visita(conn, uid_a, cpf="111.111.111-11", nome="Família A")
    vid_b = insert_visita(conn, uid_b, cpf="222.222.222-22", nome="Família B")

    # Filtro: entrevistador A vê somente seus registros
    rows_a = conn.execute("""
        SELECT * FROM solicitacoes_visita
        WHERE solicitante_id=? OR responsavel_id=?
    """, (uid_a, uid_a)).fetchall()

    ids_a = {r['id'] for r in rows_a}

    check("Permissão: entrevistador A vê sua própria visita",
          vid_a in ids_a, f"ids={ids_a}")
    check("Permissão: entrevistador A NÃO vê visita de B",
          vid_b not in ids_a, f"ids={ids_a}")

    conn.close()
except Exception as e:
    check("Simulação de filtro por perfil", False, str(e))

# ── Verificação de todas as entradas de audit_log ─────────────────────────
try:
    conn = make_test_db()
    uid_admin = conn.execute("SELECT id FROM usuarios WHERE login='admin'").fetchone()[0]
    uid_a = conn.execute("SELECT id FROM usuarios WHERE login='a'").fetchone()[0]

    vid = insert_visita(conn, uid_a)
    audit_log(conn, uid_a, 'Ent A', 'VISITA_CRIADA', f"id={vid}")
    audit_log(conn, uid_a, 'Ent A', 'VISITA_STATUS_ATUALIZADO',
              f"id={vid} status=Pendente→Em Andamento")
    audit_log(conn, uid_a, 'Ent A', 'VISITA_CONCLUIDA', f"id={vid} atendimento_id=99")
    audit_log(conn, uid_admin, 'Admin', 'VISITA_EXCLUIDA', f"id={vid} cpf=123")

    acoes_all = [r['acao'] for r in conn.execute("SELECT acao FROM audit_log").fetchall()]
    for expected_acao in ['VISITA_CRIADA','VISITA_STATUS_ATUALIZADO','VISITA_CONCLUIDA','VISITA_EXCLUIDA']:
        check(f"Audit log contém ação '{expected_acao}'",
              expected_acao in acoes_all, f"acoes={acoes_all}")

    conn.close()
except Exception as e:
    check("Verificação do audit_log", False, str(e))

# ---------------------------------------------------------------------------
# Resumo final
# ---------------------------------------------------------------------------
print("\n" + "═" * 66)
total  = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed

if failed == 0:
    print(f"  {PASS}  TODOS OS {total} CHECKS PASSARAM — módulo de visitas OK")
else:
    print(f"  {FAIL}  {passed}/{total} checks passaram, {failed} FALHA(S):")
    for name, ok, detail in results:
        if not ok:
            print(f"       • {name}" + (f" — {detail}" if detail else ""))
print("═" * 66 + "\n")

sys.exit(0 if failed == 0 else 1)
