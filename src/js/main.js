// src/js/main.js

import { setupGlobalFeatures } from './modules/global.js';
import initRadarPage from './pages/radar.js';

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM Carregado. Orquestrador JS iniciado.");

    // 1. Executa as funcionalidades globais, que rodam em todas as páginas
    setupGlobalFeatures();

    // 2. Roteamento: Verifica qual página está ativa e chama o módulo correspondente
    if (document.body.classList.contains('page-busca-licitacoes')) {
        initRadarPage();
    }
});