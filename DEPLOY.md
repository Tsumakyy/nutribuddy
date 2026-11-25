# Deploy na VPS Windows (Windows 11 / Windows Server)

Pensado para uma VPS com 8 GB de RAM e 4 vCPU, acessada por Área de Trabalho Remota (RDP).
Todos os comandos são para o **PowerShell como Administrador**.

Resultado final:

| Endereço | O que é |
|---|---|
| `http://SEU_IP/` | App (paciente e nutricionista) em versão web |
| `http://SEU_IP/api/` | API FastAPI (rodando só em `127.0.0.1:8000`) |
| `http://SEU_IP/api/docs` | Documentação interativa da API |

| Peça | Função | Roda como |
|---|---|---|
| MySQL 8.4 | banco de dados | serviço do Windows (instalador já cria) |
| API (uvicorn) | backend | serviço via **NSSM** |
| Caddy | serve o app web e repassa `/api` para a API | serviço via **NSSM** |
| Ollama (opcional) | IA do papo livre | serviço via **NSSM** |

MySQL (3306) e a API (8000) **não** ficam abertos para a internet — só as portas 80/443.

> Troque `SEU_IP` pelo IP público da VPS (ou pelo seu domínio, se tiver).

---

## 1. Instalar as ferramentas

```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.13 -e
winget install --id OpenJS.NodeJS.LTS -e
winget install --id CaddyServer.Caddy -e
winget install --id NSSM.NSSM -e
```

**Feche e abra o PowerShell (como Administrador)** para o PATH atualizar, e confira:

```powershell
git --version; py -3.13 --version; node --version; caddy version; nssm version
```

> Se algum `winget install` disser que não encontrou o pacote, procure o nome certo com
> `winget search caddy` (ou `nssm`, `python`...).

Permita scripts do npm no PowerShell (só precisa uma vez):

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### MySQL

Baixe o **MySQL Community Server 8.4 LTS (Windows MSI)** em https://dev.mysql.com/downloads/mysql/ e instale:

1. Tipo de instalação: **Typical** (ou só o Server).
2. No configurador: *Development Computer* / *Server Computer*, porta **3306**.
3. **Desmarque** "Open Windows Firewall ports for network access" (o banco não deve ficar exposto).
4. Defina a **senha do root** e guarde.
5. Deixe marcado **Configure MySQL Server as a Windows Service** e **Start at System Startup**.

Para facilitar os próximos comandos:

```powershell
$mysql = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"
```

## 2. Baixar o projeto

```powershell
git clone https://github.com/Tsumakyy/nutribuddy.git C:\nutribuddy
mkdir C:\nutribuddy\logs
```

## 3. Banco de dados

Gere uma senha forte **só com letras e números** (ela vai dentro de uma URL no `.env`):

```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 28 | ForEach-Object { [char]$_ })
```

Crie o banco e o usuário (vai pedir a senha do **root**; troque `SENHA_DO_BANCO` pela gerada acima):

```powershell
& $mysql -u root -p -e "CREATE DATABASE nutribuddy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci; CREATE USER 'nutriapp'@'localhost' IDENTIFIED BY 'SENHA_DO_BANCO'; GRANT ALL PRIVILEGES ON nutribuddy.* TO 'nutriapp'@'localhost'; FLUSH PRIVILEGES;"
```

## 4. Backend

```powershell
cd C:\nutribuddy\backend
py -3.13 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"   # copie: é o JWT_SECRET
notepad .env
```

Deixe o `.env` assim e salve:

```ini
DATABASE_URL=mysql+pymysql://nutriapp:SENHA_DO_BANCO@localhost:3306/nutribuddy?charset=utf8mb4
JWT_SECRET=COLE_O_TOKEN_GERADO_ACIMA
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=720
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
```

Teste (as tabelas são criadas automaticamente na primeira execução):

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests      # deve terminar com OK
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Em **outro** PowerShell: `Invoke-RestMethod http://127.0.0.1:8000/health` → deve mostrar `status: ok`.
Depois volte ao primeiro e pare com `Ctrl+C`.

### Dados de teste (opcional)

⚠️ **Apaga todos os usuários, dietas e conversas.** Rode só depois do teste acima (as tabelas precisam existir).
Vai pedir a senha do usuário `nutriapp`:

```powershell
& $mysql -u nutriapp -p --default-character-set=utf8mb4 nutribuddy -e "source C:/nutribuddy/backend/sql/seed_teste.sql"
```

> Use exatamente assim (com `source` e barras `/`). Redirecionar o arquivo com `Get-Content | mysql`
> no PowerShell estraga os acentos.

Acessos: `nutri@teste.com` e `ana@teste.com` … `joao@teste.com`, todos com senha `123456`.

## 5. API como serviço do Windows

```powershell
nssm install nutribuddy-api "C:\nutribuddy\backend\venv\Scripts\python.exe" "-m uvicorn app.main:app --host 127.0.0.1 --port 8000 --root-path /api --proxy-headers"
nssm set nutribuddy-api AppDirectory "C:\nutribuddy\backend"
nssm set nutribuddy-api AppStdout "C:\nutribuddy\logs\api.log"
nssm set nutribuddy-api AppStderr "C:\nutribuddy\logs\api.log"
nssm set nutribuddy-api Start SERVICE_DELAYED_AUTO_START
nssm start nutribuddy-api
nssm status nutribuddy-api        # deve mostrar SERVICE_RUNNING
```

Ver logs: `Get-Content C:\nutribuddy\logs\api.log -Tail 50 -Wait`

## 6. Versão web do app

```powershell
cd C:\nutribuddy\app_paciente
npm ci
$env:EXPO_PUBLIC_API_URL = "http://SEU_IP/api"
npx expo export --platform web
```

Isso gera a pasta `C:\nutribuddy\app_paciente\dist`.

## 7. Caddy (site + proxy da API)

Crie o arquivo de configuração:

```powershell
@'
:80 {
    encode gzip

    handle_path /api/* {
        reverse_proxy 127.0.0.1:8000 {
            transport http {
                read_timeout 90s
            }
        }
    }

    handle {
        root * C:/nutribuddy/app_paciente/dist
        try_files {path} /index.html
        file_server
    }
}
'@ | Set-Content -Encoding ascii C:\nutribuddy\Caddyfile
caddy validate --config C:\nutribuddy\Caddyfile
```

Instale como serviço:

```powershell
nssm install caddy (Get-Command caddy).Source "run --config C:\nutribuddy\Caddyfile"
nssm set caddy AppDirectory "C:\nutribuddy"
nssm set caddy AppStdout "C:\nutribuddy\logs\caddy.log"
nssm set caddy AppStderr "C:\nutribuddy\logs\caddy.log"
nssm start caddy
```

Teste na própria VPS: `Invoke-RestMethod http://localhost/api/health` e abra `http://localhost` no navegador.

## 8. Firewall

Libere só HTTP/HTTPS:

```powershell
New-NetFirewallRule -DisplayName "NutriBuddy HTTP/HTTPS" -Direction Inbound -Protocol TCP -LocalPort 80,443 -Action Allow
```

Confirme que o MySQL **não** está liberado (não deve listar nada):

```powershell
Get-NetFirewallPortFilter | Where-Object LocalPort -in 3306,8000 | Get-NetFirewallRule | Where-Object Enabled -eq True
```

> Se o painel da VPS Outlet tiver firewall próprio, libere lá também as portas 80 e 443 (e a do RDP, 3389, que você já usa).

Agora teste do seu computador: `http://SEU_IP`.

## 9. HTTPS (se tiver domínio apontando para a VPS)

No `C:\nutribuddy\Caddyfile`, troque a primeira linha `:80 {` por `seudominio.com {` e reinicie:

```powershell
nssm restart caddy
```

O Caddy emite e renova o certificado sozinho. Depois refaça o passo 6 com
`$env:EXPO_PUBLIC_API_URL = "https://seudominio.com/api"`.

## 10. IA do papo livre com Ollama (opcional, recomendado com 8 GB)

Sem o Ollama, **as trocas de alimentos funcionam normalmente**; só o papo livre usa respostas prontas.
O modelo `qwen2.5:3b` usa ~2,5 GB de RAM.

```powershell
winget install --id Ollama.Ollama -e
```

O instalador abre o Ollama como aplicativo da bandeja, que **só roda com você logado**. Para rodar como serviço:

1. Feche o Ollama da bandeja (ícone perto do relógio → *Quit Ollama*) e tire ele da inicialização:
   *Gerenciador de Tarefas → Aplicativos de inicialização → Ollama → Desabilitar*.
2. Guarde os modelos numa pasta fixa e baixe o modelo:

```powershell
mkdir C:\ollama\models
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "C:\ollama\models", "Machine")
$env:OLLAMA_MODELS = "C:\ollama\models"
$ollama = (Get-Command ollama).Source
Start-Process $ollama "serve" -WindowStyle Hidden; Start-Sleep 5
ollama pull qwen2.5:3b
Get-Process ollama* | Stop-Process -Force
```

3. Crie o serviço:

```powershell
nssm install ollama $ollama "serve"
nssm set ollama AppEnvironmentExtra "OLLAMA_MODELS=C:\ollama\models" "OLLAMA_HOST=127.0.0.1:11434"
nssm set ollama AppStdout "C:\nutribuddy\logs\ollama.log"
nssm set ollama AppStderr "C:\nutribuddy\logs\ollama.log"
nssm start ollama
Invoke-RestMethod http://127.0.0.1:11434/api/tags      # deve listar qwen2.5:3b
```

## 11. Usar o app no celular apontando para a VPS

No seu computador (não na VPS), com o Expo Go no celular:

```powershell
cd app_paciente
$env:EXPO_PUBLIC_API_URL = "http://SEU_IP/api"
npm run start
```

## Atualizar depois de um novo `git push`

```powershell
cd C:\nutribuddy
git pull
.\backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
nssm restart nutribuddy-api
cd app_paciente
npm ci
$env:EXPO_PUBLIC_API_URL = "http://SEU_IP/api"
npx expo export --platform web
```

O Caddy passa a servir a nova versão do app automaticamente (não precisa reiniciar).

## Comandos úteis

| Para | Comando |
|---|---|
| Ver status dos serviços | `nssm status nutribuddy-api; nssm status caddy; nssm status ollama` |
| Reiniciar a API | `nssm restart nutribuddy-api` |
| Logs da API | `Get-Content C:\nutribuddy\logs\api.log -Tail 50 -Wait` |
| Editar um serviço (tela gráfica) | `nssm edit nutribuddy-api` |

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `http://SEU_IP` não abre de fora, mas abre na VPS | firewall do Windows (passo 8) ou do painel da VPS |
| `/api/...` responde 502 | API parada: `nssm status nutribuddy-api` e veja `logs\api.log` |
| `Access denied for user 'nutriapp'` no log | senha do `.env` diferente da criada no MySQL |
| `Can't connect to MySQL server` | serviço MySQL parado: `Get-Service MySQL*` / `Start-Service MySQL84` |
| App diz que não conecta à API | `dist` gerado com `EXPO_PUBLIC_API_URL` errado — refaça o passo 6 |
| `npx` não roda ("execução de scripts desabilitada") | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Acentos quebrados nos dados de teste | importe o seed com `source`, como no passo 4 |
| `Table ... doesn't exist` ao rodar o seed | rode a API uma vez antes (passo 4) para criar as tabelas |
| Buddy responde "não sei te ajudar" no papo livre | Ollama não instalado/rodando (passo 10, opcional) |
