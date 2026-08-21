#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Migração Segura: PostgreSQL (Render) -> Supabase
IMPORTANTE: Não executa nenhum comando destrutivo (DROP/DELETE/TRUNCATE) no banco de origem.
"""
import sys
import os
import json
import urllib.parse
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import psycopg2
import psycopg2.extras

TABELAS_ORDEM = [
    "usuarios",
    "atendimentos",
    "solicitacoes_visita",
    "config_relatorio",
    "audit_log",
    "visita_contadores",
    "visita_fotos",
    "documentos_editaveis"
]

def safe_str(e):
    try:
        return str(e)
    except Exception:
        try:
            if hasattr(e, 'args') and e.args and isinstance(e.args[0], bytes):
                return e.args[0].decode('cp1252', errors='replace')
        except Exception:
            pass
        return repr(e)

def conectar_pg_seguro(url_ou_dsn):
    """Conecta ao PostgreSQL tratando de forma segura URLs com senhas complexas e SSL."""
    import app
    return app._conectar_pg_url(url_ou_dsn)

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def exportar_render(render_url, arquivo_saida="backup_cadunico_render.json"):
    print("\n--- 1. EXPORTANDO DADOS DO POSTGRESQL (RENDER) ---")

    try:
        conn = conectar_pg_seguro(render_url)
        cur = conn.cursor()
    except Exception as e:
        print(f"\n❌ Erro ao conectar ao PostgreSQL do Render: {safe_str(e)}")
        print("DICA: Verifique se você copiou a 'External Database URL' no painel do Render.")
        return None

    dados_backup = {}
    total_geral = 0

    for tabela in TABELAS_ORDEM:
        try:
            cur.execute(f"SELECT * FROM {tabela}")
            rows = [dict(r) for r in cur.fetchall()]
            dados_backup[tabela] = rows
            count = len(rows)
            total_geral += count
            print(f"  ✓ Tabela '{tabela}': {count} registros exportados.")
        except Exception as e:
            print(f"  ⚠️ Tabela '{tabela}': não foi possível ler ({safe_str(e)})")
            dados_backup[tabela] = []

    conn.close()

    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(dados_backup, f, indent=2, ensure_ascii=False, default=json_serial)

    print("\n✅ BACKUP LOCAL CONCLUÍDO COM SUCESSO!")
    print(f"📄 Arquivo de backup salvo em: {os.path.abspath(arquivo_saida)}")
    print(f"📊 Total de registros salvos: {total_geral}")
    return dados_backup

def importar_supabase(supabase_url, arquivo_backup="backup_cadunico_render.json"):
    print("\n--- 2. RESTAURANDO DADOS NO SUPABASE ---")
    if not os.path.exists(arquivo_backup):
        print(f"❌ Erro: Arquivo de backup '{arquivo_backup}' não encontrado!")
        return False

    with open(arquivo_backup, "r", encoding="utf-8") as f:
        dados_backup = json.load(f)

    import app
    app.DATABASE_URL = supabase_url
    app._USE_PG = True
    app._PG_FAILED = False

    try:
        conn = conectar_pg_seguro(supabase_url)
        cur = conn.cursor()
    except Exception as e:
        print(f"\n❌ Erro ao conectar ao PostgreSQL do Supabase: {safe_str(e)}")
        print("DICA: Verifique se copiou a 'Connection String (URI)' correta no painel do Supabase (Project Settings -> Database).")
        return False

    try:
        app.init_db()
    except Exception as ex_init:
        print(f"  (Aviso de inicialização de estrutura: {safe_str(ex_init)})")

    total_restaurados = 0

    for tabela in TABELAS_ORDEM:
        rows = dados_backup.get(tabela, [])
        if not rows:
            continue

        try:
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{tabela}'")
            cols_banco = set(r['column_name'] for r in cur.fetchall())
        except Exception:
            cols_banco = set()

        count_tab = 0
        for r in rows:
            r_filt = {k: v for k, v in r.items() if not cols_banco or k in cols_banco}
            if not r_filt:
                continue

            cols_str = ", ".join(r_filt.keys())
            placeholders = ", ".join(["%s"] * len(r_filt))
            values = list(r_filt.values())

            sql = f"INSERT INTO {tabela} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            try:
                cur.execute(sql, values)
                count_tab += 1
            except Exception:
                pass

        conn.commit()
        total_restaurados += count_tab
        print(f"  ✓ Tabela '{tabela}': {count_tab}/{len(rows)} registros inseridos no Supabase.")

    for t in TABELAS_ORDEM:
        try:
            cur.execute(f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), COALESCE((SELECT MAX(id) FROM {t}), 1));")
        except Exception:
            pass
    conn.commit()
    conn.close()

    print("\n🎉 MIGRAÇÃO CONCLUÍDA COM SUCESSO NO SUPABASE!")
    print(f"📊 Total de registros inseridos: {total_restaurados}")
    return True

if __name__ == '__main__':
    print("=========================================================")
    print(" 🛠️ FERRAMENTA DE MIGRAÇÃO SEGURA: RENDER -> SUPABASE")
    print("=========================================================")
    if len(sys.argv) < 2:
        print("\nUso:")
        print("  1. Exportar do Render: python migrar_render_para_supabase.py exportar \"URL_RENDER\"")
        print("  2. Importar no Supabase: python migrar_render_para_supabase.py importar \"URL_SUPABASE\"")
        sys.exit(1)

    comando = sys.argv[1].lower()
    if comando == 'exportar':
        if len(sys.argv) < 3:
            print("Informe a URL do Render: python migrar_render_para_supabase.py exportar \"URL_RENDER\"")
            sys.exit(1)
        exportar_render(sys.argv[2])
    elif comando == 'importar':
        if len(sys.argv) < 3:
            print("Informe a URL do Supabase: python migrar_render_para_supabase.py importar \"URL_SUPABASE\"")
            sys.exit(1)
        importar_supabase(sys.argv[2])
