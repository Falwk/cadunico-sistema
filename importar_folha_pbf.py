import sys
import os
import csv
import time
from datetime import datetime

# Garante saída em UTF-8 no Windows
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

PROJECT_DIR = r'c:\Users\USER\Downloads\cadunico-sistema-main\cadunico-sistema-main'
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import app

CSV_DEFAULT_PATH = r'c:\Users\USER\Downloads\Compressed\BEC.E2.BOD1.F03.C2610.P1466.A1508001.C\BEC.E2.BOD1.F03.C2610.P1466.A1508001.CSV'

def formatar_moeda(val_str):
    if not val_str:
        return 'R$ 0,00'
    s = str(val_str).strip().replace('R$', '').replace(' ', '')
    if not s:
        return 'R$ 0,00'
    return f"R$ {s}" if not s.startswith('R$') else s

def formatar_competencia(comp_str):
    s = str(comp_str).strip()
    if len(s) == 6 and s.isdigit():
        return f"{s[4:6]}/{s[0:4]}"
    return s

def executar_importacao(csv_path=None):
    if not csv_path:
        csv_path = CSV_DEFAULT_PATH

    if not os.path.exists(csv_path):
        print(f"[ERRO] Arquivo CSV nao encontrado em: {csv_path}")
        return False

    print(f"[INICIO] Iniciando importacao da Folha do Bolsa Familia...")
    print(f"[ARQUIVO] {csv_path}")
    file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    print(f"[TAMANHO] {file_size_mb:.2f} MB")

    # Inicializa banco
    app.init_db()
    conn = app.get_db()
    is_pg = app._is_pg()
    print(f"[BANCO] Conectado: {'PostgreSQL' if is_pg else 'SQLite'}")

    start_time = time.time()
    total_linhas = 0
    familias = {} # cpf -> dict de dados consolidados

    with open(csv_path, 'r', encoding='latin1') as f:
        header_line = f.readline()
        headers = [h.strip().upper() for h in header_line.split(';')]
        
        def idx(col):
            try:
                return headers.index(col)
            except ValueError:
                return -1

        i_ref = idx('REF_FOLHA')
        i_codfam = idx('COD_FAMILIAR')
        i_cpf = idx('CPF')
        i_nis = idx('NIS')
        i_nome = idx('NOME')
        i_vlrtotal = idx('VLRTOTAL')
        i_vlrbenef = idx('VLRBENEF')
        i_sitbenef = idx('SITBENEFICIO')
        i_sitbenefic = idx('SITBENEFICIARIO')
        i_sitfam = idx('SITFAM')
        i_marcarf = idx('MARCA_RF')
        i_renda = idx('RENDA_PER_CAPITA')
        i_qtd = idx('QTD_PESSOAS')
        i_end = idx('ENDERECO')
        i_bairro = idx('BAIRRO')
        i_cep = idx('CEP')
        i_tel1 = idx('TELEFONE1')

        for line in f:
            total_linhas += 1
            if not line.strip():
                continue
            parts = line.split(';')
            
            # Filtra apenas Responsáveis Familiares (MARCA_RF == 'S')
            marca_rf = parts[i_marcarf].strip().upper() if i_marcarf != -1 and i_marcarf < len(parts) else ''
            if marca_rf != 'S':
                continue

            cpf_raw = parts[i_cpf].strip() if i_cpf != -1 and i_cpf < len(parts) else ''
            cpf_limpo = ''.join(c for c in cpf_raw if c.isdigit())
            if len(cpf_limpo) != 11:
                continue

            cod_fam = parts[i_codfam].strip() if i_codfam != -1 and i_codfam < len(parts) else ''
            nis = parts[i_nis].strip() if i_nis != -1 and i_nis < len(parts) else ''
            nome = parts[i_nome].strip() if i_nome != -1 and i_nome < len(parts) else ''
            ref_folha = parts[i_ref].strip() if i_ref != -1 and i_ref < len(parts) else ''
            
            vlr_str = parts[i_vlrtotal].strip() if i_vlrtotal != -1 and i_vlrtotal < len(parts) else ''
            if not vlr_str or vlr_str == '0,00':
                vlr_str = parts[i_vlrbenef].strip() if i_vlrbenef != -1 and i_vlrbenef < len(parts) else ''
            
            sit = parts[i_sitbenefic].strip() if i_sitbenefic != -1 and i_sitbenefic < len(parts) else ''
            if not sit:
                sit = parts[i_sitbenef].strip() if i_sitbenef != -1 and i_sitbenef < len(parts) else ''
            if not sit:
                sit = parts[i_sitfam].strip() if i_sitfam != -1 and i_sitfam < len(parts) else 'LIBERADO'

            renda = parts[i_renda].strip() if i_renda != -1 and i_renda < len(parts) else ''
            qtd = parts[i_qtd].strip() if i_qtd != -1 and i_qtd < len(parts) else ''
            endereco = parts[i_end].strip() if i_end != -1 and i_end < len(parts) else ''
            bairro = parts[i_bairro].strip() if i_bairro != -1 and i_bairro < len(parts) else ''
            cep = parts[i_cep].strip() if i_cep != -1 and i_cep < len(parts) else ''
            tel = parts[i_tel1].strip() if i_tel1 != -1 and i_tel1 < len(parts) else ''

            try:
                qtd_int = int(qtd) if qtd.isdigit() else 1
            except Exception:
                qtd_int = 1

            if cpf_limpo not in familias:
                familias[cpf_limpo] = {
                    'cpf': cpf_limpo,
                    'codigo_familiar': cod_fam,
                    'nis': nis,
                    'nome_rf': nome,
                    'endereco': endereco,
                    'bairro': bairro,
                    'cep': cep,
                    'telefone': tel,
                    'renda_per_capita': formatar_moeda(renda),
                    'qtd_membros': qtd_int,
                    'valor_beneficio': formatar_moeda(vlr_str),
                    'situacao_beneficio': sit or 'LIBERADO',
                    'competencia_folha': formatar_competencia(ref_folha)
                }
            else:
                if vlr_str and vlr_str != '0,00':
                    familias[cpf_limpo]['valor_beneficio'] = formatar_moeda(vlr_str)
                if sit and sit != 'LIBERADO':
                    familias[cpf_limpo]['situacao_beneficio'] = sit

    print(f"[PROGRESSO] Linhas lidas no CSV: {total_linhas:,}")
    print(f"[PROGRESSO] Responsaveis Familiares (RFs) unicos: {len(familias):,}")

    agora = datetime.now().isoformat()
    registros_para_inserir = []

    for fam in familias.values():
        registros_para_inserir.append((
            fam['cpf'], fam['codigo_familiar'], fam['nis'], fam['nome_rf'],
            fam['endereco'], fam['bairro'], fam['cep'], fam['telefone'],
            fam['renda_per_capita'], fam['qtd_membros'], fam['valor_beneficio'],
            fam['situacao_beneficio'], fam['competencia_folha'],
            agora, agora
        ))

    print(f"[GRAVANDO] Gravando familias em beneficiarios_pbf...")

    BATCH_SIZE = 1000
    total_inseridos = 0

    if is_pg:
        insert_sql = """
            INSERT INTO beneficiarios_pbf 
                (cpf, codigo_familiar, nis, nome_rf, endereco, bairro, cep, telefone,
                 renda_per_capita, qtd_membros, valor_beneficio, situacao_beneficio, competencia_folha,
                 criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cpf) DO UPDATE SET
                codigo_familiar = EXCLUDED.codigo_familiar,
                nis = EXCLUDED.nis,
                nome_rf = EXCLUDED.nome_rf,
                endereco = EXCLUDED.endereco,
                bairro = EXCLUDED.bairro,
                cep = EXCLUDED.cep,
                telefone = EXCLUDED.telefone,
                renda_per_capita = EXCLUDED.renda_per_capita,
                qtd_membros = EXCLUDED.qtd_membros,
                valor_beneficio = EXCLUDED.valor_beneficio,
                situacao_beneficio = EXCLUDED.situacao_beneficio,
                competencia_folha = EXCLUDED.competencia_folha,
                atualizado_em = EXCLUDED.atualizado_em
        """
        cur = conn.cursor()
        for i in range(0, len(registros_para_inserir), BATCH_SIZE):
            lote = registros_para_inserir[i:i + BATCH_SIZE]
            import psycopg2.extras
            psycopg2.extras.execute_batch(cur, insert_sql, lote)
            conn.commit()
            total_inseridos += len(lote)
            print(f"   Progresso: {total_inseridos:,} / {len(registros_para_inserir):,}")
    else:
        insert_sql = """
            INSERT INTO beneficiarios_pbf 
                (cpf, codigo_familiar, nis, nome_rf, endereco, bairro, cep, telefone,
                 renda_per_capita, qtd_membros, valor_beneficio, situacao_beneficio, competencia_folha,
                 criado_em, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (cpf) DO UPDATE SET
                codigo_familiar = excluded.codigo_familiar,
                nis = excluded.nis,
                nome_rf = excluded.nome_rf,
                endereco = excluded.endereco,
                bairro = excluded.bairro,
                cep = excluded.cep,
                telefone = excluded.telefone,
                renda_per_capita = excluded.renda_per_capita,
                qtd_membros = excluded.qtd_membros,
                valor_beneficio = excluded.valor_beneficio,
                situacao_beneficio = excluded.situacao_beneficio,
                competencia_folha = excluded.competencia_folha,
                atualizado_em = excluded.atualizado_em
        """
        for i in range(0, len(registros_para_inserir), BATCH_SIZE):
            lote = registros_para_inserir[i:i + BATCH_SIZE]
            conn.executemany(insert_sql, lote)
            conn.commit()
            total_inseridos += len(lote)
            print(f"   Progresso: {total_inseridos:,} / {len(registros_para_inserir):,}")

    print(f"[SUCESSO] {total_inseridos:,} familias salvas em beneficiarios_pbf.")

    # Cruzamento com Atendimentos já cadastrados
    print("[CRUZAMENTO] Cruzando com atendimentos existentes...")
    ats = app._fetchall(conn, "SELECT id, cpf, nis, endereco, valor_beneficio_pbf FROM atendimentos")
    atualizados = 0

    for at in ats:
        cpf_at = ''.join(c for c in (at.get('cpf') or '') if c.isdigit())
        if cpf_at in familias:
            fam = familias[cpf_at]
            vlr = fam['valor_beneficio']
            nis = fam['nis']
            end = fam['endereco']
            
            if is_pg:
                app._exec(conn,
                    "UPDATE atendimentos SET beneficiario_pbf=1, valor_beneficio_pbf=%s, nis=COALESCE(nis, %s), endereco=COALESCE(endereco, %s) WHERE id=%s",
                    (vlr, nis, end, at['id'])
                )
            else:
                app._exec(conn,
                    "UPDATE atendimentos SET beneficiario_pbf=1, valor_beneficio_pbf=?, nis=COALESCE(nis, ?), endereco=COALESCE(endereco, ?) WHERE id=?",
                    (vlr, nis, end, at['id'])
                )
            atualizados += 1

    conn.commit()
    conn.close()

    tempo_total = time.time() - start_time
    print(f"\n=======================================================")
    print(f"[CONCLUIDO] IMPORTACAO E CRUZAMENTO FINALIZADOS!")
    print(f"Tempo total: {tempo_total:.2f} segundos")
    print(f"Total de familias beneficiarias no banco: {total_inseridos:,}")
    print(f"Atendimentos previamente existentes marcados com PBF: {atualizados:,} de {len(ats):,}")
    print(f"=======================================================")
    return True

if __name__ == '__main__':
    executar_importacao()
