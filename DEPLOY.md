# Como publicar o CadÚnico no Railway (online + HTTPS gratuito)

## Publicar no Render

O repositório agora inclui `render.yaml`, com o comando de instalação, o
comando de inicialização e deploy automático da branch `main`.

1. No Render, clique em **New** → **Blueprint** e conecte o repositório
   `Falwk/cadunico-sistema` na branch `main`.
2. Confirme a criação do serviço `cadunico-sistema`. O Render gera
   automaticamente a variável `CADUNICO_SECRET`.
3. Para dados persistentes, crie um **Render Postgres** e, no serviço web,
   adicione `DATABASE_URL` com a *Internal Database URL* do banco.

Se o serviço já existe, abra **Settings** e confirme: branch `main`,
**Auto-Deploy = On Commit**, Build Command `pip install -r requirements.txt`
e Start Command `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`.
Depois clique em **Manual Deploy** → **Deploy latest commit**. Um `render.yaml`
novo só é aplicado ao criar/sincronizar um Blueprint; ele não altera sozinho
um serviço criado manualmente.

## 1. Instalar o Git
Baixe em: https://git-scm.com/download/win
Execute o instalador com as opções padrão. Reinicie o terminal após instalar.

## 2. Criar repositório no GitHub
Acesse: https://github.com/new
- Repository name: cadunico-sistema
- Visibility: Private (recomendado — dados sensíveis)
- NÃO marque "Initialize this repository"
- Clique em Create repository

## 3. Configurar Git e fazer o primeiro push
Abra o Prompt de Comando na pasta do sistema e execute:

```
git config --global user.name "Falwk"
git config --global user.email "seu-email@exemplo.com"

cd c:\Users\USER\Documents\Codex\2026-06-16\files-mentioned-by-the-user-database\CadUnico_Sistema\cadunico

git init
git add .
git commit -m "primeiro commit - sistema cadunico pbf"
git branch -M main
git remote add origin https://github.com/Falwk/cadunico-sistema.git
git push -u origin main
```

O GitHub vai pedir login: use seu usuário Falwk e uma senha de acesso pessoal (token).
Para criar o token: https://github.com/settings/tokens → Generate new token (classic)
Marque a opção "repo" e clique em Generate.

## 4. Publicar no Railway
1. Acesse: https://railway.app
2. Clique em "Start a New Project"
3. Escolha "Deploy from GitHub repo"
4. Selecione: Falwk/cadunico-sistema
5. Clique em "+ New" → "Database" → "Add PostgreSQL"
6. Vá em "Variables" e adicione:
   - CADUNICO_SECRET = qualquer_frase_longa_e_aleatoria_aqui

## 5. Configurar domínio
No painel do Railway:
- Clique no seu serviço web
- Vá em "Settings" → "Networking" → "Generate Domain"
- Você terá uma URL como: https://cadunico.up.railway.app

## 6. Primeiro acesso online
- Abra a URL gerada
- Login: admin / admin123
- O sistema pedirá troca de senha obrigatória

## Atualizar o sistema depois
Sempre que fizer mudanças no código:
```
git add .
git commit -m "descricao da mudanca"
git push
```
O Railway faz redeploy automático em ~2 minutos.
