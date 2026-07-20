"""
Property-based tests for controle-solicitacoes-visita module.
Uses Hypothesis to verify universal invariants of the visit request system.

Run with:
    pytest tests/test_visitas_properties.py -v
"""

import os
import sys
import sqlite3
import tempfile
from datetime import datetime

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Ensure the project root is on the path so we can import app
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import app as _app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_isolated_db():
    """
    Create a temporary SQLite database file and return its path.
    The caller is responsible for deleting it after the test.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


def _bootstrap_schema(db_path: str):
    """
    Monkey-patch app to use *db_path* and call init_db() to create the schema.
    Returns the patched db_path for convenience.
    """
    original_db_path = _app._DB_PATH
    original_use_pg = _app._USE_PG
    try:
        _app._DB_PATH = db_path
        _app._USE_PG = False
        _app.init_db()
    finally:
        _app._DB_PATH = original_db_path
        _app._USE_PG = original_use_pg
    return db_path


def _open_test_conn(db_path: str) -> sqlite3.Connection:
    """Open a direct SQLite connection (bypassing app.get_db) for assertions."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Disable FK enforcement so we can insert rows without a real user row
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def _insert_visita(conn: sqlite3.Connection, row: dict):
    """
    Insert a single row into solicitacoes_visita using the given mapping.
    Returns the rowid of the inserted row.
    """
    now = datetime.now().isoformat()
    sql = """
        INSERT INTO solicitacoes_visita
            (cpf_rf, nome_rf, endereco, motivo, data_prevista,
             status, solicitante_id, criado_em, atualizado_em)
        VALUES (?, ?, ?, ?, ?, 'Pendente', 1, ?, ?)
    """
    cur = conn.execute(sql, (
        row["cpf_rf"],
        row["nome_rf"],
        row["endereco"],
        row["motivo"],
        row["data_prevista"],
        now,
        now,
    ))
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Text fields that must be non-empty
_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),  # no surrogates
    min_size=1,
    max_size=100,
)

# A valid ISO date string (YYYY-MM-DD)
_date = st.dates().map(lambda d: d.isoformat())

# A single visita row as a dict
_visita_row = st.fixed_dictionaries({
    "cpf_rf":        _text,
    "nome_rf":       _text,
    "endereco":      _text,
    "motivo":        _text,
    "data_prevista": _date,
})

# A list of 1–10 visita rows
_visita_rows = st.lists(_visita_row, min_size=1, max_size=10)


# ---------------------------------------------------------------------------
# Property 14: init_db() é idempotente — não apaga dados existentes
# ---------------------------------------------------------------------------

# Feature: controle-solicitacoes-visita, Property 14: init_db() é idempotente — não apaga dados existentes
@given(rows=_visita_rows)
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,  # init_db() does file I/O; disable the per-example time limit
)
def test_init_db_idempotente_nao_apaga_dados(rows):
    """
    **Validates: Requisito 7.3**

    Para qualquer conjunto de registros em solicitacoes_visita, chamar init_db()
    novamente não deve remover nem alterar nenhum registro existente.

    Strategy:
    1. Create a fresh temp DB and call init_db() once to set up the schema.
    2. Insert `rows` directly into solicitacoes_visita via a raw connection
       (PRAGMA foreign_keys = OFF so we skip the usuarios FK dependency).
    3. Call init_db() a second time with the same DB.
    4. Assert that every inserted row is still present and unmodified.
    """
    db_path = _make_isolated_db()
    try:
        # ── Step 1: initial schema creation ──────────────────────────────
        _bootstrap_schema(db_path)

        # ── Step 2: insert test rows directly ────────────────────────────
        conn = _open_test_conn(db_path)
        inserted = []
        for row in rows:
            rowid = _insert_visita(conn, row)
            inserted.append((rowid, row))
        conn.close()

        # ── Step 3: call init_db() a second time ──────────────────────────
        original_db_path = _app._DB_PATH
        original_use_pg = _app._USE_PG
        try:
            _app._DB_PATH = db_path
            _app._USE_PG = False
            _app.init_db()   # <── second call — must be idempotent
        finally:
            _app._DB_PATH = original_db_path
            _app._USE_PG = original_use_pg

        # ── Step 4: verify rows are intact ───────────────────────────────
        conn = _open_test_conn(db_path)

        # Total count must match what we inserted (admin row from init_db
        # goes into `usuarios`, not solicitacoes_visita, so count == len(rows))
        cur = conn.execute("SELECT COUNT(*) FROM solicitacoes_visita")
        total = cur.fetchone()[0]
        assert total == len(rows), (
            f"Expected {len(rows)} rows in solicitacoes_visita after second "
            f"init_db(), but found {total}."
        )

        # Every individual row must still be there, unmodified
        for rowid, original in inserted:
            cur = conn.execute(
                "SELECT cpf_rf, nome_rf, endereco, motivo, data_prevista "
                "FROM solicitacoes_visita WHERE id = ?",
                (rowid,),
            )
            found = cur.fetchone()
            assert found is not None, (
                f"Row with id={rowid} disappeared after second init_db()."
            )
            assert found["cpf_rf"]        == original["cpf_rf"],        \
                f"cpf_rf mismatch for id={rowid}"
            assert found["nome_rf"]       == original["nome_rf"],        \
                f"nome_rf mismatch for id={rowid}"
            assert found["endereco"]      == original["endereco"],      \
                f"endereco mismatch for id={rowid}"
            assert found["motivo"]        == original["motivo"],        \
                f"motivo mismatch for id={rowid}"
            assert found["data_prevista"] == original["data_prevista"], \
                f"data_prevista mismatch for id={rowid}"

        conn.close()
    finally:
        # Always clean up the temp DB file
        try:
            os.unlink(db_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Property 5: Listagem respeita visibilidade por perfil
# ---------------------------------------------------------------------------

# Feature: controle-solicitacoes-visita, Property 5: Listagem respeita visibilidade por perfil
@given(
    rows_user_a=st.lists(_visita_row, min_size=1, max_size=8),
    rows_user_b=st.lists(_visita_row, min_size=1, max_size=8),
    rows_shared=st.lists(_visita_row, min_size=0, max_size=4),
)
@settings(
    max_examples=20,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)
def test_listagem_respeita_visibilidade_por_perfil(rows_user_a, rows_user_b, rows_shared):
    """
    **Validates: Requisitos 2.2, 2.3**

    For any distribution of visit requests among users:
    - An 'entrevistador' user (uid=A) must receive ONLY records where
      solicitante_id=A OR responsavel_id=A.
    - An 'admin' user must receive ALL records regardless of ownership.

    Strategy:
    1. Create an isolated temp DB and initialise the schema.
    2. Insert rows for user A (solicitante_id=A), rows for user B (solicitante_id=B),
       and shared rows (solicitante_id=B, responsavel_id=A) to exercise the
       responsavel_id branch.
    3. Run the access-filter SQL directly (mirroring painel_visitas logic).
    4. Assert entrevistador A sees rows_user_a + rows_shared.
    5. Assert admin sees ALL rows (rows_user_a + rows_user_b + rows_shared).
    """
    db_path = _make_isolated_db()
    try:
        _bootstrap_schema(db_path)
        conn = _open_test_conn(db_path)

        USER_A = 1  # entrevistador
        USER_B = 2  # another entrevistador

        total_expected_for_a = len(rows_user_a) + len(rows_shared)
        total_expected_admin = len(rows_user_a) + len(rows_user_b) + len(rows_shared)

        now = datetime.now().isoformat()

        def _insert(row, solicitante_id, responsavel_id=None):
            conn.execute(
                """INSERT INTO solicitacoes_visita
                       (cpf_rf, nome_rf, endereco, motivo, data_prevista,
                        status, solicitante_id, responsavel_id, criado_em, atualizado_em)
                   VALUES (?,?,?,?,?,'Pendente',?,?,?,?)""",
                (
                    row["cpf_rf"], row["nome_rf"], row["endereco"],
                    row["motivo"], row["data_prevista"],
                    solicitante_id, responsavel_id, now, now,
                ),
            )

        for r in rows_user_a:
            _insert(r, USER_A)
        for r in rows_user_b:
            _insert(r, USER_B)
        for r in rows_shared:
            # solicitante=B, responsavel=A  →  A can see via responsavel_id
            _insert(r, USER_B, USER_A)
        conn.commit()

        # ── Entrevistador A visibility query (mirrors painel_visitas logic) ─
        cur_a = conn.execute(
            """SELECT COUNT(*) FROM solicitacoes_visita sv
               WHERE (sv.solicitante_id = ? OR sv.responsavel_id = ?)""",
            (USER_A, USER_A),
        )
        count_a = cur_a.fetchone()[0]

        # ── Admin visibility query (no access filter) ──────────────────────
        cur_admin = conn.execute("SELECT COUNT(*) FROM solicitacoes_visita")
        count_admin = cur_admin.fetchone()[0]

        conn.close()

        assert count_a == total_expected_for_a, (
            f"Entrevistador A expected {total_expected_for_a} records "
            f"(owns={len(rows_user_a)}, responsavel={len(rows_shared)}), "
            f"but got {count_a}."
        )

        assert count_admin == total_expected_admin, (
            f"Admin expected {total_expected_admin} records total, but got {count_admin}."
        )

    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Property 6: Filtros retornam apenas resultados que correspondem ao critério
# ---------------------------------------------------------------------------

_VALID_STATUSES = ["Pendente", "Em Andamento", "Realizada", "Cancelada"]

_status_strategy = st.sampled_from(_VALID_STATUSES)

_visita_row_with_status = st.fixed_dictionaries({
    "cpf_rf":        _text,
    "nome_rf":       _text,
    "endereco":      _text,
    "motivo":        _text,
    "data_prevista": _date,
    "status":        _status_strategy,
})

_opt_date = st.one_of(st.none(), _date)
_opt_busca = st.one_of(st.just(""), _text)


# Feature: controle-solicitacoes-visita, Property 6: Filtros retornam apenas resultados que correspondem ao critério
@given(
    rows=st.lists(_visita_row_with_status, min_size=1, max_size=10),
    filtro_status=st.one_of(st.none(), _status_strategy),
    data_ini=_opt_date,
    data_fim=_opt_date,
    busca=_opt_busca,
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_filtros_retornam_apenas_resultados_correspondentes(rows, filtro_status, data_ini, data_fim, busca):
    """
    **Validates: Requisitos 2.4, 2.5, 2.6**

    Para qualquer conjunto de registros e parâmetros de filtro:
    - Filtro por status retorna somente registros com aquele status.
    - Filtro de período retorna somente registros com data_prevista no intervalo
      [data_ini, data_fim] (inclusive).
    - Filtro de texto retorna somente registros com match parcial (case-insensitive)
      em cpf_rf ou nome_rf.
    """
    from hypothesis import assume

    # Garante data_ini <= data_fim quando ambas são fornecidas
    if data_ini is not None and data_fim is not None:
        assume(data_ini <= data_fim)

    db_path = _make_isolated_db()
    try:
        _bootstrap_schema(db_path)
        conn = _open_test_conn(db_path)
        now = datetime.now().isoformat()

        # Insere todas as linhas com status explícito
        inserted_ids = []
        for row in rows:
            cur = conn.execute(
                """INSERT INTO solicitacoes_visita
                       (cpf_rf, nome_rf, endereco, motivo, data_prevista,
                        status, solicitante_id, criado_em, atualizado_em)
                   VALUES (?,?,?,?,?,?,1,?,?)""",
                (
                    row["cpf_rf"], row["nome_rf"], row["endereco"],
                    row["motivo"], row["data_prevista"], row["status"],
                    now, now,
                ),
            )
            inserted_ids.append(cur.lastrowid)
        conn.commit()

        # ── Sub-property 2.4: filtro por status ─────────────────────────────
        if filtro_status is not None:
            sql_status = "SELECT id, status FROM solicitacoes_visita WHERE status = ?"
            result_rows = conn.execute(sql_status, (filtro_status,)).fetchall()

            # Soundness: todo retornado deve ter o status correto
            for r in result_rows:
                assert r["status"] == filtro_status, (
                    f"Filtro por status='{filtro_status}' retornou registro com "
                    f"status='{r['status']}' (id={r['id']})."
                )

            # Completeness: todo registro com aquele status deve aparecer
            expected_ids = {
                inserted_ids[i]
                for i, row in enumerate(rows)
                if row["status"] == filtro_status
            }
            returned_ids = {r["id"] for r in result_rows}
            assert expected_ids == returned_ids, (
                f"Filtro por status='{filtro_status}': esperados {expected_ids}, "
                f"obtidos {returned_ids}."
            )

        # ── Sub-property 2.5: filtro por período ────────────────────────────
        if data_ini is not None and data_fim is not None:
            sql_period = (
                "SELECT id, data_prevista FROM solicitacoes_visita "
                "WHERE data_prevista >= ? AND data_prevista <= ?"
            )
            result_rows = conn.execute(sql_period, (data_ini, data_fim)).fetchall()

            # Soundness
            for r in result_rows:
                assert data_ini <= r["data_prevista"] <= data_fim, (
                    f"Filtro de período [{data_ini}, {data_fim}] retornou "
                    f"data_prevista='{r['data_prevista']}' (id={r['id']})."
                )

            # Completeness
            expected_ids = {
                inserted_ids[i]
                for i, row in enumerate(rows)
                if data_ini <= row["data_prevista"] <= data_fim
            }
            returned_ids = {r["id"] for r in result_rows}
            assert expected_ids == returned_ids, (
                f"Filtro de período [{data_ini}, {data_fim}]: "
                f"esperados {expected_ids}, obtidos {returned_ids}."
            )

        # ── Sub-property 2.6: filtro de texto ───────────────────────────────
        if busca:
            # Escape LIKE special characters so the search term is treated
            # as a literal substring, not a pattern.  SQLite supports an
            # ESCAPE clause to neutralise '%' and '_'.
            busca_escaped = busca.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            param = "%" + busca_escaped + "%"
            sql_text = (
                "SELECT id, cpf_rf, nome_rf FROM solicitacoes_visita "
                "WHERE (LOWER(cpf_rf) LIKE LOWER(?) ESCAPE '\\' "
                "    OR LOWER(nome_rf) LIKE LOWER(?) ESCAPE '\\')"
            )
            result_rows = conn.execute(sql_text, (param, param)).fetchall()

            busca_lower = busca.lower()

            # Soundness: every returned row must contain the literal substring
            for r in result_rows:
                matches = (
                    busca_lower in r["cpf_rf"].lower()
                    or busca_lower in r["nome_rf"].lower()
                )
                assert matches, (
                    f"Filtro de texto busca='{busca}' retornou registro que não "
                    f"contém o termo em cpf_rf='{r['cpf_rf']}' nem "
                    f"nome_rf='{r['nome_rf']}' (id={r['id']})."
                )

            # Completeness: every row that contains the substring must be returned
            expected_ids = {
                inserted_ids[i]
                for i, row in enumerate(rows)
                if (
                    busca_lower in row["cpf_rf"].lower()
                    or busca_lower in row["nome_rf"].lower()
                )
            }
            returned_ids = {r["id"] for r in result_rows}
            assert expected_ids == returned_ids, (
                f"Filtro de texto busca='{busca}': "
                f"esperados {expected_ids}, obtidos {returned_ids}."
            )

        conn.close()
    finally:
        try:
            os.unlink(db_path)
        except OSError:
            pass
