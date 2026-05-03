# Objetivo

Criar uma aplicação web em Python utilizando Flask para testar e comparar o desempenho (tempo de resposta) de modelos hospedados localmente via Ollama. A aplicação possuirá uma interface gráfica moderna e interativa que permitirá gerenciar os modelos (iniciar/parar), rodar os testes de desempenho, armazenar os resultados em um banco de dados SQLite e visualizá-los em um dashboard.

## Funcionalidades e Requisitos
1. **Manipulação do Ollama (Iniciar/Parar):** O Ollama gerencia modelos na memória sob demanda, mas a aplicação vai permitir carregar explicitamente um modelo na memória (usando a flag `keep_alive = -1`) ou descarregá-lo (`keep_alive = 0`).
2. **Listagem de Modelos:** Consumir a API `/api/tags` do Ollama para listar os modelos instalados localmente.
3. **Armazenamento de Testes:** Gravar o tempo de resposta das requisições geradas pelo Ollama (como `total_duration`, convertido para milissegundos) em um banco de dados SQLite.
4. **Dashboard Comparativo:** Utilizar gráficos interativos (ex: Chart.js) para demonstrar a variação no tempo de resposta e comparar diferentes modelos.

## Design e Interface
- **Estética Moderna e Premium:** Interface construída com **Vanilla CSS** (sem Tailwind, conforme restrições de tecnologia), utilizando CSS Grid e Flexbox, um "Dark Mode" elegante, Glassmorphism (efeitos translúcidos) e animações suaves (hover effects e transições).
- **Sem Page Reloads Desnecessários:** Utilizaremos JavaScript assíncrono (Fetch API) no frontend para que a interface de gerenciar modelos e testes pareça responsiva, sem precisar recarregar a página.

---

## Proposed Changes

### 1. Estrutura Base e Backend (Flask)

#### [NEW] `app.py`
Ponto de entrada da aplicação Flask. Registrará as rotas do frontend (`/`, `/models`, `/test`) e as rotas de API para comunicação assíncrona (`/api/models`, `/api/models/load`, `/api/models/unload`, `/api/test`, `/api/dashboard`).

#### [NEW] `database.py` e `models.py`
Configuração do banco de dados utilizando `Flask-SQLAlchemy`.
Criação do modelo `TestRun`:
- `id` (Integer, Primary Key)
- `model_name` (String)
- `prompt` (Text)
- `response_time_ms` (Float) - Tempo total da requisição.
- `created_at` (DateTime)

#### [NEW] `ollama_utils.py`
Módulo auxiliar encapsulando o uso da biblioteca `requests` para interagir com o daemon do Ollama (por padrão rodando em `http://localhost:11434`):
- `get_models()`: Retorna os modelos instalados (`/api/tags`).
- `get_running_models()`: Retorna os modelos ativos na memória (`/api/ps`).
- `load_model(model_name)`: Envia requisição sem prompt com `keep_alive=-1` para pré-carregar.
- `unload_model(model_name)`: Envia requisição com `keep_alive=0` para descarregar.
- `run_test(model_name, prompt)`: Envia requisição de geração (generate) e coleta os tempos no final.

---

### 2. Frontend: Templates HTML (Jinja2)

#### [NEW] `templates/base.html`
Layout base com a navegação lateral e a área principal, utilizando estrutura semântica. Inclui importações de fontes modernas (ex: Inter), Chart.js (via CDN) e nossa folha de estilos principal.

#### [NEW] `templates/dashboard.html`
Página inicial (rota `/`). Exibe um gráfico de barras/linha comparando a média de tempo de resposta dos modelos e o histórico recente.

#### [NEW] `templates/models.html`
Página para visualização da lista de modelos. Inclui os status (Carregado/Parado) e botões de ação (Iniciar/Parar) conectados via AJAX.

#### [NEW] `templates/test.html`
Interface para executar novos testes. O usuário seleciona o modelo a partir de um dropdown, insere um prompt e clica em Testar. O resultado e o tempo são mostrados em tempo real, gravando simultaneamente no banco.

---

### 3. Frontend: Estilos e Lógica

#### [NEW] `static/css/style.css`
A folha de estilos contendo o design system moderno em Vanilla CSS:
- Paleta de cores focada em um Dark Theme (fundo `#0f172a`, cards `#1e293b` com bordas translúcidas).
- Tipografia elegante e espaçamentos consistentes.
- Micro-interações e animações (botões que reagem ao hover, modais suaves).

#### [NEW] `static/js/main.js`
Lógica de interface:
- Funções para carregar e atualizar o gráfico usando `Chart.js`.
- Interceptação dos cliques de "Iniciar/Parar" e do formulário de testes, disparando as rotas da nossa própria API no Flask (`/api/...`).

#### [NEW] `requirements.txt`
Contendo `Flask`, `Flask-SQLAlchemy` e `requests`.

---

## User Review Required

> [!IMPORTANT]
> - A aplicação pressupõe que o **Ollama já está rodando** em seu computador na porta padrão (`http://localhost:11434`).
> - Apenas o tempo de resposta de geração (`total_duration` no retorno do Ollama) será considerado como métrica primária do teste.
> - A criação de um ambiente virtual em `.venv` já está configurada. Posso proceder com a instalação do Flask e demais dependências ali dentro?

Por favor, aprove o plano ou informe se deseja alguma alteração!
