// ============================================================
// etapa5_resumo.js - ETAPA 5: Resumo Final
// ============================================================

const Etapa5Module = {
    
    btnVoltar: null,
    btnFinalizar: null,
    
    init() {
        console.log('📌 Etapa5Module: inicializando...');
        
        this.btnVoltar = document.getElementById('btn-voltar-etapa4');
        this.btnFinalizar = document.getElementById('btn-finalizar-processo');
        
        this.configurarEventos();
        console.log('✅ Etapa5Module: inicializado');
    },
    
    configurarEventos() {
        if (this.btnVoltar) {
            this.btnVoltar.addEventListener('click', () => {
                if (typeof WizardModule !== 'undefined') WizardModule.irParaEtapa(4);
            });
        }
        
        if (this.btnFinalizar) {
            this.btnFinalizar.addEventListener('click', () => {
                this.finalizar();
            });
        }
    },
    
    async aoEntrar() {
        console.log('👋 Etapa 5 ativada');
        await this.carregarResumo();
    },
    
    async carregarResumo() {
        try {
            const areaId = document.getElementById('id_area_selecionado')?.value ||
                          document.getElementById('area_select')?.value;
            const auditoriaId = document.getElementById('auditoria_select')?.value;
            const entrevistado = document.getElementById('entrevistado_processo')?.value || '';
            
            // Buscar processos
            const idsSalvos = JSON.parse(sessionStorage.getItem('processos_salvos_ids') || '[]');
            let processos = [];
            
            if (idsSalvos.length > 0) {
                const response = await window.fetchComAutenticacao(`/api/processos-por-ids?ids=${idsSalvos.join(',')}`);
                const data = await response.json();
                if (data.success) processos = data.processos;
            }
            
            if (WizardModule.isEdicao()) {
                const procId = WizardModule.getProcessoId();
                const response = await window.fetchComAutenticacao(`/api/processo/${procId}/dados`);
                const data = await response.json();
                if (data.success) {
                    processos = [{ ...data, id: procId }];
                }
            }
            
            this.preencherResumo(entrevistado, processos);
            
        } catch (error) {
            console.error('Erro ao carregar resumo:', error);
        }
    },
    
    preencherResumo(entrevistado, processos) {
        // Entrevistado
        document.getElementById('resumo-entrevistado').textContent = entrevistado || '-';
        
        if (processos.length === 0) {
            document.getElementById('resumo-codigo').textContent = '-';
            document.getElementById('resumo-nome').textContent = 'Nenhum processo';
            document.getElementById('resumo-executores').textContent = '-';
            document.getElementById('resumo-descricao').textContent = '-';
            document.getElementById('resumo-etapa-ini').textContent = '-';
            document.getElementById('resumo-produto').textContent = '-';
            document.getElementById('resumo-etapa-fim').textContent = '-';
            document.getElementById('resumo-objetivo').textContent = '-';
            document.getElementById('resumo-qtd-riscos').textContent = '0 riscos';
            return;
        }
        
        // Pegar o primeiro processo (para simplificar)
        const proc = processos[0];
        
        document.getElementById('resumo-codigo').textContent = proc.codigo_processo || '-';
        document.getElementById('resumo-nome').textContent = proc.nome_processo || '-';
        document.getElementById('resumo-descricao').textContent = proc.descricao || '-';
        document.getElementById('resumo-etapa-ini').textContent = proc.etapa_ini || '-';
        document.getElementById('resumo-produto').textContent = proc.produto || '-';
        document.getElementById('resumo-etapa-fim').textContent = proc.etapa_fim || '-';
        document.getElementById('resumo-objetivo').textContent = proc.objetivo || '-';
        
        // Buscar executores
        this.carregarExecutoresResumo(proc.id);
        
        // Buscar riscos
        this.carregarRiscosResumo(proc.id);
    },
    
    async carregarExecutoresResumo(processoId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/executores`);
            const data = await response.json();
            
            if (data.success && data.executores.length > 0) {
                const nomes = data.executores.map(e => e.nome).join(', ');
                document.getElementById('resumo-executores').textContent = nomes;
            } else {
                document.getElementById('resumo-executores').textContent = '-';
            }
        } catch (error) {
            document.getElementById('resumo-executores').textContent = '-';
        }
    },
    
    async carregarRiscosResumo(processoId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/riscos`);
            const data = await response.json();
            
            if (data.success && data.riscos.length > 0) {
                document.getElementById('resumo-qtd-riscos').textContent = `${data.riscos.length} riscos`;
                
                const container = document.getElementById('resumo-riscos-container');
                container.innerHTML = data.riscos.map(r => `
                    <div class="resumo-risco-item">
                        <strong>${r.nome_risco}</strong> | Score: ${r.score_risco || 0}
                    </div>
                `).join('');
            }
        } catch (error) {
            // silencioso
        }
    },
    
    finalizar() {
        window.mostrarToast('✅ Cadastro finalizado com sucesso!', 'success');
        sessionStorage.removeItem('processos_salvos_ids');
        
        if (typeof WizardModule !== 'undefined') WizardModule.fechar();
        if (typeof TabelaModule !== 'undefined') TabelaModule.recarregar();
    }
    
};