"""
Script de migração: substitui chamadas diretas conn.execute(...).fetchone/fetchall
pelos helpers _fetchone/_fetchall/_exec em app.py.
Execute uma vez: python migrate_db_calls.py
"""
import re

PATH = 'app.py'

with open(PATH, encoding='utf-8') as f:
    src = f.read()

# 1. conn.execute(sql, params).fetchall() → _fetchall(conn, sql, params)
src = re.sub(
    r'conn\.execute\((\s*)("""|\'\'\')(.*?)\2,\s*(.*?)\)\.fetchall\(\)',
    lambda m: f'_fetchall(conn, {m.group(2)}{m.group(3)}{m.group(2)}, {m.group(4)})',
    src, flags=re.DOTALL
)
src = re.sub(
    r'conn\.execute\((".*?"),\s*(.*?)\)\.fetchall\(\)',
    r'_fetchall(conn, \1, \2)',
    src
)

# 2. conn.execute(sql, params).fetchone() → _fetchone(conn, sql, params)
src = re.sub(
    r'conn\.execute\((".*?"),\s*(.*?)\)\.fetchone\(\)',
    r'_fetchone(conn, \1, \2)',
    src
)
src = re.sub(
    r'conn\.execute\((\(.*?\)),\s*(.*?)\)\.fetchone\(\)',
    r'_fetchone(conn, \1, \2)',
    src
)

# 3. conn.execute(sql).fetchone() → _fetchone(conn, sql)
src = re.sub(
    r'conn\.execute\((".*?")\)\.fetchone\(\)',
    r'_fetchone(conn, \1)',
    src
)

# 4. conn.execute(sql).fetchall() → _fetchall(conn, sql)
src = re.sub(
    r'conn\.execute\((".*?")\)\.fetchall\(\)',
    r'_fetchall(conn, \1)',
    src
)

# 5. conn.execute(sql, params) sem fetch → _exec(conn, sql, params)
# Só substitui quando não é CREATE TABLE / ALTER TABLE (já tratados em init_db)
def replace_exec(m):
    full = m.group(0)
    sql_arg = m.group(1)
    params_arg = m.group(2)
    # Não toca em CREATE, ALTER, DDL dentro do init_db
    if any(kw in sql_arg.upper() for kw in ['CREATE', 'ALTER', 'DROP']):
        return full
    return f'_exec(conn, {sql_arg}, {params_arg})'

src = re.sub(
    r'conn\.execute\((".*?"),\s*(\(.*?\))\)',
    replace_exec,
    src
)

# 6. Simples conn.execute(sql) sem params e sem fetch → _exec(conn, sql)
def replace_exec_noparam(m):
    full = m.group(0)
    sql_arg = m.group(1)
    if any(kw in sql_arg.upper() for kw in ['CREATE', 'ALTER', 'DROP']):
        return full
    return f'_exec(conn, {sql_arg})'

src = re.sub(
    r'conn\.execute\((".*?")\)(?!\s*\.(fetchone|fetchall|commit))',
    replace_exec_noparam,
    src
)

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(src)

print("Migração concluída. Verifique app.py manualmente para casos edge.")
