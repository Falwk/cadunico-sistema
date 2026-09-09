# 📤 Procedimento Operacional: Como Enviar a Chave de API e Documentos
### Guia Prático para o Gestor e Administrador · SETAS Tomé-Açu

Este guia descreve o fluxo seguro e oficial para disponibilizar a Chave de API do sistema para outra secretaria, órgão ou desenvolvedor parceiro.

---

## 🗺️ Fluxograma em 3 Etapas:

```
┌──────────────────────────────────────┐
│  ETAPA 1: Formalização e Assinatura  │
│  - Preencher e assinar o Termo LGPD  │
│  - Emitir o Ofício de Concessão      │
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│  ETAPA 2: Envio da Documentação      │
│  - Enviar e-mail institucional       │
│  - Anexar docs/ e manual técnico     │
└──────────────────┬───────────────────┘
                   │
┌──────────────────▼───────────────────┐
│  ETAPA 3: Envio Seguro da Chave      │
│  - Gerar link temporário (PwPush)    │
│  - Enviar chave por canal seguro     │
└──────────────────────────────────────┘
```

---

## 📝 Passo a Passo Detalhado:

### Etapa 1: Formalização Jurídica e Administrativa
1. Abra o arquivo [`docs/TERMO_DE_COMPROMISSO_E_SIGILO_API.md`](./TERMO_DE_COMPROMISSO_E_SIGILO_API.md).
2. Preencha os dados da entidade solicitante e imprima para colher as assinaturas (ou utilize assinatura digital Gov.br).
3. Emita o [`docs/MODELO_OFICIO_CONCESSAO_API.md`](./MODELO_OFICIO_CONCESSAO_API.md) com o número de protocolo oficial da Secretaria.

---

### Etapa 2: Como Gerar o Link Seguro da Chave de API (PwPush / Bitwarden)
⚠️ **Nunca cole a chave no corpo do e-mail aberto!** Em vez disso, crie um link protegido por senha com autodestruição:

1. Acesse o site gratuito e seguro: **[https://pwpush.com](https://pwpush.com)** (ou [Bitwarden Send](https://vault.bitwarden.com/#/send)).
2. No campo de texto, cole a sua Chave de API (ex: `setas-beneficios-token-2026`).
3. Nas opções de expiração:
   * **Expirar após:** `1 visualização` ou `24 horas`.
4. Clique em **"Push It"** (Gerar Link).
5. Copie o link gerado (ex: `https://pwpush.com/p/abc123xyz`).

---

### Etapa 3: Envio do E-mail Institucional

Envie o e-mail oficial para o gestor técnico do outro sistema utilizando o modelo abaixo:

```text
Para: contato@orgao-solicitante.gov.br
Assunto: Liberação de Acesso Técnico e Credenciais da API — Sistema Cadastro Único (SETAS Tomé-Açu)

Prezada Equipe Técnica,

Em atenção ao Requerimento/Processo administrativo referente à integração com o Sistema de Gestão do Cadastro Único e Visitas Domiciliares da SETAS / Prefeitura de Tomé-Açu, encaminhamos as diretrizes técnicas para consumo da API:

1. Parâmetros de Integração:
• Ambiente: Produção
• URL Base: https://cadunico-sistema.onrender.com (ou domínio configurado)
• Documentação Técnica: Em anexo (CHAVES_DE_API_E_INTEGRACOES.md)
• Ofício e Termo de Compromisso LGPD: Em anexo (OFICIO_CONCESSAO_API.pdf)

2. Credencial de Acesso (Chave de API / Token):
Por questões de segurança e conformidade com a LGPD (Lei 13.709/2018), a chave de autenticação foi disponibilizada em cofre temporário com link de visualização única:
👉 Link Seguro: [COLE_O_LINK_DO_PWPUSH_AQUI]

Informamos que este link expira automaticamente após a primeira leitura ou em 24 horas. Salve a credencial de forma segura nas variáveis de ambiente do seu servidor.

Qualquer dúvida ou suporte técnico, estamos à disposição.

Atenciosamente,

Coordenação de Tecnologia e Informação
Secretaria Municipal de Trabalho e Assistência Social – SETAS
Prefeitura Municipal de Tomé-Açu / PA
```

---
**SETAS · Prefeitura Municipal de Tomé-Açu**
