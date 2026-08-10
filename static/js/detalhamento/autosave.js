// ============================================================
// autosave.js - MÓDULO DE AUTOSAVE
// ============================================================

const AutoSaveModule = {

    timer: null,
    enabled: true,
    indicator: null,

    init() {
        console.log('📌 AutoSaveModule: inicializado');
        this._injectCSS();
    },

    // ============================================================
    // SALVAR RASCUNHO
    // ============================================================
    salvarRascunho() {
        if (!this.enabled) return;

        const nomeEtapa = document.getElementById('modal-nome-etapa')?.value?.trim() || '';
        if (!nomeEtapa && !document.getElementById('modal-descricao-etapa')?.value) return;

        const rascunho = {
            id: document.getElementById('modal-etapa-id')?.value || '',
            codigo_etapa: document.getElementById('modal-codigo-etapa')?.value || '',
            nome_etapa: nomeEtapa,
            descricao_etapa: document.getElementById('modal-descricao-etapa')?.value || '',
            como_e_feito: document.getElementById('modal-como-feito')?.value || '',
            objetivo_etapa: document.getElementById('modal-objetivo-etapa')?.value || '',
            status_etapa: document.getElementById('modal-status-etapa')?.value || 'ATIVA',
            politica_interna: document.getElementById('modal-politica-interna')?.value || '',
            timestamp: Date.now()
        };

        try {
            localStorage.setItem(this._getKey(), JSON.stringify(rascunho));
            this._mostrarIndicador();
        } catch (error) {
            console.error('Erro ao salvar rascunho:', error);
        }
    },

    // ============================================================
    // CARREGAR RASCUNHO
    // ============================================================
    carregarRascunho() {
        const key = this._getKey();
        const salvo = localStorage.getItem(key);
        if (!salvo) return;

        try {
            const rascunho = JSON.parse(salvo);
            const diffMin = (Date.now() - rascunho.timestamp) / 1000 / 60;
            if (diffMin > 30 || !rascunho.nome_etapa) {
                localStorage.removeItem(key);
                return;
            }
            if (confirm('⚠️ Rascunho encontrado. Restaurar?')) {
                this._restaurar(rascunho);
                window.mostrarToast('📋 Rascunho restaurado!', 'info');
            } else {
                localStorage.removeItem(key);
            }
        } catch (error) {
            console.error('Erro ao carregar rascunho:', error);
        }
    },

    // ============================================================
    // LIMPAR RASCUNHO
    // ============================================================
    limparRascunho() {
        localStorage.removeItem(this._getKey());
    },

    // ============================================================
    // HABILITAR / DESABILITAR
    // ============================================================
    habilitar() { this.enabled = true; },
    desabilitar() { this.enabled = false; },

    // ============================================================
    // TEM RASCUNHO?
    // ============================================================
    temRascunho() {
        const key = this._getKey();
        const salvo = localStorage.getItem(key);
        if (!salvo) return false;
        try {
            const r = JSON.parse(salvo);
            return !!r.nome_etapa;
        } catch { return false; }
    },

    // ============================================================
    // SETUP (configurar listeners nos campos)
    // ============================================================
    setup() {
        const campos = ['modal-nome-etapa', 'modal-descricao-etapa', 'modal-como-feito',
                        'modal-objetivo-etapa', 'modal-status-etapa', 'modal-politica-interna'];
        campos.forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.removeEventListener('input', this._handler);
                el.addEventListener('input', () => this._debounce());
            }
        });
    },

    // ============================================================
    // PRIVADOS
    // ============================================================
    _debounce() {
        if (this.timer) clearTimeout(this.timer);
        this.timer = setTimeout(() => this.salvarRascunho(), 1000);
    },

    _getKey() {
        const etapaId = document.getElementById('modal-etapa-id')?.value || '';
        const processoId = (typeof TabelaEtapasModule !== 'undefined') ? TabelaEtapasModule.processoAtualId : 'sem_processo';
        return `autosave_etapa_${processoId}_${etapaId || 'nova'}`;
    },

    _restaurar(rascunho) {
        const campos = {
            'modal-nome-etapa': rascunho.nome_etapa,
            'modal-descricao-etapa': rascunho.descricao_etapa,
            'modal-como-feito': rascunho.como_e_feito,
            'modal-objetivo-etapa': rascunho.objetivo_etapa,
            'modal-politica-interna': rascunho.politica_interna
        };
        Object.keys(campos).forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = campos[id] || '';
        });
        const statusEl = document.getElementById('modal-status-etapa');
        if (statusEl) statusEl.value = rascunho.status_etapa || 'ATIVA';
    },

    _mostrarIndicador() {
        if (this.indicator) this.indicator.remove();
        this.indicator = document.createElement('div');
        this.indicator.className = 'autosave-indicator';
        this.indicator.innerHTML = '<i class="fas fa-save"></i> Rascunho salvo';
        this.indicator.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#28a745;color:white;padding:8px 16px;border-radius:20px;font-size:12px;z-index:10001;box-shadow:0 2px 8px rgba(0,0,0,0.2);';
        document.body.appendChild(this.indicator);
        setTimeout(() => {
            if (this.indicator) {
                this.indicator.remove();
                this.indicator = null;
            }
        }, 2000);
    },

    _injectCSS() {
        if (document.getElementById('autosave-css')) return;
        const style = document.createElement('style');
        style.id = 'autosave-css';
        style.textContent = `
            @keyframes fadeInOut {
                0% { opacity: 0; transform: translateY(20px); }
                15% { opacity: 1; transform: translateY(0); }
                85% { opacity: 1; transform: translateY(0); }
                100% { opacity: 0; transform: translateY(-20px); }
            }
            @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
        `;
        document.head.appendChild(style);
    }

};