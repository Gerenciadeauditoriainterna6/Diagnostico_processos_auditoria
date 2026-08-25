// ============================================================
// OrientacaoModule.js
// Descrição: Gerencia cards de orientação (retrato/paisagem)
// ============================================================

const OrientacaoModule = (() => {
    // ============================================================
    // VARIÁVEIS PRIVADAS
    // ============================================================
    
    let cards = [];
    
    // ============================================================
    // FUNÇÕES PRIVADAS
    // ============================================================
    
    function configurarEventos() {
        console.log('🔄 Configurando eventos dos cards de orientação');
        console.log('   Cards encontrados:', cards.length);
        
        cards.forEach((card, index) => {
            console.log(`   Card ${index}:`, card.dataset.orientacao);
            
            card.addEventListener('click', () => {
                console.log('👆 Card clicado:', card.dataset.orientacao);
                
                const radio = card.querySelector('input[type="radio"]');
                
                if (radio) {
                    // Marcar o radio button
                    radio.checked = true;
                    console.log('✅ Radio marcado:', radio.value);
                    
                    // Atualizar classes visuais
                    cards.forEach(c => {
                        c.classList.remove('active');
                    });
                    card.classList.add('active');
                    console.log('✅ Classe active adicionada ao card');
                } else {
                    console.error('❌ Radio button não encontrado no card');
                }
            });
        });
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('📌 OrientacaoModule inicializado');
        
        // Buscar todos os cards de orientação
        cards = document.querySelectorAll('.orientacao-card');
        
        console.log('   Cards encontrados:', cards.length);
        
        if (cards.length === 0) {
            console.warn('⚠️ Nenhum card de orientação encontrado');
            return;
        }
        
        // Configurar eventos
        configurarEventos();
    }
    
    function getOrientacaoSelecionada() {
        const radioSelecionado = document.querySelector('input[name="orientacao"]:checked');
        const orientacao = radioSelecionado?.value || 'RETRATO';
        
        console.log('🔄 Orientação atual:', orientacao);
        return orientacao;
    }
    
    // ============================================================
    // RETORNO PÚBLICO
    // ============================================================
    
    return {
        init: init,
        getOrientacaoSelecionada: getOrientacaoSelecionada
    };
})();