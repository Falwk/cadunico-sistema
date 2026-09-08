# 💾 Plano de Continuidade e Procedimentos de Backup (Disaster Recovery)
### Sistema Cadastro Único & Visitas Domiciliares · Tomé-Açu / PA

Este plano define a política de segurança, contingência, frequência de backups e os procedimentos para restauração completa dos serviços em caso de falhas de infraestrutura, corrupção de dados ou desastres operacionais.

---

## 1. Objetivos de Recuperação (SLAs)

* **RPO (Recovery Point Objective):** Máximo de **24 horas** de perda de dados tolerável (mitigado pelos backups automáticos diários e persistência em nuvem com WAL no PostgreSQL).
* **RTO (Recovery Time Objective):** Tempo máximo estimado para restauração completa do sistema: **30 minutos**.

---

## 2. Camadas de Backup Implementadas

O sistema opera com 3 níveis complementares de redundância:

```
                  ┌─────────────────────────────────────┐
                  │   Banco de Dados Supabase (AWS)     │
                  │   (Replicação e Point-in-Time WAL)  │
                  └──────────────────┬──────────────────┘
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           ▼                                                   ▼
┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
│ Backup Automático Telegram Bot  │                 │ Exportações em Lote no Painel   │
│ - Compactação .ZIP diária       │                 │ - Planilhas Excel (.xlsx)       │
│ - Banco SQL / JSON / Anexos     │                 │ - Relatórios PDF Formatados     │
│ - Enviado para o celular        │                 │ - Baixados sob demanda pelo ADM │
└─────────────────────────────────┘                 └─────────────────────────────────┘
```

---

## 3. Módulo de Backup Automático via Telegram

### ⚙️ Como Funciona o Pacote `.zip`:
Diariamente, no horário programado (ex: 23:00 / 03:00), o sistema executa a rotina `_enviar_backup_telegram()`:
1. Extrai todos os registros das tabelas (`atendimentos`, `usuarios`, `solicitacoes_visita`, `audit_log`, `config_relatorio`, `documentos_editaveis`) em formato JSON estruturado com codificação UTF-8.
2. Gera o arquivo de manifesto com data/hora, versão do sistema e total de registros exportados.
3. Compacta tudo em um arquivo `backup_cadunico_AAAA-MM-DD_HH-MM.zip`.
4. Envia o arquivo diretamente para o chat ou grupo privado de administradores no Telegram com legenda formatada em Markdown.

### 🔗 Endpoint do Agendador (Cron):
* **URL:** `https://seu-dominio.onrender.com/api/v1/cron/backup-telegram`
* **Método:** `GET` ou `POST`
* **Acionamento:** Configurado no [cron-job.org](https://cron-job.org) para execução diária.

---

## 4. Procedimento de Recuperação de Desastres (*Disaster Recovery*)

Em caso de necessidade de restauração total do banco de dados (por exemplo, migração para um novo banco Supabase ou servidor VPS):

### Passo 1: Obtenção do Arquivo de Backup
Localize o último arquivo `.zip` enviado no canal do Telegram ou o backup exportado pelo Administrador.

### Passo 2: Execução do Script de Restauração
No terminal da aplicação ou ambiente local:
```bash
# Executa o script de restauração apontando para a nova URL de banco
python restore_backup.py --file backup_cadunico_2026-09-08.zip --db-url "postgresql://novo-banco..."
```

### Passo 3: Sincronização de Sequências
O sistema executa automaticamente a função `init_db()` ao inicializar, sincronizando os contadores `SERIAL` para o valor máximo (`MAX(id)`) existente nas tabelas, garantindo que novas inserções não gerem conflito de chaves primárias.

### Passo 4: Verificação de Integridade
Acesse o endpoint de diagnóstico:
`https://seu-dominio.onrender.com/health`
Verifique se a contagem total de atendimentos e visitas coincide com o relatório anterior.

---
**Coordenação de Tecnologia e Informação · SETAS Tomé-Açu**
