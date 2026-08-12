// ============================================================
// wizard.js - MÓDULO DO WIZARD (Navegação e Controle)
// 
// Responsabilidade:
// - Abrir/fechar o modal do wizard
// - Controlar navegação entre etapas (1 a 5)
// - Atualizar barra de progresso
// - Saber se é 'novo' ou 'edicao'
// - Guardar o ID do processo em edição
// ============================================================

const WizardModule = {
    
    // Estado do wizard
    modo: 'novo',          
    processoId: null,      
    etapaAtual: 1,
    etapaMaximaAtingida: 1,         
    
    // Elementos do DOM
    modal: null,
    
    // ============================================================
    // INICIALIZAÇÃO
    // ============================================================
    init() {
        console.log('📌 WizardModule: inicializando...');
        
        this.modal = document.getElementById('modal-wizard');
        
        if (!this.modal) {
            console.warn('⚠️ WizardModule: modal não encontrado');
            return;
        }
        
        // Botão fechar (X)
        const btnFechar = document.getElementById('btn-fechar-wizard');
        if (btnFechar) {
            btnFechar.addEventListener('click', () => this.fechar());
        }

        // Configurar clique na barra de progresso
        document.querySelectorAll('.progress-steps .step').forEach(step => {
            step.addEventListener('click', () => {
                const etapa = parseInt(step.dataset.step);
                this.clicarProgresso(etapa);
            });
        });
        
        console.log('✅ WizardModule: inicializado');
    },

    clicarProgresso(etapa) {
        // No modo NOVO: só permite voltar para etapas já concluídas
        if (this.modo === 'novo') {
            // A etapa máxima que o usuário já atingiu
            if (etapa > this.etapaMaximaAtingida) {
                window.mostrarToast('⚠️ Avance pelas etapas para desbloquear.', 'warning');
                return;
            }
        }
        
        // No modo EDIÇÃO: permite qualquer etapa
        this.irParaEtapa(etapa);
    },
    
    // ============================================================
    // ABRIR / FECHAR
    // ============================================================
    abrir(modo, processoId = null) {
        console.log(`🧙 Wizard: abrindo - Modo: ${modo}, ID: ${processoId || 'novo'}`);
        
        this.modo = modo;
        this.processoId = processoId;
        this.etapaAtual = 1;
        this.etapaMaximaAtingida = 1;
        
        // ⭐ Se for EDIÇÃO, limpar os IDs salvos e setar apenas o ID atual
        if (modo === 'edicao' && processoId) {
            sessionStorage.setItem('processos_salvos_ids', JSON.stringify([processoId]));
            sessionStorage.setItem('modo_edicao', 'true');
            sessionStorage.setItem('processo_id', processoId);
        } else if (modo === 'novo') {
            sessionStorage.removeItem('processos_salvos_ids');
            sessionStorage.removeItem('modo_edicao');
            sessionStorage.removeItem('processo_id');
        }
        
        this.modal.style.display = 'flex';
        this.irParaEtapa(1);
    },
    
    fechar() {
        console.log('🧙 Wizard: fechando');
        
        this.modal.style.display = 'none';
        this.etapaAtual = 1;
        
        // Recarrega a tabela (caso algo tenha sido salvo)
        if (typeof TabelaModule !== 'undefined') {
            TabelaModule.recarregar();
        }
    },
    
    // ============================================================
    // NAVEGAÇÃO ENTRE ETAPAS
    // ============================================================
    irParaEtapa(etapa) {
        console.log(`📍 Wizard: indo para etapa ${etapa}`);

        // ⭐ Registrar etapa máxima atingida
        if (etapa > this.etapaMaximaAtingida) {
            this.etapaMaximaAtingida = etapa;
        }
        
        // Esconde todas as etapas
        for (let i = 1; i <= 5; i++) {
            const el = document.getElementById(this.getEtapaId(i));
            if (el) el.style.display = 'none';
        }
        
        // Mostra a etapa desejada
        const el = document.getElementById(this.getEtapaId(etapa));
        if (el) el.style.display = 'block';

        const wizardBody = document.querySelector('.modal-wizard-body');
        if (wizardBody) {
            wizardBody.scrollTop = 0;
        }
        
        this.etapaAtual = etapa;
        this.atualizarProgresso(etapa);
        
        // Avisa o módulo da etapa que ela foi ativada
        this.notificarEtapa(etapa);
    },
    
    proximaEtapa() {
        if (this.etapaAtual < 5) {
            this.irParaEtapa(this.etapaAtual + 1);
        }
    },
    
    etapaAnterior() {
        if (this.etapaAtual > 1) {
            this.irParaEtapa(this.etapaAtual - 1);
        }
    },
    
    // ============================================================
    // UTILITÁRIOS
    // ============================================================
    getEtapaId(etapa) {
        const mapa = {
            1: 'auditoria-section',
            2: 'info-basicas-section',
            3: 'detalhes-section',
            4: 'riscos-section',
            5: 'visualizar-section'
        };
        return mapa[etapa];
    },
    
    atualizarProgresso(etapa) {
        const steps = document.querySelectorAll('.progress-steps .step');
        steps.forEach((step, index) => {
            step.classList.remove('active', 'completed');
            if (index + 1 === etapa) {
                step.classList.add('active');
            } else if (index + 1 < etapa) {
                step.classList.add('completed');
            }
            
            // ⭐ No modo edição, todos são clicáveis
            if (this.modo === 'edicao') {
                step.style.cursor = 'pointer';
            }
        });
    },
    
    notificarEtapa(etapa) {
        console.log(`🔔 Notificando etapa ${etapa}`);
        switch (etapa) {

            case 1:
                if (typeof Etapa1Module !== 'undefined') Etapa1Module.aoEntrar();
                break;
            case 2:
                if (typeof Etapa2Module !== 'undefined') Etapa2Module.aoEntrar();
                break;
            case 3:
                if (typeof Etapa3Module !== 'undefined') Etapa3Module.aoEntrar();
                break;
            case 4:
                if (typeof Etapa4Module !== 'undefined') Etapa4Module.aoEntrar();
                break;
            case 5:
                if (typeof Etapa5Module !== 'undefined') Etapa5Module.aoEntrar();
                break;
        }
    },
    
    // ============================================================
    // GETTERS
    // ============================================================
    getModo() {
        return this.modo;
    },
    
    getProcessoId() {
        return this.processoId;
    },
    
    isEdicao() {
        return this.modo === 'edicao';
    }
    
};