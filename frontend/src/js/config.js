// Configuração do Frontend
const CONFIG = {
    // URL base do backend - ajustar conforme ambiente
    API_BASE_URL: process.env.NODE_ENV === 'production' 
        ? 'https://api.radar-pncp.com'  // URL de produção
        : 'http://localhost:5000',      // URL de desenvolvimento
    
    // Endpoints da API
    ENDPOINTS: {
        LICITACOES: '/api/licitacoes',
        EXPORTAR_CSV: '/api/exportar-csv',
        DETALHES_LICITACAO: '/api/licitacao',
        MUNICIPIOS: '/api/municipios',
        MODALIDADES: '/api/modalidades',
        CONTATO: '/processar-contato'
    },
    
    // Configurações de paginação
    PAGINATION: {
        DEFAULT_ITEMS_PER_PAGE: 10,
        MAX_ITEMS_PER_PAGE: 100
    },
    
    // Configurações de localStorage
    STORAGE_KEYS: {
        FAVORITOS: 'radarPncpFavoritos',
        FILTROS: 'radarPncpUltimosFiltros',
        COLLAPSE_STATE: 'radarPncpCollapseState',
        COOKIE_CONSENT: 'radarPncpCookieConsent'
    }
};

// Função para construir URL completa da API
function buildApiUrl(endpoint, params = {}) {
    const url = new URL(CONFIG.API_BASE_URL + endpoint);
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
            url.searchParams.append(key, params[key]);
        }
    });
    return url.toString();
}

// Função para fazer requisições à API
async function apiRequest(endpoint, options = {}) {
    const url = CONFIG.API_BASE_URL + endpoint;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include', // Para incluir cookies de sessão
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, finalOptions);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Erro na requisição à API:', error);
        throw error;
    }
}

// Exportar configurações para uso global
window.CONFIG = CONFIG;
window.buildApiUrl = buildApiUrl;
window.apiRequest = apiRequest;

