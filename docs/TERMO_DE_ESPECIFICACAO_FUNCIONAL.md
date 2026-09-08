# 📋 Termo de Especificação Funcional e Escopo do Sistema
### Sistema Cadastro Único & Visitas Domiciliares · Tomé-Açu / PA

Este documento estabelece a especificação técnica e funcional dos módulos que compõem o sistema oficial de gestão da **Secretaria Municipal de Trabalho e Assistência Social (SETAS)**.

---

## 1. Módulos do Sistema

### 1.1. Módulo de Registro de Atendimentos
* **Objetivo:** Registro ágil e seguro de todos os atendimentos presenciais prestados aos cidadãos nos polos de Tomé-Açu (Sede) e Quatro Bocas.
* **Regras de Negócio e Validações:**
  * **Data:** Registro cronológico obrigatório.
  * **CPF do RF:** Validação estrita de 11 dígitos pelos dois dígitos verificadores com máscara automática (`000.000.000-00`).
  * **Nome do RF:** Validação estrita por regex, permitindo apenas letras, espaços, apóstrofos e hífens, rejeitando números ou caracteres especiais.
  * **Bairro / Localidade:** Autocomplete inteligente priorizando a unidade do entrevistador (23 bairros urbanos) com suporte a digitação livre para zonas rurais (vilas, comunidades e ramais).
  * **Código Familiar:** Obrigatório para garantia de vínculo unívoco com a base nacional do CadÚnico.
  * **Composição Familiar (Qtd. Membros) e Renda Per Capita:** Campos numéricos/moeda obrigatórios para cálculo e acompanhamento socioeconômico.
  * **Tipos de Atendimento:** Inclusão, Atualização Cadastral, Emissão de Folha Resumo, Averiguação Unipessoal, Averiguação de Renda, Bloqueio/Desbloqueio SIBEC (permissão controlada), etc.

---

### 1.2. Módulo de Gestão de Visitas Domiciliares
* **Objetivo:** Controle e agendamento de averiguações in loco realizadas por entrevistadores e assistentes sociais.
* **Funcionalidades:**
  * Geração de código identificador sequencial anual único (ex: `VD-2026-0001`).
  * Classificação territorial por Zona Urbana ou Zona Rural, com pontos de referência e telefones de contato.
  * Painel de acompanhamento por status: `Pendente`, `Agendada`, `Realizada`, `Não Localizada`, `Cancelada`.
  * Filtro de visitas atrasadas com alertas visuais.
  * Registro de Parecer Técnico Assistencial e upload de fotos comprobatórias da moradia integradas ao Cloudinary.
  * Emissão do Termo Oficial de Visita Domiciliar em formato PDF para assinatura.

---

### 1.3. Módulo de Histórico Familiar Unificado
* **Objetivo:** Visão consolidada de todas as interações de uma mesma família com a assistência social do município.
* **Funcionalidades:**
  * Busca instantânea por CPF do RF ou Código Familiar.
  * Exibição cronológica de todos os atendimentos realizados, entrevistadores responsáveis, pareceres e visitas domiciliares vinculadas à família.

---

### 1.4. Módulo de Relatórios Gerenciais e Estatísticos
* **Objetivo:** Fornecimento de dados e métricas para a gestão municipal e prestação de contas aos conselhos (CMAS) e MDS.
* **Funcionalidades:**
  * Relatórios mensais, semanais e customizados por período e polo.
  * Exportação de dados completos em planilha Excel formatada (`.xlsx`) com fórmulas e cabeçalho oficial.
  * Gráficos dinâmicos de atendimentos por bairro, tipos de demanda e produtividade por entrevistador.

---

### 1.5. Módulo Administrativo e de Auditoria
* **Gerenciamento de Usuários:** Criação, edição, desativação, reset de senhas e atribuição de polos (`Quatro Bocas` / `Tomé-Açu Sede`).
* **Trilha de Auditoria:** Log permanente e pesquisável de todas as ações de usuários no sistema.
* **Editor de Documentos:** Edição e geração instantânea de modelos oficiais em formato PDF e DOCX (Word).

---
**Secretaria Municipal de Trabalho e Assistência Social · Prefeitura de Tomé-Açu**
