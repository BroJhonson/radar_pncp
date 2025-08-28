// src/js/modules/global.js

function debounce(func, wait, immediate) {
    let timeout;
    return function() {
        const context = this, args = arguments;
        const later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}


export function setupGlobalFeatures() {
    console.log("Configurando funcionalidades globais...");

    // --- LÓGICA PARA POSICIONAR O PAINEL DE FEEDBACK ---
    const templateFeedback = document.getElementById('template-painel-feedback');
    const placeholderDesktop = document.getElementById('feedback-placeholder-desktop');
    const placeholderMobile = document.getElementById('feedback-placeholder-mobile');
    const mobileMenuButton = document.getElementById('mobileMenuButton');

    if (templateFeedback && placeholderDesktop && placeholderMobile) {
        const cloneFeedbackContent = () => {
            placeholderDesktop.innerHTML = '';
            placeholderMobile.innerHTML = '';
            return templateFeedback.content.cloneNode(true);
        };
        const positionFeedbackPanel = () => {
            const feedbackContent = cloneFeedbackContent();
            if (window.innerWidth >= 992) {
                placeholderDesktop.appendChild(feedbackContent);
            } else {
                placeholderMobile.appendChild(feedbackContent);
            }
        };
        positionFeedbackPanel();
        window.addEventListener('resize', debounce(positionFeedbackPanel, 200));
    }

    // Reduz o z-index do dropdown do menu mobile quando qualquer offcanvas estiver aberto
    if (mobileMenuButton) {
        const offcanvasElements = document.querySelectorAll('.offcanvas');
        const mobileMenuDropdown = mobileMenuButton.closest('.dropdown');

        offcanvasElements.forEach(offcanvasEl => {
            offcanvasEl.addEventListener('show.bs.offcanvas', () => {
                if (mobileMenuDropdown) mobileMenuDropdown.style.zIndex = '1040'; // Menor que o backdrop (1590)
            });
            offcanvasEl.addEventListener('hidden.bs.offcanvas', () => {
                if (mobileMenuDropdown) mobileMenuDropdown.style.zIndex = ''; // Volta ao padrão
            });
        });
    }

    // --- LÓGICA DO BOTÃO "VOLTAR AO TOPO" ---
    function scrollToTop() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    const btnVoltarAoTopo = document.getElementById('btnVoltarAoTopo');
    if (btnVoltarAoTopo) {
        btnVoltarAoTopo.addEventListener('click', scrollToTop);

        window.onscroll = function() {
            // Usa classList para adicionar/remover a classe 'show'
            if (document.body.scrollTop > 100 || document.documentElement.scrollTop > 100) {
                btnVoltarAoTopo.classList.add('show');
            } else {
                btnVoltarAoTopo.classList.remove('show');
            }
        };
    }

    // --- LÓGICA DO BANNER DE COOKIES ---
    const COOKIE_CONSENT_KEY = 'radarPncpCookieConsent';
    const banner = document.getElementById('cookieConsentBanner');
    const btnAceitar = document.getElementById('btnAceitarCookies');

    if (!localStorage.getItem(COOKIE_CONSENT_KEY) && banner) {
        setTimeout(() => banner.classList.add('show'), 500);
    }
    if (btnAceitar) {
        btnAceitar.addEventListener('click', () => {
            localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({ accepted: true, timestamp: new Date().toISOString() }));
            if (banner) banner.classList.remove('show');
        });
    }

    // --- LÓGICA PARA AJUSTAR O LOGO POR PÁGINA ---
    function ajustarLogoPorPagina() {
        const logoDesktop = document.getElementById('logoDesktop');
        const logoBuscaLicitacoes = document.getElementById('logoBuscaLicitacoes');
        const logoMobile = document.getElementById('logoMobile');
        const logoBuscaLicitacoesMobile = document.getElementById('logoBuscaLicitacoesMobile');

        if (!logoDesktop || !logoBuscaLicitacoes || !logoMobile || !logoBuscaLicitacoesMobile) return;

        if (document.body.classList.contains('page-busca-licitacoes')) {
            logoDesktop.style.display = 'none';
            logoBuscaLicitacoes.style.display = 'inline-block';
            logoMobile.style.display = 'none';
            logoBuscaLicitacoesMobile.style.display = 'inline-block';
        } else {
            logoDesktop.style.display = 'inline-block';
            logoBuscaLicitacoes.style.display = 'none';
            logoMobile.style.display = 'inline-block';
            logoBuscaLicitacoesMobile.style.display = 'none';
        }
    }
    ajustarLogoPorPagina();

    // --- LÓGICA ESPECÍFICA DA HOME PAGE ---
    if (document.body.classList.contains('page-home')) {
        console.log("Lógica da Home Page (acordeão) iniciada.");
        const accordionCards = document.querySelectorAll('.accordion-card');
        const isMobile = () => window.innerWidth <= 767;

        const setupAccordionListeners = () => {
            accordionCards.forEach(card => {
                card.removeEventListener('mouseover', handleMouseOver);
                card.removeEventListener('click', handleClick);
            });
            if (isMobile()) {
                accordionCards.forEach(card => card.addEventListener('click', handleClick));
            } else {
                accordionCards.forEach(card => card.addEventListener('mouseover', handleMouseOver));
            }
        };

        function handleMouseOver() {
            accordionCards.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
        }

        function handleClick() {
            const isAlreadyActive = this.classList.contains('active');
            accordionCards.forEach(c => c.classList.remove('active'));
            if (!isAlreadyActive) {
                this.classList.add('active');
            }
        }
        setupAccordionListeners();
        window.addEventListener('resize', debounce(setupAccordionListeners, 250));
    }
}