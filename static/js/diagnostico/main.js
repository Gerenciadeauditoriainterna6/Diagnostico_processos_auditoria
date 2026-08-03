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

    if (typeof Etapa1Module !== 'undefined') {
        Etapa1Module.init();
        console.log('   ✅ Etapa1Module inicializado');
    }

    if (typeof Etapa2Module !== 'undefined') {
        Etapa2Module.init();
        console.log('   ✅ Etapa2Module inicializado');
    }

    if (typeof Etapa3Module !== 'undefined') {
        Etapa3Module.init();
        console.log('   ✅ Etapa3Module inicializado');
    }
    
});