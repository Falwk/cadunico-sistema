# Design Document — Visita Domiciliar Completa

## Overview

Este documento descreve o design técnico para a expansão do módulo de Visitas Domiciliares do sistema CadÚnico. A expansão adiciona seis capacidades ao sistema existente (Flask + SQLite/PostgreSQL + Cloudinary + ReportLab):

1. **Numeração automática** de solicitações no formato `VD-AAAA-NNNNNN`
2. **Geração de PDF** com identidade visual oficial via ReportLab
3. **Registro de resultado** da visita com formulário dedicado
4. **Upload de múltiplas fotos** da residência visitada
5. **Upload do Parecer da Assistente Social** em PDF
6. **Histórico de visitas por família** com controle de acesso por perfil

Todas as mudanças ocorrem dentro do único arquivo `app.py` e no diretório `templates/`. Nenhuma dependência nova é adicionada ao `requirements.txt`. O sistema continua compatível com SQLite (desenvolvimento) e PostgreSQL (produção via Render).

---

## Architecture

### Princípios de integração

O sistema já possui padrões estabelecidos que todas as novas funcionalidades seguem sem exceção:

- **Abstração de banco**: `_exec`, `_fetchone`, `_fetchall` + `PH` placeholder + `_adapt_sql`
- **Upload de mídia**: `_upload_anexo(file_obj, pasta)` → `(url, nome_original)`
- **Autenticação**: verificação `_requer_login()` no início de cada rota
- **Auditoria**: chamada `audit(acao, detalhe)` após qualquer mutação de estado
- **Templates**: `{% extends 'base.html' %}` com CSS classes `.card`, `.btn`, `.form-group`, `.alerta`

### Mapa de mudanças em `app.py`

```
app.py (existente ~2229 linhas)
│
├── init_db()                       MODIFICADO: adiciona novas tabelas e colunas via migração segura
├── nova_visita() [POST]             MODIFICADO: chama _gerar_numero_vd() antes do INSERT
│
├── _gerar_numero_vd(conn, ano)      NOVO: gera número sequencial atômico
├── gerar_pdf_visita(visita_id)      NOVO: retorna bytes do PDF via ReportLab
│
├── /visitas/<id>/pdf  [GET]         NOVA ROTA: entrega PDF como download
├── /visitas/<id>/resultado  [GET,POST]  NOVA ROTA: formulário de resultado dedicado
├── /visitas/<id>/fotos  [POST]      NOVA ROTA: upload de múltiplas fotos
├── /visitas/familia/<cpf>  [GET]    NOVA ROTA: histórico por família
│
├── detalhe_visita() [GET]           MODIFICADO: passa fotos, numero_vd, link histórico, flags
└── editar_visita() [POST]           MODIFICADO: aceita novo campo parecer_as
```

### Fluxo de criação de solicitação (Req. 1)

```
POST /visitas/nova
  → validar campos
  → abrir transação
      → _gerar_numero_vd(conn, ano_belem)
          → SELECT/INSERT em visita_contadores (lock atômico)
          → formatar "VD-{ano}-{n:06d}"
      → INSERT solicitacoes_visita com numero_vd
  → commit
  → redirect detalhe
```

### Fluxo de registro de resultado (Req. 3)

```
POST /visitas/<id>/resultado
  → validar data_realizada (obrigatório, não-futuro)
  → se parecer_as: validar extensão + tamanho → _upload_anexo(pasta='visitas_pareceres')
  → abrir transação
      → UPDATE solicitacoes_visita SET status='Realizada', data_realizada, observacoes,
                                       parecer_as_url, parecer_as_nome, atualizado_em
      → INSERT atendimentos (origem='Visita Domiciliar')
  → commit
  → audit + flash + redirect detalhe
```

---

## Database Schema Changes

### Novas colunas em `solicitacoes_visita`

| Coluna | Tipo | Nulável | Descrição |
|--------|------|---------|-----------|
| `numero_vd` | TEXT | SIM (NULL em registros antigos) | Identificador no formato `VD-AAAA-NNNNNN` |
| `parecer_as_url` | TEXT | SIM | URL Cloudinary do parecer da AS |
| `parecer_as_nome` | TEXT | SIM | Nome original do arquivo do parecer |

### Nova tabela `visita_contadores`

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS visita_contadores (
    ano             INTEGER PRIMARY KEY,
    ultimo_numero   INTEGER NOT NULL DEFAULT 0
);

-- PostgreSQL (equivalente; ano é chave primária)
CREATE TABLE IF NOT EXISTS visita_contadores (
    ano             INTEGER PRIMARY KEY,
    ultimo_numero   INTEGER NOT NULL DEFAULT 0
);
```

Essa tabela armazena um registro por ano (ex.: `ano=2026, ultimo_numero=42`). O incremento atômico usa `SELECT FOR UPDATE` no PostgreSQL e transação exclusiva no SQLite.

### Nova tabela `visita_fotos`

```sql
-- SQLite
CREATE TABLE IF NOT EXISTS visita_fotos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitacao_id  INTEGER NOT NULL REFERENCES solicitacoes_visita(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    nome_arquivo    TEXT NOT NULL,
    criado_em       TEXT NOT NULL
);

-- PostgreSQL
CREATE TABLE IF NOT EXISTS visita_fotos (
    id              SERIAL PRIMARY KEY,
    solicitacao_id  INTEGER NOT NULL REFERENCES solicitacoes_visita(id) ON DELETE CASCADE,
    url             TEXT NOT NULL,
    nome_arquivo    TEXT NOT NULL,
    criado_em       TEXT NOT NULL
);
```

### Estratégia de migração

As colunas novas em `solicitacoes_visita` são adicionadas via `ALTER TABLE … ADD COLUMN IF NOT EXISTS` (PostgreSQL) ou `ALTER TABLE … ADD COLUMN` envolvido em `try/except` (SQLite), exatamente como as migrações já existentes em `init_db()`. As tabelas novas usam `CREATE TABLE IF NOT EXISTS`. Não é necessário script de migração separado — `init_db()` é idempotente e roda em cada inicialização da aplicação.

```python
# Trecho de init_db() — PostgreSQL
migracoes_novas = [
    "ALTER TABLE solicitacoes_visita ADD COLUMN IF NOT EXISTS numero_vd TEXT",
    "ALTER TABLE solicitacoes_visita ADD COLUMN IF NOT EXISTS parecer_as_url TEXT",
    "ALTER TABLE solicitacoes_visita ADD COLUMN IF NOT EXISTS parecer_as_nome TEXT",
]

# Trecho de init_db() — SQLite
for col_sql in [
    "ALTER TABLE solicitacoes_visita ADD COLUMN numero_vd TEXT",
    "ALTER TABLE solicitacoes_visita ADD COLUMN parecer_as_url TEXT",
    "ALTER TABLE solicitacoes_visita ADD COLUMN parecer_as_nome TEXT",
]:
    try:
        c.execute(col_sql)
    except Exception:
        pass
```

---

## Components and Interfaces

### Função `_gerar_numero_vd(conn, ano: int) -> str`

**Localização**: `app.py`, nível de módulo (acima das rotas de visita)

**Responsabilidade**: Dentro de uma conexão já aberta (com transação em andamento), gera o próximo `numero_vd` para o ano informado de forma atômica.

```python
def _gerar_numero_vd(conn, ano: int) -> str:
    """
    Incrementa atomicamente o contador de VD para o ano e retorna
    o número no formato 'VD-AAAA-NNNNNN'.
    Lança ValueError se o contador atingir 999999.
    """
    if _USE_PG:
        # SELECT FOR UPDATE garante exclusão mútua em PostgreSQL
        row = _fetchone(conn,
            "SELECT ultimo_numero FROM visita_contadores WHERE ano = %s FOR UPDATE",
            (ano,)
        )
        if row is None:
            _exec(conn,
                "INSERT INTO visita_contadores (ano, ultimo_numero) VALUES (%s, 1)",
                (ano,)
            )
            proximo = 1
        else:
            proximo = row['ultimo_numero'] + 1
            if proximo > 999999:
                raise ValueError("limite_anual")
            _exec(conn,
                "UPDATE visita_contadores SET ultimo_numero = %s WHERE ano = %s",
                (proximo, ano)
            )
    else:
        # SQLite: a transação exclusiva da conexão já garante serialização
        row = _fetchone(conn,
            "SELECT ultimo_numero FROM visita_contadores WHERE ano = ?",
            (ano,)
        )
        if row is None:
            _exec(conn,
                "INSERT INTO visita_contadores (ano, ultimo_numero) VALUES (?, 1)",
                (ano,)
            )
            proximo = 1
        else:
            proximo = row['ultimo_numero'] + 1
            if proximo > 999999:
                raise ValueError("limite_anual")
            _exec(conn,
                "UPDATE visita_contadores SET ultimo_numero = ? WHERE ano = ?",
                (proximo, ano)
            )
    return f"VD-{ano}-{proximo:06d}"
```

**Integração com `nova_visita()`**: A chamada ocorre dentro de um bloco `try/except` que envolve o INSERT. Se `_gerar_numero_vd` lançar `ValueError("limite_anual")`, o handler exibe a mensagem de limite. Qualquer outra exceção exibe a mensagem de erro genérico de banco.

**Fuso horário para o ano**: O ano é obtido com:
```python
from datetime import timezone, timedelta
_TZ_BELEM = timezone(timedelta(hours=-3))
ano_belem = datetime.now(_TZ_BELEM).year
```

---

### Função `gerar_pdf_visita(visita_id: int) -> bytes`

**Localização**: `app.py`, nível de módulo

**Responsabilidade**: Abre o banco, busca a solicitação (404 se não encontrada), monta o PDF via ReportLab `SimpleDocTemplate` + `platypus` e retorna os bytes para o caller (a rota `/visitas/<id>/pdf`).

**Imports necessários** (adicionados ao topo de `app.py`):
```python
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Image, Spacer, HRFlowable
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
```

**Estrutura do documento gerado** (ver seção PDF Layout abaixo para detalhes visuais):
```python
def gerar_pdf_visita(visita_id: int) -> bytes:
    conn = get_db()
    visita = _fetchone(conn, "SELECT * FROM solicitacoes_visita WHERE id=?", (visita_id,))
    if not visita:
        conn.close()
        return None  # rota converte para 404

    solicitante = _fetchone(conn, "SELECT nome FROM usuarios WHERE id=?",
                            (visita['solicitante_id'],))
    responsavel = None
    if visita['responsavel_id']:
        responsavel = _fetchone(conn, "SELECT nome FROM usuarios WHERE id=?",
                                (visita['responsavel_id'],))
    conn.close()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = _build_pdf_story(visita, solicitante, responsavel)
    doc.build(story)
    return buf.getvalue()
```

A função auxiliar `_build_pdf_story(visita, solicitante, responsavel) -> list` constrói a lista de `Flowable`s.

---

### Validação de arquivos — funções auxiliares

```python
_EXTENSOES_FOTO    = {'.jpg', '.jpeg', '.png', '.webp'}
_EXTENSAO_PARECER  = '.pdf'
_TAMANHO_MAX_FOTO  = 10 * 1024 * 1024   # 10 MB
_TAMANHO_MAX_PARECER = 20 * 1024 * 1024  # 20 MB

def _extensao(filename: str) -> str:
    """Retorna extensão em minúsculas, ex: '.pdf'"""
    return os.path.splitext(filename)[1].lower()

def _validar_foto(arquivo) -> str | None:
    """Retorna mensagem de erro ou None se válido."""
    ext = _extensao(arquivo.filename)
    if ext not in _EXTENSOES_FOTO:
        return f"Formato não suportado: '{arquivo.filename}'. Use JPG, PNG ou WEBP."
    arquivo.seek(0, 2)
    tamanho = arquivo.tell()
    arquivo.seek(0)
    if tamanho > _TAMANHO_MAX_FOTO:
        return f"A imagem '{arquivo.filename}' excede o limite de 10 MB."
    return None

def _validar_parecer(arquivo) -> str | None:
    """Retorna mensagem de erro ou None se válido."""
    if _extensao(arquivo.filename) != _EXTENSAO_PARECER:
        return "O parecer deve ser um arquivo PDF."
    arquivo.seek(0, 2)
    tamanho = arquivo.tell()
    arquivo.seek(0)
    if tamanho > _TAMANHO_MAX_PARECER:
        return "O arquivo PDF excede o limite de 20 MB."
    return None
```

---

## New Routes / Endpoints

### `GET /visitas/<int:visita_id>/pdf`

**Função**: `pdf_visita(visita_id)`

| Aspecto | Detalhe |
|---------|---------|
| Auth | Obrigatória; redireciona para `/login` se não autenticado |
| Permissão | Mesmo critério de `detalhe_visita`: admin vê tudo; entrevistador só se for solicitante ou responsável |
| Sucesso | `200 OK`, `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="<numero_vd>.pdf"` |
| Visita não encontrada | `404` |
| ID inválido | Flask já retorna `404` pelo type-cast `<int:visita_id>` |

```python
@app.route('/visitas/<int:visita_id>/pdf', methods=['GET'])
def pdf_visita(visita_id):
    if _requer_login():
        return redirect(url_for('login'))
    # verificar permissão ...
    pdf_bytes = gerar_pdf_visita(visita_id)
    if pdf_bytes is None:
        abort(404)
    numero_vd = # busca numero_vd da visita
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{numero_vd or f'visita-{visita_id}'}.pdf"
    )
```

---

### `GET /visitas/<int:visita_id>/resultado`  
### `POST /visitas/<int:visita_id>/resultado`

**Função**: `resultado_visita(visita_id)`

| Método | Comportamento |
|--------|---------------|
| GET | Renderiza `resultado_visita.html` com o formulário |
| POST | Valida, faz upload do parecer (se fornecido), atualiza DB, cria atendimento |

**Parâmetros POST** (form-data, multipart):

| Campo | Tipo | Obrigatório | Validação |
|-------|------|-------------|-----------|
| `data_realizada` | `date` (YYYY-MM-DD) | Sim | ≤ data atual |
| `observacoes` | `text` | Não | — |
| `parecer_as` | `file` | Não | extensão `.pdf`, ≤ 20 MB |

**Permissão**: solicitante, responsável ou admin, e status não-terminal.

**Respostas**:
- `302` para `detalhe_visita` em caso de sucesso
- Re-renderiza formulário com erros em caso de validação falha
- Se upload do parecer falha: salva resultado sem URL, flash de aviso (não bloqueia)

**Separação de concerns**: esta rota é deliberadamente separada de `/visitas/<id>/status` para:
1. Ter validações próprias (data obrigatória, extensão PDF)
2. Criar o registro em `atendimentos` de forma explícita e auditável
3. Manter `/visitas/<id>/status` para transições simples de status (admin) sem a lógica de resultado

---

### `POST /visitas/<int:visita_id>/fotos`

**Função**: `upload_fotos_visita(visita_id)`

| Aspecto | Detalhe |
|---------|---------|
| Auth | Obrigatória |
| Permissão | Solicitante, responsável ou admin; status não-terminal |
| Content-Type | `multipart/form-data` |
| Campo de arquivo | `fotos` (multiple) |
| Sucesso | `302` de volta para `detalhe_visita` com flash de resumo |

**Lógica de processamento**:
1. Busca a visita e verifica permissão/status
2. Conta fotos já existentes: `SELECT COUNT(*) FROM visita_fotos WHERE solicitacao_id=?`
3. Para cada arquivo em `request.files.getlist('fotos')`:
   - Valida extensão → erro individual se inválida
   - Valida tamanho → erro individual se excede 10 MB
   - Verifica se a adição excederia o limite de 10 → rejeita os excedentes
   - Se passa todas as validações → `_upload_anexo(arquivo, pasta='visitas_fotos')`
   - Se upload OK → INSERT em `visita_fotos`
4. Commit único ao final
5. Flash consolidado: "X foto(s) adicionada(s). Rejeitadas: [lista de erros]."

---

### `GET /visitas/familia/<cpf>`

**Função**: `historico_familia(cpf)`

| Aspecto | Detalhe |
|---------|---------|
| Auth | Obrigatória |
| Parâmetro URL | `cpf` — pode conter pontos/hífen ou só dígitos |
| CPF inválido | HTTP 400 + mensagem "CPF inválido." |
| Perfil `entrevistador` | Filtra por `solicitante_id = uid OR responsavel_id = uid` |
| Perfil `admin` | Sem filtro adicional |
| Ordem | `criado_em DESC` |
| Template | `historico_familia.html` |

```python
@app.route('/visitas/familia/<cpf>', methods=['GET'])
def historico_familia(cpf):
    if _requer_login():
        return redirect(url_for('login'))
    cpf_digits = ''.join(c for c in cpf if c.isdigit())
    if not validar_cpf(cpf_digits):
        return render_template('erro_400.html',
                               msg='CPF inválido.'), 400
    # query com filtro por perfil ...
    return render_template('historico_familia.html', visitas=visitas, cpf=cpf_digits)
```

**Nota de rota**: a rota `/visitas/familia/<cpf>` é registrada **antes** de `/visitas/<int:visita_id>` no arquivo para evitar conflito de prefixo. Como Flask usa `<int:…>` para IDs numéricos, não há colisão na prática, mas a ordem explícita é mais segura.

---

## Data Models

### `solicitacoes_visita` — estado pós-migração

```
id                  PK
cpf_rf              TEXT NOT NULL
nome_rf             TEXT NOT NULL
logradouro          TEXT NOT NULL DEFAULT ''
numero              TEXT NOT NULL DEFAULT ''
complemento         TEXT
bairro              TEXT NOT NULL DEFAULT ''
referencia          TEXT
zona                TEXT NOT NULL DEFAULT 'Urbana'
motivo              TEXT NOT NULL
data_realizada      TEXT
status              TEXT NOT NULL DEFAULT 'Pendente'
solicitante_id      INTEGER FK → usuarios.id
responsavel_id      INTEGER FK → usuarios.id (nullable)
observacoes         TEXT
motivo_cancelamento TEXT
anexo_url           TEXT
anexo_nome          TEXT
atendimento_id      INTEGER
numero_vd           TEXT          ← NOVO
parecer_as_url      TEXT          ← NOVO
parecer_as_nome     TEXT          ← NOVO
criado_em           TEXT NOT NULL
atualizado_em       TEXT NOT NULL
```

### `visita_contadores`

```
ano             INTEGER PK
ultimo_numero   INTEGER NOT NULL DEFAULT 0
```

Exemplo de estado: `{ ano: 2026, ultimo_numero: 142 }` significa que a 142ª VD de 2026 foi `VD-2026-000142`.

### `visita_fotos`

```
id              PK (AUTOINCREMENT / SERIAL)
solicitacao_id  INTEGER FK → solicitacoes_visita.id (ON DELETE CASCADE)
url             TEXT NOT NULL   (URL Cloudinary)
nome_arquivo    TEXT NOT NULL   (nome original do arquivo)
criado_em       TEXT NOT NULL   (ISO 8601)
```

---

## PDF Layout Description

O PDF é gerado em formato A4 (21 × 29,7 cm) com margens de 2 cm em todos os lados.

### Seção 1 — Cabeçalho com logos (altura ~3 cm)

Implementado como uma `Table` de 1 linha × 3 colunas com larguras proporcionais (3 cm | auto | 3 cm):

| Coluna esquerda | Centro | Coluna direita |
|-----------------|--------|----------------|
| `cadunico.png` (3 × 3 cm, preserva proporção) | Título "SOLICITAÇÃO DE VISITA DOMICILIAR" em negrito + subtítulo "Secretaria de Assistência Social" em cinza | `bolsafamilia.png` (3 × 3 cm) |

Abaixo da tabela de logos, centralizado, o brasão `prefeitura.png` (4 × 2 cm) + nome do município.

Se qualquer arquivo de logo não existir em `static/logos/`, o `Image` é simplesmente omitido (verificação `os.path.exists` antes de instanciar). A `Table` ainda é gerada com a célula em branco.

### Seção 2 — Número e status (barra colorida)

```
┌─────────────────────────────────────────────────────────────┐
│  Nº VD-2026-000001                          Status: Pendente│
└─────────────────────────────────────────────────────────────┘
```

`Table` de 1 linha × 2 colunas com `BACKGROUND` `#1F4E79` (azul escuro), texto branco, fonte Helvetica-Bold 12.

### Seção 3 — Dados do beneficiário

`Table` de múltiplas linhas com cabeçalhos de campo em `#F5F6F8` (cinza claro) e valores em branco. Colunas adaptadas para 2 por linha onde possível.

```
CPF do RF:         [cpf_rf]          Nome do RF:   [nome_rf]
Logradouro:        [logradouro, nº, complemento]
Bairro:            [bairro]          Zona:         [zona]
Ponto de ref.:     [referencia ou —]
Motivo da visita:  [motivo]
```

### Seção 4 — Dados administrativos

```
Data de criação:   [DD/MM/AAAA]     Status:        [status]
Solicitante:       [nome]            Responsável:   [nome ou "Não atribuído"]
Data realizada:    [DD/MM/AAAA ou —]
```

### Seção 5 — Observações (condicional)

`Paragraph` com label "Observações:" em bold se `visita['observacoes']` não for nulo.

### Seção 6 — Campos de assinatura

`HRFlowable` (linha horizontal de 8 cm) × 2, dispostos em `Table` de 1 linha × 2 colunas:

```
________________________             ________________________
Assinatura do Entrevistador          Assinatura do RF
[nome do responsável]                [nome do RF]
```

### Seção 7 — Rodapé

`Table` de 1 linha com `BACKGROUND` `#F5F6F8`. Texto: nome do setor, endereço, e-mail, município. Fonte tamanho 8, cor `#4B5563`.

---

## Template Changes

### `templates/nova_visita.html` — sem alteração de layout

A rota `nova_visita()` é modificada em Python para chamar `_gerar_numero_vd` e inserir `numero_vd` no banco. O template não precisa ser alterado pois o número não é exibido no formulário de criação — apenas nas páginas de detalhe e listagem.

---

### `templates/detalhe_visita.html` — modificações

1. **Exibir `numero_vd`** junto ao badge de status (ex.: `VD-2026-000001 · #42 · criado em …`).

2. **Botão "Baixar PDF"** — sempre visível para usuários autenticados:
   ```html
   <a href="{{ url_for('pdf_visita', visita_id=visita.id) }}"
      class="btn btn-outline btn-sm" target="_blank">📄 Baixar PDF</a>
   ```

3. **Botão "Registrar Resultado da Visita"** — visível somente se `pode_registrar_resultado`:
   ```html
   {% if pode_registrar_resultado %}
   <a href="{{ url_for('resultado_visita', visita_id=visita.id) }}"
      class="btn btn-primary">✅ Registrar Resultado da Visita</a>
   {% endif %}
   ```
   A flag `pode_registrar_resultado` é calculada no view: `visita.status in ('Pendente', 'Em Andamento') AND tem_permissao`.

4. **Seção de Parecer AS** — condicional, logo após os dados principais:
   ```html
   {% if visita.parecer_as_url %}
   <div class="card">
     <div class="card-title">Parecer da Assistente Social</div>
     <a href="{{ visita.parecer_as_url }}" target="_blank"
        class="btn btn-outline btn-sm" download="{{ visita.parecer_as_nome }}">
       📎 {{ visita.parecer_as_nome }}
     </a>
   </div>
   {% endif %}
   ```

5. **Seção de Fotos** — grid de miniaturas com link para imagem completa:
   ```html
   {% if fotos %}
   <div class="card">
     <div class="card-title">Fotos da Residência</div>
     <div style="display:flex;flex-wrap:wrap;gap:8px">
       {% for foto in fotos %}
       <a href="{{ foto.url }}" target="_blank">
         <img src="{{ foto.url }}" alt="{{ foto.nome_arquivo }}"
              style="width:100px;height:100px;object-fit:cover;border-radius:6px">
       </a>
       {% endfor %}
     </div>
   </div>
   {% endif %}
   ```

6. **Formulário de upload de fotos** — exibido para status não-terminais:
   ```html
   {% if pode_editar %}
   <div class="card">
     <div class="card-title">Adicionar Fotos da Residência</div>
     <form method="POST" action="{{ url_for('upload_fotos_visita', visita_id=visita.id) }}"
           enctype="multipart/form-data">
       <div class="form-group">
         <input type="file" name="fotos" multiple
                accept=".jpg,.jpeg,.png,.webp">
         <p class="text-muted" style="font-size:.82rem;margin-top:6px">
           JPG, PNG ou WEBP. Máx. 10 MB por imagem. Limite de 10 fotos por solicitação.
         </p>
       </div>
       <button type="submit" class="btn btn-outline btn-sm">Enviar Fotos</button>
     </form>
   </div>
   {% endif %}
   ```

7. **Link "Ver Histórico da Família"** — sempre visível:
   ```html
   <a href="{{ url_for('historico_familia', cpf=visita.cpf_rf) }}"
      class="btn btn-outline btn-sm">🏠 Ver Histórico da Família</a>
   ```

---

### `templates/painel_visitas.html` — modificações

Adicionar coluna `Nº VD` na tabela, entre a coluna "Data" e "CPF do RF":
```html
<th>Nº VD</th>
...
<td>{{ v.numero_vd or '—' }}</td>
```

---

### `templates/editar_visita.html` — modificações

Adicionar seção de upload do Parecer AS (análogo ao campo de `anexo`):
```html
<div class="card">
  <div class="card-title">Parecer da Assistente Social
    <span class="text-muted" style="font-weight:400">(opcional)</span>
  </div>
  {% if visita.parecer_as_nome %}
  <p style="margin-bottom:10px;font-size:.88rem">
    Parecer atual: <a href="{{ visita.parecer_as_url }}" target="_blank">
      {{ visita.parecer_as_nome }}</a>
  </p>
  {% endif %}
  <div class="form-group">
    <input type="file" name="parecer_as" accept=".pdf">
    <p class="text-muted" style="font-size:.82rem;margin-top:6px">
      Somente PDF. Máx. 20 MB.
    </p>
  </div>
</div>
```

---

### `templates/resultado_visita.html` — NOVO

Template estendendo `base.html` com:
- Card "Registrar Resultado da Visita"
- Campo `data_realizada` (type=date, max={{ hoje }}, required)
- Campo `observacoes` (textarea, opcional)
- Campo `parecer_as` (file, accept=".pdf", opcional)
- Botões Cancelar (volta para detalhe) e Salvar

---

### `templates/historico_familia.html` — NOVO

Template estendendo `base.html` com:
- Título "Histórico de Visitas — CPF [cpf formatado]"
- Tabela: Nº VD | Data/Hora | Motivo | Status (badge colorido) | Responsável | Link Detalhe
- Mensagem de vazio: "Nenhuma visita domiciliar registrada para este CPF."
- Botão "+ Nova Solicitação" pré-preenchendo o CPF na query string

---

## Correctness Properties

*Uma propriedade é uma característica ou comportamento que deve ser verdadeiro em toda execução válida do sistema — essencialmente, uma afirmação formal sobre o que o sistema deve fazer. Propriedades servem como ponte entre especificações legíveis por humanos e garantias de correção verificáveis por máquina.*

---

### Property 1: Número VD tem formato correto

*Para qualquer* solicitação de visita criada com sucesso, o campo `numero_vd` retornado deve corresponder ao padrão `VD-\d{4}-\d{6}` e o componente de ano deve ser igual ao ano de criação.

**Validates: Requirements 1.1, 1.4**

---

### Property 2: Números VD são únicos por ano

*Para qualquer* conjunto de N solicitações inseridas no mesmo ano, todos os valores de `numero_vd` devem ser distintos entre si.

**Validates: Requirements 1.2**

---

### Property 3: Virada de ano reinicia o contador

*Para qualquer* ano Y com pelo menos um registro, a primeira solicitação inserida com ano Y+1 deve ter `numero_vd` terminando em `000001`.

**Validates: Requirements 1.3**

---

### Property 4: PDF sempre contém os dados da solicitação

*Para qualquer* solicitação de visita com `numero_vd`, CPF do RF e nome do RF definidos, o texto extraído do PDF gerado por `gerar_pdf_visita` deve conter o `numero_vd`, o CPF do RF e o nome do RF.

**Validates: Requirements 2.1, 2.3**

---

### Property 5: PDF sempre contém campos de assinatura

*Para qualquer* solicitação de visita válida, o texto extraído do PDF gerado deve conter as strings "Assinatura do Entrevistador" e "Assinatura do RF".

**Validates: Requirements 2.4**

---

### Property 6: Botão de resultado aparece exatamente para status não-terminais com permissão

*Para qualquer* solicitação com status `Pendente` ou `Em Andamento` e um usuário que seja solicitante, responsável ou admin, o template `detalhe_visita.html` renderizado deve conter o botão "Registrar Resultado da Visita".

*Para qualquer* solicitação com status `Realizada` ou `Cancelada`, o botão não deve aparecer, independentemente do perfil do usuário.

**Validates: Requirements 3.1, 3.7**

---

### Property 7: Submissão do resultado com data válida transiciona para Realizada

*Para qualquer* data passada ou presente válida submetida no formulário de resultado de uma solicitação não-terminal, o status da solicitação deve ser atualizado para `Realizada`, `data_realizada` deve ser persistida e um registro deve ser criado em `atendimentos` com `origem = 'Visita Domiciliar'`.

**Validates: Requirements 3.3**

---

### Property 8: Datas futuras são rejeitadas no resultado

*Para qualquer* data futura (posterior à data atual) submetida como `data_realizada`, o formulário de resultado deve ser rejeitado com a mensagem "A data de realização não pode ser uma data futura." e nenhuma alteração deve ocorrer no banco.

**Validates: Requirements 3.6**

---

### Property 9: Apenas arquivos com extensão válida são aceitos no upload de fotos

*Para qualquer* arquivo enviado com extensão fora do conjunto `{.jpg, .jpeg, .png, .webp}` (comparação case-insensitive), o sistema deve rejeitar esse arquivo individualmente com mensagem de formato não suportado. Arquivos válidos no mesmo lote devem ser processados normalmente.

**Validates: Requirements 4.2, 4.3, 4.6**

---

### Property 10: Limite de 10 fotos é sempre respeitado

*Para qualquer* sequência de uploads válidos para uma mesma solicitação, o número total de registros em `visita_fotos` para aquela solicitação nunca deve exceder 10. Qualquer arquivo que excederia esse limite deve ser rejeitado com a mensagem "Limite de 10 fotos por solicitação atingido."

**Validates: Requirements 4.4**

---

### Property 11: Fotos armazenadas são recuperáveis via detalhe da solicitação

*Para qualquer* solicitação com N fotos em `visita_fotos`, o template `detalhe_visita.html` renderizado deve conter exatamente N elementos `<img>` vinculados às URLs das fotos.

**Validates: Requirements 4.7, 4.8**

---

### Property 12: Parecer AS válido é armazenado e exibido como link de download

*Para qualquer* arquivo `.pdf` com tamanho ≤ 20 MB enviado como Parecer AS, após upload com sucesso, a URL e o nome original devem ser persistidos em `solicitacoes_visita`, e o template `detalhe_visita.html` deve conter um `<a>` com `href` apontando para essa URL.

**Validates: Requirements 5.3, 5.6**

---

### Property 13: Histórico de família exibe todos os registros em ordem cronológica decrescente

*Para qualquer* CPF com N solicitações associadas, a rota `/visitas/familia/<cpf>` deve exibir exatamente N solicitações ordenadas por `criado_em` descendente.

**Validates: Requirements 6.1**

---

### Property 14: Filtro por perfil no histórico de família

*Para qualquer* usuário com perfil `entrevistador`, a rota `/visitas/familia/<cpf>` deve exibir somente as solicitações onde `solicitante_id` ou `responsavel_id` corresponde ao ID do usuário autenticado.

*Para qualquer* usuário com perfil `admin`, todas as solicitações para o CPF devem ser exibidas, sem filtro por usuário.

**Validates: Requirements 6.5, 6.6**

---

### Property 15: CPF inválido na URL retorna HTTP 400

*Para qualquer* string que, após remoção de caracteres não-dígitos, não corresponda a um CPF com 11 dígitos e dígitos verificadores válidos, a rota `/visitas/familia/<cpf>` deve retornar HTTP 400 com a mensagem "CPF inválido."

**Validates: Requirements 6.7**

---

## Error Handling

### Erros de banco de dados na geração do Número VD (Req. 1.6 e 1.7)

```python
# Em nova_visita(), bloco POST:
try:
    with conn:  # transação
        ano_belem = datetime.now(_TZ_BELEM).year
        numero_vd = _gerar_numero_vd(conn, ano_belem)
        # ... INSERT solicitacoes_visita ...
except ValueError as e:
    conn.close()
    if str(e) == "limite_anual":
        flash("Limite de solicitações para o ano atingido. Contate o administrador.", "erro")
    else:
        flash("Erro ao gerar número da solicitação. Tente novamente.", "erro")
    return render_template('nova_visita.html', erros=erros, form=form, usuarios=usuarios)
except Exception:
    conn.rollback()
    conn.close()
    flash("Erro ao gerar número da solicitação. Tente novamente.", "erro")
    return render_template('nova_visita.html', erros=erros, form=form, usuarios=usuarios)
```

### Falha de upload do Parecer AS no resultado (Req. 3.8)

O upload é tentado antes do UPDATE. Se `_upload_anexo` retornar `(None, None)`, o resultado é salvo sem URL e um `flash` de aviso é exibido após o commit. A visita **não** fica em estado inconsistente.

### Falha de upload de foto individual (Req. 4.3)

Cada arquivo é tentado individualmente. Erros de Cloudinary para um arquivo não interrompem o processamento dos demais. Uma lista de erros é acumulada e exibida no flash consolidado.

### Substituição de Parecer AS — remoção do arquivo anterior (Req. 5.7)

```python
# Em editar_visita() POST, quando novo parecer_as é fornecido:
if visita['parecer_as_url']:
    try:
        import cloudinary.uploader
        # Extrai public_id da URL e chama destroy
        public_id = _extrair_public_id_cloudinary(visita['parecer_as_url'])
        if public_id:
            cloudinary.uploader.destroy(public_id)
    except Exception as e:
        app.logger.warning(f"Falha ao remover parecer anterior do Cloudinary: {e}")
        # Não bloqueia — segue com o upload do novo
```

A função `_extrair_public_id_cloudinary(url: str) -> str | None` extrai o public_id a partir da estrutura da URL do Cloudinary (`…/upload/v<version>/<folder>/<nome>`). Em caso de falha na extração ou remoção, apenas um warning é logado — o arquivo orphan no Cloudinary é aceitável como trade-off de resiliência.

### Visita não encontrada / acesso negado

Todas as rotas novas seguem o padrão existente:
- Visita inexistente: `abort(404)` para rotas de PDF; `flash + redirect` para rotas HTML
- Acesso negado (entrevistador sem permissão): `flash('Acesso negado.', 'erro') + redirect painel`
- Status terminal em rota de resultado: `flash + redirect detalhe`

### Validação de CPF na rota de histórico

```python
cpf_digits = ''.join(c for c in cpf if c.isdigit())
if not validar_cpf(cpf_digits):
    return render_template('erro_generico.html',
                           codigo=400, msg='CPF inválido.'), 400
```

Se `templates/erro_400.html` não existir, usar o template genérico de erro já existente no projeto.

---

## Testing Strategy

### Abordagem dual

- **Testes unitários**: exemplos concretos, condições de erro, integrações entre componentes
- **Testes de propriedade**: verificam propriedades universais via Hypothesis (já presente no projeto, conforme `.hypothesis/` no repositório)

### Testes de propriedade (Hypothesis)

**Biblioteca**: `hypothesis` (já instalada — evidenciada pela presença do diretório `.hypothesis/`)

**Configuração**: cada teste de propriedade deve rodar com `@settings(max_examples=100)` e incluir um comentário de rastreamento:

```python
# Feature: visita-domiciliar-completa, Property 1: numero_vd formato correto
@given(st.text(min_size=1), st.text(min_size=1), ...)
@settings(max_examples=100)
def test_numero_vd_formato(cpf, nome, ...):
    ...
```

**Isolamento de banco**: usar SQLite em memória (`:memory:`) para todos os testes de propriedade — zero I/O, execução rápida, 100 iterações por teste são viáveis.

**Mocking de Cloudinary**: usar `unittest.mock.patch('cloudinary.uploader.upload')` retornando `{'secure_url': 'https://fake.url/img.jpg'}` para testes de upload.

### Testes unitários (exemplos e casos de borda)

| Caso | Tipo | Critério validado |
|------|------|-------------------|
| Criar visita → numero_vd gerado | Exemplo | Req. 1.4 |
| Limite de 999999 → mensagem específica | Edge case | Req. 1.7 |
| `GET /visitas/<id>/pdf` sem login → 302 | Exemplo | Req. 2.7 |
| `GET /visitas/99999/pdf` → 404 | Edge case | Req. 2.8 |
| Resultado sem data → mensagem | Edge case | Req. 3.5 |
| Parecer AS com .docx → rejeitado | Edge case | Req. 5.4 |
| Parecer AS > 20 MB → rejeitado | Edge case | Req. 5.5 |
| Histórico família CPF vazio → mensagem | Edge case | Req. 6.3 |
| Upload Cloudinary falha → resultado salvo sem URL | Edge case | Req. 3.8 |
| Logo ausente → PDF gerado sem exceção | Edge case | Req. 2.6 |

### Cobertura por requisito

| Requisito | Properties | Exemplos/Edge cases |
|-----------|-----------|---------------------|
| 1 — Numeração VD | P1, P2, P3 | límite 999999, falha DB |
| 2 — PDF | P4, P5 | auth, 404, logos ausentes |
| 3 — Resultado | P6, P7, P8 | sem data, falha Cloudinary |
| 4 — Fotos | P9, P10, P11 | extensão inválida, UI |
| 5 — Parecer AS | P12 | ext inválida, tamanho, substituição |
| 6 — Histórico | P13, P14, P15 | vazio, link detalhe |
