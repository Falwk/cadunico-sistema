# 🚀 Guia de Deploy e Infraestrutura
### Sistema Cadastro Único & Visitas Domiciliares · Tomé-Açu / PA

Este documento orienta a implantação do sistema tanto em **Servidores Dedicados (Cloud VPS Ubuntu)** quanto em plataformas de nuvem gerenciada (**Render + Supabase + Cloudinary**).

---

## 🏗️ Arquitetura de Produção

```
[ Usuários (Celular/PC) ]
           │ (HTTPS / Porta 443)
           ▼
    [ Nginx / Render ]
           │ (Reverse Proxy)
           ▼
[ Gunicorn WSGI (Python 3.10+) ]
           │ (Flask Application)
    ┌──────┴──────────────────────────┐
    ▼                                 ▼
[ PostgreSQL (Supabase Pooler) ]   [ Cloudinary Storage ]
(Banco Relacional + RLS)           (Fotos e PDFs de Anexos)
```

---

## 🖥️ Opção A: Implantação em Cloud VPS (Ubuntu 22.04 / 24.04 LTS)

### 1. Atualização do Sistema e Instalação de Pacotes
Conecte-se via SSH como `root` e execute:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx libpq-dev
```

### 2. Clonagem do Projeto e Configuração do Ambiente
```bash
cd /var/www
git clone https://github.com/Falwk/cadunico-sistema.git cadunico
cd cadunico
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configuração do Serviço Systemd (`gunicorn.service`)
Crie o arquivo de serviço para que a aplicação inicialize automaticamente com o servidor:
```bash
sudo nano /etc/systemd/system/cadunico.service
```

Cole a configuração:
```ini
[Unit]
Description=Gunicorn instance to serve CadUnico Sistema
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/cadunico
Environment="PATH=/var/www/cadunico/venv/bin"
Environment="DATABASE_URL=postgresql://postgres.cfcdmuffivnukleadiyl:Amand%4027Telm%4007@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
Environment="CADUNICO_SECRET=cadunico_tomeacu_chave_segura_2026"
Environment="CLOUDINARY_URL=cloudinary://SUA_CHAVE_AQUI"
ExecStart=/var/www/cadunico/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

Ative e inicialize o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl start cadunico
sudo systemctl enable cadunico
```

### 4. Configuração do Nginx (Proxy Reverso e SSL)
Crie o bloco de configuração do Nginx:
```bash
sudo nano /etc/nginx/sites-available/cadunico
```

Cole a configuração:
```nginx
server {
    listen 80;
    server_name seu-dominio.com.br;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Ative o site e instale o certificado HTTPS gratuito:
```bash
sudo ln -s /etc/nginx/sites-available/cadunico /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d seu-dominio.com.br
```

---

## ☁️ Opção B: Implantação no Render (Managed Web Service)

1. Crie um **Web Service** no [Render Dashboard](https://dashboard.render.com).
2. Conecte ao repositório `Falwk/cadunico-sistema`.
3. Configure os parâmetros:
   * **Runtime:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `gunicorn app:app`
4. Na aba **Environment Variables**, adicione:
   * `DATABASE_URL`
   * `CADUNICO_SECRET`
   * `CLOUDINARY_URL`

---

## ⏰ Configuração do Agendador de Backup (Cron Job)
Para que o backup diário para o Telegram seja disparado pontualmente:
1. Cadastre uma tarefa no **[cron-job.org](https://cron-job.org)**:
   * **URL:** `https://seu-dominio.com.br/api/v1/cron/backup-telegram`
   * **Frequência:** Diariamente às 23:00 (Fuso horário: `America/Belem`).
