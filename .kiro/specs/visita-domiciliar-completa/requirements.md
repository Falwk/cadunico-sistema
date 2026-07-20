# Requirements Document

## Introduction

Este documento especifica os requisitos para a expansão do módulo de Visitas Domiciliares do sistema CadÚnico (Flask + PostgreSQL/SQLite). As funcionalidades abrangem: numeração automática de solicitações no formato `VD-AAAA-NNNNNN`, geração de PDF/impressão com identidade visual oficial, registro do resultado da visita com preenchimento automático de controle interno, upload de múltiplas fotos da residência, upload de relatório/parecer da assistente social em PDF, e histórico completo de visitas agrupado por CPF do Responsável Familiar (RF).

O sistema já possui a tabela `solicitacoes_visita`, integração com Cloudinary para upload de arquivos, e a biblioteca ReportLab disponível em `requirements.txt`.

---

## Glossary

- **Sistema**: A aplicação Flask do CadÚnico.
- **RF**: Responsável Familiar — titular do cadastro na família.
- **CPF_RF**: CPF do Responsável Familiar.
- **Solicitação_Visita**: Registro de uma solicitação de visita domiciliar na tabela `solicitacoes_visita`.
- **Número_VD**: Identificador único de uma Solicitação_Visita no formato `VD-AAAA-NNNNNN`, onde `AAAA` é o ano de criação (4 dígitos, fuso horário America/Belem) e `NNNNNN` é um contador sequencial de seis dígitos com zero-padding, reiniciado a cada ano.
- **Contador_Anual**: Sequência numérica crescente por ano calendário que determina o `NNNNNN` do Número_VD. Gerado atomicamente no banco de dados para garantir unicidade em ambiente concorrente.
- **PDF_Solicitação**: Documento PDF gerado pelo Sistema via ReportLab com identidade visual oficial, entregue como download com nome `VD-AAAA-NNNNNN.pdf`.
- **Resultado_Visita**: Conjunto de informações registradas após a realização de uma visita (data, observações do entrevistador, Parecer_AS opcional).
- **Controle_Interno**: Campos da Solicitação_Visita que registram a execução: `data_realizada`, `responsavel_id`, `observacoes`, status `Realizada`.
- **Foto_Residência**: Arquivo de imagem (extensão `.jpg`, `.jpeg`, `.png` ou `.webp`) da residência visitada, armazenado no Cloudinary na pasta `visitas_fotos`.
- **Parecer_AS**: Documento PDF (extensão `.pdf`, máximo 20 MB) contendo o relatório e parecer da assistente social, armazenado no Cloudinary na pasta `visitas_pareceres`.
- **Histórico_Família**: Listagem cronológica de todas as Solicitações_Visita associadas a um CPF_RF, ordenada da mais recente para a mais antiga.
- **Entrevistador**: Usuário com perfil `entrevistador` que executa visitas domiciliares.
- **Admin**: Usuário com perfil `admin` com permissões ampliadas sobre todas as solicitações.
- **Cloudinary**: Serviço externo de armazenamento de mídia já integrado ao Sistema.
- **ReportLab**: Biblioteca Python para geração de PDF já presente no `requirements.txt`.
- **Status Terminal**: Status que impede edição da Solicitação_Visita: `Realizada` ou `Cancelada`.

---

## Requirements

### Requirement 1: Numeração Automática da Solicitação

**User Story:** Como entrevistador, quero que cada nova solicitação de visita receba automaticamente um número único no formato VD-AAAA-NNNNNN, para que eu possa identificar e rastrear solicitações sem ambiguidade.

#### Acceptance Criteria

1. WHEN uma nova Solicitação_Visita é criada com sucesso, the Sistema SHALL atribuir automaticamente um Número_VD no formato `VD-AAAA-NNNNNN`, onde `AAAA` é o ano de criação (fuso horário America/Belem) e `NNNNNN` é o Contador_Anual com zero-padding de seis dígitos.
2. The Sistema SHALL garantir que o Número_VD seja único dentro do mesmo ano calendário — nenhumas duas Solicitações_Visita criadas no mesmo ano possuem o mesmo `NNNNNN`. A unicidade SHALL ser garantida por operação atômica no banco de dados (SELECT MAX + INSERT em transação serializada ou sequence/autoincrement dedicado).
3. WHEN o ano calendário muda (virada de ano em America/Belem), the Sistema SHALL reiniciar o Contador_Anual a partir de `000001` para as novas Solicitações_Visita criadas a partir dessa data.
4. The Sistema SHALL persistir o Número_VD junto à Solicitação_Visita no momento da inserção.
5. WHEN o Número_VD é exibido na interface (listagem, detalhe, PDF), the Sistema SHALL exibir o valor completo no formato `VD-AAAA-NNNNNN`.
6. IF a geração do Número_VD falha por erro de banco de dados, THEN the Sistema SHALL rejeitar a inserção da Solicitação_Visita e exibir a mensagem "Erro ao gerar número da solicitação. Tente novamente."
7. IF o Contador_Anual atingir 999999 para o ano corrente, THEN the Sistema SHALL rejeitar novas inserções e exibir a mensagem "Limite de solicitações para o ano atingido. Contate o administrador."

---

### Requirement 2: Impressão e PDF com Identidade Visual Oficial

**User Story:** Como entrevistador, quero imprimir ou baixar um PDF da solicitação de visita com a identidade visual oficial da prefeitura, para que o documento possa ser apresentado formalmente durante a visita.

#### Acceptance Criteria

1. WHEN um usuário autenticado acessa a rota `/visitas/<id>/pdf`, the Sistema SHALL gerar e entregar um arquivo PDF da Solicitação_Visita correspondente como download com o nome de arquivo `<Número_VD>.pdf` (ex.: `VD-2026-000001.pdf`).
2. The PDF_Solicitação SHALL conter um cabeçalho com: a logo do CadÚnico (`cadunico.png`) à esquerda, o brasão da prefeitura (`prefeitura.png`) centralizado e a logo do Bolsa Família (`bolsafamilia.png`) à direita.
3. The PDF_Solicitação SHALL conter os seguintes dados: Número_VD, CPF_RF, nome do RF, endereço completo (logradouro, número, complemento, bairro, zona, ponto de referência), motivo da visita, status, data de criação no formato DD/MM/AAAA, nome do solicitante e nome do entrevistador responsável.
4. The PDF_Solicitação SHALL conter dois campos de assinatura: um rotulado "Assinatura do Entrevistador" e outro rotulado "Assinatura do RF", cada um com uma linha horizontal de no mínimo 6 cm de largura e o nome respectivo abaixo da linha.
5. The PDF_Solicitação SHALL utilizar azul escuro `#1F4E79` para cabeçalhos de seção e `#F5F6F8` como cor de fundo do rodapé.
6. IF um logotipo necessário não existe no diretório `static/logos/`, THEN the Sistema SHALL gerar o PDF_Solicitação omitindo apenas o logotipo ausente sem interromper a geração dos demais elementos.
7. IF o usuário não está autenticado ao acessar `/visitas/<id>/pdf`, THEN the Sistema SHALL redirecionar para a página de login.
8. IF a Solicitação_Visita com o `<id>` informado não existe no banco de dados, THEN the Sistema SHALL retornar HTTP 404.
9. IF `<id>` na URL não é um inteiro válido, THEN the Sistema SHALL retornar HTTP 404.

---

### Requirement 3: Registro do Resultado da Visita

**User Story:** Como entrevistador, quero registrar o resultado de uma visita domiciliar por meio de um botão dedicado que preenche automaticamente o controle interno, para que o fluxo de conclusão seja simples e sem retrabalho.

#### Acceptance Criteria

1. WHEN uma Solicitação_Visita tem status `Pendente` ou `Em Andamento` E o usuário autenticado é o solicitante, o responsável ou possui perfil `admin`, the Sistema SHALL exibir o botão "Registrar Resultado da Visita" na página de detalhe da solicitação.
2. WHEN o botão "Registrar Resultado da Visita" é acionado, the Sistema SHALL exibir um formulário com: campo data de realização (tipo date, obrigatório), campo observações do entrevistador (textarea, opcional) e campo upload do Parecer_AS (arquivo PDF, opcional).
3. WHEN o formulário de resultado é submetido com `data_realizada` no formato `YYYY-MM-DD` e com valor menor ou igual à data atual, the Sistema SHALL atualizar o status para `Realizada`, persistir `data_realizada` e `observacoes`, e criar um registro de atendimento vinculado na tabela `atendimentos` com `origem = 'Visita Domiciliar'`.
4. WHEN o formulário de resultado é submetido com um Parecer_AS válido (extensão `.pdf`, ≤ 20 MB) e o upload ao Cloudinary é bem-sucedido, the Sistema SHALL armazenar a URL e o nome original do arquivo na Solicitação_Visita.
5. IF o formulário de resultado é submetido sem `data_realizada`, THEN the Sistema SHALL rejeitar o envio e exibir a mensagem "Informe a data de realização da visita."
6. IF `data_realizada` é uma data futura (posterior à data atual), THEN the Sistema SHALL rejeitar o envio e exibir a mensagem "A data de realização não pode ser uma data futura."
7. WHILE a Solicitação_Visita tem status `Realizada` ou `Cancelada`, the Sistema SHALL ocultar o botão "Registrar Resultado da Visita" para todos os usuários.
8. IF o upload do Parecer_AS ao Cloudinary falha, THEN the Sistema SHALL salvar o resultado da visita sem o anexo e exibir o aviso "Resultado registrado, mas o parecer não pôde ser anexado. Tente enviá-lo novamente."

---

### Requirement 4: Upload de Múltiplas Fotos da Residência

**User Story:** Como entrevistador, quero anexar múltiplas fotos da residência durante ou após a visita, para que a documentação visual fique centralizada na solicitação.

#### Acceptance Criteria

1. The Sistema SHALL disponibilizar um campo de upload múltiplo de imagens na página de detalhe da Solicitação_Visita (para solicitações com status não-terminal) e na página de registro do resultado.
2. WHEN o Entrevistador seleciona arquivos para upload, the Sistema SHALL aceitar somente arquivos cuja extensão (case-insensitive) seja `.jpg`, `.jpeg`, `.png` ou `.webp`.
3. WHEN um lote de arquivos é enviado, the Sistema SHALL realizar o upload ao Cloudinary (pasta `visitas_fotos`) de cada arquivo que passe nas validações de extensão e tamanho, mesmo que outros arquivos do mesmo lote falhem na validação.
4. The Sistema SHALL manter um limite cumulativo de 10 Fotos_Residência por Solicitação_Visita. IF o upload de novas fotos excederia esse limite, THEN the Sistema SHALL rejeitar os arquivos excedentes e exibir "Limite de 10 fotos por solicitação atingido."
5. IF um arquivo do lote excede 10 MB, THEN the Sistema SHALL rejeitar apenas esse arquivo e exibir "A imagem '<nome_original>' excede o limite de 10 MB."
6. IF um arquivo do lote tem extensão não permitida, THEN the Sistema SHALL rejeitar apenas esse arquivo e exibir "Formato não suportado: '<nome_original>'. Use JPG, PNG ou WEBP."
7. WHEN fotos estão vinculadas a uma Solicitação_Visita, the Sistema SHALL exibi-las como miniaturas na página de detalhe; ao clicar em uma miniatura, the Sistema SHALL abrir a imagem em tamanho completo em uma nova aba ou em um overlay modal.
8. WHEN ao menos um arquivo do lote passa em todas as validações e o upload ao Cloudinary é bem-sucedido, the Sistema SHALL armazenar a URL retornada pelo Cloudinary e o nome original do arquivo, vinculados à Solicitação_Visita.
9. WHEN um lote contém arquivos com falhas de validação misturados com arquivos válidos, the Sistema SHALL processar e salvar os válidos e exibir uma mensagem de erro consolidada listando os arquivos rejeitados e o motivo de cada rejeição.

---

### Requirement 5: Upload do Relatório e Parecer da Assistente Social

**User Story:** Como assistente social, quero anexar meu relatório e parecer em PDF a uma solicitação de visita, para que o documento técnico fique disponível no sistema vinculado à família visitada.

#### Acceptance Criteria

1. IF uma Solicitação_Visita tem status diferente de `Realizada` e `Cancelada`, THEN the Sistema SHALL disponibilizar um campo de upload do Parecer_AS na página de edição da solicitação e na página de registro do resultado.
2. WHEN um arquivo é enviado no campo de Parecer_AS, the Sistema SHALL validar que a extensão do arquivo (case-insensitive) é `.pdf` antes de iniciar qualquer upload.
3. WHEN um arquivo enviado como Parecer_AS passa nas validações de extensão (`.pdf`) e tamanho (≤ 20 MB), the Sistema SHALL fazer upload para o Cloudinary na pasta `visitas_pareceres` e armazenar a URL retornada e o nome original do arquivo na Solicitação_Visita.
4. IF o arquivo enviado como Parecer_AS não tem extensão `.pdf`, THEN the Sistema SHALL rejeitar o envio antes de qualquer upload e exibir a mensagem "O parecer deve ser um arquivo PDF."
5. IF o arquivo enviado como Parecer_AS excede 20 MB, THEN the Sistema SHALL rejeitar o envio antes de qualquer upload e exibir a mensagem "O arquivo PDF excede o limite de 20 MB."
6. WHEN um Parecer_AS está vinculado à Solicitação_Visita, the Sistema SHALL exibir na página de detalhe um link que, ao ser clicado, inicia o download do arquivo com o nome original.
7. WHEN um novo Parecer_AS válido é enviado para uma Solicitação_Visita que já possui um Parecer_AS, the Sistema SHALL substituir a URL e o nome armazenados pelo novo arquivo; o arquivo anterior no Cloudinary SHALL ser removido via API do Cloudinary.

---

### Requirement 6: Histórico Completo de Visitas por Família

**User Story:** Como entrevistador, quero consultar o histórico completo de visitas domiciliares de uma família pelo CPF do RF, para que eu possa avaliar o histórico antes de realizar uma nova visita.

#### Acceptance Criteria

1. The Sistema SHALL disponibilizar uma rota `/visitas/familia/<cpf>` que, para um CPF_RF válido, exibe todas as Solicitações_Visita associadas ao CPF_RF informado, ordenadas da mais recente para a mais antiga por `criado_em`.
2. The Histórico_Família SHALL exibir, para cada Solicitação_Visita: Número_VD, data de criação no formato DD/MM/AAAA HH:MM, motivo, badge de status com cor correspondente ao status (Pendente: amarelo `#FFF3CD`/`#856404`; Em Andamento: azul `#BDD7EE`/`#1F4E79`; Realizada: verde `#D4EDDA`/`#1A6B3C`; Cancelada: vermelho `#FDECEA`/`#8B1A1A`), nome do entrevistador responsável (ou "Não atribuído") e link para o detalhe da solicitação.
3. WHEN não há Solicitações_Visita para o CPF_RF informado, the Sistema SHALL exibir a mensagem "Nenhuma visita domiciliar registrada para este CPF."
4. The Sistema SHALL exibir na página de detalhe de cada Solicitação_Visita um link "Ver Histórico da Família" que direciona para `/visitas/familia/<cpf_rf>`.
5. WHEN um usuário com perfil `entrevistador` acessa o Histórico_Família, the Sistema SHALL exibir somente as Solicitações_Visita nas quais o `solicitante_id` ou o `responsavel_id` corresponde ao ID do usuário autenticado. IF nenhuma solicitação atende a esse critério, the Sistema SHALL exibir a mensagem "Nenhuma visita domiciliar registrada para este CPF."
6. WHEN um usuário com perfil `admin` acessa o Histórico_Família, the Sistema SHALL exibir todas as Solicitações_Visita para o CPF_RF, independentemente de solicitante ou responsável.
7. IF o valor `<cpf>` na URL, após remoção de caracteres não-dígitos, não corresponde a um CPF com 11 dígitos e dígitos verificadores válidos, THEN the Sistema SHALL retornar HTTP 400 e exibir a mensagem "CPF inválido."
