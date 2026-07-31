// ============================================================
// utils.js - FUNÇÕES UTILITÁRIAS COMPARTILHADAS
// ============================================================
// Este módulo NÃO tem `init()` nem elementos de DOM guardados,
// porque ele não "pertence" a nenhuma parte específica da tela —
// é uma caixa de ferramentas que os outros módulos vão chamar.
//
// IMPORTANTE: por isso ele precisa ser o PRIMEIRO <script> carregado
// no HTML, antes de filtros.js, tabela.js, wizard.js, etc.

const UtilsModule = {

    // ============================================================
    // SEGURANÇA: Escapar HTML para prevenir XSS
    // ============================================================
    // Sempre que formos inserir texto vindo do usuário/banco dentro
    // de innerHTML, passamos por aqui primeiro. Isso troca caracteres
    // perigosos (< > " ' &) por suas versões "seguras" em HTML, para
    // que um nome de processo tipo <script>alert(1)</script> vire só
    // texto na tela, e não código executado.
    escapeHtml: function(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    // ============================================================
    // FORMATAÇÃO DE DATA: YYYY-MM-DD -> DD/MM/YYYY
    // ============================================================
    formatarDataParaExibicao: function(dataString) {
        if (!dataString) return '-';
        const partes = dataString.split('-');
        if (partes.length === 3) {
            return `${partes[2]}/${partes[1]}/${partes[0]}`;
        }
        return dataString;
    },

    // ============================================================
    // TOAST DE NOTIFICAÇÃO
    // ============================================================
    // Mostra uma mensagem temporária no canto da tela.
    // tipo: 'success' | 'error' | 'warning' | 'info'
    mostrarToast: function(mensagem, tipo = 'info') {
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 100000000;
            `;
            document.body.appendChild(toastContainer);
        }

        const cores = {
            success: { bg: '#d4edda', border: '#28a745', text: '#155724', icon: '✅' },
            error:   { bg: '#f8d7da', border: '#dc3545', text: '#721c24', icon: '❌' },
            warning: { bg: '#fff3cd', border: '#ffc107', text: '#856404', icon: '⚠️' },
            info:    { bg: '#d1ecf1', border: '#17a2b8', text: '#0c5460', icon: 'ℹ️' }
        };

        const cor = cores[tipo] || cores.info;

        const toast = document.createElement('div');
        toast.className = 'toast-notification';
        toast.style.cssText = `
            background: ${cor.bg};
            border-left: 4px solid ${cor.border};
            color: ${cor.text};
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 8px;
            font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        `;

        // Nota: escapamos a mensagem aqui (o código antigo não fazia isso)
        toast.innerHTML = `
            <span style="font-size: 18px;">${cor.icon}</span>
            <span>${this.escapeHtml(mensagem)}</span>
            <span style="margin-left: auto; cursor: pointer; opacity: 0.7;" onclick="this.parentElement.remove()">✕</span>
        `;

        toastContainer.appendChild(toast);
        this._garantirEstilosToast();

        setTimeout(() => {
            if (toast && toast.parentElement) {
                toast.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        }, 4000);
    },

    // Injeta o CSS das animações do toast (slideIn/slideOut) uma única vez.
    // Função "privada" (começa com _) - é um detalhe interno do módulo,
    // outros arquivos não deveriam chamar isso diretamente.
    _garantirEstilosToast: function() {
        if (document.getElementById('toast-styles')) return;
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    },

    // ============================================================
    // MODAL DE CONFIRMAÇÃO (substitui o confirm() nativo do navegador)
    // ============================================================
    // Uso:
    //   const ok = await UtilsModule.mostrarConfirmacao('Tem certeza?');
    //   if (ok) { ...faz a ação... }
    //
    // Retorna uma Promise<boolean>: true se confirmou, false se cancelou.
    mostrarConfirmacao: function(mensagem) {
        return new Promise((resolve) => {
            let modal = document.getElementById('modalConfirmacao');

            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'modalConfirmacao';
                modal.className = 'modal';
                modal.style.cssText = `
                    position: fixed;
                    top: 0; left: 0; width: 100%; height: 100%;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 100000;
                `;
                modal.innerHTML = `
                    <div class="modal-content" style="max-width: 400px; margin: 0 auto;">
                        <div class="modal-header">
                            <h2><i class="fas fa-question-circle"></i> Confirmar Ação</h2>
                            <button class="modal-close" id="btnFecharConfirmacao" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>
                        </div>
                        <div class="modal-body">
                            <p id="mensagemConfirmacao">Tem certeza que deseja realizar esta ação?</p>
                            <p style="font-size: 12px; color: #666; margin-top: 10px;">Esta ação não poderá ser desfeita.</p>
                            <div class="modal-buttons" style="margin-top: 25px; display: flex; justify-content: flex-end; gap: 10px;">
                                <button type="button" id="btnCancelarConfirmacao" style="background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">Cancelar</button>
                                <button type="button" id="btnConfirmarAcao" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer;">Confirmar</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(modal);
            }

            const modalEl = document.getElementById('modalConfirmacao');
            const mensagemEl = document.getElementById('mensagemConfirmacao');
            const btnConfirmar = document.getElementById('btnConfirmarAcao');
            const btnCancelar = document.getElementById('btnCancelarConfirmacao');
            const btnFechar = document.getElementById('btnFecharConfirmacao');

            mensagemEl.textContent = mensagem;
            modalEl.style.display = 'flex';
            document.body.style.overflow = 'hidden';

            function resolver(valor) {
                modalEl.style.display = 'none';
                document.body.style.overflow = 'auto';
                resolve(valor);
            }

            // Clonar+substituir os botões "limpa" listeners de chamadas
            // anteriores (senão, na 2ª vez que o modal abre, o clique
            // dispararia a Promise antiga E a nova ao mesmo tempo).
            const novoConfirmar = btnConfirmar.cloneNode(true);
            const novoCancelar = btnCancelar.cloneNode(true);
            const novoFechar = btnFechar.cloneNode(true);
            btnConfirmar.replaceWith(novoConfirmar);
            btnCancelar.replaceWith(novoCancelar);
            btnFechar.replaceWith(novoFechar);

            novoConfirmar.onclick = () => resolver(true);
            novoCancelar.onclick = () => resolver(false);
            novoFechar.onclick = () => resolver(false);

            modalEl.onclick = (e) => {
                if (e.target === modalEl) resolver(false);
            };
        });
    },

    // ============================================================
    // CÁLCULO DE SCORE DE RISCO (Impacto x Probabilidade)
    // ============================================================
    // Tabela fixa: cada combinação impacto+probabilidade vale de 0 a 15
    // pontos. É usada tanto para o risco "bruto" quanto para o "apetite"
    // (risco residual, depois do tratamento).
    MAPA_RISCO: {
        "MUITO ALTO_MUITO ALTO": 15, "ALTO_MUITO ALTO": 14, "MÉDIO_MUITO ALTO": 13, "BAIXO_MUITO ALTO": 12,
        "MUITO ALTO_ALTO": 11,       "ALTO_ALTO": 10,       "MÉDIO_ALTO": 9,        "BAIXO_ALTO": 8,
        "MUITO ALTO_MÉDIO": 7,       "ALTO_MÉDIO": 6,       "MÉDIO_MÉDIO": 5,       "BAIXO_MÉDIO": 4,
        "MUITO ALTO_BAIXO": 3,       "ALTO_BAIXO": 2,       "MÉDIO_BAIXO": 1,       "BAIXO_BAIXO": 0
    },

    calcularScoreRisco: function(impacto, probabilidade) {
        const chave = `${impacto.toUpperCase().trim()}_${probabilidade.toUpperCase().trim()}`;
        const score = this.MAPA_RISCO[chave];

        if (score === undefined) {
            console.warn(`⚠️ UtilsModule: combinação não encontrada no mapa: "${chave}"`);
            return 0;
        }
        return score;
    },

    // Nível curto ('low'|'medium'|'high'|'critical') — usado como classe CSS
    getScoreLevel: function(score) {
        if (score <= 3) return 'low';
        if (score <= 7) return 'medium';
        if (score <= 11) return 'high';
        return 'critical';
    },

    // Texto amigável do nível, para mostrar ao usuário
    getScoreLevelText: function(score) {
        if (score <= 3) return 'BAIXA EXPOSIÇÃO';
        if (score <= 7) return 'SOB OBSERVAÇÃO';
        if (score <= 11) return 'ATENÇÃO';
        return 'CRÍTICO';
    },

    // Emoji colorido — no código antigo essa lógica if/else estava
    // copiada e colada em uns 4 lugares diferentes; agora é uma função só.
    getScoreEmoji: function(score) {
        if (score <= 3) return '🟢';
        if (score <= 7) return '🟡';
        if (score <= 11) return '🟠';
        return '🔴';
    }

};