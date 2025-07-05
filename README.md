# Radar PNCP - Ferramenta de Busca de Licitações

## Visão Geral

O Radar PNCP é uma aplicação web desenvolvida em Flask (Python) que atua como uma interface amigável e poderosa para o Portal Nacional de Contratações Públicas (PNCP). O objetivo principal é facilitar a busca, filtragem e acompanhamento de licitações públicas, oferecendo uma experiência de usuário superior à do portal oficial.

A aplicação é gratuita e de acesso público, com funcionalidades como filtros avançados, salvamento de licitações favoritas (usando `localStorage`) e um blog informativo.

---

## Estrutura do Projeto

O projeto segue uma estrutura padrão para aplicações Flask, separando lógica, templates e arquivos estáticos.

/frontend/
|
├── static/
| ├── css/
| | └── style.css # Folha de estilo principal
| ├── js/
| | └── main.js # Lógica JavaScript do frontend
| └── images/
| └── ... # Imagens, logos e ícones
|
├── templates/
| ├── base.html # Template base com header e footer
| ├── index.html # Homepage do projeto
| ├── radar.html # Página principal da ferramenta de busca
| ├── pagina_blog.html # Página de listagem dos artigos do blog
| ├── pagina_post_individual.html # Template para um único post
| ├── pagina_contato.html # Página com formulário de contato
| ├── pagina_politica_privacidade.html # Política de Privacidade
| ├── pagina_politica_cookies.html # Política de Cookies
| └── 404.html # Página de erro 404
|
└── app.py # Arquivo principal da aplicação Flask


---

## Tecnologias Utilizadas

*   **Backend:** Python com o micro-framework Flask.
*   **Frontend:** HTML5, CSS3, JavaScript (Vanilla JS).
*   **Framework CSS:** Bootstrap 5 para layout responsivo e componentes base.
*   **Templates:** Jinja2 (integrado ao Flask).
*   **Bibliotecas JS:** AOS (Animate On Scroll) para animações de rolagem.

---

## Principais Funcionalidades Implementadas

### Frontend (JavaScript - `main.js`)

*   **Lógica de Página Específica:** O `main.js` utiliza a classe do `<body>` (ex: `.page-home`, `.page-busca-licitacoes`) para executar scripts apenas nas páginas relevantes.
*   **Busca de Licitações (`radar.html`):**
    *   Comunicação via `fetch` com uma API interna (`/api/frontend/licitacoes`) para buscar dados.
    *   Renderização dinâmica da tabela de resultados e da paginação.
    *   Manipulação de múltiplos filtros (palavras-chave, datas, UFs, modalidades, status).
    *   Seleção de linha na tabela para melhor feedback visual.
*   **Sistema de Favoritos:**
    *   Utiliza o `localStorage` do navegador para persistir os dados.
    *   Funções para adicionar, remover e verificar favoritos.
    *   Sincronização da UI (botões e listas) em tempo real.
*   **Responsividade Dinâmica:**
    *   O acordeão horizontal da homepage se transforma em vertical no mobile.
    *   A tabela de licitações se transforma em uma lista de "cards" no mobile para melhor legibilidade.
*   **Banner de Cookies:** Gerencia o consentimento do usuário, salvando a preferência no `localStorage` para não exibir o banner novamente.

### Estilização (CSS - `style.css`)

*   **Design Responsivo (Mobile-First approach):** Uso intensivo de Media Queries para adaptar o layout do desktop para tablets e celulares.
*   **Componentes Customizados:** Estilos para acordeão horizontal, botões flutuantes, cards de blog, e painéis laterais (offcanvas).
*   **Microinterações:** Efeitos de `hover`, transições suaves e animações para criar uma experiência de usuário mais rica.
*   **Isolamento de Estilos:** Uso de classes no `<body>` para aplicar estilos específicos por página, evitando conflitos.

---

## Como Executar o Projeto Localmente

1.  **Pré-requisitos:** Certifique-se de ter o Python 3 instalado.
2.  **Clone o repositório:**
    ```bash
    git clone [URL_DO_SEU_REPOSITORIO]
    cd [NOME_DA_PASTA]
    ```
3.  **Crie e ative um ambiente virtual:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```
4.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt 
    # (Lembre-se de criar um arquivo requirements.txt com 'pip freeze > requirements.txt')
    ```
5.  **Execute a aplicação:**
    ```bash
    flask run
    # ou
    python app.py
    ```
6.  Abra o navegador e acesse `http://127.0.0.1:5000`.