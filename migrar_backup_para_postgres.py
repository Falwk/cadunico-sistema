#!/usr/bin/env python3
"""
Script de Migração de Backup para PostgreSQL (ou SQLite Ativo)
--------------------------------------------------------------
Uso:
    python migrar_backup_para_postgres.py <caminho_do_arquivo.zip ou .db>

Exemplo:
    python migrar_backup_para_postgres.py database.db
    python migrar_backup_para_postgres.py Backup_CadUnico_COMPLETO.zip
"""

import sys
import os
import sqlite3
import json
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
import app

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

def _get_table_cols(conn, tab):
    try:
        if app._is_pg():
            rows = app._fetchall(conn, f"SELECT column_name FROM information_schema.columns WHERE table_name='{tab}'")
            return set(r['column_name'] for r in rows)
        else:
            rows = conn.execute(f"PRAGMA table_info({tab})").fetchall()
            return set(r[1] for r in rows)
    except Exception:
        return set()

def _bulk_insert_cli(conn, tab, rows_list):
    if not rows_list:
        return 0
    from collections import defaultdict
    t_cols = _get_table_cols(conn, tab)
    batches = defaultdict(list)
    for r in rows_list:
        row_filt = {k: v for k, v in r.items() if not t_cols or k in t_cols}
        if not row_filt:
            continue
        cols_tuple = tuple(sorted(row_filt.keys()))
        vals = [row_filt[k] for k in cols_tuple]
        batches[cols_tuple].append(vals)

    count_added = 0
    cur = conn.cursor()
    for cols_tuple, val_matrix in batches.items():
        if not val_matrix:
            continue
        cols_str = ', '.join(cols_tuple)
        placeholders = ', '.join([str(app.PH)] * len(cols_tuple))
        if app._is_pg():
            sql = f"INSERT INTO {tab} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            try:
                import psycopg2.extras
                psycopg2.extras.execute_batch(cur, app._adapt_sql(sql), val_matrix, page_size=200)
            except Exception:
                for v in val_matrix:
                    try:
                        cur.execute(app._adapt_sql(sql), v)
                    except Exception:
                        pass
        else:
            sql = f"INSERT OR IGNORE INTO {tab} ({cols_str}) VALUES ({placeholders})"
            cur.executemany(app._adapt_sql(sql), val_matrix)
        count_added += len(val_matrix)
    return count_added

def migrar(filepath):
    if not os.path.exists(filepath):
        print(f"❌ Erro: Arquivo de backup não encontrado em '{filepath}'")
        return

    print(f"📦 Inicializando migração a partir de: {filepath}")
    app.init_db()
    conn = app.get_db()
    
    total_restaurados = 0
    tabelas_afetadas = set()
    filename = os.path.basename(filepath).lower()

    if filename.endswith('.zip'):
        with zipfile.ZipFile(filepath, 'r') as zf:
            tabelas_ordem = ['usuarios', 'atendimentos', 'solicitacoes_visita', 'config_relatorio', 'audit_log', 'visita_contadores', 'visita_fotos']
            for tab in tabelas_ordem:
                json_name = f"tabelas_json/dados_{tab}.json"
                if json_name in zf.namelist():
                    with zf.open(json_name) as f:
                        rows = json.loads(f.read().decode('utf-8'))
                        n_inserted = _bulk_insert_cli(conn, tab, rows)
                        if n_inserted > 0:
                            total_restaurados += n_inserted
                            tabelas_afetadas.add(tab)
                        print(f"  ✓ Tabela '{tab}': {n_inserted} registros restaurados")

    elif filename.endswith('.db') or filename.endswith('.sqlite'):
        src_conn = sqlite3.connect(filepath)
        src_conn.row_factory = sqlite3.Row

        tabelas_ordem = ['usuarios', 'atendimentos', 'solicitacoes_visita', 'config_relatorio', 'audit_log', 'visita_contadores', 'visita_fotos']
        for tab in tabelas_ordem:
            try:
                rows = [dict(r) for r in src_conn.execute(f"SELECT * FROM {tab}").fetchall()]
                n_inserted = _bulk_insert_cli(conn, tab, rows)
                if n_inserted > 0:
                    total_restaurados += n_inserted
                    tabelas_afetadas.add(tab)
                print(f"  ✓ Tabela '{tab}': {n_inserted} registros migrados")
            except Exception as e:
                print(f"  ⚠️ Aviso na tabela '{tab}': {e}")
        src_conn.close()

    conn.commit()

    if app._is_pg():
        print("🔄 Sincronizando sequências de IDs no PostgreSQL...")
        for t in ['usuarios', 'atendimentos', 'solicitacoes_visita', 'audit_log', 'visita_fotos']:
            try:
                app._exec(conn, f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE((SELECT MAX(id) FROM {t}), 1));")
            except Exception:
                pass
        conn.commit()

    conn.close()
    print(f"✅ Migração concluída com sucesso! Total de {total_restaurados} registros gravados.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        default_db = os.path.join(BASE_DIR, 'database.db')
        if os.path.exists(default_db):
            migrar(default_db)
        else:
            print("Uso: python migrar_backup_para_postgres.py <caminho_do_arquivo.zip ou .db>")
    else:
        migrar(sys.argv[1])
