# Ollama Performance Tester

## a) O que é o projeto
O **Ollama Performance Tester** é uma aplicação web construída em Python utilizando o framework Flask. Seu principal objetivo é facilitar o teste de desempenho e tempo de resposta de Modelos de Linguagem de Larga Escala (LLMs) executados localmente através do [Ollama](https://ollama.com). 

Com uma interface gráfica moderna e interativa (Dark Theme), a aplicação permite:
- Visualizar todos os modelos disponíveis na sua instalação local do Ollama.
- Carregar ou descarregar modelos na memória com um clique.
- Executar prompts personalizados para cada modelo e medir o tempo de inferência (`total_duration`).
- Armazenar o histórico de testes em um banco de dados local (SQLite).
- Acompanhar um Dashboard comparativo que exibe o tempo médio de resposta de cada modelo testado e o histórico detalhado.

---

## b) Pré-requisitos
Para que o projeto funcione corretamente, você precisa ter os seguintes itens instalados no seu ambiente:

1. **Python 3.8+**: Necessário para rodar o backend Flask.
2. **Ollama**: O software do Ollama deve estar instalado e o daemon deve estar rodando na sua máquina (por padrão na porta `11434`).
   - Você precisa ter feito o download (pull) de pelo menos um modelo pelo Ollama. Exemplo: `ollama run llama3`.

---

## c) Passo-a-passo para executar o projeto

1. **Abra o terminal** e navegue até a pasta raiz do projeto:
   ```bash
   cd /Users/ar/Projects/ai/llm_test_api
   ```

2. **Ative o ambiente virtual**:
   ```bash
   source .venv/bin/activate
   ```

3. **(Opcional) Instale as dependências** (caso ainda não tenham sido instaladas):
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicie a aplicação Flask**:
   ```bash
   python app.py
   ```
   *Você verá a mensagem indicando que o servidor está rodando em `http://127.0.0.1:5001`.*

5. **Acesse no navegador**:
   Abra o seu navegador web favorito e acesse [http://127.0.0.1:5001](http://127.0.0.1:5001).

---

## d) Manual de Operações (Como usar)

A interface da aplicação é dividida em três páginas principais, acessíveis pelo menu lateral esquerdo:

### 1. Dashboard (`/`)
- Ao entrar na aplicação, você visualizará o **Dashboard**.
- **Average Response Time**: Um gráfico de barras que compara o tempo médio de resposta (em milissegundos) dos modelos que já foram testados.
- **Recent Tests**: Uma tabela mostrando o histórico dos últimos testes realizados, qual modelo foi utilizado, o prompt enviado e a data/hora exata.

### 2. Models (`/models`)
- Aqui você visualiza a lista de todos os modelos LLMs instalados no seu Ollama local.
- **Status "Running" / "Stopped"**: A aplicação indica se o modelo está carregado na memória do computador.
- **Ações**: 
  - **Load to Memory**: Se o modelo estiver parado, você pode forçar o carregamento dele para a memória.
  - **Stop**: Se o modelo já estiver carregado e consumindo recursos, clique aqui para descarregá-lo imediatamente e liberar memória.

### 3. Run Test (`/test`)
- Esta é a página onde você irá realizar as inferências.
- **Select Model**: Escolha, no menu dropdown, qual dos seus modelos você deseja testar. Os modelos atualmente carregados na memória terão uma flag `(Loaded)`.
- **Prompt**: Insira a pergunta ou comando (prompt) que o modelo deverá processar.
- **Run Test**: Clique neste botão para enviar o prompt ao Ollama. A interface indicará que está aguardando ("Running Test..."). 
- **Resultado**: Ao final, a resposta completa do modelo será exibida na tela juntamente com a principal métrica extraída: o **Tempo de Resposta (Response Time) em ms**.
- Simultaneamente, o teste é gravado de forma automática no banco de dados SQLite (`test_metrics.db`) para compor as métricas do Dashboard.

---

## e) Antigravity & Antigravity Kit 2.0

Este projeto foi desenvolvido com a ajuda do Antigravity e pode ser expandido utilizando o **Antigravity Kit 2.0**, uma poderosa suíte de workflows e agentes de inteligência artificial.

### Como instalar
O kit é instalado diretamente no diretório do seu projeto. Caso ainda não tenha feito, rode o comando abaixo no terminal da raiz do seu projeto:

```bash
npx @vudovn/ag-kit init
```
*(Você precisará ter o Node.js/npx instalados na sua máquina).*

Isso criará uma pasta `.agent/` contendo todas as regras de IA, workflows (`brainstorm`, `create`, `ui-ux-pro-max`, etc.) e scripts utilitários.

### Como usar
Uma vez instalado, o Antigravity Kit ativa protocolos inteligentes no seu assistente de IA para a manipulação deste repositório. Você pode interagir com o assistente utilizando os "Slash Commands" que vêm incluídos no Kit. 

Alguns comandos que você pode usar durante o desenvolvimento:
- **`@[/ui-ux-pro-max]`**: Aciona o motor avançado de design, capaz de gerar paletas de cores, selecionar tipografia e reescrever o CSS inteiro com base no seu tipo de projeto. *(Foi este comando que gerou o visual premium do nosso painel!)*
- **`@[/brainstorm]`**: Inicia um protocolo socrático para planejar novas features antes de escrever o código.
- **`@[/test]`**: Avalia seu código ou cria suítes de teste automaticamente.
- **`@[/status]`**: Analisa a saúde do projeto.

Basta digitar os comandos acima no prompt do seu assistente IA para acionar os workflows específicos do Kit! Para mais informações e atualizações, confira o repositório oficial: [vudovn/antigravity-kit](https://github.com/vudovn/antigravity-kit).
