// ============================================================
// OrientacaoModule.js
// Módulo para gerenciar cards de orientação (retrato/paisagem)
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
        cards.forEach(card => {
            card.addEventListener('click', () => {
                const radio = card.querySelector('input[type="radio"]');
                
                if (radio) {
                    // Marcar o radio button
                    radio.checked = true;
                    
                    // Atualizar classes visuais
                    cards.forEach(c => c.classList.remove('active'));
                    card.classList.add('active');
                }
            });
        });
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('🔄 Inicializando OrientacaoModule...');
        
        // Buscar todos os cards de orientação
        cards = document.querySelectorAll('.orientacao-card');
        
        if (cards.length === 0) {
            console.warn('⚠️ Nenhum card de orientação encontrado');
            return;
        }
        
        // Configurar eventos
        configurarEventos();
        
        console.log('✅ OrientacaoModule inicializado');
    }
    
    function getOrientacaoSelecionada() {
        const radioSelecionado = document.querySelector('input[name="orientacao"]:checked');
        return radioSelecionado?.value || 'RETRATO';
    }
    
    function getCards() {
        return cards;
    }
    
    // ============================================================
    // RETORNO PÚBLICO (API do módulo)
    // ============================================================
    
    return {
        init: init,
        getOrientacaoSelecionada: getOrientacaoSelecionada,
        getCards: getCards
    };
})();