const AreasModule = (() => {
    // ============================================================
    // VARIÁVEIS PRIVADAS
    // ============================================================
    
    let selectArea = null;
    let areasCarregadas = false;
    
    // ============================================================
    // FUNÇÕES PRIVADAS
    // ============================================================
    
    async function carregarAreas() {
        if (!selectArea) return;
        
        selectArea.innerHTML = '<option value="">Carregando áreas...</option>';
        selectArea.disabled = true;
        
        try {
            const response = await fetchComAutenticacao('/api/relatorios/areas');
            const data = await response.json();
            
            if (data.success && data.areas && data.areas.length > 0) {
                selectArea.innerHTML = '<option value="">Selecione uma área...</option>';
                
                data.areas.forEach(area => {
                    const option = document.createElement('option');
                    option.value = area.id;
                    option.textContent = area.nome;
                    selectArea.appendChild(option);
                });
                
                selectArea.disabled = false;
                areasCarregadas = true;
                
            } else {
                selectArea.innerHTML = '<option value="">Nenhuma área encontrada</option>';
                selectArea.disabled = true;
                areasCarregadas = false;
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar áreas:', error);
            selectArea.innerHTML = '<option value="">Erro ao carregar áreas</option>';
            selectArea.disabled = true;
            areasCarregadas = false;
        }
    }
    
    function configurarEventos() {
        if (!selectArea) return;
        
        selectArea.addEventListener('change', () => {
            const areaId = selectArea.value;
            const btnGerar = document.getElementById('btn-gerar-relatorio');
            const resultadoDiv = document.getElementById('resultado-relatorio');
            
            if (areaId) {
                // ⭐ Carregar auditorias da área selecionada
                if (typeof AuditoriasModule !== 'undefined') {
                    AuditoriasModule.carregarPorArea(areaId);
                }
                
                // Desabilitar botão até selecionar auditoria
                if (btnGerar) btnGerar.disabled = true;
                
                // Ocultar resultado anterior
                if (resultadoDiv) resultadoDiv.style.display = 'none';
                
            } else {
                // Nenhuma área selecionada
                if (typeof AuditoriasModule !== 'undefined') {
                    AuditoriasModule.limparSelecao();
                }
                
                if (btnGerar) btnGerar.disabled = true;
            }
        });
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('📂 Inicializando AreasModule...');
        
        selectArea = document.getElementById('area_relatorio');
        
        if (!selectArea) {
            console.warn('⚠️ Elemento #area_relatorio não encontrado');
            return;
        }
        
        configurarEventos();
        
        return carregarAreas();
    }
    
    function recarregar() {
        return carregarAreas();
    }
    
    function getAreaSelecionada() {
        if (!selectArea) return null;
        
        const areaId = selectArea.value;
        const areaNome = selectArea.options[selectArea.selectedIndex]?.textContent || '';
        
        return {
            id: areaId || null,
            nome: areaNome || null
        };
    }
    
    function getSelectArea() {
        return selectArea;
    }
    
    function temAreasCarregadas() {
        return areasCarregadas;
    }
    
    return {
        init: init,
        recarregar: recarregar,
        getAreaSelecionada: getAreaSelecionada,
        getSelectArea: getSelectArea,
        temAreasCarregadas: temAreasCarregadas
    };
})();