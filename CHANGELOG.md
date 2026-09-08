# 📜 Histórico de Mudanças (Changelog)
### Sistema Cadastro Único & Visitas Domiciliares · Tomé-Açu / PA

Todas as atualizações notáveis, correções de segurança e novas funcionalidades implementadas no sistema estão documentadas cronologicamente abaixo.

---

## [Versão 2.5.0] - 08/09/2026
### ✨ Novidades & Melhorias
* **Divisão de Polos e Ordenação Dinâmica de Bairros:**
  * Implementação da lista oficial com 23 bairros urbanos divididos por polo administrativo (**Quatro Bocas** e **Tomé-Açu Sede**).
  * O sistema agora detecta a unidade de lotação do entrevistador logado e reordena dinamicamente o *autocomplete* de A a Z priorizando o seu polo de atuação.
  * Suporte a digitação livre para qualquer localidade rural (vilas, comunidades, ramais e assentamentos).
* **Restrição Estrita de Caracteres no Nome do RF:**
  * Bloqueio em tempo real de dígitos numéricos e caracteres especiais no campo Nome do Responsável Familiar, aceitando exclusivamente letras, acentuações da língua portuguesa, espaços, apóstrofos e hífens.
* **Campos Obrigatórios Reforçados:**
  * Validações obrigatórias no frontend e backend para os campos: **Código Familiar**, **Bairro / Localidade**, **Qtd. Membros** e **Renda Per Capita**.

---

## [Versão 2.4.0] - 02/09/2026
### 🛡️ Segurança & Blindagem de Dados
* **Ativação Geral do Row Level Security (RLS) no Supabase:**
  * Ativação e garantia de RLS em todas as 8 tabelas do banco de dados relacional (`usuarios`, `atendimentos`, `solicitacoes_visita`, `audit_log`, etc.).
  * Bloqueio total de requisições anônimas externas pela API PostgREST do Supabase, mantendo acesso exclusivo via backend autenticado.
* **Sincronização de Sequências SERIAL:**
  * Auto-recuperação e alinhamento de sequências primárias do PostgreSQL no startup do sistema.

---

## [Versão 2.3.0] - 25/08/2026
### 📦 Módulo de Backups & Automação
* **Backup Automático via Telegram Bot:**
  * Integração da rotina que compacta banco de dados, tabelas em JSON, anexos e manifesto em `.zip` e envia via Telegram.
  * Criação do endpoint seguro `/api/v1/cron/backup-telegram` e `/health` para monitoramento de disponibilidade 24/7.
* **Correção de Colisão em Queries SQL:**
  * Auditoria em 12 consultas SQL com `JOIN` para definir aliases explícitos (`a.id AS id`), eliminando ambiguidades entre IDs de atendimentos e usuários.

---

## [Versão 2.2.0] - 20/08/2026
### 👨‍👩‍👧‍👦 Histórico Familiar & Documentos
* **Módulo de Histórico Familiar por CPF / Código Familiar:**
  * Painel de consulta unificado do histórico completo de atendimentos e visitas de uma mesma família.
* **Compressão Inteligente de Anexos:**
  * Otimização de uploads de documentos em PDF e imagens JPEG/PNG antes do envio para o Cloudinary, reduzindo tempo de tráfego e espaço ocupado.

---

## [Versão 2.0.0] - 15/08/2026
### 🚀 Migração para PostgreSQL (Supabase)
* Migração da camada de persistência de SQLite local para PostgreSQL gerenciado em nuvem de alta disponibilidade com Transaction Pooler.
* Criação do Módulo de Solicitação e Acompanhamento de Visitas Domiciliares (`solicitacoes_visita`).
* Implementação do painel administrativo completo, controle de tentativas de login e trilha de auditoria (`audit_log`).
