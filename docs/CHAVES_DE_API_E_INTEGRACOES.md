# 🔑 Guia de Chaves de API, Segredos e Integrações
### Sistema Cadastro Único & Visitas Domiciliares · Tomé-Açu / PA

Este documento estabelece a especificação técnica, o inventário de credenciais, as políticas de segurança e os procedimentos para obtenção, configuração e rotação de todas as **Chaves de API e Segredos** do sistema.

---

## 📋 1. Inventário de Chaves e Variáveis de Ambiente

| Variável / Chave | Finalidade | Onde Configurar | Nível de Criticidade |
| :--- | :--- | :--- | :---: |
| **`DATABASE_URL`** | Conexão autenticada ao PostgreSQL do Supabase (Transaction Pooler). | Variáveis de Ambiente (Render / VPS) | 🔴 **Crítico** |
| **`CADUNICO_SECRET`** | Chave criptográfica mestra para assinatura de cookies e sessões de usuários. | Variáveis de Ambiente (Render / VPS) | 🔴 **Crítico** |
| **`CLOUDINARY_URL`** | Chave de API para upload, compressão e armazenamento seguro de fotos e anexos de visitas. | Variáveis de Ambiente (Render / VPS) | 🟠 **Alto** |
| **`TELEGRAM_BOT_TOKEN`** | Token de autenticação do Bot do Telegram para envio diário de backups em `.zip`. | Painel Admin (Central de Backups) | 🟠 **Alto** |
| **`TELEGRAM_CHAT_ID`** | Identificador numérico do grupo ou chat privado que recebe os backups. | Painel Admin (Central de Backups) | 🟡 **Médio** |
| **`X-CRON-SECRET`** | Token de autenticação para disparo seguro do endpoint de backup via agendador externo. | Cabeçalho HTTP / Parâmetro URL | 🟡 **Médio** |

---

## 🛠️ 2. Como Obter e Configurar Cada Chave

### 2.1. String de Conexão do Banco de Dados (`DATABASE_URL`)
1. Acesse o painel do [Supabase](https://supabase.com/dashboard).
2. Vá em **Project Settings** → **Database** → **Connection string**.
3. Selecione a aba **Transaction Pooler** (Porta `6543`) e copie a URI:
   ```text
   postgresql://postgres.[PROJETO]:[SENHA]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
   ```
4. Configure essa URL na variável de ambiente `DATABASE_URL` do seu servidor.

---

### 2.2. Chave de Armazenamento em Nuvem (`CLOUDINARY_URL`)
1. Acesse o painel do [Cloudinary](https://cloudinary.com/console).
2. No Dashboard principal, copie a **API Environment Variable**.
3. O formato é:
   ```text
   cloudinary://API_KEY:API_SECRET@CLOUD_NAME
   ```
4. Cole esse valor na variável de ambiente `CLOUDINARY_URL`.

---

### 2.3. Token do Bot do Telegram (`TELEGRAM_BOT_TOKEN` e `CHAT_ID`)
1. No aplicativo do Telegram, procure pelo usuário oficial **`@BotFather`**.
2. Envie o comando `/newbot` e siga as instruções para definir o nome e o usuário do bot.
3. Ao finalizar, o BotFather fornecerá o token no formato:
   ```text
   1234567890:ABCDefGhIjKlMnOpQrStUvWxYz123456789
   ```
4. Para descobrir o seu `CHAT_ID`:
   * Inicie uma conversa com o seu novo bot (clique em **Começar / Start**).
   * Encaminhe uma mensagem para o bot **`@userinfobot`** ou acesse `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`.
   * Copie o número do `id` do seu usuário ou grupo (ex: `123456789` ou `-100123456789`).
5. No painel do sistema, acesse **Central de Backups** → Cole o Token e o Chat ID e clique em **Salvar**.

---

## 📡 3. Autenticação e Consumo da API de Agendamento (Cron)

O sistema disponibiliza um endpoint protegido para execução de rotinas automáticas de contingência e backup.

### Endpoint de Backup Automático:
* **URL:** `https://seu-dominio.com.br/api/v1/cron/backup-telegram`
* **Métodos Suportados:** `GET` ou `POST`

#### Opção de Autenticação via Cabeçalho (Header):
```http
POST /api/v1/cron/backup-telegram HTTP/1.1
Host: seu-dominio.com.br
X-CRON-SECRET: setas-beneficios-token-2026
```

#### Opção de Autenticação via Parâmetro na URL:
```text
https://seu-dominio.com.br/api/v1/cron/backup-telegram?secret=setas-beneficios-token-2026
```

#### Exemplo de Resposta de Sucesso (`HTTP 200 OK`):
```json
{
  "sucesso": true,
  "mensagem": "Backup enviado para o Telegram com sucesso!"
}
```

---

## 🛡️ 4. Política de Segurança e Boas Práticas para Chaves

1. 🚫 **Proibição de Hardcode no Código-Fonte:**
   * Nenhuma chave privada, token ou senha de banco de dados deve ser inserida diretamente no código (`app.py`) ou commitada no repositório do GitHub.
   * Utilize sempre variáveis de ambiente no servidor ou um arquivo `.env` local (que deve constar no `.gitignore`).

2. 🔄 **Procedimento de Rotação de Chaves (Em caso de vazamento acidental):**
   * **Supabase:** Vá em *Project Settings* → *Database* → *Database Password* e clique em **Reset database password**. Atualize a `DATABASE_URL` no servidor.
   * **Telegram:** Envie `/revoke` no `@BotFather` para invalidar o token antigo e gerar um novo instantaneamente.
   * **Cloudinary:** No painel do Cloudinary, acesse *Settings* → *Access Keys* e gere uma nova *API Secret*.

3. 👥 **Princípio do Menor Privilégio:**
   * O token do Telegram deve ser exclusivo para o bot de backups do Cadastro Único, sem compartilhamento com outros sistemas ou canais públicos.

---
**Coordenação de Tecnologia e Segurança da Informação · SETAS Tomé-Açu**
