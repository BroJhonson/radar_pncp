// static/js/main.js
// FUNÇÃO PARA DE BOTÃO TOPO
function scrollToTop() { // Função global
    window.scrollTo({top: 0, behavior: 'smooth'});
}

// DIFERENCIAR A LOGO POR PAGINA
function ajustarLogoPorPagina() {
    const logoDesktop = document.getElementById('logoDesktop');
    const logoBuscaLicitacoes = document.getElementById('logoBuscaLicitacoes');
    const logoMobile = document.getElementById('logoMobile');
    const logoBuscaLicitacoesMobile = document.getElementById('logoBuscaLicitacoesMobile');

    if (!logoDesktop || !logoBuscaLicitacoes || !logoMobile || !logoBuscaLicitacoesMobile) return;

    if (document.body.classList.contains('page-busca-licitacoes')) {
        logoDesktop.style.display = 'none';
        logoBuscaLicitacoes.style.display = 'inline-block'; // ou 'block'
        logoMobile.style.display = 'none';
        logoBuscaLicitacoesMobile.style.display = 'inline-block'; // ou 'block'
    } else {
        logoDesktop.style.display = 'inline-block';
        logoBuscaLicitacoes.style.display = 'none';
        logoMobile.style.display = 'inline-block';
        logoBuscaLicitacoesMobile.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM Carregado. Iniciando main.js...");

    // Ajuda a não disparar o 'resize' excessivamente ajuda a controlar a frequência com que positionFeedbackPanel é chamada
    // durante o evento resize. Sem isso, a função seria chamada muitas vezes enquanto o usuário arrasta a janela, o que pode ser custoso.
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

    // --- LÓGICA PARA POSICIONAR O PAINEL DE FEEDBACK ---
    const templateFeedback = document.getElementById('template-painel-feedback');
    const placeholderDesktop = document.getElementById('feedback-placeholder-desktop');
    const placeholderMobile = document.getElementById('feedback-placeholder-mobile');

    if (templateFeedback && placeholderDesktop && placeholderMobile) {
        const cloneFeedbackContent = () => {
            // Remove qualquer conteúdo anterior dos placeholders
            placeholderDesktop.innerHTML = '';
            placeholderMobile.innerHTML = '';

            // Clona o conteúdo do template
            const feedbackNode = templateFeedback.content.cloneNode(true);
            return feedbackNode;
        };

        const positionFeedbackPanel = () => {
            const feedbackContent = cloneFeedbackContent(); // Pega uma nova cópia do conteúdo

            if (window.innerWidth >= 992) { // Breakpoint 'lg' do Bootstrap (Desktop)
                placeholderDesktop.appendChild(feedbackContent);
                placeholderMobile.innerHTML = ''; // Garante que o mobile esteja vazio
            } else { // Mobile
                placeholderMobile.appendChild(feedbackContent);
                placeholderDesktop.innerHTML = ''; // Garante que o desktop esteja vazio
            }
        };

        positionFeedbackPanel(); // Chama na carga inicial
        window.addEventListener('resize', debounce(positionFeedbackPanel, 200)); // Chama no redimensionamento com debounce
    }
    // --- FIM DA LÓGICA DO PAINEL DE FEEDBACK ---

    // --- LOGICA PRA EMPURRAR O HEADER QUANDO O OFFCANVAS FOR ABERTO ---
    const headerElement = document.querySelector('header.border-bottom');
    const offcanvasElements = document.querySelectorAll('.offcanvas');
    let originalScrollY = 0; // Variável para armazenar a posição de rolagem

    if (headerElement && offcanvasElements.length > 0) {
        offcanvasElements.forEach(offcanvasEl => {
            offcanvasEl.addEventListener('show.bs.offcanvas', function () {
                // Só executa em telas mobile (onde o header não é fixo)
                if (window.innerWidth < 992) {
                    originalScrollY = window.scrollY; // Salva a posição atual de rolagem

                    // Calcula a posição do topo do header em relação à viewport
                    const headerRect = headerElement.getBoundingClientRect();
                    const headerHeight = headerElement.offsetHeight;

                    // Se o topo do header estiver visível ou acima da viewport (headerRect.top <= 0)
                    // E se a rolagem atual for menor que a altura do header
                    // (ou seja, o header está total ou parcialmente visível no topo)
                    if (headerRect.top < headerHeight && originalScrollY < headerHeight) {
                        // Rola a página para que o header saia da tela
                        // A nova posição de rolagem será a altura do header
                        // (ou a posição atual + o restante da altura do header visível)
                        let scrollToPosition = headerHeight;
                        if (originalScrollY > 0 && originalScrollY < headerHeight) {
                            // Se já rolou um pouco, mas não o suficiente
                            scrollToPosition = originalScrollY + (headerHeight - originalScrollY);
                        }


                        window.scrollTo({
                            top: scrollToPosition,
                            behavior: 'smooth' // Rolagem suave!
                        });
                    }
                }
            });

            offcanvasEl.addEventListener('hidden.bs.offcanvas', function () {
                // Só executa em telas mobile
                if (window.innerWidth < 992) {
                    // Rola de volta para a posição original, suavemente
                    window.scrollTo({
                        top: originalScrollY,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    // ========= GERENCIADOR DE COOKIES ========= // 
    const COOKIE_CONSENT_KEY = 'radarPncpCookieConsent';

    const banner = document.getElementById('cookieConsentBanner');
    const btnAceitar = document.getElementById('btnAceitarCookies');

    // Verifica se o consentimento já foi dado
    const consentimentoDado = localStorage.getItem(COOKIE_CONSENT_KEY);

    // Se não há consentimento registrado E o banner existe
    if (!consentimentoDado && banner) {
        // Mostra o banner com um pequeno atraso para não ser tão abrupto
        setTimeout(() => {
            banner.classList.add('show');
        }, 500); // 0.5 segundo
    }
    
    // Se o botão de aceitar existe, adiciona o evento de clique
    if (btnAceitar) {
        btnAceitar.addEventListener('click', () => {
            // 1. Grava o consentimento no localStorage
            // Salvamos 'true' e a data, para futuras auditorias ou expiração
            localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify({accepted: true, timestamp: new Date().toISOString()}));
            
            // 2. Esconde o banner
            if (banner) {
                banner.classList.remove('show');
            }
            console.log("Consentimento de cookies aceito e gravado.");
        });
    }
    // --- FIM DO GERENCIADOR DE COOKIES ---

    // FORMATAR DATA E HORA
    const formatDateTime = (dateTimeString) => {
        if (!dateTimeString) return 'N/I';
        try {
            const dateObj = new Date(dateTimeString);
            // Verifica se a data é válida
            if (isNaN(dateObj.getTime())) {
                // Tenta adicionar 'Z' se for uma string sem fuso e falhou
                const dateObjUTC = new Date(dateTimeString + 'Z');
                if (isNaN(dateObjUTC.getTime())) {
                    console.warn("Data/hora inválida recebida:", dateTimeString);
                    return 'Data/Hora Inválida';
                }
                return dateObjUTC.toLocaleString('pt-BR', {
                    year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit' // Removido 'second' para mais limpeza
                });
            }
            return dateObj.toLocaleString('pt-BR', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit' // Removido 'second' para mais limpeza
            });
        } catch (e) {
            console.error("Erro ao formatar data e hora:", dateTimeString, e);
            return 'Data/Hora Inválida';
        }
    };


    // ======================================== //
    // ============== HOME PAGE =============== //    
    if (document.body.classList.contains('page-home')) {
        console.log("Página Home detectada. Lógica específica da home pode ir aqui.");
        
        const accordionCards = document.querySelectorAll('.accordion-card');
        const isMobile = () => window.innerWidth <= 767;

        const setupAccordionListeners = () => {
            // Remove listeners antigos para evitar duplicação ao redimensionar
            accordionCards.forEach(card => {
                card.removeEventListener('mouseover', handleMouseOver);
                card.removeEventListener('click', handleClick);
            });

            if (isMobile()) {
                // Em mobile, usa o evento de CLIQUE
                accordionCards.forEach(card => card.addEventListener('click', handleClick));
            } else {
                // Em desktop, usa o evento de MOUSEOVER
                accordionCards.forEach(card => card.addEventListener('mouseover', handleMouseOver));
            }
        };

        function handleMouseOver() {
            // 'this' se refere ao card que acionou o evento
            accordionCards.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
        }

        function handleClick() {
            // Verifica se o card clicado já está ativo
            const isAlreadyActive = this.classList.contains('active');
            
            // Remove 'active' de todos
            accordionCards.forEach(c => c.classList.remove('active'));

            // Se não estava ativo, ativa-o. (Isso cria um efeito de "toggle")
            if (!isAlreadyActive) {
                this.classList.add('active');
            }
        }

        // Configura os listeners na carga inicial da página
        setupAccordionListeners();
        // E reconfigura se o usuário redimensionar a janela (ex: virar o tablet)
        window.addEventListener('resize', debounce(setupAccordionListeners, 250));
    }

    // ======================================== //
    // ========= GERENCIAR FAVORITOS ========== // 
    const FAVORITOS_KEY = 'radarPncpFavoritos';

    function getFavoritos() {
        const favoritosJson = localStorage.getItem(FAVORITOS_KEY);
        try {
            // Tenta parsear, se for inválido ou não existir, retorna array vazio
            return favoritosJson ? JSON.parse(favoritosJson) : [];
        } catch (e) {
            console.error("Erro ao parsear favoritos do localStorage:", e);
            localStorage.removeItem(FAVORITOS_KEY); // Remove item corrompido
            return [];
        }
    }

    function adicionarFavorito(pncpId) {
        if (!pncpId) return false;
        let favoritos = getFavoritos();
        if (!favoritos.includes(pncpId)) {
            favoritos.push(pncpId);
            localStorage.setItem(FAVORITOS_KEY, JSON.stringify(favoritos));
            console.log("Adicionado aos favoritos:", pncpId, "Lista atual:", favoritos);
            return true;
        }
        console.log(pncpId, "já era favorito.");
        return false; // Já era favorito
    }

    function removerFavorito(pncpId) {
        if (!pncpId) return false;
        let favoritos = getFavoritos();
        const index = favoritos.indexOf(pncpId);
        if (index > -1) {
            favoritos.splice(index, 1);
            localStorage.setItem(FAVORITOS_KEY, JSON.stringify(favoritos));
            console.log("Removido dos favoritos:", pncpId, "Lista atual:", favoritos);
            return true;
        }
        console.log(pncpId, "não encontrado nos favoritos para remover.");
        return false; // Não era favorito
    }

    function isFavorito(pncpId) {
        if (!pncpId) return false;
        return getFavoritos().includes(pncpId);
    }
    // --- FIM DAS FUNÇÕES DE FAVORITOS ---

    // ============================================ //
    // ======== FUNÇÃO PRINCIPAL DO RADAR ========= //

    if (document.body.classList.contains('page-busca-licitacoes')) { //ENTRAR NA PAGINA DO BUSCADOR DE LICITAÇÕES
        console.log("Página de busca de licitações detectada (via body_class). Inicializando funcionalidades...");

        // Elementos do DOM
        const filtrosAtivosContainer = document.getElementById('filtrosAtivosContainer');
        const filtrosAtivosTexto = document.getElementById('filtrosAtivosTexto');
        const linkLimparFiltrosRapido = document.getElementById('linkLimparFiltrosRapido');
        const ufsContainer = document.getElementById('ufsContainerDropdown');
        const municipiosHelp = document.getElementById('municipiosHelp');
        const modalidadesContainer = document.getElementById('modalidadesContainerDropdown'); 
        const statusContainer = document.getElementById('statusContainer');
        const statusWarning = document.getElementById('statusWarning');
        const dataPubInicioInput = document.getElementById('dataPubInicio');
        const dataPubFimInput = document.getElementById('dataPubFim');
        const dataAtualizacaoInicioInput = document.getElementById('dataAtualizacaoInicio'); // Você precisará adicionar este input no HTML
        const dataAtualizacaoFimInput = document.getElementById('dataAtualizacaoFim');     // e este também
        const valorMinInput = document.getElementById('valorMin');
        const valorMaxInput = document.getElementById('valorMax');
        const btnBuscarLicitacoes = document.getElementById('btnBuscarLicitacoes');
        const btnLimparFiltros = document.getElementById('btnLimparFiltros');    
        const licitacoesTableBody = document.getElementById('licitacoesTableBody');
        const paginationControls = document.getElementById('paginationControls');
        const totalRegistrosInfo = document.getElementById('totalRegistrosInfo');
        const exibicaoInfo = document.getElementById('exibicaoInfo');
        const ordenarPorSelect = document.getElementById('ordenarPor');
        const itensPorPaginaSelect = document.getElementById('itensPorPagina');
        const palavraChaveInclusaoInputField = document.getElementById('palavraChaveInclusaoInput'); // Novo ID        
        const tagsPalavraInclusaoContainer = document.getElementById('tagsPalavraInclusaoContainer');
        const palavraChaveExclusaoInputField = document.getElementById('palavraChaveExclusaoInput'); // Novo ID        
        const tagsPalavraExclusaoContainer = document.getElementById('tagsPalavraExclusaoContainer');
        const loadingOverlay = document.getElementById('loadingOverlay');
        const listaFavoritosSidebar = document.getElementById('lista-favoritos-sidebar'); // lISTAR OS fAVORITOS        
        const detailsPanelElement = document.getElementById('detailsPanel'); 
        const offcanvasFiltrosBody = document.getElementById('offcanvasFiltrosBody'); //Funcionalidade de ctrl+enter no painel de filtros

        if(linkLimparFiltrosRapido) { // Garante que o elemento existe
            linkLimparFiltrosRapido.addEventListener('click', function(e){
                e.preventDefault(); // Previne o comportamento padrão do link (navegar para #)                
                limparFiltros(); // Chama a função principal de limpar filtros
            });
        }
        // Arrays para armazenar as palavras-chave
        let palavrasChaveInclusao = [];
        let palavrasChaveExclusao = [];
        // Estado da Aplicação (para filtros, paginação, etc.)
        let currentPage = 1;
        
        // --- CONFIGURAÇÕES DE FILTROS ---
        const ufsLista = [ /* ... sua lista de UFs ... */ 
            { sigla: "AC", nome: "Acre" }, { sigla: "AL", nome: "Alagoas" }, { sigla: "AP", nome: "Amapá" },
            { sigla: "AM", nome: "Amazonas" }, { sigla: "BA", nome: "Bahia" }, { sigla: "CE", nome: "Ceará" },
            { sigla: "DF", nome: "Distrito Federal" }, { sigla: "ES", nome: "Espírito Santo" }, { sigla: "GO", nome: "Goiás" },
            { sigla: "MA", nome: "Maranhão" }, { sigla: "MT", nome: "Mato Grosso" }, { sigla: "MS", nome: "Mato Grosso do Sul" },
            { sigla: "MG", nome: "Minas Gerais" }, { sigla: "PA", nome: "Pará" }, { sigla: "PB", nome: "Paraíba" },
            { sigla: "PR", nome: "Paraná" }, { sigla: "PE", nome: "Pernambuco" }, { sigla: "PI", nome: "Piauí" },
            { sigla: "RJ", nome: "Rio de Janeiro" }, { sigla: "RN", nome: "Rio Grande do Norte" }, { sigla: "RS", nome: "Rio Grande do Sul" },
            { sigla: "RO", nome: "Rondônia" }, { sigla: "RR", nome: "Roraima" }, { sigla: "SC", nome: "Santa Catarina" },
            { sigla: "SP", nome: "São Paulo" }, { sigla: "SE", nome: "Sergipe" }, { sigla: "TO", nome: "Tocantins" }
        ];

        // BOTÃO DE EXPORTAR
        const btnExportarCsv = document.getElementById('btnExportarCsv');
        if (btnExportarCsv) {
            btnExportarCsv.addEventListener('click', function() {
                // --- COLETOR DE FILTROS PARA EXPORTAÇÃO ---
                const params = new URLSearchParams();

                // Palavras-chave
                if (palavrasChaveInclusao.length > 0) {
                    palavrasChaveInclusao.forEach(p => params.append('palavraChave', p));
                }
                if (palavrasChaveExclusao.length > 0) {
                    palavrasChaveExclusao.forEach(p => params.append('excluirPalavra', p));
                }
                // UFs, Modalidades, Status
                document.querySelectorAll('.filter-uf:checked').forEach(cb => params.append('uf', cb.value));
                document.querySelectorAll('.filter-modalidade:checked').forEach(cb => params.append('modalidadeId', cb.value));
                const statusSelecionado = document.querySelector('.filter-status:checked');
                if (statusSelecionado) {
                    params.append('statusRadar', statusSelecionado.value);
                }
                // Municípios
                document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked').forEach(cb => params.append('municipioNome', cb.value));
                // Filtros Avançados
                if (dataPubInicioInput.value) params.append('dataPubInicio', dataPubInicioInput.value);
                if (dataPubFimInput.value) params.append('dataPubFim', dataPubFimInput.value);
                if (dataAtualizacaoInicioInput.value) params.append('dataAtualizacaoInicio', dataAtualizacaoInicioInput.value);
                if (dataAtualizacaoFimInput.value) params.append('dataAtualizacaoFim', dataAtualizacaoFimInput.value);
                if (valorMinInput.value) params.append('valorMin', valorMinInput.value);
                if (valorMaxInput.value) params.append('valorMax', valorMaxInput.value);
                // Ordenação (para o caso de querer o CSV ordenado)
                const [orderByField, orderDirValue] = ordenarPorSelect.value.split('_');
                params.append('orderBy', orderByField);
                params.append('orderDir', orderDirValue.toUpperCase());
                // ---------------------------------------------

                console.log("Exportando com os seguintes parâmetros:", params.toString());
                
                // Constrói a URL e abre em uma nova aba para iniciar o download
                const url = `/api/exportar-csv?${params.toString()}`;
                window.open(url, '_blank');
            });
        }

        // Função Ctrl + Enter aplica filtros, e para limpeza de filtros individuais no painel
        if (offcanvasFiltrosBody) { // Garante que o container dos filtros existe
                        
            offcanvasFiltrosBody.addEventListener('keydown', function(event) {
                // event.key === 'Enter' verifica se a tecla Enter foi pressionada.
                // event.ctrlKey verifica se a tecla Ctrl está pressionada.
                // event.metaKey verifica se a tecla Command (Cmd) está pressionada no Mac.
                
                if ((event.key === 'Enter' || event.key === 'NumpadEnter') && (event.ctrlKey || event.metaKey)) {
                    console.log("Ctrl+Enter pressionado, aplicando filtros...");
                    
                    // Previne o comportamento padrão do Enter (ex: submeter um formulário se houver)
                    event.preventDefault(); 
                    
                    // Chama a sua função de buscar licitações, passando a primeira página
                    buscarLicitacoes(1); 

                    // Opcional: Fechar o Offcanvas de filtros após aplicar
                    const offcanvasFiltrosElement = document.getElementById('offcanvasFiltros');
                    if (offcanvasFiltrosElement) {
                        offcanvasFiltrosElement.addEventListener('show.bs.offcanvas', function () {
                            // Re-renderiza as tags de inclusão e exclusão quando o painel é aberto
                            renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
                            renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
                        });
                        const bsOffcanvas = bootstrap.Offcanvas.getInstance(offcanvasFiltrosElement);
                        if (bsOffcanvas) {
                            bsOffcanvas.hide();
                        }
                    }
                }
            });
        
            offcanvasFiltrosBody.addEventListener('click', function(event) {
                // Verifica se o elemento clicado é o nosso botão de limpar
                if (event.target.classList.contains('btn-limpar-grupo')) {
                    const tipoLimpeza = event.target.dataset.limpar;
                    console.log("Limpando filtro:", tipoLimpeza); // Para debug

                    switch (tipoLimpeza) {
                        case 'status':
                            // Reseta o radio button para o valor padrão
                            const defaultStatus = document.querySelector('.filter-status[value="A Receber/Recebendo Proposta"]');
                            if (defaultStatus) defaultStatus.checked = true;
                            break;

                        case 'modalidades':
                            // Desmarca todos os checkboxes de modalidade
                            document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked').forEach(cb => cb.checked = false);
                            updateModalidadeSelectedCount(); // Atualiza o contador visual
                            break;

                        case 'inclusao':
                            // Limpa o array e as tags de palavras-chave de inclusão
                            palavrasChaveInclusao = [];
                            renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
                            break;
                        
                        case 'exclusao':
                            // Limpa o array e as tags de palavras-chave de exclusão
                            palavrasChaveExclusao = [];
                            renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
                            break;
                        
                        case 'localizacao': // Exemplo se você agrupar UF e Município
                            document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked').forEach(cb => cb.checked = false);
                            handleUFChange(); // Esta função já limpa os municípios e atualiza os contadores
                            break;

                        // Adicione mais 'case' aqui para outros filtros que você criar
                    }
                }
            });
        }

        // FUNÇÃO DE TAGS NAS PALAVRAS-CHAVE
        function renderTags(palavrasArray, containerElement, tipo) {
            if (!containerElement) return; // Proteção
            containerElement.innerHTML = ''; // Limpa tags existentes
            palavrasArray.forEach((palavra, index) => {
                const tag = document.createElement('span');
                tag.classList.add('tag-item');
                tag.textContent = palavra;

                const removeBtn = document.createElement('button');
                removeBtn.classList.add('remove-tag');
                removeBtn.innerHTML = '×';
                removeBtn.title = 'Remover palavra';
                removeBtn.type = 'button'; // Boa prática para botões que não submetem formulários
                removeBtn.addEventListener('click', () => {
                    if (tipo === 'inclusao') {
                        palavrasChaveInclusao.splice(index, 1);
                        renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
                    } else if (tipo === 'exclusao') {
                        palavrasChaveExclusao.splice(index, 1);
                        renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
                    }
                    // Opcional: Disparar busca ou atualização da UI de filtros ativos aqui
                    // atualizarExibicaoFiltrosAtivos();
                    // buscarLicitacoes(1); // Se quiser que a busca seja imediata ao remover tag
                });
                tag.appendChild(removeBtn);
                containerElement.appendChild(tag);
            });
        }

        function addPalavraChave(inputField, palavrasArray, containerElement, tipo) {
            if (!inputField) return; // Proteção
            const termos = inputField.value.trim(); // Pega o valor atual e remove a vírgula/ponto e vírgula

            if (termos) {
                // Divide por vírgula ou ponto e vírgula, e limpa cada termo
                const novasPalavras = termos.split(/[,;]+/)
                                        .map(p => p.trim())
                                        .filter(p => p !== "" && p.length > 0); // Garante que não adicione strings vazias

                let adicionouAlguma = false;
                novasPalavras.forEach(novaPalavra => {
                    if (!palavrasArray.includes(novaPalavra)) { // Evita duplicatas
                        palavrasArray.push(novaPalavra);
                        adicionouAlguma = true;
                    }
                });

                inputField.value = ''; // Limpa o input APÓS processar

                if (adicionouAlguma) {
                    renderTags(palavrasArray, containerElement, tipo);
                }
            }
        }

        // Event Listeners para adicionar palavras-chave (VERSÃO MELHORADA)
        function configurarInputDeTags(inputField, palavrasArray, containerElement, tipo) {
            if (!inputField) return;

            // Handler para a tecla "Enter"
            // Usar 'keyup' é geralmente melhor para 'Enter' do que 'keypress'
            inputField.addEventListener('keyup', function(e) {
                // e.key === 'Enter' é o padrão moderno.
                // e.keyCode === 13 é para navegadores mais antigos ou casos específicos.
                // NumpadEnter também é importante.
                if (e.key === 'Enter' || e.key === 'NumpadEnter' || e.keyCode === 13) {
                    e.preventDefault(); // Previne submissão de formulário se o input estiver em um
                    addPalavraChave(inputField, palavrasArray, containerElement, tipo);
                }
            });

            // Handler para vírgula e ponto e vírgula usando o evento 'input'
            // O evento 'input' dispara sempre que o valor do campo muda.
            inputField.addEventListener('input', function(e) {
                const valorAtual = inputField.value;
                // Verifica se o último caractere digitado foi uma vírgula ou ponto e vírgula
                if (valorAtual.endsWith(',') || valorAtual.endsWith(';')) {
                    // Remove o último caractere (a vírgula/ponto e vírgula) ANTES de adicionar
                    inputField.value = valorAtual.slice(0, -1);
                    addPalavraChave(inputField, palavrasArray, containerElement, tipo);
                }
            });
        }
        // FIM DA FUNÇÃO DE TAGS NAS PALAVRAS-CHAVE
    

        // FUNÇÃO DAS TAGS NO TOPO
        function atualizarExibicaoFiltrosAtivos() {
            if (!filtrosAtivosContainer || !filtrosAtivosTexto) return;

            let filtrosAplicados = [];

            // Palavras-chave de Inclusão
            if (palavrasChaveInclusao.length > 0) {
                filtrosAplicados.push(`Buscar: ${palavrasChaveInclusao.map(p => `<span class="badge bg-primary">${p}</span>`).join(' ')}`);
            }
            // Palavras-chave de Exclusão
            if (palavrasChaveExclusao.length > 0) {
                filtrosAplicados.push(`Excluir: ${palavrasChaveExclusao.map(p => `<span class="badge bg-danger">${p}</span>`).join(' ')}`);
            }
            // UFs
            const ufsSelecionadas = Array.from(document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked')).map(cb => cb.value);
            if (ufsSelecionadas.length > 0) {
                filtrosAplicados.push(`UF: ${ufsSelecionadas.map(uf => `<span class="badge bg-secondary">${uf}</span>`).join(' ')}`);
            }
            // Municípios
            const municipiosSelecionados = Array.from(document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked')).map(cb => cb.value);
            if (municipiosSelecionados.length > 0) {
                filtrosAplicados.push(`Município: ${municipiosSelecionados.map(m => `<span class="badge bg-info text-dark">${m}</span>`).join(' ')}`);
            }
            // Modalidades
            const modalidadesSelecionadas = Array.from(document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked'))
                                            .map(cb => {
                                                const label = document.querySelector(`label[for="${cb.id}"]`);
                                                return label ? label.textContent : cb.value; // Pega o nome do label
                                            });
            if (modalidadesSelecionadas.length > 0) {
                filtrosAplicados.push(`Modalidade: ${modalidadesSelecionadas.map(m => `<span class="badge bg-warning text-dark">${m}</span>`).join(' ')}`);
            }
            // Status
            const statusSelecionadoRadio = document.querySelector('.filter-status:checked');
            if (statusSelecionadoRadio && statusSelecionadoRadio.value) { // Se não for "Todos"
                const labelStatus = document.querySelector(`label[for="${statusSelecionadoRadio.id}"]`);
                filtrosAplicados.push(`Status: <span class="badge bg-success">${labelStatus ? labelStatus.textContent : statusSelecionadoRadio.value}</span>`);
            } else if (statusSelecionadoRadio && statusSelecionadoRadio.value === "") {
                filtrosAplicados.push(`Status: <span class="badge bg-dark">Todos</span>`);
            }
            // Datas Publicação
            if (dataPubInicioInput.value || dataPubFimInput.value) {
                let strDataPub = "Data Pub.: ";
                if (dataPubInicioInput.value) strDataPub += `de ${new Date(dataPubInicioInput.value+'T00:00:00').toLocaleDateString('pt-BR')} `;
                if (dataPubFimInput.value) strDataPub += `até ${new Date(dataPubFimInput.value+'T00:00:00').toLocaleDateString('pt-BR')}`;
                filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strDataPub.trim()}</span>`);
            }
            // Datas Atualização (SE OS INPUTS EXISTIREM)
            if (dataAtualizacaoInicioInput && dataAtualizacaoFimInput && (dataAtualizacaoInicioInput.value || dataAtualizacaoFimInput.value)) {
                let strDataAtual = "Data Atual.: ";
                if (dataAtualizacaoInicioInput.value) strDataAtual += `de ${new Date(dataAtualizacaoInicioInput.value+'T00:00:00').toLocaleDateString('pt-BR')} `;
                if (dataAtualizacaoFimInput.value) strDataAtual += `até ${new Date(dataAtualizacaoFimInput.value+'T00:00:00').toLocaleDateString('pt-BR')}`;
                filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strDataAtual.trim()}</span>`);
            }
            // Valor
            if (valorMinInput.value || valorMaxInput.value) {
                let strValor = "Valor: ";
                if (valorMinInput.value) strValor += `min R$ ${valorMinInput.value} `;
                if (valorMaxInput.value) strValor += `max R$ ${valorMaxInput.value}`;
                filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strValor.trim()}</span>`);
            }


            if (filtrosAplicados.length > 0) {
                filtrosAtivosTexto.innerHTML = filtrosAplicados.join(' • '); // Separador • é um ponto
                filtrosAtivosContainer.style.display = 'block';
            } else {
                filtrosAtivosTexto.innerHTML = 'Nenhum filtro aplicado.';
                // filtrosAtivosContainer.style.display = 'none'; // Ou mostrar "Nenhum filtro aplicado"
            }
        }

        //  FUNÇÃO DE FILTROS - ESTADO -UF
        function updateUFSelectedCount() {
            const count = document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked').length;
            const badge = document.getElementById('ufSelectedCount');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? '' : 'none';
            }
        }

        //  FUNÇÃO DE FILTROS - MODALIDADE
        function updateModalidadeSelectedCount() {
            // O container de modalidades no seu JS original é 'modalidadesContainer'
            const count = document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked').length;
            const badge = document.getElementById('modalidadesSelectedCount');
            if (badge) {
                badge.textContent = count;
                badge.style.display = count > 0 ? 'inline-block' : 'none';
            }
        }

        //  FUNÇÃO DE FILTROS - MUNICIPIO
        function updateMunicipioSelectedCount() {
            const count = document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked').length;
            const badge = document.getElementById('municipiosSelectedCount');
            if (badge) {
                badge.textContent = count;
                // No seu HTML o badge já tem '0', então só precisamos controlar a visibilidade se quiser.
                // Para consistência, vamos usar a mesma lógica:
                badge.style.display = count > 0 ? 'inline-block' : 'none';
                if (count === 0) badge.textContent = '0'; // Garante que o '0' volte ao limpar.
            }
        }

        // FUNÇÃO PESQUISA DENTRO DOS FILTROS
        function setupFilterSearch(inputId, containerId, itemSelector) {
            const searchInput = document.getElementById(inputId);
            const container = document.getElementById(containerId);

            if (!searchInput || !container) {
                return; // Sai da função se os elementos não existirem
            }

            searchInput.addEventListener('input', function () {
                const searchTerm = searchInput.value.toLowerCase();
                const items = container.querySelectorAll(itemSelector);

                items.forEach(item => {
                    // Acessa o texto do <label> que está dentro do div do item
                    const label = item.querySelector('label');
                    if (label) {
                        const itemText = label.textContent.toLowerCase();
                        // Mostra ou esconde o item (o div.form-check) com base na busca
                        if (itemText.includes(searchTerm)) {
                            item.style.display = 'block'; // Ou '' para voltar ao padrão
                        } else {
                            item.style.display = 'none';
                        }
                    }
                });
            });
            container.addEventListener('click', function(event) {
                // Verifica se o que foi clicado foi realmente um checkbox
                if (event.target.matches('.form-check-input')) {
                    
                    // 1. Limpa o campo de busca
                    searchInput.value = '';

                    // 2. Garante que todos os itens da lista fiquem visíveis novamente
                    const items = container.querySelectorAll(itemSelector);
                    items.forEach(item => {
                        item.style.display = 'block';
                    });
                }
            });        
        }

        // ======== FUNÇÕES PARA SALVAR FILTROS DA SEÇÃO ATUAL =========== //
        const FILTROS_KEY = 'radarPncpUltimosFiltros';
        function salvarFiltrosAtuais() {
            // 1. Coleta todos os valores dos campos de filtro
            const filtros = {
                // Palavras-chave já estão em arrays globais
                palavrasChaveInclusao: palavrasChaveInclusao,
                palavrasChaveExclusao: palavrasChaveExclusao,
                
                // Status
                status: document.querySelector('.filter-status:checked')?.value || "A Receber/Recebendo Proposta",
                
                // UFs e Municípios
                ufs: Array.from(document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked')).map(cb => cb.value),
                municipios: Array.from(document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked')).map(cb => cb.value),

                // Modalidades
                modalidades: Array.from(document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked')).map(cb => cb.value),
                
                // Filtros Avançados
                dataPubInicio: dataPubInicioInput.value,
                dataPubFim: dataPubFimInput.value,
                dataAtualizacaoInicio: dataAtualizacaoInicioInput.value,
                dataAtualizacaoFim: dataAtualizacaoFimInput.value,
                valorMin: valorMinInput.value,
                valorMax: valorMaxInput.value,
                
                // Configurações da Tabela
                ordenacao: ordenarPorSelect.value,
                itensPorPagina: itensPorPaginaSelect.value,
            };

            // 2. Salva o objeto de filtros no localStorage como uma string JSON
            localStorage.setItem(FILTROS_KEY, JSON.stringify(filtros));
            console.log("Filtros salvos no localStorage:", filtros);
        }

        // ---- FUNÇÃO PARA CARREGAR FILTROS SALVOS DA ULTIMA SEÇÃO ----
        function carregarFiltrosSalvos() {
            const filtrosSalvosJson = localStorage.getItem(FILTROS_KEY);
            if (!filtrosSalvosJson) {
                console.log("Nenhum filtro salvo encontrado.");
                return; // Sai se não houver nada salvo
            }

            try {
                const filtros = JSON.parse(filtrosSalvosJson);
                console.log("Carregando filtros salvos:", filtros);

                // --- PREENCHE OS CAMPOS ---

                // 1. Palavras-chave
                if (filtros.palavrasChaveInclusao) {
                    palavrasChaveInclusao = filtros.palavrasChaveInclusao;
                    renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
                }
                if (filtros.palavrasChaveExclusao) {
                    palavrasChaveExclusao = filtros.palavrasChaveExclusao;
                    renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
                }

                // 2. Status
                if (filtros.status) {
                    const radioStatus = document.querySelector(`.filter-status[value="${filtros.status}"]`);
                    if (radioStatus) radioStatus.checked = true;
                }

                // 3. UFs (Precisamos marcar e depois chamar a função que carrega os municípios)
                if (filtros.ufs && filtros.ufs.length > 0) {
                    filtros.ufs.forEach(ufSigla => {
                        const checkUf = document.querySelector(`#ufsContainerDropdown .filter-uf[value="${ufSigla}"]`);
                        if (checkUf) checkUf.checked = true;
                    });
                    // Dispara a função para carregar os municípios baseados nas UFs marcadas
                    handleUFChange().then(() => {
                        // SÓ DEPOIS que os municípios carregarem, tentamos marcar os salvos
                        if (filtros.municipios && filtros.municipios.length > 0) {
                            filtros.municipios.forEach(munNome => {
                                const checkMun = document.querySelector(`#municipiosContainerDropdown .filter-municipio[value="${munNome}"]`);
                                if (checkMun) checkMun.checked = true;
                            });
                            updateMunicipioSelectedCount();
                        }
                    });
                }

                // 4. Modalidades
                if (filtros.modalidades && filtros.modalidades.length > 0) {
                    filtros.modalidades.forEach(modId => {
                        const checkMod = document.querySelector(`#modalidadesContainerDropdown .filter-modalidade[value="${modId}"]`);
                        if (checkMod) checkMod.checked = true;
                    });
                    updateModalidadeSelectedCount();
                }

                // 5. Filtros Avançados
                if (filtros.dataPubInicio) dataPubInicioInput.value = filtros.dataPubInicio;
                if (filtros.dataPubFim) dataPubFimInput.value = filtros.dataPubFim;
                if (filtros.dataAtualizacaoInicio) dataAtualizacaoInicioInput.value = filtros.dataAtualizacaoInicio;
                if (filtros.dataAtualizacaoFim) dataAtualizacaoFimInput.value = filtros.dataAtualizacaoFim;
                if (filtros.valorMin) valorMinInput.value = filtros.valorMin;
                if (filtros.valorMax) valorMaxInput.value = filtros.valorMax;

                // 6. Configurações da Tabela
                if (filtros.ordenacao) ordenarPorSelect.value = filtros.ordenacao;
                if (filtros.itensPorPagina) itensPorPaginaSelect.value = filtros.itensPorPagina;

            } catch (e) {
                console.error("Erro ao carregar filtros salvos:", e);
                localStorage.removeItem(FILTROS_KEY); // Remove dados corrompidos
            }
        }

        // --- LÓGICA PARA LEMBRAR ESTADO DOS FILTROS COLAPSÁVEIS ---
        // --- Quando o usuario reabrir a pagina, os filtros colapsáveis devem reabrir como estavam antes
        const COLLAPSE_KEY = 'radarPncpCollapseState';
        const collapsibles = document.querySelectorAll('.filter-collapsible .collapse');
        // Salva o estado quando um filtro é aberto/fechado
        collapsibles.forEach(el => {
            el.addEventListener('shown.bs.collapse', event => {
                const state = JSON.parse(localStorage.getItem(COLLAPSE_KEY) || '{}');
                state[event.target.id] = true;
                localStorage.setItem(COLLAPSE_KEY, JSON.stringify(state));
            });
            el.addEventListener('hidden.bs.collapse', event => {
                const state = JSON.parse(localStorage.getItem(COLLAPSE_KEY) || '{}');
                state[event.target.id] = false;
                localStorage.setItem(COLLAPSE_KEY, JSON.stringify(state));
            });
        });
        // Aplica o estado salvo quando a página carrega
        function aplicarEstadoCollapse() {
            const state = JSON.parse(localStorage.getItem(COLLAPSE_KEY) || '{}');
            for (const id in state) {
                if (state[id]) {
                    const el = document.getElementById(id);
                    if (el) {
                        new bootstrap.Collapse(el, { toggle: false }).show();
                    }
                }
            }
        }


        // ====================== FAVORITOS ====================== //
        // --- FUNÇÃO PARA ATUALIZAR A UI DO BOTÃO DE FAVORITO --- //
        function atualizarBotaoFavoritoUI(buttonElement, pncpId) {
            if (!buttonElement || !pncpId) return;
            const ehFavoritoAgora = isFavorito(pncpId);
            const icon = buttonElement.querySelector('i');

            buttonElement.title = ehFavoritoAgora ? 'Desfavoritar' : 'Favoritar';

           // Lógica para o ícone (estrela cheia/vazia)
            if (icon) {
                if (ehFavoritoAgora) {
                    icon.classList.remove('bi-star');
                    icon.classList.add('bi-star-fill'); // Estrela cheia
                    // Para o botão de detalhes que é btn-link, a cor da estrela já é text-warning.
                    // Para o botão da tabela, vamos garantir que ele pareça 'ativo' ou diferente.
                    if (!buttonElement.classList.contains('btn-link')) { // Se NÃO for o botão de detalhes (ou seja, é o da tabela)
                        buttonElement.classList.remove('btn-outline-warning');
                        buttonElement.classList.add('btn-warning', 'active'); // Mantém o fundo amarelo para o botão da tabela
                    } else { // Se FOR o botão de detalhes (btn-link)
                        buttonElement.classList.add('active'); // Só adiciona 'active' para indicar o estado
                    }
                } else { // Não é favorito
                    icon.classList.remove('bi-star-fill');
                    icon.classList.add('bi-star'); // Estrela vazia
                    if (!buttonElement.classList.contains('btn-link')) { // Botão da tabela
                        buttonElement.classList.remove('btn-warning', 'active');
                        buttonElement.classList.add('btn-outline-warning');
                    } else { // Botão de detalhes
                        buttonElement.classList.remove('active');
                    }
                }
            }
        }
        // --- HANDLER PARA O CLIQUE NO BOTÃO DE FAVORITAR ---
        function handleFavoritarClick(event) { // Sempre espera o evento da delegação
            const button = event.target.closest('.btn-favoritar'); // Pega o botão com a classe .btn-favoritar
            if (!button) return; 

            const pncpId = button.dataset.pncpId;
            if (!pncpId) return;

            let alterou = false;
            if (isFavorito(pncpId)) {
                alterou = removerFavorito(pncpId);
            } else {
                alterou = adicionarFavorito(pncpId);
            }

            if (alterou) {
                atualizarBotaoFavoritoUI(button, pncpId); // Atualiza o botão clicado

                // Sincronizar UI de outros botões para o mesmo PNCP ID
                // Primeiro, o botão na tabela (se não for o que foi clicado)
                const btnNaTabela = licitacoesTableBody.querySelector(`.btn-favoritar[data-pncp-id="${pncpId}"]`);
                if (btnNaTabela && btnNaTabela !== button) {
                    atualizarBotaoFavoritoUI(btnNaTabela, pncpId);
                }
                // Segundo, o botão nos detalhes (se não for o que foi clicado)
                const btnNosDetalhes = document.getElementById('detailsPanelFavoriteBtn');
                if (btnNosDetalhes && btnNosDetalhes !== button && btnNosDetalhes.dataset.pncpId === pncpId) {
                    atualizarBotaoFavoritoUI(btnNosDetalhes, pncpId);
                }

                renderizarFavoritosSidebar();
            }
        }        
        // --- CONFIGURAR EVENT LISTENERS ---
        if (licitacoesTableBody) {
            licitacoesTableBody.addEventListener('click', handleFavoritarClick);
        }
        if (detailsPanelElement) { // Delegação no corpo do painel de detalhes
            detailsPanelElement.addEventListener('click', function(event) {
                // Verifica se o clique foi no botão de favorito (que agora está no header)
                // O ID #detailsPanelFavoriteBtn é importante aqui.
                const favoriteButton = event.target.closest('#detailsPanelFavoriteBtn');
                if (favoriteButton) {
                    handleFavoritarClick(event); // Passa o evento para o handler
                }
                // Se tiver outros botões com .btn-favoritar no painel de detalhes, eles também seriam pegos
                // pela condição mais genérica event.target.closest('.btn-favoritar') se preferir
            });
        }      
        document.addEventListener('click', function(event) {
            // Verifica se o elemento clicado (ou um de seus pais) é o botão de remover
            const removeButton = event.target.closest('.btn-remover-fav-sidebar');

            if (removeButton) {
                event.preventDefault();
                event.stopPropagation();
                const pncpId = removeButton.dataset.pncpId;
                if (pncpId) {
                    removerFavorito(pncpId); // Remove do localStorage
                    renderizarFavoritosSidebar(); // Re-renderiza AMBAS as listas
                    
                    // Atualiza o estado visual dos botões de favoritar na tabela e nos detalhes
                    const btnNaTabela = licitacoesTableBody.querySelector(`.btn-favoritar[data-pncp-id="${pncpId}"]`);
                    if (btnNaTabela) atualizarBotaoFavoritoUI(btnNaTabela, pncpId);

                    const btnNosDetalhes = document.getElementById('detailsPanelFavoriteBtn');
                    if (btnNosDetalhes && btnNosDetalhes.dataset.pncpId === pncpId) atualizarBotaoFavoritoUI(btnNosDetalhes, pncpId);
                }
            }

            // Lógica para clicar no link e abrir detalhes (pode ser mantida aqui também)
            const linkLicitacao = event.target.closest('.sidebar-fav-link');
            if(linkLicitacao) {
                event.preventDefault();
                const pncpId = linkLicitacao.dataset.pncpId;
                const fakeButton = document.createElement('button');
                fakeButton.dataset.pncpId = pncpId;
                const fakeEvent = { currentTarget: fakeButton };
                handleDetalhesClick(fakeEvent);
            }
        });

        // Cache para dados de licitações (para não buscar toda hora só para a sidebar)
        let cacheLicitacoesSidebar = {}; 

        async function renderizarFavoritosSidebar() {
            // Pega as duas listas possíveis. Uma pode não existir dependendo do layout (desktop/mobile).
            const listaSidebar = document.getElementById('lista-favoritos-sidebar');
            const listaOffcanvas = document.getElementById('lista-favoritos-offcanvas');
            
            // Se nenhum dos dois lugares para renderizar os favoritos for encontrado, não faz nada.
            if (!listaSidebar && !listaOffcanvas) {
                return;
            }

            const favoritosIds = getFavoritos();

            // Cria as mensagens padrão uma vez
            const msgVazio = '<li class="list-group-item text-muted small">Nenhuma licitação favoritada ainda.</li>';
            const msgLoader = '<li class="list-group-item text-muted small"><div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>Carregando...</li>';
            const msgErro = '<li class="list-group-item text-danger small fst-italic">Erro ao carregar dados dos favoritos.</li>';
            
            // Prepara as listas (com verificação se elas existem)
            if (listaSidebar) listaSidebar.innerHTML = msgLoader;
            if (listaOffcanvas) listaOffcanvas.innerHTML = msgLoader;
            
            if (favoritosIds.length === 0) {
                if (listaSidebar) listaSidebar.innerHTML = msgVazio;
                if (listaOffcanvas) listaOffcanvas.innerHTML = msgVazio;
                return;
            }
            
            let contentRendered = false;

            for (const pncpId of favoritosIds) {
                let licData = cacheLicitacoesSidebar[pncpId];
                if (!licData) {
                    try {
                        const response = await fetch(`/api/frontend/licitacao/${encodeURIComponent(pncpId)}`);
                        if (response.ok) {
                            const fullData = await response.json();
                            if (fullData.licitacao) {
                                licData = fullData.licitacao;
                                cacheLicitacoesSidebar[pncpId] = licData;
                            }
                        }
                    } catch (error) {
                        console.error("Erro ao buscar favorito para sidebar:", error);
                    }
                }

                if (licData) {
                    if (!contentRendered) {
                        // Limpa o "Carregando..."
                        if (listaSidebar) listaSidebar.innerHTML = '';
                        if (listaOffcanvas) listaOffcanvas.innerHTML = '';
                        contentRendered = true;
                    }

                    const objeto = licData.objetoCompra || licData.numeroControlePNCP;
                    const itemHtml = `
                        <li class="list-group-item d-flex justify-content-between align-items-center py-1 px-1" style="font-size: 0.78em;">
                            <a href="#" class="text-decoration-none text-dark flex-grow-1 me-1 sidebar-fav-link" title="${objeto}" data-pncp-id="${pncpId}">
                                ${objeto.length > 45 ? objeto.substring(0, 42) + '...' : objeto}
                            </a>
                            <button class="btn btn-sm btn-outline-danger p-0 px-1 btn-remover-fav-sidebar" title="Remover dos Favoritos" data-pncp-id="${pncpId}">
                                <i class="bi bi-x-lg" style="font-size: 0.7em;"></i>
                            </button>
                        </li>
                    `;
                    
                    // Adiciona o item em AMBAS as listas, se elas existirem
                    if (listaSidebar) listaSidebar.insertAdjacentHTML('beforeend', itemHtml);
                    if (listaOffcanvas) listaOffcanvas.insertAdjacentHTML('beforeend', itemHtml);
                }
            }

            if (!contentRendered && favoritosIds.length > 0) {
                if (listaSidebar) listaSidebar.innerHTML = msgErro;
                if (listaOffcanvas) listaOffcanvas.innerHTML = msgErro;
            }
        }      
        // ------------------------------------------------------ //


        // --- FUNÇÃO DE EXECUSÃO - MODALIDADES ---
        async function popularModalidades() { 
            if (!modalidadesContainer) return; // Se o container não for encontrado, a função para aqui
            modalidadesContainer.innerHTML = '<small class="text-muted">Carregando modalidades...</small>';
            try {
                const response = await fetch('/api/frontend/referencias/modalidades');            
                if (!response.ok) throw new Error(`Erro ${response.status} ao buscar modalidades.`);
                const modalidadesApi = await response.json();

                modalidadesContainer.innerHTML = ''; 
                if (modalidadesApi && modalidadesApi.length > 0) {
                    modalidadesApi.sort((a, b) => a.modalidadeNome.localeCompare(b.modalidadeNome)); 
                    modalidadesApi.forEach(mod => {
                        const div = document.createElement('div');
                        div.classList.add('form-check');
                        div.innerHTML = `
                            <input class="form-check-input filter-modalidade" type="checkbox" value="${mod.modalidadeId}" id="mod-${mod.modalidadeId}">
                            <label class="form-check-label" for="mod-${mod.modalidadeId}">${mod.modalidadeNome}</label>
                        `;
                        modalidadesContainer.appendChild(div);

                        // Adiciona o listener para atualizar o contador a cada clique
                        div.querySelector('.filter-modalidade').addEventListener('change', updateModalidadeSelectedCount);
                    });
                } else {
                    modalidadesContainer.innerHTML = '<small class="text-danger">Nenhuma modalidade encontrada.</small>';
                }
            } catch (error) {
                console.error("Erro ao carregar modalidades:", error);
                modalidadesContainer.innerHTML = `<small class="text-danger">Erro ao carregar modalidades: ${error.message}</small>`;
            }
            // Atualiza a contagem inicial (deve ser 0)
            updateModalidadeSelectedCount();
        }

        // --- FUNÇÃO DE EXECUSÃO - STATUS ---
        async function popularStatus() { 
            if (!statusContainer) return;
            statusContainer.innerHTML = '<small class="text-muted">Carregando status...</small>';
            try {
                const response = await fetch('/api/frontend/referencias/statusradar');
                if (!response.ok) throw new Error(`Erro ${response.status} ao buscar status radar.`);
                const statusRadarApi = await response.json();

                statusContainer.innerHTML = ''; 
                if (statusRadarApi && statusRadarApi.length > 0) {
                    const defaultStatusValue = "A Receber/Recebendo Proposta"; 
                    
                    statusRadarApi.sort((a,b) => a.nome.localeCompare(b.nome)); 

                    statusRadarApi.forEach(st => {
                        const div = document.createElement('div');
                        div.classList.add('form-check');
                        const isChecked = st.id === defaultStatusValue; 
                        // Gerar um ID de elemento mais seguro
                        const elementId = `status-radar-${st.id.toLowerCase().replace(/[^a-z0-9-_]/g, '') || 'unk'}`;
                        div.innerHTML = `
                            <input class="form-check-input filter-status" type="radio" name="statusLicitacao" 
                                value="${st.id}" id="${elementId}" ${isChecked ? 'checked' : ''}>
                            <label class="form-check-label" for="${elementId}">${st.nome}</label>
                        `;
                        statusContainer.appendChild(div);
                        // Não precisamos mais de currentFilters.statusRadar aqui
                    });

                    const divTodos = document.createElement('div');
                    divTodos.classList.add('form-check');
                    const idTodos = "status-radar-todos";
                    divTodos.innerHTML = `
                        <input class="form-check-input filter-status" type="radio" name="statusLicitacao" value="" id="${idTodos}">
                        <label class="form-check-label" for="${idTodos}">Todos</label>
                    `;
                    statusContainer.appendChild(divTodos);

                    document.querySelectorAll('.filter-status').forEach(radio => {
                        radio.addEventListener('change', handleStatusChange); 
                    });

                } else {
                    statusContainer.innerHTML = '<small class="text-danger">Nenhum status encontrado.</small>';
                }
            } catch (error) {
                console.error("Erro ao carregar status radar:", error);
                statusContainer.innerHTML = `<small class="text-danger">Erro ao carregar status: ${error.message}</small>`;
            }
        }

        // --- FUNÇÃO DE EXECUSÃO - ESTADOS ---
        function popularUFs() { 
            if (!ufsContainer) return;
            ufsContainer.innerHTML = ''; 
            ufsLista.forEach(uf => {
                const div = document.createElement('div');
                div.classList.add('form-check');
                // Gerar um ID de elemento mais seguro
                const elementId = `uf-${uf.sigla.toLowerCase().replace(/[^a-z0-9-_]/g, '')}`;
                div.innerHTML = `
                    <input class="form-check-input filter-uf" type="checkbox" value="${uf.sigla}" id="${elementId}">
                    <label class="form-check-label" for="${elementId}">${uf.nome} (${uf.sigla})</label>
                `;
                ufsContainer.appendChild(div);
            });
            document.querySelectorAll('.filter-uf').forEach(checkbox => {
                checkbox.addEventListener('change', handleUFChange);
            });

            updateUFSelectedCount(); 
        }

        // --- FUNÇÃO DE EXECUSÃO - ESTADOS E MUNICIPIOS ---
        async function handleUFChange() {       
            updateUFSelectedCount(); // Mantém a chamada para o contador de UF

            const ufsSelecionadas = Array.from(document.querySelectorAll('.filter-uf:checked')).map(cb => cb.value);
            const municipiosContainer = document.getElementById('municipiosContainerDropdown');
            const municipiosDropdownButton = document.getElementById('dropdownMunicipiosButton'); 
            const municipiosHelp = document.getElementById('municipiosHelp');

            if (!municipiosContainer || !municipiosDropdownButton) return;

            // Limpa e desabilita o botão enquanto carrega ou se não há UFs
            municipiosDropdownButton.disabled = true;
            municipiosContainer.innerHTML = '';
            
            if (ufsSelecionadas.length === 0) {
                municipiosContainer.innerHTML = '<small class="text-muted p-2">Selecione uma UF primeiro</small>';
                if (municipiosHelp) municipiosHelp.textContent = "Selecione uma ou mais UFs para listar os municípios.";
                updateMunicipioSelectedCount(); // Reseta a contagem para 0 
                return; //Sai da função
            }

            municipiosDropdownButton.disabled = false;

            municipiosContainer.innerHTML = '<div class="p-2 text-muted">Carregando municípios...</div>';
            if (municipiosHelp) municipiosHelp.textContent = `Carregando municípios para ${ufsSelecionadas.join(', ')}...`;

            let todosMunicipios = [];
            let ufsComErro = [];

            for (const uf of ufsSelecionadas) {
                try {
                    const response = await fetch(`/api/ibge/municipios/${uf}`);
                    const data = await response.json(); // Consome o stream uma vez e armazena
                    console.log(`Resposta da API para UF ${uf}:`, data); // Usa a variável data
                    if (!response.ok) {
                        ufsComErro.push(uf);
                        continue;
                    }
                    data.forEach(mun => {
                        todosMunicipios.push({
                            id: `${uf}-${mun.id}`,
                            nome: `${mun.nome} (${uf})`,
                            nomeOriginal: mun.nome,
                            uf: uf
                        });
                    });
                } catch (error) {
                    console.error(`Erro crítico ao carregar municípios para ${uf}:`, error);
                    ufsComErro.push(uf);
                }
            }

            todosMunicipios.sort((a, b) => a.nome.localeCompare(b.nome));
            municipiosContainer.innerHTML = ''; // Limpa "Carregando..."

            if (todosMunicipios.length > 0) {
                todosMunicipios.forEach(mun => {
                    const div = document.createElement('div');
                    div.classList.add('form-check', 'ms-2');
                    const munId = `mun-${mun.id.replace(/[^a-zA-Z0-9]/g, '')}`;
                    div.innerHTML = `
                        <input class="form-check-input filter-municipio" type="checkbox" value="${mun.nomeOriginal}" id="${munId}">
                        <label class="form-check-label" for="${munId}">${mun.nome}</label>
                    `;
                    municipiosContainer.appendChild(div);
                });
                
                // Adiciona listeners aos novos checkboxes de município
                document.querySelectorAll('.filter-municipio').forEach(cb => {
                    cb.addEventListener('change', updateMunicipioSelectedCount);
                });
                            
                if(municipiosHelp) municipiosHelp.textContent = `Municípios de ${ufsSelecionadas.join(', ')}. Selecione um ou mais.`;
            } else {
                municipiosContainer.innerHTML = '<small class="text-danger p-2">Nenhum município encontrado.</small>';
                if (municipiosHelp) municipiosHelp.textContent = "Nenhum município encontrado para as UFs selecionadas.";
            }

            if (ufsComErro.length > 0 && municipiosHelp) {
                municipiosHelp.textContent += ` (Erro ao carregar de: ${ufsComErro.join(', ')})`;
            }
            
            updateMunicipioSelectedCount(); // Atualiza a contagem (será 0 neste ponto)
        }

        
        function handleStatusChange(event) {
            const selectedStatus = event.target.value;
            // Regra: Se "Todos" (ID vazio) ou "Encerradas" (ID 2) for selecionado, palavra-chave é obrigatória
            if (selectedStatus === "" || selectedStatus === "Encerrada") {
                // Não vamos bloquear aqui, mas podemos avisar ou validar na hora de buscar
            }
        }
        
        
        // --- FUNÇÕES DE BUSCA E RENDERIZAÇÃO DE LICITAÇÕES ---
        async function buscarLicitacoes(page = 1) {
            
            // Função de carregamento de aplicar filtros
            const btnAplicar = document.getElementById('btnBuscarLicitacoes');
            if (btnAplicar) {
                btnAplicar.disabled = true; // Desabilita o botão
                btnAplicar.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Buscando...`;
            }

            salvarFiltrosAtuais(); // SALVA OS FILTROS ANTES DE EXECUTAR A BUSCA
            
            currentPage = page;
            
            const params = new URLSearchParams();
            
            if(loadingOverlay) loadingOverlay.classList.remove('d-none');

            // Coleta palavraChave uma vez no início da função
            if (palavrasChaveInclusao.length > 0) {
                palavrasChaveInclusao.forEach(p => params.append('palavraChave', p));
            }
            if (palavrasChaveExclusao.length > 0) {
                palavrasChaveExclusao.forEach(p => params.append('excluirPalavra', p));
            }
                    
            document.querySelectorAll('.filter-uf:checked').forEach(cb => params.append('uf', cb.value));
            document.querySelectorAll('.filter-modalidade:checked').forEach(cb => params.append('modalidadeId', cb.value));
            
            const statusSelecionadoRadio = document.querySelector('.filter-status:checked');
            let statusRadarValor = '';
            if (statusSelecionadoRadio) {
                statusRadarValor = statusSelecionadoRadio.value;
            }

            if (statusRadarValor) {
                params.append('statusRadar', statusRadarValor);
            }

            // Validação de palavra-chave para statusRadar "Todos" (valor vazio) ou "Encerradas"
            if(statusWarning) statusWarning.classList.add('d-none');
            
            if ((statusRadarValor === "" || statusRadarValor === "Encerrada") && palavrasChaveInclusao.length === 0) {
                if(statusWarning) {
                    statusWarning.textContent = 'Palavra-chave de busca é obrigatória para este status.';
                    statusWarning.classList.remove('d-none');
                }
                if(licitacoesTableBody) licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Forneça uma palavra-chave para buscar com o status selecionado.</td></tr>`;
                if(totalRegistrosInfo) totalRegistrosInfo.textContent = '0';
                if(exibicaoInfo) exibicaoInfo.textContent = '';
                if(paginationControls) paginationControls.innerHTML = '';
                if (loadingOverlay) loadingOverlay.classList.add('d-none'); // Esconde o loading
                return; 
            }
            
            // Coleta de Municípios
            const municipiosSelecionados = Array.from(document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked')).map(cb => cb.value);
            if (municipiosSelecionados.length > 0) {
                municipiosSelecionados.forEach(mun => params.append('municipioNome', mun));
            }

            // Datas de Publicação
            const dataInicio = dataPubInicioInput.value;
            if (dataInicio) params.append('dataPubInicio', dataInicio);
            const dataFim = dataPubFimInput.value;
            if (dataFim) params.append('dataPubFim', dataFim);

            // >>> ADICIONAR COLETA DAS DATAS DE ATUALIZAÇÃO <<<
            if(dataAtualizacaoInicioInput && dataAtualizacaoFimInput) { // Verificar se os elementos existem
                const dataAtualInicio = dataAtualizacaoInicioInput.value;
                if (dataAtualInicio) params.append('dataAtualizacaoInicio', dataAtualInicio);
                const dataAtualFim = dataAtualizacaoFimInput.value;
                if (dataAtualFim) params.append('dataAtualizacaoFim', dataAtualFim);
            }


            const valMin = valorMinInput.value;
            if (valMin) params.append('valorMin', valMin);
            const valMax = valorMaxInput.value;
            if (valMax) params.append('valorMax', valMax);

            params.append('pagina', currentPage);
            params.append('porPagina', itensPorPaginaSelect.value);

            const [orderByField, orderDirValue] = ordenarPorSelect.value.split('_');
            params.append('orderBy', orderByField);
            params.append('orderDir', orderDirValue.toUpperCase()); 


            licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center">Buscando licitações... <div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>`;
            totalRegistrosInfo.textContent = '-';
            exibicaoInfo.textContent = '';

            try {
                const response = await fetch(`/api/frontend/licitacoes?${params.toString()}`);
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({})); // Tenta pegar o corpo do erro se for JSON
                    
                    console.error("Erro da API:", response.status, errorData); // Log detalhado do erro

                    let errorMessage = `Erro ${response.status}`;
                    if (response.status === 400 && errorData.erro) {
                        // Erro de validação específico do backend (ex: orderBy inválido)
                        errorMessage = `Erro de validação: ${errorData.erro}${errorData.detalhes ? ' ('+errorData.detalhes+')' : ''}`;
                    } else if (response.status === 404) {
                        // Embora 404 seja mais comum para detalhes de uma licitação específica,
                        // pode acontecer se o endpoint /licitacoes em si não for encontrado.
                        errorMessage = "Recurso não encontrado no servidor (404).";
                    } else if (errorData.erro_backend) {
                        // Erro genérico do backend que foi repassado pelo nosso /api/frontend/licitacoes
                        errorMessage = `Erro no servidor: ${errorData.erro_backend}`;
                    } else if (errorData.erro_frontend) {
                        // Erro no nosso backend Flask que faz o proxy (ex: não conseguiu conectar ao backend RADAR)
                        errorMessage = `Erro no servidor do frontend: ${errorData.erro_frontend}`;
                    } else if (response.statusText) {
                        // Usa o texto de status HTTP se não houver JSON
                        errorMessage = `Erro ${response.status}: ${response.statusText}`;
                    }
                    throw new Error(errorMessage); // Lança o erro para ser pego pelo catch
                }
                            
                const data = await response.json(); 

                renderLicitacoesTable(data.licitacoes);
                renderPagination(data);
                atualizarExibicaoFiltrosAtivos();
                                    
                totalRegistrosInfo.textContent = data.total_registros || '0';
                if (data.licitacoes && data.licitacoes.length > 0) {
                    const inicio = (data.pagina_atual - 1) * parseInt(data.por_pagina, 10) + 1; // Garantir que por_pagina é número
                    const fim = inicio + data.licitacoes.length - 1;
                    exibicaoInfo.textContent = `Exibindo ${inicio}-${fim} de ${data.total_registros}`;
                } else {
                    exibicaoInfo.textContent = "Nenhum resultado";
                    if (!data.total_registros || data.total_registros === 0) {
                        licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center">Nenhuma licitação encontrada para os filtros aplicados.</td></tr>`;
                    }
                }

            } catch (error) {
                console.error("Erro ao buscar licitações:", error);
                licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Erro ao buscar licitações: ${error.message}</td></tr>`;
                totalRegistrosInfo.textContent = '0';
                exibicaoInfo.textContent = 'Erro';
                paginationControls.innerHTML = '';
            }finally {
                // Ao final da busca (sucesso ou erro), restaura o botão (carregamento filtros)
                if (btnAplicar) {
                    btnAplicar.disabled = false;
                    btnAplicar.innerHTML = `<i class="bi bi-search"></i> Aplicar Filtros`;
                }
                // Oculta o overlay de carregamento no final, seja sucesso ou erro
                if (loadingOverlay) loadingOverlay.classList.add('d-none');
            }
        }

        function renderLicitacoesTable(licitacoes) {
            if(!licitacoesTableBody) return; //Proteção - Adicionado quando adicionamos a função favoritos
            licitacoesTableBody.innerHTML = ''; 
            if (!licitacoes || licitacoes.length === 0) {
                licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center">Nenhuma licitação encontrada para os filtros aplicados.</td></tr>`;
                return;
            }

            licitacoes.forEach(lic => {
                const tr = document.createElement('tr');
                const statusBadgeClass = getStatusBadgeClass(lic.situacaoReal); 
                const objetoCompleto = lic.objetoCompra || 'N/I';
                const objetoCurto = objetoCompleto.substring(0, 100);
                let objetoHtml = objetoCompleto; // Por padrão, mostra completo
                if (objetoCompleto.length > 100) {
                    objetoHtml = `<span class="objeto-curto">${objetoCurto}... <a href="#" class="ver-mais-objeto" data-objeto-completo="${lic.id}">Ver mais</a></span>
                                <span class="objeto-completo d-none">${objetoCompleto} <a href="#" class="ver-menos-objeto" data-objeto-completo="${lic.id}">Ver menos</a></span>`;
                }

                // --- LÓGICA PARA VALOR TOTAL ESTIMADO ---
                let valorEstimadoDisplay = 'N/I'; // Default se não for nem sigiloso nem um número
                if (lic.valorTotalEstimado === null) {
                    valorEstimadoDisplay = '<span class="text-info fst-italic">Sigiloso</span>';
                } else if (lic.valorTotalEstimado !== undefined && lic.valorTotalEstimado !== '' && !isNaN(parseFloat(lic.valorTotalEstimado))) {
                    // Verifica se não é undefined, não é string vazia, e é um número
                    valorEstimadoDisplay = `R$ ${parseFloat(lic.valorTotalEstimado).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                } else if (typeof lic.valorTotalEstimado === 'string' && lic.valorTotalEstimado.trim() === '') {                    
                    // Se string vazia será "Sigiloso":
                    valorEstimadoDisplay = '<span class="text-info fst-italic">Sigiloso</span>';
                } else if (!lic.valorTotalEstimado && lic.valorTotalEstimado !== 0) { // Cobre null, undefined, ""
                    // Se quiser que string vazia ou valor inválido seja Sigiloso também:
                    valorEstimadoDisplay = '<span class="text-info fst-italic">Sigiloso</span>';
                }

                // FAVORITO 
                const ehFavorito = isFavorito(lic.numeroControlePNCP); // Verifica se é FAVORITO
                const btnFavoritoHtml = `
                    <button class="btn btn-sm ${ehFavorito ? 'btn-warning active' : 'btn-outline-warning'} btn-favoritar" 
                            title="${ehFavorito ? 'Desfavoritar' : 'Favoritar'}" data-pncp-id="${lic.numeroControlePNCP}">
                        <i class="bi ${ehFavorito ? 'bi-star-fill' : 'bi-star'}"></i>
                    </button>
                `;
                
                // A ORDEM DA LINHA DENTRO DA TABELA.
                tr.innerHTML = `
                    <td data-label="Município/UF" class="align-middle">${lic.unidadeOrgaoMunicipioNome || 'N/I'}/${lic.unidadeOrgaoUfSigla || 'N/I'}</td>
                    <td data-label="Objeto"><div class="objeto-container" data-lic-id="${lic.id}">${objetoHtml}</div></td>
                    <td data-label="Órgão" class="align-middle">${lic.orgaoEntidadeRazaoSocial || 'N/I'}</td>
                    <td data-label="Status" class="align-middle"><span class="badge ${statusBadgeClass}">${lic.situacaoReal || lic.situacaoCompraNome || 'N/I'}</span></td>
                    <td data-label="Valor (R$)" class="align-middle">${valorEstimadoDisplay}</td>
                    <td data-label="Modalidade" class="align-middle">${lic.modalidadeNome || 'N/I'}</td>
                    <td data-label="Atualização" class="align-middle">${lic.dataAtualizacao ? new Date(lic.dataAtualizacao + 'T00:00:00Z').toLocaleDateString('pt-BR') : 'N/I'}</td>
                    <td data-label="Ações" class="text-nowrap align-middle"> <!-- Botões -->
                        <!-- DETALHES -->
                        <button class="btn btn-sm btn-info btn-detalhes" title="Mais Detalhes" data-pncp-id="${lic.numeroControlePNCP}"><i class="bi bi-eye-fill"></i></button>                                                
                        <!-- FAVORITO -->
                        ${btnFavoritoHtml}
                        <!-- ACESSAR PNCP -->
                       <!-- <a href="${lic.link_portal_pncp || '#'}" class="btn btn-sm btn-outline-primary" title="Acessar PNCP" target="_blank" ${!lic.link_portal_pncp ? 'disabled aria-disabled="true"' : ''}><i class="bi bi-box-arrow-up-right"></i></a> -->
                    </td>
                `;                
                licitacoesTableBody.appendChild(tr);
            });
            
            document.querySelectorAll('.ver-mais-objeto').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const container = this.closest('.objeto-container');
                    container.querySelector('.objeto-curto').classList.add('d-none');
                    container.querySelector('.objeto-completo').classList.remove('d-none');
                });
            });
            document.querySelectorAll('.ver-menos-objeto').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const container = this.closest('.objeto-container');
                    container.querySelector('.objeto-completo').classList.add('d-none');
                    container.querySelector('.objeto-curto').classList.remove('d-none');
                });
            });

            document.querySelectorAll('.btn-detalhes').forEach(button => {
                button.addEventListener('click', handleDetalhesClick);
            });
        } 

        // Função auxiliar para definir a classe do badge de status
        function getStatusBadgeClass(situacaoReal) {
            if (!situacaoReal) return 'bg-secondary';
            const statusLower = situacaoReal.toLowerCase();
            if (statusLower.includes('recebendo') || statusLower.includes('aberta') || statusLower.includes('divulgada')) {
                return 'bg-success'; // Verde para ativas
            } else if (statusLower.includes('encerrada') || statusLower.includes('homologada') || statusLower.includes('concluída')) {
                return 'bg-primary'; // Azul para encerradas/concluídas
            } else if (statusLower.includes('julgamento')) {
                return 'bg-warning text-dark'; // Amarelo para em julgamento
            } else if (statusLower.includes('suspensa')) {
                return 'bg-info text-dark'; // Ciano para suspensas
            } else if (statusLower.includes('anulada') || statusLower.includes('revogada') || statusLower.includes('cancelada')) {
                return 'bg-danger'; // Vermelho para anuladas/canceladas
            }
            return 'bg-secondary'; // Padrão
        }


        function renderPagination(data) {
            paginationControls.innerHTML = '';
            if (!data || !data.licitacoes || data.total_paginas == null || data.total_paginas <= 1) { // Adicionada checagem para data.licitacoes e data.total_paginas
                console.log("renderPagination: Dados insuficientes ou não precisa de paginação.", data);
                return;
            }

            const pagina_atual = parseInt(data.pagina_atual, 10); // Garantir que é número
            const total_paginas = parseInt(data.total_paginas, 10); // Garantir que é número

            // Validação adicional
            if (isNaN(pagina_atual) || isNaN(total_paginas)) {
                console.error("renderPagination: pagina_atual ou total_paginas não são números válidos.", data);
                return;
            }

            // Botão Anterior
            const prevLi = document.createElement('li');
            prevLi.classList.add('page-item');
            if (pagina_atual === 1) {
                prevLi.classList.add('disabled');
            }
            prevLi.innerHTML = `<a class="page-link" href="#" data-page="${pagina_atual - 1}">Anterior</a>`;
            paginationControls.appendChild(prevLi);

            // Números das Páginas (lógica simples para mostrar algumas páginas)
            let startPage = Math.max(1, pagina_atual - 2);
            let endPage = Math.min(total_paginas, pagina_atual + 2);

            // Ajustar startPage e endPage para sempre mostrar um número fixo de links se possível
            const maxPageLinks = 5; // Número de links de página que queremos mostrar (ex: 1 ... 3 4 5 ... 10)
            if (endPage - startPage + 1 < maxPageLinks) {
                if (pagina_atual < maxPageLinks / 2) { // Perto do início
                    endPage = Math.min(total_paginas, startPage + maxPageLinks - 1);
                } else if (pagina_atual > total_paginas - maxPageLinks / 2) { // Perto do fim
                    startPage = Math.max(1, endPage - maxPageLinks + 1);
                } else { // No meio
                    const diff = Math.floor((maxPageLinks - (endPage - startPage + 1)) / 2);
                    startPage = Math.max(1, startPage - diff);
                    endPage = Math.min(total_paginas, endPage + (maxPageLinks - (endPage - startPage + 1) - diff) ) ; // O que sobrou
                }
                // Reajuste final se estourar os limites
                if (endPage - startPage + 1 > maxPageLinks) {
                    if (startPage === 1) endPage = startPage + maxPageLinks - 1;
                    else startPage = endPage - maxPageLinks + 1;
                }
            }

            if (startPage > 1) {
                const firstLi = document.createElement('li');
                firstLi.classList.add('page-item');
                firstLi.innerHTML = `<a class="page-link" href="#" data-page="1">1</a>`;
                paginationControls.appendChild(firstLi);
                if (startPage > 2) {
                    const dotsLi = document.createElement('li');
                    dotsLi.classList.add('page-item', 'disabled');
                    dotsLi.innerHTML = `<span class="page-link">...</span>`;
                    paginationControls.appendChild(dotsLi);
                }
            }

            for (let i = startPage; i <= endPage; i++) {
                const pageLi = document.createElement('li');
                pageLi.classList.add('page-item');
                if (i === pagina_atual) {
                    pageLi.classList.add('active');
                }
                pageLi.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
                paginationControls.appendChild(pageLi);
            }
            
            if (endPage < total_paginas) {
                if (endPage < total_paginas - 1) {
                    const dotsLi = document.createElement('li');
                    dotsLi.classList.add('page-item', 'disabled');
                    dotsLi.innerHTML = `<span class="page-link">...</span>`;
                    paginationControls.appendChild(dotsLi);
                }
                const lastLi = document.createElement('li');
                lastLi.classList.add('page-item');
                lastLi.innerHTML = `<a class="page-link" href="#" data-page="${total_paginas}">${total_paginas}</a>`;
                paginationControls.appendChild(lastLi);
            }

            // Botão Próximo
            const nextLi = document.createElement('li');
            nextLi.classList.add('page-item');
            if (pagina_atual === total_paginas) {
                nextLi.classList.add('disabled');
            }
            nextLi.innerHTML = `<a class="page-link" href="#" data-page="${pagina_atual + 1}">Próxima</a>`;
            paginationControls.appendChild(nextLi);

            // Adicionar event listeners aos links de paginação
            paginationControls.querySelectorAll('.page-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    // Verifica se o elemento pai (li) está desabilitado ou ativo
                    const parentLi = this.closest('.page-item');
                    if (parentLi && (parentLi.classList.contains('disabled') || parentLi.classList.contains('active'))) {
                        return;
                    }
                    const page = parseInt(this.dataset.page);
                    if (page && !isNaN(page)) { // Verifica se page é um número válido
                        buscarLicitacoes(page);
                    }
                });
            });
        }
        
        // --- FUNÇÃO DE LIMPAR FILTROS ---
        function limparFiltros() {        
            if(palavraChaveInclusaoInputField) palavraChaveInclusaoInputField.value = '';
            if(palavraChaveExclusaoInputField) palavraChaveExclusaoInputField.value = '';

            palavrasChaveInclusao = []; // Limpa o array
            palavrasChaveExclusao = []; // Limpa o array
            renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao'); // Re-renderiza (vazio)
            renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao'); // Re-renderiza (vazio)

            //document.querySelectorAll('.filter-uf:checked').forEach(cb => cb.checked = false);
            //handleUFChange(); 
            document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked').forEach(cb => cb.checked = false);
            // Atualizar contagem e municípios após desmarcar UFs
            if (typeof updateUFSelectedCount === "function") updateUFSelectedCount(); // Atualiza badge de UF SE ESSE TIVER PROBLEMA, UTILIZAR O DE CIMA
            handleUFChange(); // Isso deve limpar e desabilitar os municípios e atualizar o badge de municípios
            
            //document.querySelectorAll('.filter-modalidade:checked').forEach(cb => cb.checked = false);           
            //updateModalidadeSelectedCount(); // >>> Resetar o contador de modalidades <<<
            document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked').forEach(cb => cb.checked = false);
            if (typeof updateModalidadeSelectedCount === "function") updateModalidadeSelectedCount(); // Atualiza badge de modalidade (criar essa função)

            

            // Resetar status para o default
            const radiosStatus = document.querySelectorAll('.filter-status');
            let defaultStatusRadio = null;
            const defaultStatusValue = "A Receber/Recebendo Proposta"; // Mesmo default usado em popularStatus
            radiosStatus.forEach(radio => {
                if (radio.value === defaultStatusValue) {
                    defaultStatusRadio = radio;
                }
                // Desmarcar todos primeiro (embora radio buttons se auto-desmarquem, é uma garantia)
                // radio.checked = false; // Não precisa, pois ao marcar um, os outros desmarcam
            });

            if (defaultStatusRadio) {
                defaultStatusRadio.checked = true;
            } else if (radiosStatus.length > 0) {
                // Se o default específico não for encontrado, marcar o primeiro que não seja "Todos"
                const primeiroValido = Array.from(radiosStatus).find(r => r.value !== "");
                if (primeiroValido) primeiroValido.checked = true;
                else if(radiosStatus.length > 0) radiosStatus[0].checked = true; // Como último recurso, marca o primeiro
            }
            statusWarning.classList.add('d-none');

            if(dataPubInicioInput) dataPubInicioInput.value = '';
            if(dataPubFimInput) dataPubFimInput.value = '';
            if(dataAtualizacaoInicioInput) dataAtualizacaoInicioInput.value = '';
            if(dataAtualizacaoFimInput) dataAtualizacaoFimInput.value = '';
            if(valorMinInput) valorMinInput.value = '';
            if(valorMaxInput) valorMaxInput.value = '';
            
            const advancedCollapse = document.getElementById('collapseAdvanced');
            if (advancedCollapse && advancedCollapse.classList.contains('show')) {
                new bootstrap.Collapse(advancedCollapse).hide();
            }
                    
            console.log("Filtros limpos, buscando licitações...");        
            atualizarExibicaoFiltrosAtivos();             
            buscarLicitacoes(1); 
        }


        // --- HANDLERS (MANIPULADORES) DE EVENTOS GLOBAIS ---
        if (btnBuscarLicitacoes) {
            btnBuscarLicitacoes.addEventListener('click', () => buscarLicitacoes(1));
        }
        if (btnLimparFiltros) {
            btnLimparFiltros.addEventListener('click', limparFiltros);
        }
        if (ordenarPorSelect) {
            ordenarPorSelect.addEventListener('change', () => buscarLicitacoes(currentPage)); // Rebusca a página atual com nova ordenação
        }
        if (itensPorPaginaSelect) {
            itensPorPaginaSelect.addEventListener('change', () => buscarLicitacoes(1)); // Volta para a primeira página com nova quantidade
        }

        // Placeholder para função de detalhes
        const detailsPanelBody  = document.getElementById('detailsPanel');
        const detailsPanel = detailsPanelBody  ? new bootstrap.Offcanvas(detailsPanelBody ) : null;
        const detailsPanelContent = document.getElementById('detailsPanelContent');
        // ... (outros elementos do painel de detalhes)

        async function handleDetalhesClick(event) {
            const button = event.currentTarget;
            const pncpId = button.dataset.pncpId;
            if (!pncpId || !detailsPanel) return;

            detailsPanelContent.innerHTML = '<p class="text-center">Carregando detalhes...</p>';
            // Limpar outras partes do painel (itens, arquivos)
            document.getElementById('detailsPanelItensTableBody').innerHTML = '';
            document.getElementById('detailsPanelItensPagination').innerHTML = '';
            document.getElementById('detailsPanelArquivosList').innerHTML = '';

            detailsPanel.show();

            try {
                const response = await fetch(`/api/frontend/licitacao/${encodeURIComponent(pncpId)}`);
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({erro_frontend: "Erro desconhecido na resposta da API de detalhes."}));
                    throw new Error(errorData.erro_backend || errorData.erro_frontend || `Erro ${response.status}`);
                }
                const data = await response.json();
                //(DEBUG)
                console.log("Dados DETALHES para PNCP ID:", pncpId, JSON.parse(JSON.stringify(data))); // Log profundo dos dados
                renderDetailsPanelContent(data); // Implementar esta função

            } catch (error) {
                console.error("Erro ao buscar detalhes da licitação:", error);
                detailsPanelContent.innerHTML = `<p class="text-center text-danger">Erro ao carregar detalhes: ${error.message}</p>`;
            }
        }

        // --- LÓGICA PARA SELECIONAR LINHA DA TABELA ---
        if (licitacoesTableBody) {
            licitacoesTableBody.addEventListener('click', function(event) {
                // Encontra o elemento <tr> que foi clicado
                const trClicada = event.target.closest('tr');
        
                if (!trClicada) return;
                
                // Ignora o clique se for em um botão ou link
                if (event.target.closest('a, button')) {
                    return;
                }
        
                // Encontra a linha já selecionada e remove a classe
                const linhaJaSelecionada = licitacoesTableBody.querySelector('.linha-selecionada');
                if (linhaJaSelecionada) {
                    linhaJaSelecionada.classList.remove('linha-selecionada');
                }
        
                // Adiciona a classe à nova linha clicada
                trClicada.classList.add('linha-selecionada');
            });
        }

        // FUNÇÃO DO PAINEL DETALHES
        function renderDetailsPanelContent(data) {
            if(!detailsPanelElement) return; // Proteção - Adicionado qnd adicionou função favorito

            if (!data || !data.licitacao) {
                detailsPanelContent.innerHTML = '<p class="text-center text-danger">Dados da licitação não encontrados.</p>';
                return;
            }
            const lic = data.licitacao;
            const detailsPanelSubtitle = document.getElementById('detailsPanelSubtitle'); // Subtítulo (Edital)
            const detailsPanelLabel = document.getElementById('detailsPanelLabel');


            // FAVORITO dentro dos detalhes
            const favoriteIconContainer = document.getElementById('detailsPanelFavoriteIconContainer');
            if (favoriteIconContainer) {
                favoriteIconContainer.innerHTML = ''; // Limpa anterior
                if (lic && lic.numeroControlePNCP) {
                    const ehFavorito = isFavorito(lic.numeroControlePNCP);
                    const favButton = document.createElement('button');
                    
                    favButton.id = 'detailsPanelFavoriteBtn'; 
                    favButton.classList.add('btn', 'btn-link', 'text-warning', 'p-0', 'btn-favoritar'); 
                    favButton.style.fontSize = '1.5rem'; 
                    
                    favButton.dataset.pncpId = lic.numeroControlePNCP;
                    favButton.title = ehFavorito ? 'Desfavoritar' : 'Favoritar'; // O title é importante para acessibilidade e tooltip
                    
                    // APENAS O ÍCONE AQUI
                    favButton.innerHTML = `<i class="bi ${ehFavorito ? 'bi-star-fill' : 'bi-star'}"></i>`;
                    
                    favoriteIconContainer.appendChild(favButton);
                }
            }            
            //-----------------------------------------------------------------------------------


            let tituloPrincipal = `Detalhes: ${lic.numeroControlePNCP || 'N/I'}`; // Fallback
            if (lic.unidadeOrgaoNome) {
                tituloPrincipal = lic.unidadeOrgaoNome;
            } else if (lic.processo) { 
                tituloPrincipal = `Processo: ${lic.processo}`;
            }
            
            if (detailsPanelLabel) {
                detailsPanelLabel.textContent = tituloPrincipal;
            }

            if (detailsPanelSubtitle) { // Se o elemento para subtítulo existir
                if (lic.numeroCompra && lic.anoCompra) {
                    detailsPanelSubtitle.textContent = `Edital: ${lic.numeroCompra}/${lic.anoCompra}`;
                    detailsPanelSubtitle.style.display = 'block'; // Garante que está visível
                } else if (lic.numeroCompra) {
                    detailsPanelSubtitle.textContent = `Número da Compra: ${lic.numeroCompra}`;
                    detailsPanelSubtitle.style.display = 'block';
                } else {
                    detailsPanelSubtitle.textContent = '';
                    detailsPanelSubtitle.style.display = 'none'; // Oculta se não houver edital
                }
            }
            
            const formatDate = (dateString) => {
                if (!dateString) return 'N/I';
                // Adiciona 'Z' para garantir que seja tratada como UTC se não tiver fuso,
                // evitando problemas de off-by-one day dependendo do fuso do cliente.
                // Se a data já vier com fuso do backend, pode não ser necessário o 'Z'.
                return new Date(dateString + 'T00:00:00Z').toLocaleDateString('pt-BR');
            };

            let numeroEditalHtml = '';
            if (lic.numeroCompra && lic.anoCompra) {
                numeroEditalHtml = `<p class="mb-1"><strong>Edital:</strong> ${lic.numeroCompra}/${lic.anoCompra}</small></p>`;
            } else if (lic.numeroCompra) {
                numeroEditalHtml = `<p class="mb-0"><strong>Número Compra:</strong> ${lic.numeroCompra}</small></p>`;
            }

            let htmlContent = ` 
                <p><strong>Número PNCP:</strong> ${lic.numeroControlePNCP || 'N/I'}</p>
                ${lic.processo ? `<p><strong>Número do Processo:</strong> ${lic.processo}</p>` : ''}     
                <p><strong>Objeto:</strong></p>
                <div class="mb-2" style="white-space: pre-wrap; background-color: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 150px; overflow-y: auto;">${lic.objetoCompra || 'N/I'}</div>
                <p><strong>Órgão:</strong> ${lic.orgaoEntidadeRazaoSocial || 'N/I'}</p>
                <p><strong>Unidade Compradora:</strong> ${lic.unidadeOrgaoNome || 'N/I'}</p>
                <p><strong>Município/UF:</strong> ${lic.unidadeOrgaoMunicipioNome || 'N/I'}/${lic.unidadeOrgaoUfSigla || 'N/I'}</p>
                <p><strong>Modalidade:</strong> ${lic.modalidadeNome || 'N/I'}</p>                    
                ${lic.amparoLegalNome ? `<p><strong>Amparo Legal:</strong> ${lic.amparoLegalNome}</p>` : ''}
                ${
                    lic.valorTotalHomologado
                        ? `<p><strong>Valor Total Homologado:</strong> R$ ${parseFloat(lic.valorTotalHomologado).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>`
                        : ''
                }
                ${lic.modoDisputaNome ? `<p><strong>Modo de Disputa:</strong> ${lic.modoDisputaNome}</p>` : '<p class="text-muted small"><small><strong>Modo de Disputa:</strong> (Não informado)</small></p>'}
                ${lic.tipolnstrumentoConvocatorioNome ? `<p><strong>Tipo:</strong> ${lic.tipolnstrumentoConvocatorioNome}</p>` : '<p class="text-muted small"><small><strong>Tipo:</strong> (Não informado)</small></p>'}
                <p><strong>Situação Atual:</strong> <span class="badge ${getStatusBadgeClass(lic.situacaoReal)}">${lic.situacaoReal || 'N/I'}</span></p>                
                <p><strong>Data Publicação PNCP:</strong> ${formatDate(lic.dataPublicacaoPncp)}</p>                
                <div class="my-2 p-2 border-start border-primary border-3 bg-light-subtle rounded-end">
                    <p class="mb-1"><strong>Início Recebimento Propostas:</strong> ${formatDateTime(lic.dataAberturaProposta)} (Horário de Brasília)</p>
                    <p class="mb-0"><strong>Fim Recebimento Propostas:</strong> ${formatDateTime(lic.dataEncerramentoProposta)} (Horário de Brasília)</p>
                </div>
                <p><strong>Última Atualização:</strong> ${formatDate(lic.dataAtualizacao)}</p>            
                <p><strong>Valor Total Estimado:</strong> ${lic.valorTotalEstimado === null ? '<span class="text-info fst-italic">Sigiloso</span>' : (lic.valorTotalEstimado ? 
                    `R$ ${parseFloat(lic.valorTotalEstimado).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Sigiloso')}</p>
                <p><strong>Informação Complementar:</strong></p>
                <div style="white-space: pre-wrap; background-color: #f8f9fa; padding: 10px; border-radius: 5px; max-height: 150px; overflow-y: auto;">
                    ${lic.informacaoComplementar || 'Nenhuma'}
                </div>
                
            `;

            
            let justificativaHtml = '';
            if (lic.justificativaPresencial) {
                const textoCompleto = lic.justificativaPresencial;
                const limite = 200;
                if (textoCompleto.length > limite) {
                    const textoCurto = textoCompleto.substring(0, limite);
                    // Usar IDs únicos para cada instância se houver múltiplas licitações abertas (não é o caso aqui com um só painel)
                    justificativaHtml = `
                        <p><strong>Justificativa Presencial:</strong></p>
                        <div class="justificativa-container">
                            <span class="justificativa-curta" style="white-space: pre-wrap;">${textoCurto}... <a href="#" class="ver-mais-justificativa">Ver mais</a></span>
                            <span class="justificativa-completa d-none" style="white-space: pre-wrap;">${textoCompleto} <a href="#" class="ver-menos-justificativa">Ver menos</a></span>
                        </div>`;
                } else {
                    justificativaHtml = `<p><strong>Justificativa Presencial:</strong></p><div style="white-space: pre-wrap;">${textoCompleto}</div>`;
                }
            }
            
            htmlContent += justificativaHtml;
            // Renderizar conteúdo 
            detailsPanelContent.innerHTML = htmlContent;

            const verMaisJust = detailsPanelContent.querySelector('.ver-mais-justificativa');
            if (verMaisJust) {
                verMaisJust.addEventListener('click', function(e) {
                    e.preventDefault();
                    const container = this.closest('.justificativa-container');
                    container.querySelector('.justificativa-curta').classList.add('d-none');
                    container.querySelector('.justificativa-completa').classList.remove('d-none');
                });
            }
            const verMenosJust = detailsPanelContent.querySelector('.ver-menos-justificativa');
            if (verMenosJust) {
                verMenosJust.addEventListener('click', function(e) {
                    e.preventDefault();
                    const container = this.closest('.justificativa-container');
                    container.querySelector('.justificativa-completa').classList.add('d-none');
                    container.querySelector('.justificativa-curta').classList.remove('d-none');
                });
            }


  
            // Botão acessar PNCP -Controle para testar se o link é funcional
            const btnPncp = document.getElementById('detailsPanelBtnPncp');
            if (btnPncp) {
                if (lic.link_portal_pncp && lic.link_portal_pncp.trim() !== "") {
                    btnPncp.href = lic.link_portal_pncp;
                    btnPncp.classList.remove('disabled'); // Estilo visual de habilitado
                    btnPncp.removeAttribute('aria-disabled'); // Acessibilidade
                } else {
                    btnPncp.href = '#'; // Impede navegação
                    btnPncp.classList.add('disabled');   // Estilo visual de desabilitado
                    btnPncp.setAttribute('aria-disabled', 'true'); // Acessibilidade
                }
            }
                    
            // Botão Sistema de Origem 
            const btnSistemaOrigem = document.getElementById('detailsPanelBtnSistemaOrigem');
            if (btnSistemaOrigem) {
                if (lic.linkSistemaOrigem && lic.linkSistemaOrigem.trim() !== "") { // Assumindo que 'linkSistemaOrigem' virá da API
                    btnSistemaOrigem.disabled = false; 
                    btnSistemaOrigem.innerHTML = '<i class="bi bi-building"></i> Acessar Sistema de Origem';
                    // Definir o que acontece ao clicar. Se for apenas um link:
                    btnSistemaOrigem.onclick = () => { window.open(lic.linkSistemaOrigem, '_blank'); };
                } else {
                    btnSistemaOrigem.disabled = true;
                    btnSistemaOrigem.innerHTML = '<i class="bi bi-building"></i> Sistema de Origem (Não disponível)';
                    btnSistemaOrigem.onclick = null; // Remove handler anterior se houver
                }
            }


            renderDetailsPanelItens(data.itens || []);
            renderDetailsPanelArquivos(data.arquivos || []);
        }

        // Placeholder para renderizar itens e arquivos no painel de detalhes
        let currentDetalhesItens = [];
        let currentDetalhesItensPage = 1;
        const ITENS_POR_PAGINA_DETALHES = 5;

        function renderDetailsPanelItens(itens) {
            currentDetalhesItens = itens;
            currentDetalhesItensPage = 1;
            displayDetalhesItensPage();
        }

        function displayDetalhesItensPage() {
            const tableBody = document.getElementById('detailsPanelItensTableBody');
            const pagination = document.getElementById('detailsPanelItensPagination');
            tableBody.innerHTML = '';
            pagination.innerHTML = '';

            
            if (!currentDetalhesItens || currentDetalhesItens.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Nenhum item encontrado.</td></tr>';
                return;
            }

            const totalPages = Math.ceil(currentDetalhesItens.length / ITENS_POR_PAGINA_DETALHES);
            const startIndex = (currentDetalhesItensPage - 1) * ITENS_POR_PAGINA_DETALHES;
            const endIndex = startIndex + ITENS_POR_PAGINA_DETALHES;
            const pageItens = currentDetalhesItens.slice(startIndex, endIndex);

            pageItens.forEach(item => {
                const tr = document.createElement('tr');
                // --- LÓGICA PARA VALOR UNITÁRIO ESTIMADO DO ITEM ---
                let valorUnitarioDisplay = 'N/I';
                if (item.valorUnitarioEstimado === null) {
                    valorUnitarioDisplay = '<span class="text-info fst-italic">Sigiloso</span>';
                } else if (item.valorUnitarioEstimado !== undefined && item.valorUnitarioEstimado !== '' && !isNaN(parseFloat(item.valorUnitarioEstimado))) {
                    valorUnitarioDisplay = parseFloat(item.valorUnitarioEstimado).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
                }
                // --- LÓGICA PARA VALOR TOTAL DO ITEM ---
                let valorTotalItemDisplay = 'N/I';
                if (item.valorTotal === null) {
                    valorTotalItemDisplay = '<span class="text-info fst-italic">Sigiloso</span>';
                } else if (item.valorTotal !== undefined && item.valorTotal !== '' && !isNaN(parseFloat(item.valorTotal))) {
                    valorTotalItemDisplay = parseFloat(item.valorTotal).toLocaleString('pt-BR', {style: 'currency', currency: 'BRL'});
                }

                tr.innerHTML = `
                    <td data-label="Item">${item.numeroItem || 'N/I'}</td>
                    <td data-label="Descrição">${item.descricao || 'N/I'}</td>
                    <td data-label="Qtde." class="text-end">${item.quantidade || 'N/I'}</td>
                    <td data-label="Un." class="text-center">${item.unidadeMedida || 'N/I'}</td>
                    <td data-label="Vl. Unit." class="text-end">${valorUnitarioDisplay}</td>
                    <td data-label="Vl. Total" class="text-end">${valorTotalItemDisplay}</td>
                `;
                tableBody.appendChild(tr);
            });

            // Paginação simples para itens
            if (totalPages > 1) {
                // Botão Anterior
                const prevLi = document.createElement('li');
                prevLi.classList.add('page-item');
                if (currentDetalhesItensPage === 1) {
                    prevLi.classList.add('disabled');
                }
                prevLi.innerHTML = `<a class="page-link page-link-sm" href="#">Ant</a>`;
                prevLi.addEventListener('click', (e) => { e.preventDefault(); if(currentDetalhesItensPage > 1) { currentDetalhesItensPage--; displayDetalhesItensPage(); }});
                pagination.appendChild(prevLi);

                // Info da Página
                const pageInfo = document.createElement('li');
                pageInfo.classList.add('page-item', 'disabled');
                pageInfo.innerHTML = `<span class="page-link page-link-sm">${currentDetalhesItensPage}/${totalPages}</span>`;
                pagination.appendChild(pageInfo);

                // Botão Próximo
                const nextLi = document.createElement('li');
                nextLi.classList.add('page-item');
                if (currentDetalhesItensPage === totalPages) {
                    nextLi.classList.add('disabled'); // Adiciona a classe 'disabled' apenas se necessário
                }   
                nextLi.innerHTML = `<a class="page-link page-link-sm" href="#">Próx</a>`;
                nextLi.addEventListener('click', (e) => { e.preventDefault(); if(currentDetalhesItensPage < totalPages) { currentDetalhesItensPage++; displayDetalhesItensPage(); }});
                pagination.appendChild(nextLi);
            
            } else if (totalPages === 1 && currentDetalhesItens.length > 0) { 
                const pageInfo = document.createElement('li');
                pageInfo.classList.add('page-item');
                pageInfo.classList.add('disabled');
                pageInfo.innerHTML = `<span class="page-link page-link-sm">${currentDetalhesItensPage} / ${totalPages}</span>`;
                pagination.appendChild(pageInfo);
            }
            
        }


        function renderDetailsPanelArquivos(arquivos) {
            const listElement = document.getElementById('detailsPanelArquivosList');
            listElement.innerHTML = '';
            if (!arquivos || arquivos.length === 0) {
                const li = document.createElement('li');
                li.classList.add('list-group-item');
                li.textContent = 'Nenhum arquivo encontrado.';
                listElement.appendChild(li);
                return;
            }
            arquivos.forEach(arq => {
                const li = document.createElement('li');
                li.classList.add('list-group-item');
                li.innerHTML = `<a href="${arq.link_download}" target="_blank"><i class="bi bi-file-earmark-arrow-down"></i> ${arq.titulo || 'Arquivo sem título'}</a>`;
                listElement.appendChild(li);
            });
        }

        // --- INICIALIZAÇÃO DA PÁGINA ---
        async function inicializarPagina() {        
                    
            popularUFs(); 
            await popularModalidades(); 
            await popularStatus();   
            
            //aplicarEstadoCollapse() //Isso lembra os estados do collapse, mas não quero por agr
            carregarFiltrosSalvos(); // Tenta carregar os filtros salvos da última sessão
            renderizarFavoritosSidebar();
            
            buscarLicitacoes(1); 
                       
            setupFilterSearch('ufSearchInput', 'ufsContainerDropdown', '.form-check');
            setupFilterSearch('modalidadeSearchInput', 'modalidadesContainerDropdown', '.form-check');
            setupFilterSearch('municipioSearchInput', 'municipiosContainerDropdown', '.form-check');

            configurarInputDeTags(palavraChaveInclusaoInputField, palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
            configurarInputDeTags(palavraChaveExclusaoInputField, palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');

        }


        // --- ATRIBUIÇÃO DE EVENT LISTENERS (colocar após a definição das funções) ---
        if (btnBuscarLicitacoes) {
            btnBuscarLicitacoes.addEventListener('click', () => buscarLicitacoes(1));
        }
        if (btnLimparFiltros) {
            btnLimparFiltros.addEventListener('click', limparFiltros);
        }
        // Corrigido para buscar a página atual, não a primeira sempre na ordenação
        if (ordenarPorSelect) {
            ordenarPorSelect.addEventListener('change', () => buscarLicitacoes(currentPage || 1)); 
        }
        if (itensPorPaginaSelect) {
            itensPorPaginaSelect.addEventListener('change', () => buscarLicitacoes(1)); 
        }
        // Adicionar o event listener para btnAtualizarTabela aqui também, se a função já existir
        const btnAtualizarTabela = document.getElementById('btnAtualizarTabela');
        if (btnAtualizarTabela) {
            btnAtualizarTabela.disabled = false; 
            btnAtualizarTabela.addEventListener('click', () => {
                console.log("Botão Atualizar Tabela clicado - Refazendo busca para página:", currentPage);
                if (currentPage < 1) currentPage = 1; 
                buscarLicitacoes(currentPage); 
            });
        }

        inicializarPagina(); 

    } else if (document.body.classList.contains('page-home')) {
        console.log("Página Home detectada. Lógica específica da home pode ir aqui.");
        // Ex: inicializar um carrossel, etc.
    } else if (document.body.classList.contains('page-blog')) {
        console.log("Página Blog detectada.");
        // Ex: adicionar interatividade aos posts do blog
    }
    
    
        
    // Lógica para o Botão "Voltar ao Topo"
    const btnVoltarAoTopo = document.getElementById('btnVoltarAoTopo');

    if (btnVoltarAoTopo) {
        // Adicionar listener via JS é mais limpo que onclick inline
        btnVoltarAoTopo.addEventListener('click', scrollToTop); // <--- Adicione o listener aqui

        window.onscroll = function() {scrollFunction()}; // Mantenha esta parte

        function scrollFunction() { // Esta função pode ficar dentro do DOMContentLoaded se quiser
            if (document.body.scrollTop > 100 || document.documentElement.scrollTop > 100) {
                btnVoltarAoTopo.style.display = "flex"; // Usar 'flex' ao invés de 'block" por causa do align/justify
            } else {
                btnVoltarAoTopo.style.display = "none";
            }
        }
    }
    ajustarLogoPorPagina(); // Chama na carga de cada página

});