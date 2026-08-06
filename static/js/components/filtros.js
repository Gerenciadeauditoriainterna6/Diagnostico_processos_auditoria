// ============================================================
// filtros.js - COMPONENTE REUTILIZÁVEL: Filtros Área/Auditoria
// ============================================================

const FiltrosModule = {
    
    areaSelect: null,
    auditoriaSelect: null,
    onAreaChange: null,     // Callback: function(areaId)
    onAuditoriaChange: null, // Callback: function(auditoriaId)
    
    init(config = {}) {
        this.prefix = config.prefix || 'filtro';
        this.onAreaChange = config.onAreaChange || null;
        this.onAuditoriaChange = config.onAuditoriaChange || null;
        
        this.areaSelect = document.getElementById(`${this.prefix}_area_select`);
        this.auditoriaSelect = document.getElementById(`${this.prefix}_auditoria_select`);
        
        if (!this.areaSelect) return;
        
        this.areaSelect.addEventListener('change', () => this.aoMudarArea());
        this.auditoriaSelect.addEventListener('change', () => this.aoMudarAuditoria());
    },
    
    async aoMudarArea() {
        const areaId = this.areaSelect.value;
        
        this.auditoriaSelect.innerHTML = '<option value="">Carregando...</option>';
        this.auditoriaSelect.disabled = true;
        
        if (!areaId) {
            this.auditoriaSelect.innerHTML = '<option value="">Selecione uma área primeiro...</option>';
            if (this.onAreaChange) this.onAreaChange(null);
            return;
        }
        
        try {
            const response = await window.fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
            const data = await response.json();
            
            this.auditoriaSelect.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            
            if (data.auditorias && data.auditorias.length > 0) {
                data.auditorias.forEach(aud => {
                    const option = document.createElement('option');
                    option.value = aud.id;
                    option.textContent = `${aud.codigo_auditoria || ''} - ${aud.titulo || ''}`.trim();
                    this.auditoriaSelect.appendChild(option);
                });
            }
            
            this.auditoriaSelect.disabled = false;
            
            if (this.onAreaChange) this.onAreaChange(areaId);
            
        } catch (error) {
            this.auditoriaSelect.innerHTML = '<option value="">Erro ao carregar</option>';
        }
    },
    
    aoMudarAuditoria() {
        const auditoriaId = this.auditoriaSelect.value;
        if (this.onAuditoriaChange) this.onAuditoriaChange(auditoriaId || null);
    },
    
    getAreaId() {
        return this.areaSelect?.value || null;
    },
    
    getAuditoriaId() {
        return this.auditoriaSelect?.value || null;
    }
    
};