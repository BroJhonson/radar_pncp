# Plano de Refatoração: Separação Frontend/Backend

## 1. Nova Estrutura de Pastas

```
radar_pncp/
├── backend/
│   ├── app.py
│   ├── sync_api.py
│   ├── create_admin.py
│   ├── limpeza_db.py
│   ├── create_mariadb.sql
│   ├── requirements.txt
│   ├── src/                 # Lógica de negócio Python
│   ├── database/            # Arquivos de banco de dados (ex: sqlite.db)
│   └── config/              # Arquivos de configuração (ex: .env)
└── frontend/
    ├── public/              # Assets estáticos (CSS, JS compilado, imagens)
    ├── src/                 # Código fonte do frontend (JS, SCSS, HTML)
    │   ├── js/
    │   ├── scss/
    │   └── templates/       # Templates HTML (se o frontend renderizar)
    ├── package.json
    ├── package-lock.json
    └── build_scripts/       # Scripts de build do frontend (ex: esbuild)
```

## 2. Ajustes Necessários para Comunicação

- **Backend (Flask):**
    - Expor endpoints de API para o frontend.
    - Configurar CORS para permitir requisições do domínio do frontend.
    - Garantir que o banco de dados e a lógica de negócio estejam acessíveis apenas pelo backend.

- **Frontend (JavaScript):**
    - Atualizar todas as chamadas de API para apontar para os novos endpoints do backend.
    - Utilizar variáveis de ambiente (ou um arquivo de configuração) para gerenciar a URL base do backend.
    - Ajustar caminhos de assets estáticos (CSS, JS, imagens) para refletir a nova estrutura `public/`.

## 3. O que Permanecerá Inalterado

- **Lógica de Negócio:** Nenhuma alteração será feita na lógica interna dos arquivos Python (`app.py`, `sync_api.py`, `src/`).
- **Esquema do Banco de Dados:** O arquivo `create_mariadb.sql` e a estrutura do banco de dados permanecerão os mesmos.
- **Linguagens e Frameworks:** Python/Flask para o backend e HTML/SCSS/JavaScript para o frontend serão mantidos.
- **Funcionalidades:** Todas as funcionalidades existentes deverão operar exatamente como antes da refatoração.

