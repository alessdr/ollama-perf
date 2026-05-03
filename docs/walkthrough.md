# Walkthrough: Aplicação de Teste de Desempenho do Ollama

A aplicação foi completamente construída conforme o plano de implementação aprovado. A seguir, um resumo das funcionalidades e estrutura implementada.

## 1. Arquitetura e Estrutura do Backend
A aplicação utiliza **Flask** como servidor web, atuando também como ponte (API) entre o Frontend e o daemon do Ollama.

- **`app.py`**: Gerencia o roteamento do frontend (Dashboard, Models, Run Test) e expõe rotas `/api/...` para que o frontend carregue dados assincronamente (evitando recarregamento de páginas).
- **`ollama_utils.py`**: Um wrapper feito em cima da biblioteca `requests` para comunicar com a API nativa do Ollama (`http://localhost:11434`). Possui funções para:
  - Listar modelos (`/api/tags`)
  - Verificar quais modelos estão em memória (`/api/ps`)
  - Carregar um modelo na memória explicitamente enviando requisição sem prompt e com `keep_alive = -1`.
  - Descarregar da memória usando `keep_alive = 0`.
  - Executar e medir o tempo (utilizando a métrica original do Ollama `total_duration` e convertendo para milissegundos).
- **Banco de Dados**: Configurado com **SQLite** (`test_metrics.db`) usando **Flask-SQLAlchemy**. Possui a tabela `TestRun` para persistir o nome do modelo, o prompt, o tempo de resposta em milissegundos e o timestamp.

## 2. Design e Interface (Frontend)
Para a estética da aplicação, optamos por um design moderno e elegante utilizando apenas **Vanilla CSS** e JavaScript padrão (Fetch API).

- **Dark Theme Moderno**: O arquivo `style.css` usa variáveis CSS para definir uma paleta focada em tons escuros (`#0f172a`, `#1e293b`), com detalhes e botões em azul e elementos "Glassmorphism" (fundo translúcido com `backdrop-filter: blur()`).
- **Dashboard Interativo**: A página inicial utiliza `Chart.js` via CDN para mostrar um gráfico de barras comparativo (Tempo Médio de Resposta por Modelo) e uma tabela com o histórico das execuções recentes.
- **Gerenciamento de Modelos**: Permite visualizar de forma clara o status do modelo (Rodando / Parado) com botões para interagir com a API e gerenciar o uso da memória diretamente do navegador.
- **Execução do Teste**: Um formulário limpo que puxa os modelos disponíveis, exibe um spinner animado nativo em CSS durante a execução, mostra a resposta do LLM e exibe o tempo total da inferência formatado.

## 3. Validação e Testes
O ambiente virtual `.venv` foi configurado e todos os pacotes foram instalados (`Flask`, `Flask-SQLAlchemy`, `requests`).
A aplicação foi testada, o banco de dados SQLite inicializa corretamente e a interface foi carregada com sucesso. 

> [!TIP]
> **Como rodar o projeto?**
> Abra o seu terminal, navegue até a pasta do projeto (`/Users/ar/Projects/ai/llm_test_api`) e execute:
> ```bash
> source .venv/bin/activate
> python app.py
> ```
> Depois, acesse `http://127.0.0.1:5001` no seu navegador! Lembre-se de certificar-se de que o Ollama esteja rodando na sua máquina.
