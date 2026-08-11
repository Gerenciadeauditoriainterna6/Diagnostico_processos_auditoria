// ============================================================
// modal_risco_etapa.js - MÓDULO DO MODAL DE RISCO DA ETAPA
// USA OS MESMOS IDs DO modal_risco_form.html
// ============================================================

const ModalRiscoEtapaModule = {
    
    etapaIdAtual: null,
    codigoEtapaAtual: null,
    nomeEtapaAtual: null,
    riscoIdEditando: null,
    
    init() {
        console.log('📌 ModalRiscoEtapaModule: inicializado');
        
        document.getElementById('btn-fechar-modal')?.addEventListener('click', () => this.fechar());
        document.getElementById('btn-cancelar-modal')?.addEventListener('click', () => this.fechar());
        document.getElementById('btn-salvar-modal')?.addEventListener('click', () => this.salvar());
        
        document.getElementById('modal-impacto')?.addEventListener('change', () => this.atualizarScoreRisco());
        document.getElementById('modal-probabilidade')?.addEventListener('change', () => this.atualizarScoreRisco());
        document.getElementById('apetite_impacto')?.addEventListener('change', () => this.atualizarScoreApetite());
        document.getElementById('apetite_probabilidade')?.addEventListener('change', () => this.atualizarScoreApetite());
    },
    
    abrir(etapaId, codigoEtapa, nomeEtapa) {
        this.etapaIdAtual = etapaId;
        this.codigoEtapaAtual = codigoEtapa;
        this.nomeEtapaAtual = nomeEtapa;
        this.riscoIdEditando = null;
        
        document.getElementById('modal-title').innerHTML = `<i class="fas fa-exclamation-triangle"></i> Novo Risco - ${codigoEtapa} - ${nomeEtapa}`;

        this.limpar();
        this.atualizarScoreRisco();
        this.atualizarScoreApetite();
        
        // ⭐ Carregar objetivo da etapa
        this.carregarObjetivoEtapa(etapaId);

        document.getElementById('modal-risco').style.display = 'flex';
    },

    async carregarObjetivoEtapa(etapaId) {
        try {
            const response = await window.fetchComAutenticacao(`/api/etapa/${etapaId}`);
            const data = await response.json();
            if (data.success && data.etapa) {
                document.getElementById('modal-objetivo-texto').textContent = 
                    data.etapa.objetivo_etapa || 'Nenhum objetivo cadastrado para esta etapa.';
            }
        } catch (error) {
            document.getElementById('modal-objetivo-texto').textContent = 'Erro ao carregar objetivo.';
        }
    },
    
    async editar(riscoId, etapaId, codigoEtapa, nomeEtapa) {
        this.etapaIdAtual = etapaId;
        this.codigoEtapaAtual = codigoEtapa;
        this.nomeEtapaAtual = nomeEtapa;

        try {
            const response = await window.fetchComAutenticacao(`/api/risco-etapa/${riscoId}`);
            const data = await response.json();
            if (!data.success) { window.mostrarToast('❌ Erro', 'error'); return; }

            const risco = data.risco;
            this.riscoIdEditando = riscoId;

            document.getElementById('modal-nome_risco').value = risco.nome_risco || '';
            document.getElementById('modal-fator_risco').value = risco.fator_risco || '';
            document.getElementById('modal-melhoria').value = risco.consequencia || '';
            document.getElementById('apetite_impacto').value = (risco.impacto_aceitavel || 'MÉDIO').toUpperCase();
            document.getElementById('apetite_probabilidade').value = (risco.probabilidade_aceitavel || 'MÉDIO').toUpperCase();
            document.getElementById('modal-desc-tratamento').value = risco.desc_tratamento || '';
            document.getElementById('modal-motivo_risco').value = risco.motivo_classificacao || '';
            document.getElementById('modal-prazo-implantacao').value = risco.prazo_implantacao || '';

            const categorias = risco.categoria ? risco.categoria.split(', ').map(c => c.trim().toUpperCase()) : [];
            document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => {
                cb.checked = categorias.includes(cb.value.toUpperCase());
            });

            document.getElementById('modal-impacto').value = (risco.impacto || 'MÉDIO').toUpperCase();
            document.getElementById('modal-probabilidade').value = (risco.probabilidade || 'MÉDIO').toUpperCase();
            document.getElementById('modal-como-tratar').value = (risco.tratamento || '').toUpperCase();

            this.atualizarScoreRisco();
            this.atualizarScoreApetite();

            document.getElementById('modal-title').innerHTML = `<i class="fas fa-edit"></i> Editar Risco - ${codigoEtapa} - ${nomeEtapa}`;
            document.getElementById('modal-risco').style.display = 'flex';

        } catch (error) {
            window.mostrarToast('❌ Erro ao carregar', 'error');
        }
    },
    
    async excluir(riscoId, nomeRisco, etapaId, codigoEtapa, nomeEtapa) {
        if (!confirm(`Excluir o risco "${nomeRisco}"?`)) return;
        try {
            const response = await window.fetchComAutenticacao(`/api/risco-etapa/${riscoId}`, { method: 'DELETE' });
            const data = await response.json();
            if (data.success) {
                window.mostrarToast('✅ Risco excluído!', 'success');
                await EtapasRiscosModule.carregarRiscosDaEtapa(etapaId, codigoEtapa, nomeEtapa);
                await EtapasRiscosModule.atualizarBadgeRiscos(etapaId);
            }
        } catch (error) {
            window.mostrarToast('❌ Erro', 'error');
        }
    },
    
    async salvar() {
        const nomeRisco = document.getElementById('modal-nome_risco').value.trim().toUpperCase();
        if (!nomeRisco) { window.mostrarToast('❌ Nome obrigatório!', 'error'); return; }

        const dados = {
            id: this.riscoIdEditando,
            etapa_id: this.etapaIdAtual,
            auditoria_id: document.getElementById('filtro_auditoria_select')?.value || null,
            nome_risco: nomeRisco,
            fator_risco: document.getElementById('modal-fator_risco').value.trim().toUpperCase(),
            consequencia: document.getElementById('modal-melhoria')?.value?.trim().toUpperCase() || '',
            impacto: document.getElementById('modal-impacto').value.toUpperCase(),
            probabilidade: document.getElementById('modal-probabilidade').value.toUpperCase(),
            tratamento: document.getElementById('modal-como-tratar').value.toUpperCase(),
            desc_tratamento: document.getElementById('modal-desc-tratamento').value.trim().toUpperCase(),
            motivo: document.getElementById('modal-motivo_risco').value.trim().toUpperCase(),
            prazo_implantacao: document.getElementById('modal-prazo-implantacao')?.value?.trim().toUpperCase() || null,
        };

        try {
            const response = await window.fetchComAutenticacao('/api/risco-etapa/salvar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dados)
            });
            const data = await response.json();
            if (data.success) {
                window.mostrarToast('✅ Risco salvo!', 'success');
                this.fechar();
                await EtapasRiscosModule.carregarRiscosDaEtapa(this.etapaIdAtual, this.codigoEtapaAtual, this.nomeEtapaAtual);
                await EtapasRiscosModule.atualizarBadgeRiscos(this.etapaIdAtual);
            } else {
                window.mostrarToast('❌ ' + (data.error || 'Erro'), 'error');
            }
        } catch (error) {
            window.mostrarToast('❌ Erro de conexão', 'error');
        }
    },

    fechar() {
        document.getElementById('modal-risco').style.display = 'none';
    },

    limpar() {
        document.getElementById('modal-nome_risco').value = '';
        document.getElementById('modal-fator_risco').value = '';
        document.getElementById('modal-melhoria') ? document.getElementById('modal-melhoria').value = '' : null;
        document.getElementById('modal-desc-tratamento').value = '';
        document.getElementById('modal-motivo_risco').value = '';
        document.getElementById('modal-prazo-implantacao') ? document.getElementById('modal-prazo-implantacao').value = '' : null;
        document.getElementById('modal-impacto').value = '';
        document.getElementById('modal-probabilidade').value = '';
        document.getElementById('modal-como-tratar').value = '';
        document.getElementById('apetite_impacto').value = '';
        document.getElementById('apetite_probabilidade').value = '';
        document.querySelectorAll('#categorias-checkboxes input[type="checkbox"]').forEach(cb => cb.checked = false);
        this.atualizarScoreRisco();
        this.atualizarScoreApetite();
    },

    atualizarScoreRisco() {
        const impacto = document.getElementById('modal-impacto')?.value || '';
        const prob = document.getElementById('modal-probabilidade')?.value || '';
        const score = calcularScoreRisco(impacto, prob);
        const preview = document.getElementById('modal-score-preview');
        if (preview) preview.innerHTML = `<strong>Risco Bruto: ${score}</strong>`;
        return score;
    },

    atualizarScoreApetite() {
        const impacto = document.getElementById('apetite_impacto')?.value || '';
        const prob = document.getElementById('apetite_probabilidade')?.value || '';
        const score = calcularScoreRisco(impacto, prob);
        const preview = document.getElementById('apetite-score-preview');
        if (preview) preview.innerHTML = `<strong>Risco Residual: ${score}</strong>`;
        return score;
    }
    
};