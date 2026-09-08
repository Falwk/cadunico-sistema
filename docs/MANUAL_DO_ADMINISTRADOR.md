# ⚙️ Manual do Administrador e Coordenação
### Sistema Cadastro Único & Visitas Domiciliares · Tomé-Açu / PA

Este manual destina-se aos Coordenadores, Gestores e Administradores do sistema, cobrindo o gerenciamento de usuários, relatórios consolidados, segurança e backups.

---

## 👥 1. Gestão de Usuários e Polos

Acesse **"Painel Admin"** → **"Usuários"**:

### ➕ Cadastrar Novo Servidor / Entrevistador:
1. Clique em **"Novo Usuário"**.
2. Preencha o **Nome Completo**, **Login**, **E-mail**, **Telefone** e defina uma senha inicial (ex: `mudar123`).
3. **Polo / Unidade:** Escolha entre **`Quatro Bocas`** ou **`Tomé-Açu (Sede)`**. *(Essa escolha define qual lista de bairros será priorizada no formulário do entrevistador).*
4. **Perfil:** Selecione `Entrevistador` ou `Administrador`.
5. **Permissão SIBEC:** Marque se o servidor for autorizado a operar ações do SIBEC (bloqueio, desbloqueio, cancelamento).
6. **Trocar Senha no 1º Acesso:** Marque `Sim` para que o servidor seja obrigado a criar uma senha pessoal ao logar.

### 🔑 Resetar Senha / Desbloquear Usuário:
* Se um servidor errar a senha mais de 5 vezes e for bloqueado:
  1. Localize o usuário na lista.
  2. Clique em **"Editar / Resetar Senha"**.
  3. Defina a nova senha temporária e zere o contador de tentativas de login.

---

## 📊 2. Emissão de Relatórios Oficiais e Exportação Excel

Acesse **"Relatórios & Estatísticas"**:
* **Filtros Disponíveis:** Por período (diário, semanal, mensal, anual), por entrevistador, por polo (`Tomé-Açu Sede` ou `Quatro Bocas`), por bairro ou por tipo de atendimento.
* **Exportação Excel (`.xlsx`):** Clique no botão verde **"Baixar Planilha Excel"** para obter o relatório completo formatado com cabeçalho oficial da Prefeitura e SETAS, pronto para envio aos órgãos de fiscalização e MDS.
* **Gráficos e Indicadores:** Visualize a distribuição dos atendimentos mais demandados e o ranking de bairros atendidos.

---

## 🚗 3. Supervisão de Visitas Domiciliares

Acesse **"Visitas Domiciliares"** → **"Painel de Visitas"**:
* Visualize todas as solicitações do município por status (`Pendente`, `Agendada`, `Realizada`).
* **Atribuição de Responsável:** O administrador pode distribuir visitas pendentes para entrevistadores específicos ou para a equipe de campo.
* **Parecer Técnico e Fotos:** Ao concluir a visita, o técnico anexa o parecer social descritivo e as fotos da habitação. O administrador pode emitir o **Termo de Visita em PDF** oficial com a assinatura digital do sistema.

---

## 💾 4. Central de Backups e Telegram

Acesse **"Central de Backups"**:

### 🤖 Configurar Bot do Telegram:
1. Cole o **`BOT_TOKEN`** (fornecido pelo @BotFather no Telegram).
2. Cole o **`CHAT_ID`** do seu chat ou grupo de administradores.
3. Marque a opção **"Backup Automático Ativo"** e clique em **"Salvar"**.
4. Clique no botão **"Testar Envio Agora"** para validar se o arquivo `.zip` chega no seu celular.

### 📥 Backup Manual Imediato:
* Clique em **"Baixar Backup Completo em ZIP"** a qualquer momento para salvar uma cópia local de segurança no seu computador.

---

## 📜 5. Trilha de Auditoria (`audit_log`)

Acesse **"Painel Admin"** → **"Logs de Auditoria"**:
* O sistema registra automaticamente quem fez login, quem registrou, editou ou excluiu qualquer atendimento, com data, hora, IP e dados alterados.
* Utilize o campo de busca para rastrear o histórico de qualquer CPF ou matrícula em caso de averiguações internas.

---
**Coordenação Geral do Cadastro Único · SETAS Tomé-Açu**
