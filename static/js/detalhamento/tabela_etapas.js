// ============================================================
// tabela_etapas.js - MÓDULO DA TABELA DE ETAPAS
// ============================================================

const TabelaEtapasModule = {

    processoAtualId: null,
    processoAtualCodigo: null,

    init() {
        console.log('📌 TabelaEtapasModule: inicializado');
    },

    // ============================================================
    // CARREGAR DADOS DO PROCESSO
    // ============================================================
    async carregarDadosProcesso() {
        const params = new URLSearchParams(window.location.search);
        const processoId = params.get('processo_id');
        const processoCodigo = params.get('processo_codigo');

        if (!processoId) {
            document.getElementById('processo-info').innerHTML = '<span class="alert-error">❌ Nenhum processo selecionado.</span>';
            return;
        }

        this.processoAtualId = processoId;
        this.processoAtualCodigo = processoCodigo;

        let auditoriaId = null;
        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${processoId}/dados`);
            const data = await response.json();
            if (data.success) {
                auditoriaId = data.auditoria_id;
            }
        } catch (error) {
            console.error('Erro ao buscar processo:', error);
        }

        document.getElementById('modal-processo-id').value = processoId;

        const container = document.getElementById('etapas-container');

        if (auditoriaId) {
            container.innerHTML = this._spinnerHTML('Verificando permissão...');
            try {
                const resp = await window.fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
                const dados = await resp.json();
                if (dados.autorizado) {
                    await this.carregarEtapas();
                } else {
                    container.innerHTML = '<div class="alert-error"><i class="fas fa-lock"></i> Sem permissão.</div>';
                    const btn = document.getElementById('btn-nova-etapa');
                    if (btn) btn.style.display = 'none';
                }
            } catch (error) {
                container.innerHTML = '<div class="alert-error">Erro ao verificar permissão.</div>';
            }
        } else {
            await this.carregarEtapas();
        }
    },

    // ============================================================
    // CARREGAR ETAPAS
    // ============================================================
    async carregarEtapas() {
        const container = document.getElementById('etapas-container');
        container.innerHTML = this._spinnerHTML('Carregando etapas...');

        try {
            const response = await window.fetchComAutenticacao(`/api/processo/${this.processoAtualId}/etapas`);
            const data = await response.json();

            if (data.success) {
                document.getElementById('processo-info').innerHTML = `
                    <i class="fas fa-tag"></i> Processo: <strong>${escapeHtml(this.processoAtualCodigo || '')}</strong> - Total: <strong>${data.etapas.length}</strong>
                `;

                if (data.etapas.length === 0) {
                    container.innerHTML = '<div class="empty-message">Nenhuma etapa. Clique em "Nova Etapa".</div>';
                } else {
                    this.renderizar(data.etapas);
                }
            } else {
                container.innerHTML = `<div class="empty-message">❌ ${data.error || 'Erro'}</div>`;
            }
        } catch (error) {
            container.innerHTML = '<div class="empty-message">❌ Erro de conexão.</div>';
        }
    },

    // ============================================================
    // RENDERIZAR ETAPAS
    // ============================================================
    async renderizar(etapas) {
        const container = document.getElementById('etapas-container');

        const cardsHtml = await Promise.all(etapas.map(async (etapa) => {
            const executoresNomes = await ExecutoresModule.getNomes(etapa.executores_etapa);

            let statusBadge = '';
            if (!etapa.tem_analise_auditado) {
                statusBadge = '<span class="status-badge status-pendente">Análise do Auditado Pendente</span>';
            } else {
                statusBadge = '<span class="status-badge status-concluido">Análise do Auditado Realizada</span>';
            }

            return `
                <div class="etapa-card" data-etapa-id="${etapa.id}">
                    <div class="etapa-card-header">
                        <div class="etapa-info">
                            <span class="etapa-codigo">${escapeHtml(etapa.codigo_etapa)}</span>
                            <span class="etapa-nome">${escapeHtml(etapa.nome_etapa)}</span>
                            ${statusBadge}
                        </div>
                        <div class="etapa-actions">
                            <button class="btn-view-etapa" onclick="VisualizarModule.abrir(${etapa.id})">👁️</button>
                            <button class="btn-edit-etapa" onclick="ModalEtapaModule.editar(${etapa.id})">✏️</button>
                            <button class="btn-delete-etapa" onclick="ModalEtapaModule.excluir(${etapa.id}, '${escapeHtml(etapa.nome_etapa)}')">🗑️</button>
                        </div>
                    </div>
                </div>
            `;
        }));

        container.innerHTML = cardsHtml.join('');
    },

    // ============================================================
    // SPINNER HTML
    // ============================================================
    _spinnerHTML(mensagem) {
        return `
            <div style="text-align: center; padding: 60px 20px;">
                <div class="dot-spinner">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
                <p style="margin-top: 25px; color: #666; font-size: 14px;">${mensagem}</p>
            </div>
        `;
    }

};