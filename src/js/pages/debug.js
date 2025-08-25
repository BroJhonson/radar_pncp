// src/js/pages/radar.js -- VERSÃO DE DEBUG COMPLETA

import { getFavoritos, adicionarFavorito, removerFavorito, isFavorito } from '../modules/favorites.js';

export default function initRadarPage() {
    console.log("[DEBUG] 🚀 initRadarPage() INICIADO.");

    // Elementos do DOM (código original omitido por brevidade)
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
    const dataAtualizacaoInicioInput = document.getElementById('dataAtualizacaoInicio');
    const dataAtualizacaoFimInput = document.getElementById('dataAtualizacaoFim');
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
    const palavraChaveInclusaoInputField = document.getElementById('palavraChaveInclusaoInput');
    const tagsPalavraInclusaoContainer = document.getElementById('tagsPalavraInclusaoContainer');
    const palavraChaveExclusaoInputField = document.getElementById('palavraChaveExclusaoInput');
    const tagsPalavraExclusaoContainer = document.getElementById('tagsPalavraExclusaoContainer');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const listaFavoritosSidebar = document.getElementById('lista-favoritos-sidebar');
    const detailsPanelElement = document.getElementById('detailsPanel');
    const offcanvasFiltrosBody = document.getElementById('offcanvasFiltrosBody');

    // Estado da Aplicação
    let palavrasChaveInclusao = [];
    let palavrasChaveExclusao = [];
    let currentPage = 1;
    let cacheLicitacoesSidebar = {};

    // Constantes e Configurações (código original omitido por brevidade)
    const FILTROS_KEY = 'radarPncpUltimosFiltros';
    const COLLAPSE_KEY = 'radarPncpCollapseState';
    const ufsLista = [
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

    // --- FUNÇÕES COM LOGS DE DEBUG ---

    function salvarFiltrosAtuais() {
        console.log('[DEBUG] 💾 SALVANDO FILTROS no localStorage...');
        const filtros = {
            palavrasChaveInclusao: palavrasChaveInclusao,
            palavrasChaveExclusao: palavrasChaveExclusao,
            status: document.querySelector('.filter-status:checked')?.value || "A Receber/Recebendo Proposta",
            ufs: Array.from(document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked')).map(cb => cb.value),
            municipios: Array.from(document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked')).map(cb => cb.value),
            modalidades: Array.from(document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked')).map(cb => cb.value),
            dataPubInicio: dataPubInicioInput.value,
            dataPubFim: dataPubFimInput.value,
            dataAtualizacaoInicio: dataAtualizacaoInicioInput.value,
            dataAtualizacaoFim: dataAtualizacaoFimInput.value,
            valorMin: valorMinInput.value,
            valorMax: valorMaxInput.value,
            ordenacao: ordenarPorSelect.value,
            itensPorPagina: itensPorPaginaSelect.value,
        };
        localStorage.setItem(FILTROS_KEY, JSON.stringify(filtros));
        console.log('[DEBUG] ✅ Filtros salvos. Estado atual:', {
            inclusao: palavrasChaveInclusao,
            exclusao: palavrasChaveExclusao
        });
        console.log('[DEBUG] localStorage agora contém:', localStorage.getItem(FILTROS_KEY));
    }

    function carregarFiltrosSalvos() {
        //console.log('[DEBUG] 🔄 CARREGANDO FILTROS do localStorage...');
        const filtrosSalvosJson = localStorage.getItem(FILTROS_KEY);
        if (!filtrosSalvosJson) {
            console.log("[DEBUG] 텅 Nenhum filtro salvo encontrado.");
            return;
        }
        try {
            const filtros = JSON.parse(filtrosSalvosJson);
            console.log("[DEBUG] 🔎 Filtros encontrados:", filtros);

            // Reseta os arrays em memória ANTES de carregar
            palavrasChaveInclusao = [];
            palavrasChaveExclusao = [];

            if (filtros.palavrasChaveInclusao) {
                palavrasChaveInclusao = filtros.palavrasChaveInclusao;
                console.log("[DEBUG] Carregando para memória palavrasChaveInclusao:", palavrasChaveInclusao);
            }
            if (filtros.palavrasChaveExclusao) {
                palavrasChaveExclusao = filtros.palavrasChaveExclusao;
                console.log("[DEBUG] Carregando para memória palavrasChaveExclusao:", palavrasChaveExclusao);
            }

            renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
            renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');

            if (filtros.status) {
                const radioStatus = document.querySelector(`.filter-status[value="${filtros.status}"]`);
                if (radioStatus) radioStatus.checked = true;
            }
            if (filtros.ufs && filtros.ufs.length > 0) {
                filtros.ufs.forEach(ufSigla => {
                    const checkUf = document.querySelector(`#ufsContainerDropdown .filter-uf[value="${ufSigla}"]`);
                    if (checkUf) checkUf.checked = true;
                });
                handleUFChange().then(() => {
                    if (filtros.municipios && filtros.municipios.length > 0) {
                        filtros.municipios.forEach(munNome => {
                            const checkMun = document.querySelector(`#municipiosContainerDropdown .filter-municipio[value="${munNome}"]`);
                            if (checkMun) checkMun.checked = true;
                        });
                        updateMunicipioSelectedCount();
                    }
                });
            }
            if (filtros.modalidades && filtros.modalidades.length > 0) {
                filtros.modalidades.forEach(modId => {
                    const checkMod = document.querySelector(`#modalidadesContainerDropdown .filter-modalidade[value="${modId}"]`);
                    if (checkMod) checkMod.checked = true;
                });
                updateModalidadeSelectedCount();
            }
            if (filtros.dataPubInicio) dataPubInicioInput.value = filtros.dataPubInicio;
            if (filtros.dataPubFim) dataPubFimInput.value = filtros.dataPubFim;
            if (filtros.dataAtualizacaoInicio) dataAtualizacaoInicioInput.value = filtros.dataAtualizacaoInicio;
            if (filtros.dataAtualizacaoFim) dataAtualizacaoFimInput.value = filtros.dataAtualizacaoFim;
            if (filtros.valorMin) valorMinInput.value = filtros.valorMin;
            if (filtros.valorMax) valorMaxInput.value = filtros.valorMax;
            if (filtros.ordenacao) ordenarPorSelect.value = filtros.ordenacao;
            if (filtros.itensPorPagina) itensPorPaginaSelect.value = filtros.itensPorPagina;

        } catch (e) {
            console.error("[DEBUG] ❌ Erro ao carregar/parsear filtros:", e);
            localStorage.removeItem(FILTROS_KEY);
        }
    }

    function renderTags(palavrasArray, containerElement, tipo) {
        console.log(`[DEBUG] 🎨 RENDERIZANDO TAGS para '${tipo}'. Dados:`, JSON.stringify(palavrasArray));
        if (!containerElement) return;
        containerElement.innerHTML = '';
        palavrasArray.forEach((palavra, index) => {
            const tag = document.createElement('span');
            tag.classList.add('tag-item');
            tag.textContent = palavra;
            const removeBtn = document.createElement('button');
            removeBtn.classList.add('remove-tag');
            removeBtn.innerHTML = '×';
            removeBtn.title = 'Remover palavra';
            removeBtn.type = 'button';
            removeBtn.addEventListener('click', () => {
                console.log(`[DEBUG] 🖱️ Clique no 'x' da tag '${palavra}' (tipo: ${tipo})`);
                if (tipo === 'inclusao') {
                    palavrasChaveInclusao.splice(index, 1);
                    renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
                } else if (tipo === 'exclusao') {
                    palavrasChaveExclusao.splice(index, 1);
                    renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
                }
                salvarFiltrosAtuais();
            });
            tag.appendChild(removeBtn);
            containerElement.appendChild(tag);
        });
    }

    function addPalavraChave(inputField, palavrasArray, containerElement, tipo) {
        console.log(`[DEBUG] 📥 Adicionando palavra-chave para '${tipo}'...`);
        if (!inputField) return;
        const termos = inputField.value.trim();
        if (termos) {
            const novasPalavras = termos.split(/[,;]+/).map(p => p.trim()).filter(p => p !== "" && p.length > 0);
            let adicionouAlguma = false;
            novasPalavras.forEach(novaPalavra => {
                if (!palavrasArray.includes(novaPalavra)) {
                    palavrasArray.push(novaPalavra);
                    adicionouAlguma = true;
                }
            });
            inputField.value = '';
            if (adicionouAlguma) {
                console.log('[DEBUG] Novas palavras adicionadas. Array agora:', palavrasArray);
                renderTags(palavrasArray, containerElement, tipo);
                salvarFiltrosAtuais();
            }
        }
    }

    function limparFiltros() {
        console.log('[DEBUG] 🗑️ INICIANDO LIMPEZA TOTAL DE FILTROS...');

        if (palavraChaveInclusaoInputField) palavraChaveInclusaoInputField.value = '';
        if (palavraChaveExclusaoInputField) palavraChaveExclusaoInputField.value = '';

        console.log('[DEBUG] Limpando arrays de palavras-chave em memória...');
        palavrasChaveInclusao = [];
        palavrasChaveExclusao = [];

        renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
        renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
        
        document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked').forEach(cb => cb.checked = false);
        if (typeof updateUFSelectedCount === "function") updateUFSelectedCount();
        handleUFChange();
        document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked').forEach(cb => cb.checked = false);
        if (typeof updateModalidadeSelectedCount === "function") updateModalidadeSelectedCount();
        const radiosStatus = document.querySelectorAll('.filter-status');
        let defaultStatusRadio = null;
        const defaultStatusValue = "A Receber/Recebendo Proposta";
        radiosStatus.forEach(radio => {
            if (radio.value === defaultStatusValue) {
                defaultStatusRadio = radio;
            }
        });
        if (defaultStatusRadio) {
            defaultStatusRadio.checked = true;
        } else if (radiosStatus.length > 0) {
            const primeiroValido = Array.from(radiosStatus).find(r => r.value !== "");
            if (primeiroValido) primeiroValido.checked = true;
            else if (radiosStatus.length > 0) radiosStatus[0].checked = true;
        }
        statusWarning.classList.add('d-none');
        if (dataPubInicioInput) dataPubInicioInput.value = '';
        if (dataPubFimInput) dataPubFimInput.value = '';
        if (dataAtualizacaoInicioInput) dataAtualizacaoInicioInput.value = '';
        if (dataAtualizacaoFimInput) dataAtualizacaoFimInput.value = '';
        if (valorMinInput) valorMinInput.value = '';
        if (valorMaxInput) valorMaxInput.value = '';
        const advancedCollapse = document.getElementById('collapseAdvanced');
        if (advancedCollapse && advancedCollapse.classList.contains('show')) {
            new bootstrap.Collapse(advancedCollapse).hide();
        }

        console.log('[DEBUG] Chamando salvarFiltrosAtuais() após zerar os arrays...');
        salvarFiltrosAtuais(); // Chamada explícita

        console.log('[DEBUG] Limpeza concluída. Acionando nova busca...');
        atualizarExibicaoFiltrosAtivos();
        buscarLicitacoes(1);
    }
    
    // ----- COLE O RESTO DO SEU CÓDIGO DE `radar.js` A PARTIR DAQUI -----
    // (A função `inicializarPagina`, `buscarLicitacoes` e as outras)
    
    const formatDateTime = (dateTimeString) => {
        if (!dateTimeString) return 'N/I';
        try {
            const dateObj = new Date(dateTimeString);
            if (isNaN(dateObj.getTime())) {
                const dateObjUTC = new Date(dateTimeString + 'Z');
                if (isNaN(dateObjUTC.getTime())) { return 'Data/Hora Inválida'; }
                return dateObjUTC.toLocaleString('pt-BR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
            }
            return dateObj.toLocaleString('pt-BR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
        } catch (e) { return 'Data/Hora Inválida'; }
    };
    
    if (linkLimparFiltrosRapido) { linkLimparFiltrosRapido.addEventListener('click', function(e) { e.preventDefault(); limparFiltros(); });}

    if (offcanvasFiltrosBody) {
        offcanvasFiltrosBody.addEventListener('click', function(event) {
             if (event.target.classList.contains('btn-limpar-grupo')) {
                 const tipoLimpeza = event.target.dataset.limpar;
                 console.log(`[DEBUG] 🖱️ Clique no 'X' do GRUPO '${tipoLimpeza}'`);
                 let estadoAlterado = false;
                 switch (tipoLimpeza) {
                    case 'status':
                        const defaultStatus = document.querySelector('.filter-status[value="A Receber/Recebendo Proposta"]');
                        if (defaultStatus) defaultStatus.checked = true;
                        break;
                    case 'modalidades':
                        document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked').forEach(cb => cb.checked = false);
                        updateModalidadeSelectedCount();
                        break;
                    case 'inclusao':
                        if (palavrasChaveInclusao.length > 0) {
                            palavrasChaveInclusao = [];
                            renderTags(palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
                            estadoAlterado = true;
                        }
                        break;
                    case 'exclusao':
                        if (palavrasChaveExclusao.length > 0) {
                            palavrasChaveExclusao = [];
                            renderTags(palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');
                            estadoAlterado = true;
                        }
                        break;
                    case 'localizacao':
                        document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked').forEach(cb => cb.checked = false);
                        handleUFChange(); 
                        break;
                    case 'avancado':
                        if(dataPubInicioInput) dataPubInicioInput.value = '';
                        if(dataPubFimInput) dataPubFimInput.value = '';
                        if(dataAtualizacaoInicioInput) dataAtualizacaoInicioInput.value = '';
                        if(dataAtualizacaoFimInput) dataAtualizacaoFimInput.value = '';
                        if(valorMinInput) valorMinInput.value = '';
                        if(valorMaxInput) valorMaxInput.value = '';
                        break;
                 }
                 if (estadoAlterado) {
                     salvarFiltrosAtuais();
                 }
              }
        });
    }

    function configurarInputDeTags(inputField, palavrasArray, containerElement, tipo) {
        if (!inputField) return;
        inputField.addEventListener('keyup', function(e) {
            if (e.key === 'Enter' || e.key === 'NumpadEnter' || e.keyCode === 13) {
                e.preventDefault();
                addPalavraChave(inputField, palavrasArray, containerElement, tipo);
            }
        });
        inputField.addEventListener('input', function(e) {
            const valorAtual = inputField.value;
            if (valorAtual.endsWith(',') || valorAtual.endsWith(';')) {
                inputField.value = valorAtual.slice(0, -1);
                addPalavraChave(inputField, palavrasArray, containerElement, tipo);
            }
        });
    }

    function atualizarExibicaoFiltrosAtivos() {
        if (!filtrosAtivosContainer || !filtrosAtivosTexto) return;
        let filtrosAplicados = [];
        if (palavrasChaveInclusao.length > 0) {
            filtrosAplicados.push(`Buscar: ${palavrasChaveInclusao.map(p => `<span class="badge bg-primary">${p}</span>`).join(' ')}`);
        }
        if (palavrasChaveExclusao.length > 0) {
            filtrosAplicados.push(`Excluir: ${palavrasChaveExclusao.map(p => `<span class="badge bg-danger">${p}</span>`).join(' ')}`);
        }
        const ufsSelecionadas = Array.from(document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked')).map(cb => cb.value);
        if (ufsSelecionadas.length > 0) {
            filtrosAplicados.push(`UF: ${ufsSelecionadas.map(uf => `<span class="badge bg-secondary">${uf}</span>`).join(' ')}`);
        }
        const municipiosSelecionados = Array.from(document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked')).map(cb => cb.value);
        if (municipiosSelecionados.length > 0) {
            filtrosAplicados.push(`Município: ${municipiosSelecionados.map(m => `<span class="badge bg-info text-dark">${m}</span>`).join(' ')}`);
        }
        const modalidadesSelecionadas = Array.from(document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked'))
            .map(cb => {
                const label = document.querySelector(`label[for="${cb.id}"]`);
                return label ? label.textContent : cb.value;
            });
        if (modalidadesSelecionadas.length > 0) {
            filtrosAplicados.push(`Modalidade: ${modalidadesSelecionadas.map(m => `<span class="badge bg-warning text-dark">${m}</span>`).join(' ')}`);
        }
        const statusSelecionadoRadio = document.querySelector('.filter-status:checked');
        if (statusSelecionadoRadio && statusSelecionadoRadio.value) {
            const labelStatus = document.querySelector(`label[for="${statusSelecionadoRadio.id}"]`);
            filtrosAplicados.push(`Status: <span class="badge bg-success">${labelStatus ? labelStatus.textContent : statusSelecionadoRadio.value}</span>`);
        } else if (statusSelecionadoRadio && statusSelecionadoRadio.value === "") {
            filtrosAplicados.push(`Status: <span class="badge bg-dark">Todos</span>`);
        }
        if (dataPubInicioInput.value || dataPubFimInput.value) {
            let strDataPub = "Data Pub.: ";
            if (dataPubInicioInput.value) strDataPub += `de ${new Date(dataPubInicioInput.value+'T00:00:00').toLocaleDateString('pt-BR')} `;
            if (dataPubFimInput.value) strDataPub += `até ${new Date(dataPubFimInput.value+'T00:00:00').toLocaleDateString('pt-BR')}`;
            filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strDataPub.trim()}</span>`);
        }
        if (dataAtualizacaoInicioInput && dataAtualizacaoFimInput && (dataAtualizacaoInicioInput.value || dataAtualizacaoFimInput.value)) {
            let strDataAtual = "Data Atual.: ";
            if (dataAtualizacaoInicioInput.value) strDataAtual += `de ${new Date(dataAtualizacaoInicioInput.value+'T00:00:00').toLocaleDateString('pt-BR')} `;
            if (dataAtualizacaoFimInput.value) strDataAtual += `até ${new Date(dataAtualizacaoFimInput.value+'T00:00:00').toLocaleDateString('pt-BR')}`;
            filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strDataAtual.trim()}</span>`);
        }
        if (valorMinInput.value || valorMaxInput.value) {
            let strValor = "Valor: ";
            if (valorMinInput.value) strValor += `min R$ ${valorMinInput.value} `;
            if (valorMaxInput.value) strValor += `max R$ ${valorMaxInput.value}`;
            filtrosAplicados.push(`<span class="badge bg-light text-dark border">${strValor.trim()}</span>`);
        }
        if (filtrosAplicados.length > 0) {
            filtrosAtivosTexto.innerHTML = filtrosAplicados.join(' • ');
            filtrosAtivosContainer.style.display = 'block';
        } else {
            filtrosAtivosTexto.innerHTML = 'Nenhum filtro aplicado.';
        }
    }

    function updateUFSelectedCount() {
        const count = document.querySelectorAll('#ufsContainerDropdown .filter-uf:checked').length;
        const badge = document.getElementById('ufSelectedCount');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? '' : 'none';
        }
    }

    function updateModalidadeSelectedCount() {
        const count = document.querySelectorAll('#modalidadesContainerDropdown .filter-modalidade:checked').length;
        const badge = document.getElementById('modalidadesSelectedCount');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    }

    function updateMunicipioSelectedCount() {
        const count = document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked').length;
        const badge = document.getElementById('municipiosSelectedCount');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
            if (count === 0) badge.textContent = '0';
        }
    }

    function setupFilterSearch(inputId, containerId, itemSelector) {
        const searchInput = document.getElementById(inputId);
        const container = document.getElementById(containerId);
        if (!searchInput || !container) {
            return;
        }
        searchInput.addEventListener('input', function() {
            const searchTerm = searchInput.value.toLowerCase();
            const items = container.querySelectorAll(itemSelector);
            items.forEach(item => {
                const label = item.querySelector('label');
                if (label) {
                    const itemText = label.textContent.toLowerCase();
                    if (itemText.includes(searchTerm)) {
                        item.style.display = 'block';
                    } else {
                        item.style.display = 'none';
                    }
                }
            });
        });
        container.addEventListener('click', function(event) {
            if (event.target.matches('.form-check-input')) {
                searchInput.value = '';
                const items = container.querySelectorAll(itemSelector);
                items.forEach(item => {
                    item.style.display = 'block';
                });
            }
        });
    }
    
    function atualizarBotaoFavoritoUI(buttonElement, pncpId) {
        if (!buttonElement || !pncpId) return;
        const ehFavoritoAgora = isFavorito(pncpId);
        const icon = buttonElement.querySelector('i');
        buttonElement.title = ehFavoritoAgora ? 'Desfavoritar' : 'Favoritar';
        if (icon) {
            if (ehFavoritoAgora) {
                icon.classList.remove('bi-star');
                icon.classList.add('bi-star-fill');
                if (!buttonElement.classList.contains('btn-link')) {
                    buttonElement.classList.remove('btn-outline-warning');
                    buttonElement.classList.add('btn-warning', 'active');
                } else {
                    buttonElement.classList.add('active');
                }
            } else {
                icon.classList.remove('bi-star-fill');
                icon.classList.add('bi-star');
                if (!buttonElement.classList.contains('btn-link')) {
                    buttonElement.classList.remove('btn-warning', 'active');
                    buttonElement.classList.add('btn-outline-warning');
                } else {
                    buttonElement.classList.remove('active');
                }
            }
        }
    }

    function handleFavoritarClick(event) {
        const button = event.target.closest('.btn-favoritar');
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
            atualizarBotaoFavoritoUI(button, pncpId);
            const btnNaTabela = licitacoesTableBody.querySelector(`.btn-favoritar[data-pncp-id="${pncpId}"]`);
            if (btnNaTabela && btnNaTabela !== button) {
                atualizarBotaoFavoritoUI(btnNaTabela, pncpId);
            }
            const btnNosDetalhes = document.getElementById('detailsPanelFavoriteBtn');
            if (btnNosDetalhes && btnNosDetalhes !== button && btnNosDetalhes.dataset.pncpId === pncpId) {
                atualizarBotaoFavoritoUI(btnNosDetalhes, pncpId);
            }
            renderizarFavoritosSidebar();
        }
    }

    async function renderizarFavoritosSidebar() {
        const listaSidebar = document.getElementById('lista-favoritos-sidebar');
        const listaOffcanvas = document.getElementById('lista-favoritos-offcanvas');
        if (!listaSidebar && !listaOffcanvas) {
            return;
        }
        const favoritosIds = getFavoritos();
        const msgVazio = '<li class="list-group-item text-muted small">Nenhuma licitação favoritada ainda.</li>';
        const msgLoader = '<li class="list-group-item text-muted small"><div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>Carregando...</li>';
        const msgErro = '<li class="list-group-item text-danger small fst-italic">Erro ao carregar dados dos favoritos.</li>';
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
                if (listaSidebar) listaSidebar.insertAdjacentHTML('beforeend', itemHtml);
                if (listaOffcanvas) listaOffcanvas.insertAdjacentHTML('beforeend', itemHtml);
            }
        }
        if (!contentRendered && favoritosIds.length > 0) {
            if (listaSidebar) listaSidebar.innerHTML = msgErro;
            if (listaOffcanvas) listaOffcanvas.innerHTML = msgErro;
        }
    }

    async function popularModalidades() {
        if (!modalidadesContainer) return;
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
                    div.querySelector('.filter-modalidade').addEventListener('change', updateModalidadeSelectedCount);
                });
            } else {
                modalidadesContainer.innerHTML = '<small class="text-danger">Nenhuma modalidade encontrada.</small>';
            }
        } catch (error) {
            console.error("Erro ao carregar modalidades:", error);
            modalidadesContainer.innerHTML = `<small class="text-danger">Erro ao carregar modalidades: ${error.message}</small>`;
        }
        updateModalidadeSelectedCount();
    }

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
                statusRadarApi.sort((a, b) => a.nome.localeCompare(b.nome));
                statusRadarApi.forEach(st => {
                    const div = document.createElement('div');
                    div.classList.add('form-check');
                    const isChecked = st.id === defaultStatusValue;
                    const elementId = `status-radar-${st.id.toLowerCase().replace(/[^a-z0-9-_]/g, '') || 'unk'}`;
                    div.innerHTML = `
                        <input class="form-check-input filter-status" type="radio" name="statusLicitacao" 
                            value="${st.id}" id="${elementId}" ${isChecked ? 'checked' : ''}>
                        <label class="form-check-label" for="${elementId}">${st.nome}</label>
                    `;
                    statusContainer.appendChild(div);
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

    function popularUFs() {
        if (!ufsContainer) return;
        ufsContainer.innerHTML = '';
        ufsLista.forEach(uf => {
            const div = document.createElement('div');
            div.classList.add('form-check');
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

    async function handleUFChange() {
        updateUFSelectedCount();
        const ufsSelecionadas = Array.from(document.querySelectorAll('.filter-uf:checked')).map(cb => cb.value);
        const municipiosContainer = document.getElementById('municipiosContainerDropdown');
        const municipiosDropdownButton = document.getElementById('dropdownMunicipiosButton');
        const municipiosHelp = document.getElementById('municipiosHelp');
        if (!municipiosContainer || !municipiosDropdownButton) return;
        municipiosDropdownButton.disabled = true;
        municipiosContainer.innerHTML = '';
        if (ufsSelecionadas.length === 0) {
            municipiosContainer.innerHTML = '<small class="text-muted p-2">Selecione uma UF primeiro</small>';
            if (municipiosHelp) municipiosHelp.textContent = "Selecione uma ou mais UFs para listar os municípios.";
            updateMunicipioSelectedCount();
            return;
        }
        municipiosDropdownButton.disabled = false;
        municipiosContainer.innerHTML = '<div class="p-2 text-muted">Carregando municípios...</div>';
        if (municipiosHelp) municipiosHelp.textContent = `Carregando municípios para ${ufsSelecionadas.join(', ')}...`;
        let todosMunicipios = [];
        let ufsComErro = [];
        for (const uf of ufsSelecionadas) {
            try {
                const response = await fetch(`/api/ibge/municipios/${uf}`);
                const data = await response.json();
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
        municipiosContainer.innerHTML = '';
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
            document.querySelectorAll('.filter-municipio').forEach(cb => {
                cb.addEventListener('change', updateMunicipioSelectedCount);
            });
            if (municipiosHelp) municipiosHelp.textContent = `Municípios de ${ufsSelecionadas.join(', ')}. Selecione um ou mais.`;
        } else {
            municipiosContainer.innerHTML = '<small class="text-danger p-2">Nenhum município encontrado.</small>';
            if (municipiosHelp) municipiosHelp.textContent = "Nenhum município encontrado para as UFs selecionadas.";
        }
        if (ufsComErro.length > 0 && municipiosHelp) {
            municipiosHelp.textContent += ` (Erro ao carregar de: ${ufsComErro.join(', ')})`;
        }
        updateMunicipioSelectedCount();
    }

    function handleStatusChange(event) {
        const selectedStatus = event.target.value;
        if (selectedStatus === "" || selectedStatus === "Encerrada") {
            // A validação será feita na função de busca
        }
    }

    async function buscarLicitacoes(page = 1) {
        console.log(`[DEBUG] 📡 BUSCANDO LICITAÇÕES... Página: ${page}`);
        salvarFiltrosAtuais();
        const btnAplicar = document.getElementById('btnBuscarLicitacoes');
        if (btnAplicar) {
            btnAplicar.disabled = true;
            btnAplicar.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Buscando...`;
        }
        currentPage = page;
        const params = new URLSearchParams();
        if (loadingOverlay) loadingOverlay.classList.remove('d-none');
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
        if (statusWarning) statusWarning.classList.add('d-none');
        if ((statusRadarValor === "" || statusRadarValor === "Encerrada") && palavrasChaveInclusao.length === 0) {
            if (statusWarning) {
                statusWarning.textContent = 'Palavra-chave de busca é obrigatória para este status.';
                statusWarning.classList.remove('d-none');
            }
            if (licitacoesTableBody) licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Forneça uma palavra-chave para buscar com o status selecionado.</td></tr>`;
            if (totalRegistrosInfo) totalRegistrosInfo.textContent = '0';
            if (exibicaoInfo) exibicaoInfo.textContent = '';
            if (paginationControls) paginationControls.innerHTML = '';
            if (loadingOverlay) loadingOverlay.classList.add('d-none');
            if (btnAplicar) {
                btnAplicar.disabled = false;
                btnAplicar.innerHTML = `<i class="bi bi-search"></i> Aplicar Filtros`;
            }
            return;
        }
        const municipiosSelecionados = Array.from(document.querySelectorAll('#municipiosContainerDropdown .filter-municipio:checked')).map(cb => cb.value);
        if (municipiosSelecionados.length > 0) {
            municipiosSelecionados.forEach(mun => params.append('municipioNome', mun));
        }
        const dataInicio = dataPubInicioInput.value;
        if (dataInicio) params.append('dataPubInicio', dataInicio);
        const dataFim = dataPubFimInput.value;
        if (dataFim) params.append('dataPubFim', dataFim);
        if (dataAtualizacaoInicioInput && dataAtualizacaoFimInput) {
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
            console.log("[DEBUG] ⚙️ Parâmetros da API:", params.toString());
            const response = await fetch(`/api/frontend/licitacoes?${params.toString()}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error("[DEBUG] ❌ Erro da API:", response.status, errorData);
                throw new Error(`Erro na API: ${response.status}`);
            }
            const data = await response.json();
            console.log("[DEBUG] ✅ Dados recebidos da API:", data);
            renderLicitacoesTable(data.licitacoes);
            renderPagination(data);
            atualizarExibicaoFiltrosAtivos();
            totalRegistrosInfo.textContent = data.total_registros || '0';
            if (data.licitacoes && data.licitacoes.length > 0) {
                const inicio = (data.pagina_atual - 1) * parseInt(data.por_pagina, 10) + 1;
                const fim = inicio + data.licitacoes.length - 1;
                exibicaoInfo.textContent = `Exibindo ${inicio}-${fim} de ${data.total_registros}`;
            } else {
                exibicaoInfo.textContent = "Nenhum resultado";
                if (!data.total_registros || data.total_registros === 0) {
                    licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center">Nenhuma licitação encontrada para os filtros aplicados.</td></tr>`;
                }
            }
        } catch (error) {
            console.error("[DEBUG] 💥 Erro crítico ao buscar licitações:", error);
            licitacoesTableBody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Erro ao buscar licitações: ${error.message}</td></tr>`;
            totalRegistrosInfo.textContent = '0';
            exibicaoInfo.textContent = 'Erro';
            paginationControls.innerHTML = '';
        } finally {
            if (loadingOverlay) loadingOverlay.classList.add('d-none');
            if (btnAplicar) {
                btnAplicar.disabled = false;
                btnAplicar.innerHTML = `<i class="bi bi-search"></i> Aplicar Filtros`;
            }
            console.log("[DEBUG] 🏁 Fim da busca.");
        }
    }

    function renderLicitacoesTable(licitacoes) {
        if (!licitacoesTableBody) return;
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
            let objetoHtml = objetoCompleto;
            if (objetoCompleto.length > 100) {
                objetoHtml = `<span class="objeto-curto">${objetoCurto}... <a href="#" class="ver-mais-objeto" data-objeto-completo="${lic.id}">Ver mais</a></span>
                            <span class="objeto-completo d-none">${objetoCompleto} <a href="#" class="ver-menos-objeto" data-objeto-completo="${lic.id}">Ver menos</a></span>`;
            }
            let valorEstimadoDisplay = 'N/I';
            if (lic.valorTotalEstimado === null) {
                valorEstimadoDisplay = '<span class="text-info fst-italic">Sigiloso</span>';
            } else if (lic.valorTotalEstimado !== undefined && lic.valorTotalEstimado !== '' && !isNaN(parseFloat(lic.valorTotalEstimado))) {
                valorEstimadoDisplay = `R$ ${parseFloat(lic.valorTotalEstimado).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            } else if (typeof lic.valorTotalEstimado === 'string' && lic.valorTotalEstimado.trim() === '') {
                valorEstimadoDisplay = '<span class="text-info fst-italic">Sigiloso</span>';
            } else if (!lic.valorTotalEstimado && lic.valorTotalEstimado !== 0) {
                valorEstimadoDisplay = '<span class="text-info fst-italic">Sigiloso</span>';
            }
            const ehFavorito = isFavorito(lic.numeroControlePNCP);
            const btnFavoritoHtml = `
                <button class="btn btn-sm ${ehFavorito ? 'btn-warning active' : 'btn-outline-warning'} btn-favoritar" 
                        title="${ehFavorito ? 'Desfavoritar' : 'Favoritar'}" data-pncp-id="${lic.numeroControlePNCP}">
                    <i class="bi ${ehFavorito ? 'bi-star-fill' : 'bi-star'}"></i>
                </button>
            `;
            tr.innerHTML = `
                <td data-label="Município/UF" class="align-middle">${lic.unidadeOrgaoMunicipioNome || 'N/I'}/${lic.unidadeOrgaoUfSigla || 'N/I'}</td>
                <td data-label="Objeto"><div class="objeto-container" data-lic-id="${lic.id}">${objetoHtml}</div></td>
                <td data-label="Órgão" class="align-middle">${lic.orgaoEntidadeRazaoSocial || 'N/I'}</td>
                <td data-label="Status" class="align-middle"><span class="badge ${statusBadgeClass}">${lic.situacaoReal || lic.situacaoCompraNome || 'N/I'}</span></td>
                <td data-label="Valor (R$)" class="align-middle">${valorEstimadoDisplay}</td>
                <td data-label="Modalidade" class="align-middle">${lic.modalidadeNome || 'N/I'}</td>
                <td data-label="Atualização" class="align-middle">${lic.dataAtualizacao ? new Date(lic.dataAtualizacao + 'T00:00:00Z').toLocaleDateString('pt-BR') : 'N/I'}</td>
                <td data-label="Ações" class="text-nowrap align-middle">
                    <button class="btn btn-sm btn-info btn-detalhes" title="Mais Detalhes" data-pncp-id="${lic.numeroControlePNCP}"><i class="bi bi-eye-fill"></i></button>                                                
                    ${btnFavoritoHtml}
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

    function getStatusBadgeClass(situacaoReal) {
        if (!situacaoReal) return 'bg-secondary';
        const statusLower = situacaoReal.toLowerCase();
        if (statusLower.includes('recebendo') || statusLower.includes('aberta') || statusLower.includes('divulgada')) {
            return 'bg-success';
        } else if (statusLower.includes('encerrada') || statusLower.includes('homologada') || statusLower.includes('concluída')) {
            return 'bg-primary';
        } else if (statusLower.includes('julgamento')) {
            return 'bg-warning text-dark';
        } else if (statusLower.includes('suspensa')) {
            return 'bg-info text-dark';
        } else if (statusLower.includes('anulada') || statusLower.includes('revogada') || statusLower.includes('cancelada')) {
            return 'bg-danger';
        }
        return 'bg-secondary';
    }

    function renderPagination(data) {
        paginationControls.innerHTML = '';
        if (!data || !data.licitacoes || data.total_paginas == null || data.total_paginas <= 1) {
            return;
        }
        const pagina_atual = parseInt(data.pagina_atual, 10);
        const total_paginas = parseInt(data.total_paginas, 10);
        if (isNaN(pagina_atual) || isNaN(total_paginas)) {
            return;
        }
        const prevLi = document.createElement('li');
        prevLi.classList.add('page-item');
        if (pagina_atual === 1) {
            prevLi.classList.add('disabled');
        }
        prevLi.innerHTML = `<a class="page-link" href="#" data-page="${pagina_atual - 1}">Anterior</a>`;
        paginationControls.appendChild(prevLi);
        let startPage = Math.max(1, pagina_atual - 2);
        let endPage = Math.min(total_paginas, pagina_atual + 2);
        const maxPageLinks = 5;
        if (endPage - startPage + 1 < maxPageLinks) {
            if (pagina_atual < maxPageLinks / 2) {
                endPage = Math.min(total_paginas, startPage + maxPageLinks - 1);
            } else if (pagina_atual > total_paginas - maxPageLinks / 2) {
                startPage = Math.max(1, endPage - maxPageLinks + 1);
            } else {
                const diff = Math.floor((maxPageLinks - (endPage - startPage + 1)) / 2);
                startPage = Math.max(1, startPage - diff);
                endPage = Math.min(total_paginas, endPage + (maxPageLinks - (endPage - startPage + 1) - diff));
            }
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
        const nextLi = document.createElement('li');
        nextLi.classList.add('page-item');
        if (pagina_atual === total_paginas) {
            nextLi.classList.add('disabled');
        }
        nextLi.innerHTML = `<a class="page-link" href="#" data-page="${pagina_atual + 1}">Próxima</a>`;
        paginationControls.appendChild(nextLi);
        paginationControls.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const parentLi = this.closest('.page-item');
                if (parentLi && (parentLi.classList.contains('disabled') || parentLi.classList.contains('active'))) {
                    return;
                }
                const page = parseInt(this.dataset.page);
                if (page && !isNaN(page)) {
                    buscarLicitacoes(page);
                }
            });
        });
    }

    const detailsPanelBody = document.getElementById('detailsPanel');
    const detailsPanel = detailsPanelBody ? new bootstrap.Offcanvas(detailsPanelBody) : null;
    const detailsPanelContent = document.getElementById('detailsPanelContent');
    async function handleDetalhesClick(event) {
        const button = event.currentTarget;
        const pncpId = button.dataset.pncpId;
        if (!pncpId || !detailsPanel) return;
        detailsPanelContent.innerHTML = '<p class="text-center">Carregando detalhes...</p>';
        document.getElementById('detailsPanelItensTableBody').innerHTML = '';
        document.getElementById('detailsPanelItensPagination').innerHTML = '';
        document.getElementById('detailsPanelArquivosList').innerHTML = '';
        detailsPanel.show();
        try {
            const response = await fetch(`/api/frontend/licitacao/${encodeURIComponent(pncpId)}`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({
                    erro_frontend: "Erro desconhecido na resposta da API de detalhes."
                }));
                throw new Error(errorData.erro_backend || errorData.erro_frontend || `Erro ${response.status}`);
            }
            const data = await response.json();
            console.log("[DEBUG] Dados de DETALHES recebidos para PNCP ID:", pncpId, JSON.parse(JSON.stringify(data)));
            renderDetailsPanelContent(data);
        } catch (error) {
            console.error("Erro ao buscar detalhes da licitação:", error);
            detailsPanelContent.innerHTML = `<p class="text-center text-danger">Erro ao carregar detalhes: ${error.message}</p>`;
        }
    }

    function renderDetailsPanelContent(data) {
        // ... (código da função original sem alterações)
        if (!detailsPanelElement) return;
        if (!data || !data.licitacao) {
            detailsPanelContent.innerHTML = '<p class="text-center text-danger">Dados da licitação não encontrados.</p>';
            return;
        }
        const lic = data.licitacao;
        const detailsPanelSubtitle = document.getElementById('detailsPanelSubtitle');
        const detailsPanelLabel = document.getElementById('detailsPanelLabel');
        const favoriteIconContainer = document.getElementById('detailsPanelFavoriteIconContainer');
        if (favoriteIconContainer) {
            favoriteIconContainer.innerHTML = '';
            if (lic && lic.numeroControlePNCP) {
                const ehFavorito = isFavorito(lic.numeroControlePNCP);
                const favButton = document.createElement('button');
                favButton.id = 'detailsPanelFavoriteBtn';
                favButton.classList.add('btn', 'btn-link', 'text-warning', 'p-0', 'btn-favoritar');
                favButton.style.fontSize = '1.5rem';
                favButton.dataset.pncpId = lic.numeroControlePNCP;
                favButton.title = ehFavorito ? 'Desfavoritar' : 'Favoritar';
                favButton.innerHTML = `<i class="bi ${ehFavorito ? 'bi-star-fill' : 'bi-star'}"></i>`;
                favoriteIconContainer.appendChild(favButton);
            }
        }
        let tituloPrincipal = `Detalhes: ${lic.numeroControlePNCP || 'N/I'}`;
        if (lic.unidadeOrgaoNome) {
            tituloPrincipal = lic.unidadeOrgaoNome;
        } else if (lic.processo) {
            tituloPrincipal = `Processo: ${lic.processo}`;
        }
        if (detailsPanelLabel) {
            detailsPanelLabel.textContent = tituloPrincipal;
        }
        if (detailsPanelSubtitle) {
            if (lic.numeroCompra && lic.anoCompra) {
                detailsPanelSubtitle.textContent = `Edital: ${lic.numeroCompra}/${lic.anoCompra}`;
                detailsPanelSubtitle.style.display = 'block';
            } else if (lic.numeroCompra) {
                detailsPanelSubtitle.textContent = `Número da Compra: ${lic.numeroCompra}`;
                detailsPanelSubtitle.style.display = 'block';
            } else {
                detailsPanelSubtitle.textContent = '';
                detailsPanelSubtitle.style.display = 'none';
            }
        }
        const formatDate = (dateString) => {
            if (!dateString) return 'N/I';
            return new Date(dateString + 'T00:00:00Z').toLocaleDateString('pt-BR');
        };
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
        detailsPanelContent.innerHTML = htmlContent;
        // ... (resto do código da função original)
    }

    let currentDetalhesItens = [];
    let currentDetalhesItensPage = 1;
    const ITENS_POR_PAGINA_DETALHES = 5;

    function renderDetailsPanelItens(itens) {
        currentDetalhesItens = itens;
        currentDetalhesItensPage = 1;
        displayDetalhesItensPage();
    }

    function displayDetalhesItensPage() {
        // ... (código da função original sem alterações)
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
            tr.innerHTML = `
                <td data-label="Item">${item.numeroItem || 'N/I'}</td>
                <td data-label="Descrição">${item.descricao || 'N/I'}</td>
                <td data-label="Qtde." class="text-end">${item.quantidade || 'N/I'}</td>
                <td data-label="Un." class="text-center">${item.unidadeMedida || 'N/I'}</td>
                <td data-label="Vl. Unit." class="text-end">${parseFloat(item.valorUnitarioEstimado).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) || 'N/I'}</td>
                <td data-label="Vl. Total" class="text-end">${parseFloat(item.valorTotal).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) || 'N/I'}</td>
            `;
            tableBody.appendChild(tr);
        });
        if (totalPages > 1) {
             // Lógica de paginação dos itens...
        }
    }

    function renderDetailsPanelArquivos(arquivos) {
        // ... (código da função original sem alterações)
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

    async function inicializarPagina() {
        console.log('[DEBUG] 🏁 INICIALIZANDO A PÁGINA...');
        popularUFs();
        await popularModalidades();
        await popularStatus();
        carregarFiltrosSalvos();
        renderizarFavoritosSidebar();
        
        // A busca inicial será chamada depois de carregar os filtros
        buscarLicitacoes(1);
        
        setupFilterSearch('ufSearchInput', 'ufsContainerDropdown', '.form-check');
        setupFilterSearch('modalidadeSearchInput', 'modalidadesContainerDropdown', '.form-check');
        setupFilterSearch('municipioSearchInput', 'municipiosContainerDropdown', '.form-check');
        configurarInputDeTags(palavraChaveInclusaoInputField, palavrasChaveInclusao, tagsPalavraInclusaoContainer, 'inclusao');
        configurarInputDeTags(palavraChaveExclusaoInputField, palavrasChaveExclusao, tagsPalavraExclusaoContainer, 'exclusao');

        if (btnBuscarLicitacoes) {
            btnBuscarLicitacoes.addEventListener('click', () => buscarLicitacoes(1));
        }
        if (btnLimparFiltros) {
            btnLimparFiltros.addEventListener('click', limparFiltros);
        }
        if (ordenarPorSelect) {
            ordenarPorSelect.addEventListener('change', () => buscarLicitacoes(currentPage || 1));
        }
        if (itensPorPaginaSelect) {
            itensPorPaginaSelect.addEventListener('change', () => buscarLicitacoes(1));
        }
        const btnAtualizarTabela = document.getElementById('btnAtualizarTabela');
        if (btnAtualizarTabela) {
            btnAtualizarTabela.disabled = false;
            btnAtualizarTabela.addEventListener('click', () => {
                console.log("[DEBUG] Botão Atualizar Tabela clicado - Refazendo busca para página:", currentPage);
                if (currentPage < 1) currentPage = 1;
                buscarLicitacoes(currentPage);
            });
        }
        console.log('[DEBUG] ✅ Página inicializada e listeners configurados.');
    }

    inicializarPagina();
}