// ============================================================
// main.js - ORQUESTRADOR PRINCIPAL
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    
    console.log('🚀 Diagnóstico iniciando...');
    
    if (typeof FiltrosModule !== 'undefined') {
        FiltrosModule.init();
        console.log('   ✅ FiltrosModule inicializado');
    } else {
        console.warn('   ⚠️ FiltrosModule não encontrado');
    }
    
    if (typeof TabelaModule !== 'undefined') {
        TabelaModule.init();
        console.log('   ✅ TabelaModule inicializado');
    } else {
        console.warn('   ⚠️ TabelaModule não encontrado');
    }
    
    if (typeof ModaisModule !== 'undefined') {
        ModaisModule.init();
        console.log('   ✅ ModaisModule inicializado');
    }
    
    if (typeof WizardModule !== 'undefined') {
        WizardModule.init();
        console.log('   ✅ WizardModule inicializado');
    }
    
});