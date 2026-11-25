# Deploy na VPS (Ubuntu 24.04)

Resultado final, tudo atrás do Nginx na porta 80/443:

| Caminho | O que é |
|---|---|
| `http://SEU_IP/` | App (paciente e nutricionista) em versão web |
| `http://SEU_IP/api/` | API FastAPI (rodando só em `127.0.0.1:8000`) |
| `http://SEU_IP/api/docs` | Documentação interativa da API |

MySQL e a porta 8000 **não** ficam expostos na internet.

> Troque `SEU_IP` pelo IP da VPS (ou pelo seu domínio, se tiver um).

---

## 1. Pacotes do sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git python3 python3-venv python3-pip mysql-server nginx curl

# Node 24 (para gerar a versão web do app)
curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
sudo apt install -y nodejs
```

Confira as versões: `python3 --version` (precisa ser **3.12 ou mais novo**) e `node --version`.

## 2. Baixar o projeto

```bash
sudo mkdir -p /opt/nutribuddy && sudo chown $USER:$USER /opt/nutribuddy
git clone https://github.com/Tsumakyy/nutribuddy.git /opt/nutribuddy
cd /opt/nutribuddy
```

## 3. Banco de dados MySQL

Gere uma senha forte e guarde-a:

```bash
openssl rand -base64 24
```

Crie o banco e o usuário (cole a senha gerada no lugar de `SENHA_DO_BANCO`):

```bash
sudo mysql <<'SQL'
CREATE DATABASE nutribuddy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'nutriapp'@'localhost' IDENTIFIED BY 'SENHA_DO_BANCO';
GRANT ALL PRIVILEGES ON nutribuddy.* TO 'nutriapp'@'localhost';
FLUSH PRIVILEGES;
SQL
```

> Se a senha tiver caracteres como `@`, `/` ou `:`, gere outra só com letras e números — ela vai dentro de uma URL no `.env`.

## 4. Backend

```bash
cd /opt/nutribuddy/backend
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # copie: é o JWT_SECRET
nano .env
```

Deixe o `.env` assim:

```ini
DATABASE_URL=mysql+pymysql://nutriapp:SENHA_DO_BANCO@localhost:3306/nutribuddy?charset=utf8mb4
JWT_SECRET=COLE_O_TOKEN_GERADO_ACIMA
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=720
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

```bash
chmod 600 .env
```

Teste rápido (as tabelas são criadas automaticamente na primeira execução):

```bash
./venv/bin/python -m unittest discover -s tests          # deve terminar com OK
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# em outro terminal: curl http://127.0.0.1:8000/health  →  {"status":"ok"}
# depois pare com Ctrl+C
```

### Dados de teste (opcional)

⚠️ **Apaga todos os usuários, dietas e conversas.** Rode só depois do teste acima (as tabelas precisam existir):

```bash
mysql -u nutriapp -p nutribuddy < /opt/nutribuddy/backend/sql/seed_teste.sql
```

Acessos: `nutri@teste.com` e `ana@teste.com` … `joao@teste.com`, todos com senha `123456`.

## 5. Backend como serviço (sobe sozinho e reinicia se cair)

```bash
sudo tee /etc/systemd/system/nutribuddy-api.service > /dev/null <<EOF
[Unit]
Description=NutriBuddy API
After=network.target mysql.service

[Service]
User=$USER
WorkingDirectory=/opt/nutribuddy/backend
ExecStart=/opt/nutribuddy/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2 --root-path /api --proxy-headers
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now nutribuddy-api
sudo systemctl status nutribuddy-api --no-pager
```

Logs: `journalctl -u nutribuddy-api -f`

## 6. Versão web do app

```bash
cd /opt/nutribuddy/app_paciente
npm ci
EXPO_PUBLIC_API_URL=http://SEU_IP/api npx expo export --platform web
```

Isso gera a pasta `dist/`. Se depois colocar domínio com HTTPS, gere de novo com `https://seudominio.com/api`.

## 7. Nginx

```bash
sudo tee /etc/nginx/sites-available/nutribuddy > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;

    root /opt/nutribuddy/app_paciente/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90s;   # o Buddy pode levar alguns segundos com o Ollama
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/nutribuddy /etc/nginx/sites-enabled/nutribuddy
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

O Nginx precisa ler a pasta do app. Se a página der erro 403/404:

```bash
sudo chmod o+x /opt /opt/nutribuddy /opt/nutribuddy/app_paciente
sudo chmod -R o+r /opt/nutribuddy/app_paciente/dist
```

Teste: `curl http://SEU_IP/api/health` e abra `http://SEU_IP` no navegador.

## 8. Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 9. HTTPS (se tiver domínio apontando para a VPS)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo sed -i 's/server_name _;/server_name seudominio.com;/' /etc/nginx/sites-available/nutribuddy
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d seudominio.com
```

Depois refaça o passo 6 com `EXPO_PUBLIC_API_URL=https://seudominio.com/api`.

## 10. IA do papo livre (opcional)

Sem o Ollama, **as trocas de alimentos funcionam normalmente**; só o papo livre usa respostas prontas. Para ativar (precisa de ~3 GB de RAM livres):

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
sudo systemctl restart nutribuddy-api
```

## 11. Usar o app no celular apontando para a VPS

No seu computador (não na VPS), com o Expo Go no celular:

```powershell
cd app_paciente
$env:EXPO_PUBLIC_API_URL = "http://SEU_IP/api"
npm run start
```

## Atualizar depois de um novo `git push`

```bash
cd /opt/nutribuddy
git pull
./backend/venv/bin/pip install -r backend/requirements.txt
sudo systemctl restart nutribuddy-api
cd app_paciente && npm ci && EXPO_PUBLIC_API_URL=http://SEU_IP/api npx expo export --platform web
```

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `502 Bad Gateway` em `/api` | API parada: `journalctl -u nutribuddy-api -n 50` |
| `Access denied for user 'nutriapp'` | senha do `.env` diferente da criada no MySQL |
| Login no app diz que não conecta à API | `dist/` gerado com `EXPO_PUBLIC_API_URL` errado — refaça o passo 6 |
| Buddy responde "não sei te ajudar" no papo livre | Ollama não instalado/rodando (opcional) |
| `Table ... doesn't exist` ao rodar o seed | rode a API uma vez antes (passo 4) para criar as tabelas |
