# 🏛️ Governança, Segurança da Informação e Conformidade LGPD
### Secretaria Municipal de Trabalho e Assistência Social (SETAS) · Tomé-Açu / PA

Este documento estabelece as diretrizes de governança, proteção de dados pessoais e segurança da informação aplicadas ao **Sistema de Gestão do Cadastro Único e Visitas Domiciliares**, em estrita observância à **Lei Geral de Proteção de Dados Pessoais (Lei Federal nº 13.709/2018 - LGPD)** e às normas do **Ministério do Desenvolvimento e Assistência Social, Família e Combate à Fome (MDS)**.

---

## 1. Enquadramento Legal e Finalidade do Tratamento
O tratamento de dados pessoais no sistema fundamenta-se nas seguintes bases legais da LGPD:

1. **Art. 7º, III (Execução de Políticas Públicas):** O tratamento é estritamente necessário para a operacionalização dos programas sociais do Governo Federal (Bolsa Família, BPC, Tarifa Social de Energia, Carteira do Idoso, etc.) e serviços socioassistenciais do município.
2. **Art. 11, II, 'b' (Dados Sensíveis):** Tratamento indispensável à execução de políticas públicas de assistência social voltadas a populações em situação de vulnerabilidade e extrema pobreza.

---

## 2. Inventário de Dados Pessoais Coletados

| Campo | Categoria | Finalidade no Sistema |
| :--- | :--- | :--- |
| **CPF do RF** | Dado Pessoal Identificador | Identificação única nacional do Responsável Familiar junto ao MDS e Caixa Econômica Federal. |
| **Nome Completo** | Dado Pessoal | Qualificação do titular e registro documental oficial. |
| **Código Familiar** | Identificador Social | Vinculação direta da ficha ao banco nacional do Cadastro Único. |
| **Renda Per Capita** | Dado Financeiro / Socioeconômico | Avaliação de enquadramento nos critérios de elegibilidade de benefícios de transferência de renda. |
| **Qtd. Membros** | Dado Familiar | Composição familiar para cálculo de per capita e dimensionamento de benefícios. |
| **Bairro / Endereço** | Dado de Geolocalização | Mapeamento territorial, planejamento de rotas de visitas e averiguação cadastral. |
| **Fotos da Residência** | Dado Comprobatório (Visita) | Averiguação in loco de condições de habitabilidade para emissão de Parecer Técnico Assistencial. |

---

## 3. Controles Técnicos de Segurança Implementados

### 🛡️ 3.1. Row Level Security (RLS) no Banco de Dados
* Todas as tabelas no banco de dados **PostgreSQL** operam com **Row Level Security (RLS)** ativado.
* Qualquer tentativa de acesso anônimo ou direto por meio de chaves de API externas do Supabase é terminantemente bloqueada, restringindo o acesso exclusivamente ao backend autenticado do sistema.

### 🔐 3.2. Criptografia e Autenticação Forte
* **Senhas de Usuários:** Armazenadas utilizando algoritmo de hashing criptográfico com sal (*salt*) via **PBKDF2-SHA256**. Nenhuma senha é salva em texto puro.
* **Política de Troca Obrigatória:** Novos servidores cadastrados são forçados a alterar sua senha inicial no primeiro acesso.
* **Bloqueio por Tentativas Consecutivas:** Após 5 tentativas consecutivas de login incorreto, o acesso é temporariamente bloqueado para mitigar ataques de força bruta, e um alerta de auditoria é registrado.

### 📜 3.3. Trilha de Auditoria Contínua (`audit_log`)
Todas as ações críticas realizadas no sistema são gravadas de forma permanente e rastreável na tabela `audit_log`, contendo:
* Identificação do Servidor (ID e Nome)
* Endereço IP e Timestamp exato da operação
* Tipo de Ação executada (`LOGIN`, `REGISTRAR_ATENDIMENTO`, `EDITAR_ATENDIMENTO`, `EXCLUIR_ATENDIMENTO`, `EMISSAO_PARECER`)
* Metadados da família manipulada (CPF, Código Familiar)

---

## 4. Política de Acesso e Segregação de Funções (RBAC)

* **Perfil Entrevistador:** Tem permissão restrita para registrar novos atendimentos, consultar o histórico familiar, solicitar visitas domiciliares e editar apenas os registros criados por ele mesmo dentro do prazo operacional permitido. Não tem acesso a dados confidenciais de outros servidores nem a configurações de sistema.
* **Perfil Administrador (Coordenação):** Acesso à gestão de servidores, desbloqueio de acessos, emissão de relatórios consolidados do município, auditoria e configuração de backups.
* **Acesso SIBEC:** Permissão especial atribuída individualmente para registro de solicitações específicas do Sistema de Benefícios ao Cidadão.

---

## 5. Gestão de Incidentes e Descarte de Dados
* Em caso de qualquer anomalia de acesso, o painel de auditoria do administrador permite a visualização imediata da trilha temporal de eventos.
* O descarte de backups expirados e logs antigos segue as diretrizes do Conselho Nacional de Assistência Social (CNAS) e da Tabela de Temporalidade Documental do Município.

---
**Comissão de Governança Digital e Assistência Social · Tomé-Açu / PA**
