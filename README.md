# NutriBuddy

Aplicativo mobile para nutricionistas acompanharem pacientes e compartilharem planos alimentares. O paciente visualiza o plano do dia, registra check-ins e conversa com o Buddy.

## Rodar localmente no Windows

### 1. Backend

O backend usa as configurações de `backend/.env` e precisa que o banco indicado em `DATABASE_URL` esteja em execução.

```powershell
cd C:\Users\User\Desktop\nutribuddy\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: `http://localhost:8000`  
Documentação interativa: `http://localhost:8000/docs`

### 2. Aplicativo no navegador do computador

Em outro terminal:

```powershell
cd C:\Users\User\Desktop\nutribuddy\app_paciente
$env:EXPO_PUBLIC_API_URL = "http://127.0.0.1:8000"
npm run web
```

Abra o endereço mostrado pelo Expo (normalmente `http://localhost:8081`).

### Android e iPhone

O app usa Expo/React Native e compartilha as telas entre Android e iOS. Para Android, instale o Android Studio/emulador e execute `npm run android`. No emulador Android, configure a API como `http://10.0.2.2:8000`.

Para testar em um celular com Expo Go, conecte o computador e o celular à mesma rede Wi-Fi, use o IPv4 do computador no lugar de `127.0.0.1` e inicie com `npm run start -- --lan`. Por exemplo:

```powershell
$env:EXPO_PUBLIC_API_URL = "http://192.168.1.20:8000"
npm run start -- --lan
```

O endereço IP é específico da rede local. Builds nativos para iOS exigem macOS/Xcode ou um serviço de build remoto, mas o mesmo projeto Expo também pode ser compilado para iPhone.

### Primeiro acesso

1. Abra o app e escolha **Sou nutricionista e quero me cadastrar**.
2. Entre na conta profissional e use **+ Novo** para cadastrar um paciente.
3. Selecione o paciente e monte o plano por refeição.
4. O paciente entra com o e-mail e a senha cadastrados pelo nutricionista.

## Buddy e segurança do paciente

O Buddy é um companheiro de rotina, não um profissional de saúde. Após confirmação explícita do paciente, ele pode substituir refeições somente no plano efetivo do dia; a prescrição permanente do nutricionista nunca é alterada por essa conversa. Pedidos permanentes, sintomas ou questões clínicas são encaminhados ao profissional.

O contexto nutricional usa valores da tabela TACO apenas quando o nome do alimento coincide exatamente e a porção está em gramas. A base atual não possui dados de micronutrientes; o Buddy informa essa limitação e não deve inventar esses valores. Para cobrir micronutrientes, será necessário cadastrar/importar esses dados antes de habilitar recomendações que dependam deles.

### Como as trocas funcionam

As trocas não dependem da IA. O Buddy conduz a conversa em etapas (refeição → item → opções → confirmação) e calcula as porções em `backend/app/services/substitution_engine.py`:

- Só o item pedido muda; o resto da refeição fica igual.
- O substituto vem do mesmo grupo (proteína por proteína, carboidrato por carboidrato) e do mesmo estilo de refeição (pão do café não vira arroz).
- A porção iguala o macronutriente principal do grupo, e as calorias precisam ficar a até 15% do original. Quando o substituto é mais magro (ex.: frango no lugar de ovo), entra um pouco de azeite para repor a gordura.
- Itens em medida caseira ("1 fio", "à vontade") ou sem dados na tabela não recebem troca automática.
- A proposta mostrada fica salva na conversa, e o "sim" aplica exatamente ela, só para hoje.

O cadastro de alimentos usa a biblioteca `nutribr` 0.1.0, com valores por 100 g de energia e macronutrientes. A versão publicada contém somente cinco alimentos e não inclui micronutrientes; alimentos fora do catálogo podem continuar sendo registrados manualmente, mas não terão cálculo automático.

O Ollama (configurado em `backend/.env`) é usado só para o papo livre e nunca altera o plano. Sem ele, as trocas continuam funcionando normalmente.

Para habilitar respostas com IA, instale o Ollama e baixe o modelo configurado (por padrão `qwen2.5:3b`):

```powershell
ollama pull qwen2.5:3b
```

Não publique segredos de `backend/.env`. Para acesso em rede local, limite o uso a uma rede confiável e não exponha o servidor de desenvolvimento diretamente à internet.

## Bichinho do Buddy

A aba **Casa do Buddy** mostra o bichinho falando em um balão, com reações (pula ao confirmar uma troca, come no check-in, acolhe quando o paciente não segue o plano). As skins são liberadas por nível (100 pontos = 1 nível; cada refeição seguida vale 10) e a escolha fica salva no aparelho.

As imagens dos animais são do [Microsoft Fluent Emoji](https://github.com/microsoft/fluentui-emoji), licença MIT (`app_paciente/assets/pets/LICENSE-fluent-emoji.txt`).

## Deploy

Passo a passo para subir em uma VPS Windows: [DEPLOY.md](DEPLOY.md).
