#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Restauração de Atendimentos Faltantes / Excluídos
"""
import sys
import os
import json
import psycopg2
import psycopg2.extras
import app

def restaurar_atendimentos(supabase_url, arquivo_backup="backup_cadunico_render.json"):
    print("--- RESTAURANDO ATENDIMENTOS FALTANTES NO SUPABASE ---")
    if not os.path.exists(arquivo_backup):
        print(f"❌ Erro: Arquivo de backup '{arquivo_backup}' não encontrado!")
        return

    with open(arquivo_backup, "r", encoding="utf-8") as f:
        dados_backup = json.load(f)

    ats_original = dados_backup.get("atendimentos", [])
    print(f"Total no backup original: {len(ats_original)} atendimentos")

    conn = app._conectar_pg_url(supabase_url)
    cur = conn.cursor()

    cur.execute("SELECT id FROM atendimentos")
    ids_atuais = set(r['id'] for r in cur.fetchall())
    print(f"Total atualmente no Supabase: {len(ids_atuais)} atendimentos")

    faltantes = [a for a in ats_original if a['id'] not in ids_atuais]
    print(f"Atendimentos a restaurar: {len(faltantes)}")

    count = 0
    for a in faltantes:
        cols_str = ", ".join(a.keys())
        placeholders = ", ".join(["%s"] * len(a))
        values = list(a.values())

        sql = f"INSERT INTO atendimentos ({cols_str}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
        try:
            cur.execute(sql, values)
            count += 1
        except Exception as ex:
            print(f"Erro ao re-inserir ID {a['id']}: {ex}")

    conn.commit()

    cur.execute("SELECT setval(pg_get_serial_sequence('atendimentos', 'id'), COALESCE((SELECT MAX(id) FROM atendimentos), 1));")
    conn.commit()
    conn.close()

    print(f"\n✅ RESTAURAÇÃO CONCLUÍDA! {count} atendimentos re-inseridos com sucesso no Supabase.")

if __name__ == '__main__':
    url = "postgresql://postgres.cfcdmuffivnukleadiyl:Amand%4027Telm%4007@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
    if len(sys.argv) > 1:
        url = sys.argv[1]
    restaurar_atendimentos(url)
