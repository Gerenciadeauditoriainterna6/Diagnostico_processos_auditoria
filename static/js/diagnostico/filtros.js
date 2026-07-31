// ============================================================
// filtros.js - MÓDULO DE FILTROS (Área e Auditoria)
// 
// Responsabilidade:
// - Gerenciar os selects de Área e Auditoria
// - Quando a área muda, carregar as auditorias
// - Avisar o TabelaModule quando os filtros mudam
// ============================================================

const FiltrosModule = {
    
    // Elementos do DOM (preenchidos no init)
    areaSelect: null,
    auditoriaSelect: null,
    
    // ============================================================
    // INICIALIZAÇÃO
    // ============================================================
    init: function() {
        console.log('📌 FiltrosModule: inicializando...');
        
        // Pega os elementos do DOM
        this.areaSelect = document.getElementById('filtro_area_select');
        this.auditoriaSelect = document.getElementById('filtro_auditoria_select');
        
        // Verifica se os elementos existem
        if (!this.areaSelect) {
            console.warn('⚠️ FiltrosModule: select de área não encontrado');
            return;
        }
        
        if (!this.auditoriaSelect) {
            console.warn('⚠️ FiltrosModule: select de auditoria não encontrado');
            return;
        }
        
        // Configura o evento de mudança da área
        this.areaSelect.addEventListener('change', () => {
            this.aoMudarArea();
        });
        
        // Configura o evento de mudança da auditoria
        this.auditoriaSelect.addEventListener('change', () => {
            this.aoMudarAuditoria();
        });
        
        console.log('✅ FiltrosModule: inicializado');
    },
    
    // ============================================================
    // GETTERS (Retornam os valores atuais dos filtros)
    // ============================================================
    
    getAreaId: function() {
        return this.areaSelect ? this.areaSelect.value : null;
    },
    
    getAuditoriaId: function() {
        return this.auditoriaSelect ? this.auditoriaSelect.value : null;
    },
    
    getAreaNome: function() {
        if (!this.areaSelect || !this.areaSelect.value) return null;
        return this.areaSelect.options[this.areaSelect.selectedIndex].text;
    },
    
    // ============================================================
    // EVENTOS
    // ============================================================
    
    aoMudarArea: async function() {
        const areaId = this.getAreaId();
        
        console.log(`🔍 FiltrosModule: Área mudou para ID ${areaId}`);
        
        // Limpa e desabilita o select de auditoria
        this.auditoriaSelect.innerHTML = '<option value="">Carregando...</option>';
        this.auditoriaSelect.disabled = true;
        
        if (!areaId) {
            // Nenhuma área selecionada
            this.auditoriaSelect.innerHTML = '<option value="">Selecione uma área primeiro...</option>';
            return;
        }
        
        try {
            // Busca as auditorias da área
            const response = await window.fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
            
            if (!response || !response.ok) {
                throw new Error('Erro ao carregar auditorias');
            }
            
            const data = await response.json();
            
            // Preenche o select de auditorias
            this.auditoriaSelect.innerHTML = '<option value="">Todas as auditorias</option>';
            
            // ✅ Corrigido:
            if (data.auditorias && data.auditorias.length > 0) {
                data.auditorias.forEach(aud => {
                    const option = document.createElement('option');
                    option.value = aud.id;
                    option.textContent = `${aud.codigo_auditoria || ''} - ${aud.titulo || ''}`.trim() || `Auditoria ${aud.id}`;
                    this.auditoriaSelect.appendChild(option);
                });
            }
            
            this.auditoriaSelect.disabled = false;
            
            // Carrega a tabela com TODOS os processos desta área
            if (typeof TabelaModule !== 'undefined') {
                TabelaModule.carregarProcessos(areaId);
            }
            
        } catch (error) {
            console.error('❌ FiltrosModule: erro ao carregar auditorias', error);
            this.auditoriaSelect.innerHTML = '<option value="">Erro ao carregar</option>';
        }
    },
    
    aoMudarAuditoria: function() {
        const areaId = this.getAreaId();
        const auditoriaId = this.getAuditoriaId();
        
        console.log(`🔍 FiltrosModule: Auditoria mudou para ID ${auditoriaId}`);
        
        if (!areaId) return;
        
        // Carrega a tabela com os processos filtrados
        if (typeof TabelaModule !== 'undefined') {
            TabelaModule.carregarProcessos(areaId, auditoriaId || null);
        }
    }
    
};