"""
Redefine a senha de TODOS os usuários do banco para o formato werkzeug (PBKDF2).
Execute uma vez após atualizar o app.py:  python reset_senha.py
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

usuarios = conn.execute("SELECT id, login, senha FROM usuarios").fetchall()

for u in usuarios:
    senha_atual = u['senha']
    # Hashes werkzeug começam com 'pbkdf2:' ou 'scrypt:'
    # Se não começar com isso, é o formato antigo (SHA-256 hex) — precisa migrar
    if not (senha_atual.startswith('pbkdf2:') or senha_atual.startswith('scrypt:')):
        # Para o admin, redefinimos para 'admin123' e forçamos troca
        if u['login'] == 'admin':
            nova = generate_password_hash('admin123')
            conn.execute(
                "UPDATE usuarios SET senha=?, trocar_senha=1 WHERE id=?",
                (nova, u['id'])
            )
            print(f"  admin  -> senha redefinida para 'admin123' (troca obrigatória no próximo login)")
        else:
            # Demais usuários: senha redefinida para '123456' e troca obrigatória
            nova = generate_password_hash('123456')
            conn.execute(
                "UPDATE usuarios SET senha=?, trocar_senha=1 WHERE id=?",
                (nova, u['id'])
            )
            print(f"  {u['login']}  -> senha redefinida para '123456' (troca obrigatória no próximo login)")
    else:
        print(f"  {u['login']}  -> já está no formato correto, ignorado")

conn.commit()
conn.close()
print("\nConcluído. Reinicie o servidor e faça login com as credenciais acima.")
