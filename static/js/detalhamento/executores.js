// ============================================================
// executores.js - MÓDULO DE EXECUTORES
// ============================================================

const ExecutoresModule = {

    // Atributos
    todosExecutoresLista: [],
    selectedExecutoresMap: new Map(),
    nomeFuncionariosCache: new Map(),

    // Inicialização
    init() {
        console.log('📌 ExecutoresModule: inicializado');
        this.setupSearch();
        this.setupClickFora();
        
        // ⭐ Configurar o trigger do dropdown (substitui o onclick)
        const trigger = document.querySelector('.selector-trigger');
        if (trigger) {
            trigger.addEventListener('click', () => this.toggleDropdown());
        }
    },

    // ============================================================
    // CARREGAR EXECUTORES DO PROCESSO
    // ============================================================
    async carregar(processoId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/dados`);
            const data = await response.json();

            if (data.success && data.executores && data.executores.length > 0) {
                this.todosExecutoresLista = data.executores;
                this.renderizarLista();
                return this.todosExecutoresLista;
            } else {
                this.todosExecutoresLista = [];
                const optionsDiv = document.getElementById('executores-options');
                if (optionsDiv) {
                    optionsDiv.innerHTML = '<div class="no-options">⚠️ Nenhum executor cadastrado para este processo</div>';
                }
                return [];
            }
        } catch (error) {
            console.error('Erro ao carregar executores:', error);
            this.todosExecutoresLista = [];
            return [];
        }
    },

    // ============================================================
    // RENDERIZAR LISTA NO DROPDOWN
    // ============================================================
    renderizarLista(filtro = '') {
        const optionsDiv = document.getElementById('executores-options');
        if (!optionsDiv) return;

        let filteredExecutores = this.todosExecutoresLista;
        if (filtro) {
            const term = filtro.toLowerCase();
            filteredExecutores = this.todosExecutoresLista.filter(exec =>
                exec.nome.toLowerCase().includes(term) ||
                (exec.cargo && exec.cargo.toLowerCase().includes(term))
            );
        }

        if (filteredExecutores.length === 0) {
            optionsDiv.innerHTML = '<div class="no-options">❌ Nenhum executor encontrado</div>';
            return;
        }

        let html = '';
        filteredExecutores.forEach(executor => {
            const isSelected = this.selectedExecutoresMap.has(String(executor.id));
            html += `
                <div class="executor-option ${isSelected ? 'selected' : ''}" onclick="ExecutoresModule.toggle(${executor.id})">
                    <input type="checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); ExecutoresModule.toggle(${executor.id})">
                    <div class="executor-info">
                        <span class="executor-name">${escapeHtml(executor.nome)}</span>
                        ${executor.cargo ? `<span class="executor-cargo">- ${escapeHtml(executor.cargo)}</span>` : ''}
                    </div>
                </div>
            `;
        });

        optionsDiv.innerHTML = html;
    },

    // ============================================================
    // TOGGLE (SELECIONAR/DESSELECIONAR)
    // ============================================================
    toggle(executorId) {
        const executor = this.todosExecutoresLista.find(e => e.id == executorId);
        if (!executor) return;

        if (this.selectedExecutoresMap.has(String(executorId))) {
            this.selectedExecutoresMap.delete(String(executorId));
        } else {
            this.selectedExecutoresMap.set(String(executorId), executor);
        }

        this.atualizarDisplay();
        this.renderizarLista(document.getElementById('executor-search')?.value || '');
    },

    // ============================================================
    // ATUALIZAR DISPLAY DOS SELECIONADOS
    // ============================================================
    atualizarDisplay() {
        const displayDiv = document.getElementById('executores-display');
        const infoDiv = document.getElementById('executores-selecionados-info');
        if (!displayDiv || !infoDiv) return;

        if (this.selectedExecutoresMap.size === 0) {
            displayDiv.innerHTML = '<span class="placeholder">Selecione os executores...</span>';
            infoDiv.innerHTML = `
                <i class="fas fa-info-circle" style="color: #ffc107;"></i>
                Nenhum executor selecionado
            `;
        } else {
            let badgesHtml = '';
            this.selectedExecutoresMap.forEach((executor, id) => {
                badgesHtml += `
                    <span class="selected-badge">
                        ${escapeHtml(executor.nome)}
                        <span class="remove-badge" onclick="event.stopPropagation(); ExecutoresModule.toggle(${id})">&times;</span>
                    </span>
                `;
            });
            displayDiv.innerHTML = badgesHtml;

            const nomes = Array.from(this.selectedExecutoresMap.values()).map(e => e.nome).join(', ');
            infoDiv.innerHTML = `
                <i class="fas fa-check-circle" style="color: #28a745;"></i>
                <strong>${this.selectedExecutoresMap.size} executor(es) selecionado(s):</strong> ${nomes}
            `;
        }
    },

    // ============================================================
    // DROPDOWN TOGGLE
    // ============================================================
    toggleDropdown() {
        const dropdown = document.getElementById('executores-dropdown');
        if (!dropdown) return;

        if (dropdown.style.display === 'block') {
            dropdown.style.display = 'none';
        } else {
            dropdown.style.display = 'flex';
            const searchInput = document.getElementById('executor-search');
            if (searchInput) searchInput.focus();
            this.renderizarLista('');
        }
    },

    // ============================================================
    // SETUP SEARCH
    // ============================================================
    setupSearch() {
        const searchInput = document.getElementById('executor-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.renderizarLista(e.target.value);
            });
        }
    },

    // ============================================================
    // SETUP CLICK FORA
    // ============================================================
    setupClickFora() {
        document.addEventListener('click', (event) => {
            const selector = document.querySelector('.executores-selector');
            const dropdown = document.getElementById('executores-dropdown');
            if (selector && dropdown && !selector.contains(event.target)) {
                dropdown.style.display = 'none';
            }
        });
    },

    // ============================================================
    // GETTERS / SETTERS
    // ============================================================
    getSelectedIds() {
        return Array.from(this.selectedExecutoresMap.keys());
    },

    limpar() {
        this.selectedExecutoresMap.clear();
        this.atualizarDisplay();
        this.renderizarLista('');
    },

    carregarSalvos(executoresIdsString) {
        if (!executoresIdsString || executoresIdsString.trim() === '') return;
        const ids = executoresIdsString.split(',');
        ids.forEach(id => {
            const executor = this.todosExecutoresLista.find(e => String(e.id) === String(id.trim()));
            if (executor && !this.selectedExecutoresMap.has(String(executor.id))) {
                this.selectedExecutoresMap.set(String(executor.id), executor);
            }
        });
        this.atualizarDisplay();
    },

    // ============================================================
    // NOMES DOS EXECUTORES (COM CACHE)
    // ============================================================
    async getNomes(executoresIdsString) {
        if (!executoresIdsString || executoresIdsString.trim() === '') return '-';
        const ids = executoresIdsString.split(',');
        const nomes = [];

        for (const id of ids) {
            const idTrimmed = id.trim();
            if (this.nomeFuncionariosCache.has(idTrimmed)) {
                nomes.push(this.nomeFuncionariosCache.get(idTrimmed));
            } else {
                try {
                    const response = await window.fetchComAutenticacao(`/api/funcionario/${idTrimmed}`);
                    if (response.ok) {
                        const data = await response.json();
                        const nome = data.nome_funcionario;
                        this.nomeFuncionariosCache.set(idTrimmed, nome);
                        nomes.push(nome);
                    } else {
                        nomes.push(`ID: ${idTrimmed}`);
                    }
                } catch (error) {
                    nomes.push(`ID: ${idTrimmed}`);
                }
            }
        }
        return nomes.join(', ');
    }

};