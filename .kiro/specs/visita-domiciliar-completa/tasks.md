# Implementation Plan: Visita Domiciliar Completa

## Overview

Expansão do módulo de Visitas Domiciliares do CadÚnico (Flask + SQLite/PostgreSQL + Cloudinary + ReportLab).
As implementações ocorrem em `app.py` e no diretório `templates/`. Nenhuma dependência nova é adicionada.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1"] },
    { "wave": 2, "tasks": ["2"] },
    { "wave": 3, "tasks": ["3"] },
    { "wave": 4, "tasks": ["4", "5", "6", "8"] },
    { "wave": 5, "tasks": ["7"] }
  ]
}
```

## Tasks

- [x] 1. Migração do banco de dados e novas tabelas
  - [x] 1.1 Adicionar novas colunas em `solicitacoes_visita` e criar tabelas `visita_contadores` e `visita_fotos` em `init_db()`
    - Adicionar `numero_vd TEXT`, `parecer_as_url TEXT`, `parecer_as_nome TEXT` via `ALTER TABLE … ADD COLUMN IF NOT EXISTS` (PostgreSQL) e `ALTER TABLE … ADD COLUMN` em `try/except` (SQLite)
    - Criar `visita_contadores (ano INTEGER PK, ultimo_numero INTEGER NOT NULL DEFAULT 0)` com `CREATE TABLE IF NOT EXISTS`
    - Criar `visita_fotos (id PK AUTOINCREMENT/SERIAL, solicitacao_id INTEGER NOT NULL FK → solicitacoes_visita(id) ON DELETE CASCADE, url TEXT NOT NULL, nome_arquivo TEXT NOT NULL, criado_em TEXT NOT NULL)` com `CREATE TABLE IF NOT EXISTS`
    - Garantir idempotência: rodar `init_db()` múltiplas vezes não deve gerar erro
    - _Requisitos: 1.1, 1.2, 1.4, 4.8_

- [x] 2. Numeração automática VD-AAAA-NNNNNN
  - [x] 2.1 Adicionar constante `_TZ_BELEM` e implementar `_gerar_numero_vd(conn, ano: int) -> str` em `app.py`
    - Adicionar `from datetime import timezone, timedelta` e `_TZ_BELEM = timezone(timedelta(hours=-3))`
    - PostgreSQL: `SELECT ultimo_numero FROM visita_contadores WHERE ano = %s FOR UPDATE` + UPDATE/INSERT atômico
    - SQLite: SELECT + UPDATE/INSERT dentro da transação exclusiva da conexão
    - Lançar `ValueError("limite_anual")` se `proximo > 999999`
    - Retornar `f"VD-{ano}-{proximo:06d}"`
    - _Requisitos: 1.1, 1.2, 1.3, 1.7_

  - [x] 2.2 Modificar `nova_visita()` para chamar `_gerar_numero_vd` antes do INSERT
    - Calcular `ano_belem = datetime.now(_TZ_BELEM).year` antes de abrir a transação
    - Chamar `_gerar_numero_vd(conn, ano_belem)` e incluir `numero_vd` no INSERT de `solicitacoes_visita`
    - Capturar `ValueError("limite_anual")` → `flash("Limite de solicitações para o ano atingido. Contate o administrador.", "erro")` e `return render_template`
    - Capturar `Exception` genérica → `flash("Erro ao gerar número da solicitação. Tente novamente.", "erro")` e rollback
    - _Requisitos: 1.1, 1.4, 1.6, 1.7_

- [x] 3. Checkpoint — banco e numeração
  - Verificar que `init_db()` roda sem erros em SQLite
  - Verificar que as três tabelas novas/modificadas existem com as colunas corretas
  - Verificar que `_gerar_numero_vd` retorna formato `VD-2026-000001` na primeira chamada
  - Executar testes existentes em `tests/` para garantir que nada foi quebrado

- [x] 4. Geração de PDF com identidade visual oficial
  - [x] 4.1 Adicionar imports do ReportLab ao topo de `app.py`
    - Importar `SimpleDocTemplate`, `Table`, `TableStyle`, `Paragraph`, `Image`, `Spacer`, `HRFlowable` de `reportlab.platypus`
    - Importar `A4` de `reportlab.lib.pagesizes`, `getSampleStyleSheet`, `ParagraphStyle` de `reportlab.lib.styles`, `cm` de `reportlab.lib.units`, `colors` de `reportlab.lib`
    - _Requisitos: 2.1_

  - [x] 4.2 Implementar `_build_pdf_story(visita, solicitante, responsavel) -> list` em `app.py`
    - **Cabeçalho**: `Table` 1×3 — `cadunico.png` à esquerda (3×3 cm), título + subtítulo centralizado, `bolsafamilia.png` à direita (3×3 cm); verificar `os.path.exists` antes de instanciar `Image`; abaixo: brasão `prefeitura.png` (4×2 cm) centralizado com nome do município
    - **Barra número/status**: `Table` 1×2 com fundo `#1F4E79`, texto branco, Helvetica-Bold 12; coluna esq: `numero_vd`; coluna dir: `Status: <status>`
    - **Dados beneficiário**: `Table` multilinha; cabeçalhos de campo em fundo `#F5F6F8`; CPF, nome, logradouro+número+complemento, bairro+zona, referência, motivo
    - **Dados administrativos**: data criação DD/MM/AAAA, solicitante, responsável (ou "Não atribuído"), data realizada se houver
    - **Observações**: `Paragraph` condicional se `visita['observacoes']` não é nulo/vazio
    - **Assinaturas**: `Table` 1×2; cada célula: `HRFlowable` 8 cm + label + nome; rótulos "Assinatura do Entrevistador" e "Assinatura do RF"
    - **Rodapé**: `Table` 1 linha, fundo `#F5F6F8`, fonte 8, cor `#4B5563`; texto: setor, endereço, e-mail, município
    - _Requisitos: 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 4.3 Implementar `gerar_pdf_visita(visita_id: int) -> bytes | None` em `app.py`
    - Buscar visita, solicitante e responsável no banco; retornar `None` se visita não encontrada
    - Criar `SimpleDocTemplate` em `io.BytesIO()` com `pagesize=A4`, margens de 2 cm
    - Chamar `_build_pdf_story`; `doc.build(story)`; retornar `buf.getvalue()`
    - _Requisitos: 2.1, 2.3_

  - [x] 4.4 Implementar rota `GET /visitas/<int:visita_id>/pdf` (`pdf_visita`)
    - Verificar `_requer_login()` → redirecionar para `/login`
    - Verificar permissão: admin vê tudo; entrevistador só se `solicitante_id == uid or responsavel_id == uid`
    - Chamar `gerar_pdf_visita(visita_id)`; `abort(404)` se retornar `None`
    - `return send_file(io.BytesIO(pdf_bytes), mimetype='application/pdf', as_attachment=True, download_name=f"{numero_vd or f'visita-{visita_id}'}.pdf")`
    - _Requisitos: 2.1, 2.7, 2.8, 2.9_

- [ ] 5. Registro do resultado da visita
  - [x] 5.1 Implementar rota `GET|POST /visitas/<int:visita_id>/resultado` (`resultado_visita`)
    - GET: buscar visita; verificar permissão e status não-terminal; renderizar `resultado_visita.html` com `visita`, `hoje=date.today().isoformat()`
    - POST: extrair `data_realizada`, `observacoes`, arquivo `parecer_as`
    - Validações: `data_realizada` obrigatória → mensagem "Informe a data de realização da visita."; data futura → mensagem "A data de realização não pode ser uma data futura."
    - Se `parecer_as` fornecido: chamar `_validar_parecer(arquivo)`; se válido chamar `_upload_anexo(arquivo, pasta='visitas_pareceres')`; se upload falhar: salvar sem URL e flash de aviso (não bloquear)
    - UPDATE `solicitacoes_visita` SET status='Realizada', data_realizada, observacoes, parecer_as_url, parecer_as_nome, atualizado_em WHERE id=visita_id
    - INSERT em `atendimentos` (data, cpf, nome_rf, origem='Visita Domiciliar', tipos='Visita Domiciliar', usuario_id, criado_em) com RETURNING id (PG) ou lastrowid (SQLite)
    - UPDATE `solicitacoes_visita SET atendimento_id=<novo_id>` WHERE id=visita_id
    - `audit('VISITA_RESULTADO', f"id={visita_id}")` + flash "Resultado registrado com sucesso!" + redirect `detalhe_visita`
    - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [x] 5.2 Implementar `_validar_foto` e `_validar_parecer` como funções auxiliares em `app.py`
    - `_EXTENSOES_FOTO = {'.jpg', '.jpeg', '.png', '.webp'}`; `_EXTENSAO_PARECER = '.pdf'`
    - `_TAMANHO_MAX_FOTO = 10 * 1024 * 1024`; `_TAMANHO_MAX_PARECER = 20 * 1024 * 1024`
    - `_extensao(filename)` → `os.path.splitext(filename)[1].lower()`
    - `_validar_foto(arquivo)` → string de erro ou None; verifica extensão e tamanho (seek 0,2 / tell / seek 0)
    - `_validar_parecer(arquivo)` → string de erro ou None; verifica extensão e tamanho
    - _Requisitos: 3.4, 4.2, 4.5, 4.6, 5.2, 5.4, 5.5_

  - [x] 5.3 Criar template `templates/resultado_visita.html`
    - Extender `base.html`; título "Registrar Resultado da Visita"
    - Exibir Número VD e nome do RF no subtítulo
    - Card com: `data_realizada` (input type=date, max={{ hoje }}, required), `observacoes` (textarea), `parecer_as` (input type=file, accept=".pdf")
    - Exibir erros via `{% for e in erros %}<div class="alerta alerta-erro">{{ e }}</div>{% endfor %}`
    - Botões: "Cancelar" (link para `detalhe_visita`) e "Salvar Resultado" (submit)
    - _Requisitos: 3.2, 3.5, 3.6_

- [x] 6. Upload de múltiplas fotos da residência
  - [x] 6.1 Implementar rota `POST /visitas/<int:visita_id>/fotos` (`upload_fotos_visita`)
    - Verificar autenticação, permissão (solicitante, responsável ou admin) e status não-terminal
    - Contar fotos existentes: `SELECT COUNT(*) FROM visita_fotos WHERE solicitacao_id=?`
    - Para cada arquivo em `request.files.getlist('fotos')`:
      - `_validar_foto(arquivo)` → erro individual se inválido
      - Verificar se adição excederia limite de 10 → rejeitar excedentes com mensagem
      - Se válido: `_upload_anexo(arquivo, pasta='visitas_fotos')` → INSERT em `visita_fotos`
    - Commit único ao final
    - Flash consolidado com contagem de sucessos e lista de erros
    - Redirect para `detalhe_visita`
    - _Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 4.9_

- [x] 7. Atualizar templates existentes
  - [x] 7.1 Atualizar `templates/detalhe_visita.html`
    - Exibir `numero_vd` junto ao badge de status (ex.: `VD-2026-000001 · #{{ visita.id }} · criado em …`)
    - Adicionar botão "📄 Baixar PDF" → `url_for('pdf_visita', visita_id=visita.id)` (sempre visível)
    - Adicionar botão "✅ Registrar Resultado da Visita" → `url_for('resultado_visita', visita_id=visita.id)` visível apenas se `pode_registrar_resultado`
    - Adicionar seção "Parecer da Assistente Social" condicional (link download com `download="{{ visita.parecer_as_nome }}"`)
    - Adicionar seção "Fotos da Residência" com grid de miniaturas 100×100 px clicáveis (nova aba)
    - Adicionar formulário de upload de fotos (field `fotos`, multiple, accept=".jpg,.jpeg,.png,.webp") para status não-terminais
    - Adicionar link "🏠 Ver Histórico da Família" → `url_for('historico_familia', cpf=visita.cpf_rf)`
    - Passar `pode_registrar_resultado` e `fotos` do view para o template
    - _Requisitos: 2.1, 3.1, 3.7, 4.1, 4.7, 5.6, 6.4_

  - [x] 7.2 Atualizar `templates/painel_visitas.html`
    - Adicionar coluna "Nº VD" na tabela (entre Data e CPF do RF)
    - Exibir `{{ v.numero_vd or '—' }}` na coluna
    - _Requisitos: 1.5_

  - [x] 7.3 Atualizar `templates/editar_visita.html`
    - Adicionar seção "Parecer da Assistente Social" com campo `parecer_as` (type=file, accept=".pdf")
    - Exibir link do parecer atual se existir
    - Adicionar `enctype="multipart/form-data"` ao form se não presente
    - _Requisitos: 5.1_

  - [x] 7.4 Atualizar `detalhe_visita()` view em `app.py`
    - Buscar `fotos = _fetchall(conn, "SELECT * FROM visita_fotos WHERE solicitacao_id=? ORDER BY criado_em", (visita_id,))`
    - Calcular `pode_registrar_resultado = visita['status'] in ('Pendente', 'Em Andamento') and tem_permissao`
    - Passar `fotos`, `pode_registrar_resultado` para o template
    - _Requisitos: 3.1, 4.7_

  - [x] 7.5 Atualizar `editar_visita()` view em `app.py`
    - Extrair e validar `parecer_as` do POST com `_validar_parecer`
    - Se arquivo válido: `_upload_anexo(arquivo, pasta='visitas_pareceres')`
    - Se já existe `parecer_as_url` anterior e novo foi enviado com sucesso: deletar anterior via Cloudinary API (`cloudinary.uploader.destroy`)
    - Incluir `parecer_as_url` e `parecer_as_nome` no UPDATE do `solicitacoes_visita`
    - _Requisitos: 5.1, 5.3, 5.4, 5.5, 5.7_

- [x] 8. Histórico de visitas por família
  - [x] 8.1 Implementar rota `GET /visitas/familia/<cpf>` (`historico_familia`)
    - Verificar `_requer_login()`
    - Extrair dígitos do CPF: `cpf_digits = ''.join(c for c in cpf if c.isdigit())`
    - Validar com `validar_cpf(cpf_digits)` → HTTP 400 + mensagem "CPF inválido." se inválido
    - Perfil `admin`: buscar todas as solicitações do CPF
    - Perfil `entrevistador`: filtrar por `solicitante_id = uid OR responsavel_id = uid`
    - JOIN com `usuarios` para obter nome do responsável
    - Ordenar por `criado_em DESC`
    - Renderizar `historico_familia.html` com `visitas`, `cpf=cpf_digits`, `nome_rf` (do registro mais recente se existir)
    - _Requisitos: 6.1, 6.2, 6.3, 6.5, 6.6, 6.7_

  - [x] 8.2 Criar template `templates/historico_familia.html`
    - Extender `base.html`; título "Histórico de Visitas — CPF {{ cpf | formatar_cpf }}" (ou formatar inline com Jinja)
    - Botão "+ Nova Solicitação" → `url_for('nova_visita') + '?cpf=' + cpf`
    - Tabela: Nº VD | Data/Hora (DD/MM/AAAA HH:MM) | Motivo | Status (badge colorido) | Responsável | Ações (link Detalhes)
    - Badges: Pendente amarelo `#FFF3CD`/`#856404`; Em Andamento azul `#BDD7EE`/`#1F4E79`; Realizada verde `#D4EDDA`/`#1A6B3C`; Cancelada vermelho `#FDECEA`/`#8B1A1A`
    - Mensagem de vazio: "Nenhuma visita domiciliar registrada para este CPF."
    - _Requisitos: 6.2, 6.3, 6.4_

## Notes

- Todas as rotas novas seguem o padrão existente: `_requer_login()` no início, `audit()` após mutações, `conn.close()` em todos os caminhos de saída.
- O ReportLab 4.2.2 já está em `requirements.txt` — nenhuma nova dependência é adicionada.
- A rota `/visitas/familia/<cpf>` deve ser registrada **antes** de `/visitas/<int:visita_id>` no arquivo para evitar ambiguidade de prefixo.
- Registros antigos em `solicitacoes_visita` terão `numero_vd = NULL` — exibir como `—` na interface.
- Cloudinary delete (Req. 5.7) usa `cloudinary.uploader.destroy(public_id)` — o `public_id` pode ser extraído da URL salva.
