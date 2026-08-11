// ============================================================
// visualizar.js - MÓDULO DE VISUALIZAÇÃO DE ETAPA
// ============================================================

const VisualizarModule = {

    init() {
        console.log('📌 VisualizarModule: inicializado');
        
        // Configurar botão de fechar
        const btnFechar = document.querySelector('#modal-visualizar-etapa .modal-close');
        if (btnFechar) {
            btnFechar.addEventListener('click', () => this.fechar());
        }
        
    },

    // ============================================================
    // ABRIR MODAL DE VISUALIZAÇÃO
    // ============================================================
    async abrir(etapaId) {
        const modal = document.getElementById('modal-visualizar-etapa');
        const body = document.getElementById('modal-visualizar-body');
        if (!modal || !body) return;

        modal.style.display = 'flex';
        body.innerHTML = this._spinnerHTML('Carregando visualização...');

        try {
            const [respEtapa, respAnalises] = await Promise.all([
                window.fetchComAutenticacao(`/api/etapa/${etapaId}`),
                window.fetchComAutenticacao(`/api/etapa/${etapaId}/analises`)
            ]);

            const dataEtapa = await respEtapa.json();
            const dataAnalises = await respAnalises.json();

            if (dataEtapa.success) {
                body.innerHTML = await this._renderizar(dataEtapa.etapa, dataAnalises.success ? dataAnalises.analises || [] : []);
            }
        } catch (error) {
            body.innerHTML = '<div class="alert-error">Erro ao carregar dados da etapa.</div>';
        }
    },

    // ============================================================
    // FECHAR MODAL
    // ============================================================
    fechar() {
        const modal = document.getElementById('modal-visualizar-etapa');
        if (modal) modal.style.display = 'none';
    },

    // ============================================================
    // RENDERIZAR
    // ============================================================
    async _renderizar(etapa, analises) {
        const executoresNomes = typeof ExecutoresModule !== 'undefined' 
            ? await ExecutoresModule.getNomes(etapa.executores_etapa) : '-';

        const temManual = etapa.manual_nome && etapa.manual_nome.trim() !== '';
        const emAndamento = etapa.manual_em_andamento || false;

        let manualBadge = '';
        if (temManual) {
            manualBadge = '<span style="background:#d4edda;color:#155724;padding:2px 10px;border-radius:12px;font-size:11px;margin-left:8px;">✅ Concluído</span>';
        } else if (emAndamento) {
            manualBadge = '<span style="background:#fff3cd;color:#856404;padding:2px 10px;border-radius:12px;font-size:11px;margin-left:8px;">⏳ Em andamento</span>';
        } else {
            manualBadge = '<span style="background:#f8f9fa;color:#6c757d;padding:2px 10px;border-radius:12px;font-size:11px;margin-left:8px;">❌ Não anexado</span>';
        }

        const obrigacoesHtml = this._renderizarObrigacoes(etapa.obrigacoes_regulatorias);
        const analisesHtml = analises.length === 0 
            ? '<div class="analises-empty">Nenhuma Análise.</div>'
            : analises.map(a => this._renderizarAnalise(a)).join('');

        return `
            <div class="vis-etapa-container">
                <div class="vis-secao">
                    <h4><i class="fas fa-info-circle"></i> Informações Básicas</h4>
                    <div class="vis-grid">
                        <div class="vis-item"><label>Código</label><span>${escapeHtml(etapa.codigo_etapa)}</span></div>
                        <div class="vis-item"><label>Nome</label><span>${escapeHtml(etapa.nome_etapa)}</span></div>
                        <div class="vis-item"><label>Status</label><span>${escapeHtml(etapa.status_etapa)}</span></div>
                        <div class="vis-item vis-full"><label>Executores</label><span>${escapeHtml(executoresNomes)}</span></div>
                    </div>
                </div>
                <div class="vis-secao">
                    <h4><i class="fas fa-clipboard-list"></i> Detalhes</h4>
                    <div class="vis-grid">
                        <div class="vis-item vis-full"><label>Descrição</label><span>${escapeHtml(etapa.descricao_etapa) || '-'}</span></div>
                        <div class="vis-item vis-full"><label>Como é feito?</label><span>${escapeHtml(etapa.como_e_feito) || '-'}</span></div>
                        <div class="vis-item vis-full"><label>Objetivo</label><span>${escapeHtml(etapa.objetivo_etapa) || '-'}</span></div>
                    </div>
                </div>
                <div class="vis-secao">
                    <h4><i class="fas fa-gavel"></i> Políticas</h4>
                    <div class="vis-grid">
                        <div class="vis-item vis-full"><label>Política Interna</label><span>${escapeHtml(etapa.politica_interna) || '-'}</span></div>
                        <div class="vis-item vis-full"><label>Obrigações Regulatórias</label>${obrigacoesHtml}</div>
                    </div>
                </div>
                <div class="vis-secao">
                    <h4><i class="fas fa-folder-open"></i> Arquivos</h4>
                    <div class="vis-grid">
                        <div class="vis-item vis-full"><label>Manual</label><span>${manualBadge} ${temManual ? escapeHtml(etapa.manual_nome) : ''}</span></div>
                    </div>
                </div>
                <div class="vis-secao">
                    <h4><i class="fas fa-clipboard-list"></i> Análises do auditado</h4>
                    ${analisesHtml}
                </div>
            </div>
        `;
    },

    _renderizarObrigacoes(obrigacoesJson) {
        try {
            const obrigacoes = typeof obrigacoesJson === 'string' ? JSON.parse(obrigacoesJson) : (obrigacoesJson || []);
            if (obrigacoes.length === 0) return '<span style="color:#999;">Nenhuma obrigação</span>';
            return obrigacoes.map(o => `
                <div style="background:#f8f9fa;border-radius:8px;padding:12px;margin-bottom:10px;border-left:3px solid #184145;">
                    <strong>${escapeHtml(o.titulo || 'INEXISTENTE')}</strong>
                    ${o.orgao_regulador ? `<span style="color:#666;font-size:12px;">${escapeHtml(o.orgao_regulador)}</span>` : ''}
                </div>
            `).join('');
        } catch { return '<span>Erro ao carregar</span>'; }
    },

    _renderizarAnalise(a) {
        const temEvidencia = a.evidencia_nome && a.evidencia_nome.trim() !== '';
        
        return `
            <div class="analise-card">
                <div class="analise-card-info">
                    <strong>Ponto de Auditoria:</strong> ${escapeHtml(a.analise_critica || '-')}<br>
                    <strong>Sugestão:</strong> ${escapeHtml(a.sugestao_melhoria || '-')}
                    ${temEvidencia ? `
                        <br><strong>Evidência:</strong> ${escapeHtml(a.evidencia_nome)}
                        <button onclick="AnalisesModule.baixarEvidencia(${a.id}, '${escapeHtml(a.evidencia_nome)}')"
                            style="background:#0b5b99;color:white;border:none;padding:2px 10px;border-radius:4px;cursor:pointer;font-size:11px;">
                            <i class="fas fa-download"></i> Baixar
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    },

    _spinnerHTML(mensagem) {
        return `
            <div style="text-align:center;padding:60px 20px;">
                <div class="dot-spinner"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
                <p style="margin-top:25px;color:#666;font-size:14px;">${mensagem}</p>
            </div>
        `;
    }

};