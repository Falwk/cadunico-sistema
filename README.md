# 🏛️ Sistema de Gestão do Cadastro Único e Visitas Domiciliares
### Secretaria Municipal de Trabalho e Assistência Social (SETAS) · Prefeitura Municipal de Tomé-Açu / PA

Sistema integrado para gestão, registro, acompanhamento e emissão de relatórios oficiais de atendimentos às famílias do Cadastro Único e solicitações de Visitas Domiciliares.

---

## 🚀 Tecnologias Utilizadas

* **Linguagem / Backend:** Python 3.10+ / Flask 3.0
* **Servidor WSGI:** Gunicorn 22.0
* **Banco de Dados:** PostgreSQL (Supabase) via `psycopg2-binary` (com fallback transparente para SQLite em ambiente local)
* **Segurança de Dados:** Row Level Security (RLS) nativo do PostgreSQL, hashing PBKDF2/SHA256 para senhas e trilha de auditoria completa (`audit_log`)
* **Armazenamento em Nuvem:** Cloudinary API (armazenamento otimizado e seguro de anexos e documentos comprobatórios)
* **Geração de Documentos:** ReportLab (PDFs dinâmicos), `openpyxl` (planilhas Excel formatadas) e `python-docx` (documentos Word editáveis)
* **Automação:** Bot de Notificação e Backup Automático no Telegram + Endpoints de Cron Jobs

---

## 📂 Estrutura da Documentação

A documentação completa do sistema está organizada na raiz e no diretório [`docs/`](./docs/):

1. **🏛️ Governança, Compliance e LGPD:**
   * [`docs/GOVERNANCA_LGPD_E_SEGURANCA.md`](./docs/GOVERNANCA_LGPD_E_SEGURANCA.md) — Conformidade com a Lei Geral de Proteção de Dados (Lei 13.709/2018), bases legais do MDS e trilha de auditoria.
   * [`docs/PLANO_DE_CONTINUIDADE_E_BACKUPS.md`](./docs/PLANO_DE_CONTINUIDADE_E_BACKUPS.md) — Rotinas de backup automático no Telegram, exportações em lote e plano de recuperação de desastres (*Disaster Recovery*).
   * [`docs/TERMO_DE_ESPECIFICACAO_FUNCIONAL.md`](./docs/TERMO_DE_ESPECIFICACAO_FUNCIONAL.md) — Especificação dos módulos de atendimento, visitas e pareceres sociais.

2. **👥 Manuais de Operação:**
   * [`docs/MANUAL_DO_ENTREVISTADOR.md`](./docs/MANUAL_DO_ENTREVISTADOR.md) — Guia do entrevistador: registro com validações estritas, busca de cadastros, bairros por polo e visitas.
   * [`docs/MANUAL_DO_ADMINISTRADOR.md`](./docs/MANUAL_DO_ADMINISTRADOR.md) — Guia da coordenação: gestão de usuários, controle de permissões, redefinição de senhas e relatórios estatísticos.

3. **💻 Engenharia e Infraestrutura:**
   * [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md) — Dicionário de dados, tabelas, constraints, índices e políticas de RLS.
   * [`DEPLOY.md`](./DEPLOY.md) — Guia de implantação em VPS Ubuntu / Cloud e serviços gerenciados (Render/Supabase).
   * [`CHANGELOG.md`](./CHANGELOG.md) — Histórico detalhado de atualizações e novas versões.

---

## ⚙️ Variáveis de Ambiente

Para rodar em ambiente de produção (Render / VPS), configure as seguintes variáveis:

| Variável | Descrição | Exemplo |
| :--- | :--- | :--- |
| `DATABASE_URL` | String de conexão PostgreSQL (Supabase Transaction Pooler) | `postgresql://postgres.[ref]:[pass]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres` |
| `CADUNICO_SECRET` | Chave secreta criptográfica para sessões do Flask | `cadunico2026_super_secret_key_prod` |
| `CLOUDINARY_URL` | URL de integração para upload de fotos e anexos | `cloudinary://API_KEY:API_SECRET@CLOUD_NAME` |
| `PORT` | Porta de escuta da aplicação | `5000` |

---

## 💻 Instalação e Execução em Ambiente Local

```bash
# 1. Clonar o repositório
git clone https://github.com/Falwk/cadunico-sistema.git
cd cadunico-sistema

# 2. Criar e ativar o ambiente virtual (venv)
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate

# 3. Instalar as dependências
pip install -r requirements.txt

# 4. Executar a aplicação
python app.py
```
O sistema inicializará localmente no endereço `http://localhost:5000`.

---

## 🛡️ Credenciais Padrão de Primeiro Acesso
* **Usuário:** `admin`
* **Senha Inicial:** `admin123` *(O sistema exigirá a troca obrigatória de senha no primeiro login).*

---
**Prefeitura Municipal de Tomé-Açu · Secretaria Municipal de Trabalho e Assistência Social (SETAS)**
