// ============================================================
// etapa1_auditoria.js - MÓDULO DA ETAPA 1 (Vincular à Auditoria)
// 
// Responsabilidade:
// - Gerenciar selects de Área e Auditoria DENTRO do wizard
// - Se edição: preencher automaticamente
// - Habilitar botão "Próximo"
// ============================================================

const Etapa1Module = {
    
    // Elementos do DOM
    areaSelect: null,
    auditoriaSelect: null,
    btnProximo: null,
    auditoriaInner: null,
    idAreaSelecionado: null,

    // ============================================================
    // INICIALIZAÇÃO
    // ============================================================

    init() {
        console.log('📌 Etapa1Module: inicializando...');

        this.areaSelect = document.getElementById('area_select');
        this.auditoriaSelect = document.getElementById('auditoria_select');
        this.btnProximo = document.getElementById('btn-proximo-etapa2');
        this.auditoriaInner = document.getElementById('auditoria-inner');
        this.idAreaSelecionado = document.getElementById('id_area_selecionado');

        if (!this.areaSelect || !this.auditoriaSelect) {
            console.warn('⚠️ Etapa1Module: elementos não encontrados');
            return;
        }

        this.configurarEventos();
        console.log('✅ Etapa1Module: inicializado');
    },

    // ============================================================
    // CONFIGURAR EVENTOS
    // ============================================================
    configurarEventos() {
        // Quando mudar a área
        this.areaSelect.addEventListener('change', () => {
            this.aoMudarArea();
        });

        // Quando mudar a auditoria
        this.auditoriaSelect.addEventListener('change', () => {
            this.verificarHabilitarProximo();
        });

        // Botão Próximo
        if (this.btnProximo) {
            this.btnProximo.addEventListener('click', () => {
                this.avancar();
            });
        }
    },

    // ============================================================
    // QUANDO A ETAPA FOR ATIVADA
    // ============================================================
    aoEntrar() {
        console.log('👋 Etapa 1 ativada'); 
        
        if (WizardModule.isEdicao()) {
            this.carregarDadosEdicao();
        } else {
            this.resetar();
        }
    },

    // ============================================================
    // MODO EDIÇÃO: CARREGAR DADOS DO PROCESSO
    // ============================================================
    async carregarDadosEdicao() {
        const processoId = WizardModule.getProcessoId();
        console.log(`✏️ Etapa 1: carregando dados do processo ${processoId}`);

        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/dados`);
            const data = await response.json();

            if (data.success) {
                // ⭐ Os dados estão DIRETO em data, não em data.processo!
                this.areaSelect.value = data.id_area;
                this.idAreaSelecionado.value = data.id_area;
                await this.carregarAuditorias(data.id_area);
                this.auditoriaSelect.value = data.auditoria_id;
                this.verificarHabilitarProximo();
                console.log('✅ Etapa 1: dados carregados');
            }
        } catch (error) {
            console.error('❌ Etapa 1: erro ao carregar dados', error);
        }
    },

    // ============================================================
    // MODO NOVO: RESETAR CAMPOS
    // ============================================================
    resetar() {
        this.areaSelect.value = '';
        this.auditoriaSelect.innerHTML = '<option value="">Selecine uma área primeiro...</option>';
        this.auditoriaSelect.disabled = true;
        this.auditoria.Inner.style.display = 'none';
        this.btnProximo.disabled = true;
    },

    // ============================================================
    // EVENTO: MUDOU A ÁREA
    // ============================================================
    async aoMudarArea() {
        const areaId = this.areaSelect.value;

        // Salva o ID da área para uso nas próximas etapas
        if (this.idAreaSelecionado) {
            this.idAreaSelecionado.value = areaId;
        }

        if (!areaId) {
            this.auditoriaInner.style.display = 'none';
            this.auditoriaSelect.innerHTML = '<option value="">Selecine uma área primeiro...</option>';
            this.auditoriaSelect.disabled = true;
            this.btnProximo.disabled = true;
            return;
        }

        await this.carregarAuditorias(areaId);
    },

    // ============================================================
    // CARREGAR AUDITORIAS
    // ============================================================
    async carregarAuditorias(areaId) {
        this.auditoriaInner.style.display = 'block';
        this.auditoriaSelect.innerHTML = '<option value="">Carregando...</option>';
        this.auditoriaSelect.disabled = true;

        try {
            const response = await window.fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
            const data = await response.json();

            this.auditoriaSelect.innerHTML = '<option value="">Selecione uma auditoria</option>';

            if (data.auditorias && data.auditorias.length > 0) {
                data.auditorias.forEach(aud => {
                    const option = document.createElement('option');
                    option.value = aud.id;
                    option.textContent = `${aud.codigo_auditoria || ''} - ${aud.titulo || ""}`.trim();
                    this.auditoriaSelect.appendChild(option);
                });
            }

            this.auditoriaSelect.disabled = false;
        } catch (error) {
            console.error('❌ Etapa 1: erro ao carregar auditorias', error);
            this.auditoriaSelect.innerHTML = '<option value="">Erro ao carregar</option>';
        }
    },


    // ============================================================
    // VERIFICAR SE PODE AVANÇAR
    // ============================================================
    verificarHabilitarProximo() {
        const areaOk = this.areaSelect.value !== '';
        const auditoriaOk = this.auditoriaSelect.value !== '';

        this.btnProximo.disabled = !(areaOk && auditoriaOk);
    },

    // ============================================================
    // AVANÇAR PARA ETAPA 2
    // ============================================================
    avancar() {
        if (typeof WizardModule !== 'undefined') {
            WizardModule.irParaEtapa(2);
        }
    },

    // ============================================================
    // GETTERS
    // ============================================================
    getAreaId() {
        return this.areaSelect ? this.areaSelect.value : null;
    },
    
    getAuditoriaId() {
        return this.auditoriaSelect ? this.auditoriaSelect.value : null;
    }
}