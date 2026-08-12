// ============================================================
// main.js - DETALHAMENTO
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Página de detalhamento carregada');

    // Inicializar tabela
    DetalhamentoTabelaModule.init();
    
    // Inicializar filtros
    FiltrosModule.init({
        prefix: 'detalhamento',
        onAreaChange: (areaId) => {
            const tabelaContainer = document.getElementById('detalhamento-tabela-container');
            if (tabelaContainer) {
                tabelaContainer.innerHTML = '<div class="alert-info" style="text-align:center;padding:40px;"><i class="fas fa-info-circle"></i> Selecione uma auditoria para visualizar os processos.</div>';
            }
        },
        onAuditoriaChange: (auditoriaId) => {
            if (auditoriaId) {
                DetalhamentoTabelaModule.carregarProcessosDetalhamento(auditoriaId);
            }
        }
    });
    
    // Inicializar BPMN
    if (typeof BpmnModule !== 'undefined') {
        BpmnModule.init();
    }
    
    // Restaurar estado (se existir)
    setTimeout(() => {
        restaurarEstadoDetalhamento();
    }, 500);
});

// ============================================================
// RESTAURAR ESTADO
// ============================================================

function restaurarEstadoDetalhamento() {
    const estadoSalvo = sessionStorage.getItem('detalhamento_estado');
    if (!estadoSalvo) return;

    const estado = JSON.parse(estadoSalvo);
    
    const agora = new Date().getTime();
    const diffMinutes = (agora - estado.timestamp) / 1000 / 60;
    if (diffMinutes > 5) {
        sessionStorage.removeItem('detalhamento_estado');
        return;
    }
    
    // Aguardar o carregamento e setar valores
    setTimeout(() => {
        const selectArea = document.getElementById('detalhamento_area_select');
        if (selectArea && estado.area_id) {
            selectArea.value = estado.area_id;
            selectArea.dispatchEvent(new Event('change', { bubbles: true }));
            
            setTimeout(() => {
                const selectAuditoria = document.getElementById('detalhamento_auditoria_select');
                if (selectAuditoria && estado.auditoria_id) {
                    selectAuditoria.value = estado.auditoria_id;
                    selectAuditoria.dispatchEvent(new Event('change', { bubbles: true }));
                    sessionStorage.removeItem('detalhamento_estado');
                }
            }, 800);
        }
    }, 500);
}