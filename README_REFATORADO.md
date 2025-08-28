# RADAR PNCP - Arquitetura Separada Frontend/Backend

> **🎯 Refatoração Concluída:** Este projeto foi refatorado de uma aplicação monolítica para uma arquitetura separada de frontend e backend, mantendo todas as funcionalidades originais.

## 📋 Visão Geral

O **RADAR PNCP** é uma plataforma avançada para busca e acompanhamento de licitações públicas do Portal Nacional de Contratações Públicas (PNCP). Após a refatoração, a aplicação agora possui:

- **Backend:** API Flask com todas as funcionalidades de negócio
- **Frontend:** Interface estática que consome a API do backend
- **Deployment Independente:** Cada parte pode ser hospedada separadamente

## 🏗️ Nova Estrutura

```
radar_pncp/
├── backend/                 # 🔧 API Flask + Admin
│   ├── app.py              # Aplicação principal (com CORS)
│   ├── sync_api.py         # Sincronização PNCP
│   ├── requirements.txt    # Dependências Python
│   └── src/                # Código fonte Python
│
├── frontend/               # 🎨 Interface do Usuário
│   ├── public/             # Assets compilados
│   │   ├── dist/           # CSS/JS compilados
│   │   ├── images/         # Imagens
│   │   └── index.html      # Página principal
│   ├── src/                # Código fonte
│   │   ├── js/             # JavaScript + Config API
│   │   └── scss/           # Estilos SCSS
│   └── package.json        # Dependências Node.js
│
└── REFATORACAO_DOCUMENTACAO.md  # 📚 Documentação completa
```

## 🚀 Como Executar

### Backend (API + Admin)

```bash
# 1. Navegar para o backend
cd backend/

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente (.env)
FLASK_SECRET_KEY=sua_chave_secreta
MARIADB_HOST=localhost
MARIADB_USER=seu_usuario
MARIADB_PASSWORD=sua_senha
MARIADB_DATABASE=radar_pncp

# 4. Executar aplicação
python3 app.py
```

**Backend disponível em:** `http://localhost:5000`
- APIs: `/api/*`
- Admin: `/admin`

### Frontend (Interface)

```bash
# 1. Navegar para o frontend
cd frontend/

# 2. Instalar dependências
npm install

# 3. Compilar assets
npm run build:prod

# 4. Servir arquivos estáticos
npm run serve
```

**Frontend disponível em:** `http://localhost:8080`

## 🔧 Configuração da API

O frontend se conecta ao backend através do arquivo `frontend/src/js/config.js`:

```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:5000',  // Desenvolvimento
    // API_BASE_URL: 'https://api.radar-pncp.com',  // Produção
};
```

## 📦 Deployment

### Backend
- **Servidor tradicional:** Nginx + Gunicorn
- **Docker:** Dockerfile incluído
- **Cloud:** Heroku, Railway, AWS, etc.

### Frontend
- **Hosting estático:** Netlify, Vercel, GitHub Pages
- **CDN:** AWS CloudFront, Cloudflare
- **Servidor web:** Nginx, Apache

## ✨ Funcionalidades Preservadas

Todas as funcionalidades originais foram mantidas:

- ✅ Busca avançada com filtros inteligentes
- ✅ Sistema de favoritos (localStorage)
- ✅ Exportação para CSV
- ✅ Painel administrativo Flask-Admin
- ✅ Blog com posts categorizados
- ✅ Formulário de contato
- ✅ Interface responsiva

## 🔄 Migração da Versão Monolítica

Se você está migrando da versão monolítica:

1. **Backup:** Faça backup do banco de dados atual
2. **Backend:** Configure o backend com CORS habilitado
3. **Frontend:** Compile e configure URLs da API
4. **Teste:** Valide todas as funcionalidades
5. **Deploy:** Publique frontend e backend separadamente

## 🛠️ Desenvolvimento

### Scripts Disponíveis

**Backend:**
```bash
python3 app.py              # Executar aplicação
python3 sync_api.py         # Sincronizar dados PNCP
python3 create_admin.py     # Criar usuário admin
```

**Frontend:**
```bash
npm run dev                 # Desenvolvimento (watch mode)
npm run build:prod          # Build de produção
npm run serve               # Servir arquivos estáticos
```

## 📊 Benefícios da Refatoração

### Técnicos
- **Escalabilidade:** Frontend e backend escalam independentemente
- **Performance:** Frontend via CDN, backend otimizado para APIs
- **Manutenibilidade:** Código organizado e responsabilidades separadas

### Operacionais
- **Deployment flexível:** Cada parte em ambiente adequado
- **Custos otimizados:** Frontend estático é mais barato
- **Zero downtime:** Atualizações independentes

### Desenvolvimento
- **Equipes paralelas:** Frontend e backend podem ser desenvolvidos simultaneamente
- **Tecnologias específicas:** Cada parte pode evoluir independentemente
- **Debugging simplificado:** Problemas isolados por camada

## 🔒 Segurança

- **CORS configurado** para comunicação segura entre domínios
- **HTTPS obrigatório** em produção
- **Rate limiting** recomendado para APIs
- **Autenticação preservada** do sistema original

## 📚 Documentação Completa

Para informações detalhadas sobre a refatoração, consulte:
- [`REFATORACAO_DOCUMENTACAO.md`](./REFATORACAO_DOCUMENTACAO.md) - Documentação técnica completa

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto mantém a licença original. Consulte o arquivo LICENSE para detalhes.

## 🆘 Suporte

Para dúvidas sobre a refatoração ou problemas técnicos:

1. Consulte a [documentação completa](./REFATORACAO_DOCUMENTACAO.md)
2. Verifique as [issues existentes](https://github.com/BroJhonson/radar_pncp/issues)
3. Abra uma nova issue se necessário

---

**Refatoração realizada por:** Manus AI  
**Data:** Agosto 2025  
**Status:** ✅ Concluída com Sucesso

