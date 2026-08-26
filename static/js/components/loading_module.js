// ============================================================
// LoadingModule.js
// Descrição: Gerencia indicadores de carregamento visual
// ============================================================

const LoadingModule = (() => {
    // ============================================================
    // VARIÁVEIS PRIVADAS
    // ============================================================
    
    let overlay = null;
    let loadingCount = 0;
    
    // ============================================================
    // FUNÇÕES PRIVADAS
    // ============================================================
    
    function criarOverlay() {
        if (overlay) return;
        
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 999999;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        
        overlay.innerHTML = `
            <div style="
                background: white;
                padding: 40px 50px;
                border-radius: 20px;
                text-align: center;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            ">
                <div class="dot-spinner">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <p style="
                    margin-top: 25px;
                    color: #666;
                    font-size: 14px;
                    font-weight: 500;
                ">Carregando...</p>
            </div>
        `;
        
        document.body.appendChild(overlay);
    }
    
    function atualizarMensagem(mensagem) {
        if (!overlay) return;
        
        const msgElement = overlay.querySelector('p');
        if (msgElement && mensagem) {
            msgElement.textContent = mensagem;
        }
    }
    
    function mostrarComMensagem(mensagem) {
        criarOverlay();
        atualizarMensagem(mensagem);
        
        loadingCount++;
        overlay.style.display = 'flex';
        void overlay.offsetWidth;
        overlay.style.opacity = '1';
        
        console.log('🔄 Loading exibido:', mensagem || 'Carregando...');
    }
    
    function esconder() {
        loadingCount = Math.max(0, loadingCount - 1);
        
        if (loadingCount === 0 && overlay) {
            overlay.style.opacity = '0';
            
            setTimeout(() => {
                overlay.style.display = 'none';
            }, 300);
            
            console.log('✅ Loading escondido');
        }
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('📌 LoadingModule inicializado');
        criarOverlay();
    }
    
    function mostrar(mensagem) {
        mostrarComMensagem(mensagem);
    }
    
    function ocultar() {
        esconder();
    }
    
    async function executarComLoading(funcao, mensagem) {
        try {
            mostrar(mensagem);
            return await funcao();
        } finally {
            ocultar();
        }
    }
    
    // ============================================================
    // RETORNO PÚBLICO
    // ============================================================
    
    return {
        init: init,
        mostrar: mostrar,
        ocultar: ocultar,
        executarComLoading: executarComLoading
    };
})();