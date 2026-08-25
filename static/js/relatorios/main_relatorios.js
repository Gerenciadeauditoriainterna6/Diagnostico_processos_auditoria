// ============================================================
// main_relatorios.js - ORQUESTRADOR PRINCIPAL DE RELATÓRIOS
// ============================================================

document.addEventListener('DOMContentLoaded', async function() {
    
    console.log('🚀 Página de relatórios iniciando...');
    
    // Inicializar módulos na ordem correta
    if (typeof PermissoesModule !== 'undefined') {
        PermissoesModule.init();
        console.log('   ✅ PermissoesModule inicializado');
    }
    
    if (typeof AreasModule !== 'undefined') {
        await AreasModule.init();
        console.log('   ✅ AreasModule inicializado');
    }
    
    if (typeof AuditoriasModule !== 'undefined') {
        AuditoriasModule.init();
        console.log('   ✅ AuditoriasModule inicializado');
    }
    
    if (typeof ProcessosModule !== 'undefined') {
        ProcessosModule.init();
        console.log('   ✅ ProcessosModule inicializado');
    }
    
    if (typeof ConclusoesModule !== 'undefined') {
        ConclusoesModule.init();
        console.log('   ✅ ConclusoesModule inicializado');
    }
    
    if (typeof RelatoriosModule !== 'undefined') {
        RelatoriosModule.init();
        console.log('   ✅ RelatoriosModule inicializado');
    }
    
    console.log('✅ Todos os módulos de relatórios inicializados');
});