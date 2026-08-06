// ============================================================
// risco_modal.js - COMPONENTE REUTILIZÁVEL: Modal de Risco
// 
// Pode ser usado em qualquer tela:
// - Diagnóstico de processos
// - Riscos das etapas
// - Qualquer lugar que precise cadastrar riscos
// ============================================================

const RiscoModal = {
    
    // Configuração (cada tela define a sua)
    config: {
        onSave: null,        // Função chamada ao salvar: onSave(dadosDoRisco)
        onClose: null,       // Função chamada ao fechar: onClose()
        getObjetivo: null,   // Função que retorna o objetivo do processo
        getProcessoId: null, // Função que retorna o ID do processo
    },
    
    outrasCategoriasRisco: [],
    outrasCategoriasCausa: [],
    
    // ============================================================
    // INICIALIZAÇÃO
    // ============================================================
    init(config = {}) {
        this.config = { ...this.config, ...config };
        this.configurarEventos();
    },
    
    configurarEventos() {
        // Fechar (X)
        document.getElementById('btn-fechar-modal')?.addEventListener('click', () => this.fechar());
        
        // Cancelar
        document.getElementById('btn-cancelar-modal')?.addEventListener('click', () => this.fechar());
        
        // Salvar
        document.getElementById('btn-salvar-modal')?.addEventListener('click', () => this.salvar());
        
        // Scores
        document.getElementById('modal-impacto')?.addEventListener('change', () => this.atualizarScorePreview());
        document.getElementById('modal-probabilidade')?.addEventListener('change', () => this.atualizarScorePreview());
        document.getElementById('apetite_impacto')?.addEventListener('change', () => this.atualizarScorePreview());
        document.getElementById('apetite_probabilidade')?.addEventListener('change', () => this.atualizarScorePreview());
        
        // Checkbox "Outra" - Categoria Risco
        document.getElementById('check-outra-categoria-risco')?.addEventListener('change', function() {
            document.getElementById('outra-categoria-risco-container').style.display = this.checked ? 'block' : 'none';
        });
        
        // Checkbox "Outra" - Categoria Causa
        document.getElementById('check-outra-categoria-causa')?.addEventListener('change', function() {
            document.getElementById('outra-categoria-causa-container').style.display = this.checked ? 'block' : 'none';
        });
        
        // Botão + Outra Risco
        document.getElementById('btn-adicionar-outra-risco')?.addEventListener('click', () => {
            const texto = document.getElementById('outra-categoria-risco-texto').value.trim();
            if (texto) {
                this.outrasCategoriasRisco.push(texto.toUpperCase());
                this.renderizarOutrasCategorias('risco');
                document.getElementById('outra-categoria-risco-texto').value = '';
            }
        });
        
        // Botão + Outra Causa
        document.getElementById('btn-adicionar-outra-causa')?.addEventListener('click', () => {
            const texto = document.getElementById('outra-categoria-causa-texto').value.trim();
            if (texto) {
                this.outrasCategoriasCausa.push(texto.toUpperCase());
                this.renderizarOutrasCategorias('causa');
                document.getElementById('outra-categoria-causa-texto').value = '';
            }
        });
    },
    
    // ============================================================
    // ABRIR / FECHAR
    // ============================================================
    abrir(riscoData = null) {
        if (riscoData) {
            this.preencherFormulario(riscoData);
            document.getElementById('modal-title').innerHTML = '<i class="fas fa-shield-alt"></i> Editar Risco';
        } else {
            this.limparFormulario();
            document.getElementById('modal-title').innerHTML = '<i class="fas fa-shield-alt"></i> Novo Risco';
        }
        
        // Objetivo
        const objetivo = this.config.getObjetivo ? this.config.getObjetivo() : '';
        document.getElementById('modal-objetivo-texto').textContent = objetivo || '-';
        
        document.getElementById('modal-risco').style.display = 'flex';
    },
    
    fechar() {
        document.getElementById('modal-risco').style.display = 'none';
        if (this.config.onClose) this.config.onClose();
    },
    
    // ============================================================
    // FORMULÁRIO
    // ============================================================
    limparFormulario() {
        document.getElementById('modal-risco-idx').value = '';
        document.getElementById('modal-nome_risco').value = '';
        document.getElementById('modal-fator_risco').value = '';
        document.getElementById('modal-melhoria').value = '';
        document.getElementById('modal-impacto').value = '';
        document.getElementById('modal-probabilidade').value = '';
        document.getElementById('modal-motivo_risco').value = '';
        document.getElementById('modal-como-tratar').value = '';
        document.getElementById('modal-desc-tratamento').value = '';
        document.getElementById('modal-prazo-implantacao').value = '';
        document.getElementById('apetite_impacto').value = '';
        document.getElementById('apetite_probabilidade').value = '';
        document.getElementById('modal-score-preview').innerHTML = '<strong>Risco Bruto:</strong> Selecione impacto e probabilidade';
        document.getElementById('apetite-score-preview').innerHTML = '<strong>Apetite ao Risco:</strong> Selecione impacto e probabilidade aceitável';
        
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
        document.querySelectorAll('#causa-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
        
        this.outrasCategoriasRisco = [];
        this.outrasCategoriasCausa = [];
        document.getElementById('outras-categorias-risco-lista').innerHTML = '';
        document.getElementById('outras-categorias-causa-lista').innerHTML = '';
        document.getElementById('outra-categoria-risco-container').style.display = 'none';
        document.getElementById('outra-categoria-causa-container').style.display = 'none';
    },
    
    // ============================================================
    // SALVAR
    // ============================================================
    salvar() {
        const nomeRisco = document.getElementById('modal-nome_risco').value.trim();
        if (!nomeRisco) {
            window.mostrarToast('⚠️ Informe o nome do risco!', 'warning');
            return;
        }
        
        // Coletar categorias
        const categorias = [];
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]:checked').forEach(cb => {
            if (cb.value !== 'OUTRA') categorias.push(cb.value);
        });
        if (document.getElementById('check-outra-categoria-risco')?.checked) {
            this.outrasCategoriasRisco.forEach(cat => categorias.push(cat));
        }
        
        // Coletar causas
        const causas = [];
        document.querySelectorAll('#causa-checkboxes input[type="checkbox"]:checked').forEach(cb => {
            if (cb.value !== 'OUTRA') causas.push(cb.value);
        });
        if (document.getElementById('check-outra-categoria-causa')?.checked) {
            this.outrasCategoriasCausa.forEach(cat => causas.push(cat));
        }
        
        const riscoId = document.getElementById('modal-risco-idx').value;
        
        const dados = {
            processo_id: this.config.getProcessoId ? this.config.getProcessoId() : null,
            nome_risco: nomeRisco,
            fator_risco: document.getElementById('modal-fator_risco').value.trim(),
            melhoria: document.getElementById('modal-melhoria').value.trim(),
            impacto: document.getElementById('modal-impacto').value,
            probabilidade: document.getElementById('modal-probabilidade').value,
            motivo_risco: document.getElementById('modal-motivo_risco').value.trim(),
            categorias: categorias,
            categoria_causa: causas,
            como_tratar: document.getElementById('modal-como-tratar').value,
            desc_tratamento: document.getElementById('modal-desc-tratamento').value.trim(),
            prazo_implantacao: document.getElementById('modal-prazo-implantacao').value.trim(),
            apetite_impacto: document.getElementById('apetite_impacto').value,
            apetite_probabilidade: document.getElementById('apetite_probabilidade').value
        };
        
        if (riscoId) dados.id = parseInt(riscoId);
        
        // Chamar callback de salvamento
        if (this.config.onSave) {
            this.config.onSave(dados);
        }
        
        console.log('📤 Dados do risco:', dados);
    },
    
    // ============================================================
    // PREENCHER (EDIÇÃO)
    // ============================================================
    preencherFormulario(risco) {
        document.getElementById('modal-risco-idx').value = risco.id || '';
        document.getElementById('modal-nome_risco').value = risco.nome_risco || '';
        document.getElementById('modal-fator_risco').value = risco.fator_risco || '';
        document.getElementById('modal-melhoria').value = risco.melhoria || '';
        document.getElementById('modal-impacto').value = risco.impacto || '';
        document.getElementById('modal-probabilidade').value = risco.probabilidade || '';
        document.getElementById('modal-motivo_risco').value = risco.motivo_risco || '';
        document.getElementById('modal-desc-tratamento').value = risco.desc_tratamento || '';
        document.getElementById('modal-prazo-implantacao').value = risco.prazo_implantacao || '';
        document.getElementById('apetite_impacto').value = risco.apetite_impacto || '';
        document.getElementById('apetite_probabilidade').value = risco.apetite_probabilidade || '';
        
        // Tratamento
        const mapaTratamento = {
            'ACEITAR': 'Aceitar', 'MITIGAR': 'Mitigar',
            'COMPARTILHAR': 'Compartilhar', 'COMPARTILHAR (TRANSFERIR)': 'Compartilhar',
            'EVITAR': 'Evitar'
        };
        document.getElementById('modal-como-tratar').value = mapaTratamento[(risco.como_tratar || '').toUpperCase()] || '';
        
        // Categorias (checkboxes + outras)
        const categoriasSalvas = risco.categorias || [];
        const categoriasCheckbox = ['Risco Financeiro', 'Risco Legal', 'Risco Inerente', 'Risco de TI', 'Risco Reputacional', 'Risco de Integridade', 'Risco Ambiental'];
        
        this.outrasCategoriasRisco = [];
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => {
            if (cb.value === 'OUTRA') {
                const extras = categoriasSalvas.filter(c => !categoriasCheckbox.some(f => f.toUpperCase() === c.toUpperCase()));
                cb.checked = extras.length > 0;
                this.outrasCategoriasRisco = extras;
            } else {
                cb.checked = categoriasSalvas.some(c => c.toUpperCase() === cb.value.toUpperCase());
            }
        });
        
        if (this.outrasCategoriasRisco.length > 0) {
            document.getElementById('outra-categoria-risco-container').style.display = 'block';
            this.renderizarOutrasCategorias('risco');
        }
        
        // Causas (checkboxes + outras)
        const causasSalvas = risco.categoria_causa || [];
        const causasCheckbox = ['FALHA OPERACIONAL', 'FALTA DE CONTROLE', 'NÃO CONFORMIDADE', 'PROBLEMAS FINANCEIROS', 'FENÔMENO NATURAL', 'FRAUDE'];
        
        this.outrasCategoriasCausa = [];
        document.querySelectorAll('#causa-checkboxes input[type="checkbox"]').forEach(cb => {
            if (cb.value === 'OUTRA') {
                const extras = causasSalvas.filter(c => !causasCheckbox.some(f => f.toUpperCase() === c.toUpperCase()));
                cb.checked = extras.length > 0;
                this.outrasCategoriasCausa = extras;
            } else {
                cb.checked = causasSalvas.some(c => c.toUpperCase() === cb.value.toUpperCase());
            }
        });
        
        if (this.outrasCategoriasCausa.length > 0) {
            document.getElementById('outra-categoria-causa-container').style.display = 'block';
            this.renderizarOutrasCategorias('causa');
        }
        
        this.atualizarScorePreview();
    },
    
    // ============================================================
    // SCORE
    // ============================================================
    atualizarScorePreview() {
        const impacto = document.getElementById('modal-impacto').value;
        const probabilidade = document.getElementById('modal-probabilidade').value;
        const apetiteImpacto = document.getElementById('apetite_impacto').value;
        const apetiteProbabilidade = document.getElementById('apetite_probabilidade').value;
        
        const mapa = {
            "MUITO ALTO,MUITO ALTO": 15, "ALTO,MUITO ALTO": 14,
            "MÉDIO,MUITO ALTO": 13, "BAIXO,MUITO ALTO": 12,
            "MUITO ALTO,ALTO": 11, "ALTO,ALTO": 10,
            "MÉDIO,ALTO": 9, "BAIXO,ALTO": 8,
            "MUITO ALTO,MÉDIO": 7, "ALTO,MÉDIO": 6,
            "MÉDIO,MÉDIO": 5, "BAIXO,MÉDIO": 4,
            "MUITO ALTO,BAIXO": 3, "ALTO,BAIXO": 2,
            "MÉDIO,BAIXO": 1, "BAIXO,BAIXO": 0
        };
        
        const preview = document.getElementById('modal-score-preview');
        const apetitePreview = document.getElementById('apetite-score-preview');
        
        if (!impacto || !probabilidade) {
            preview.innerHTML = '<strong>Risco Bruto:</strong> Selecione impacto e probabilidade';
        } else {
            preview.innerHTML = `<strong>Risco Bruto: ${mapa[`${impacto},${probabilidade}`] || 0}</strong>`;
        }
        
        if (!apetiteImpacto || !apetiteProbabilidade) {
            apetitePreview.innerHTML = '<strong>Risco Residual:</strong> Selecione o apetite';
        } else {
            apetitePreview.innerHTML = `<strong>Risco Residual: ${mapa[`${apetiteImpacto},${apetiteProbabilidade}`] || 0}</strong>`;
        }
    },
    
    // ============================================================
    // CATEGORIAS "OUTRA"
    // ============================================================
    renderizarOutrasCategorias(tipo) {
        const listaId = tipo === 'risco' ? 'outras-categorias-risco-lista' : 'outras-categorias-causa-lista';
        const lista = tipo === 'risco' ? this.outrasCategoriasRisco : this.outrasCategoriasCausa;
        const container = document.getElementById(listaId);
        if (!container) return;
        
        container.innerHTML = lista.map((cat, index) => `
            <span style="background:#e8f4f8; padding:4px 10px; border-radius:15px; font-size:12px;">
                ${cat}
                <button type="button" style="background:none; border:none; cursor:pointer; color:#dc3545;"
                    onclick="RiscoModal.removerOutraCategoria('${tipo}', ${index})">&times;</button>
            </span>
        `).join('');
    },
    
    removerOutraCategoria(tipo, index) {
        if (tipo === 'risco') this.outrasCategoriasRisco.splice(index, 1);
        else this.outrasCategoriasCausa.splice(index, 1);
        this.renderizarOutrasCategorias(tipo);
    }
    
};