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
        
        // ⭐ Loading global (substitui o spinner inline)
        LoadingModule.mostrar('Carregando visualização...');

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
        } finally {
            // ⭐ SEMPRE esconder loading
            LoadingModule.ocultar();
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

        let manualStatus = '';
        if (temManual) {
            manualStatus = '<span class="vis-badge vis-badge-success"><i class="fas fa-check-circle"></i> Manual Concluído</span>';
        } else if (emAndamento) {
            manualStatus = '<span class="vis-badge vis-badge-warning"><i class="fas fa-clock"></i> Manual em Andamento</span>';
        } else {
            manualStatus = '<span class="vis-badge vis-badge-empty"><i class="fas fa-times-circle"></i> Nenhum Manual</span>';
        }

        const statusEtapa = etapa.status_etapa === 'ATIVA' 
            ? '<span class="vis-badge vis-badge-success"><i class="fas fa-circle"></i> ATIVA</span>'
            : '<span class="vis-badge vis-badge-danger"><i class="fas fa-circle"></i> INATIVA</span>';

        const obrigacoesHtml = this._renderizarObrigacoes(etapa.obrigacoes_regulatorias);
        const analisesHtml = analises.length === 0 
            ? '<div class="vis-empty"><i class="fas fa-clipboard"></i> Nenhuma análise cadastrada</div>'
            : analises.map(a => this._renderizarAnalise(a)).join('');

        return `
            <div class="vis-etapa-container-v2">
                
                <!-- Cabeçalho -->
                <div class="vis-header">
                    <div class="vis-codigo">${escapeHtml(etapa.codigo_etapa)}</div>
                    <div class="vis-titulo">${escapeHtml(etapa.nome_etapa)}</div>
                    ${statusEtapa}
                </div>
                
                <!-- Grid de informações -->
                <div class="vis-grid-v2">
                    <div class="vis-col">
                        <!-- Executores -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-users"></i> Executores
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(executoresNomes)}
                            </div>
                        </div>
                        
                        <!-- Descrição -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-align-left"></i> Descrição
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(etapa.descricao_etapa) || '<span class="vis-nao-informado">Não informado</span>'}
                            </div>
                        </div>
                        
                        <!-- Como é feito -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-cogs"></i> Como é feito?
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(etapa.como_e_feito) || '<span class="vis-nao-informado">Não informado</span>'}
                            </div>
                        </div>
                    </div>
                    
                    <div class="vis-col">
                        <!-- Objetivo -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-bullseye"></i> Objetivo
                            </div>
                            <div class="vis-card-body">
                                ${escapeHtml(etapa.objetivo_etapa) || '<span class="vis-nao-informado">Não informado</span>'}
                            </div>
                        </div>
                        
                        <!-- Manual -->
                        <div class="vis-card">
                            <div class="vis-card-header">
                                <i class="fas fa-book"></i> Manual da Etapa
                            </div>
                            <div class="vis-card-body">
                                ${manualStatus}
                                ${temManual ? `
                                    <div style="margin-top:6px;font-size:13px;display:flex;align-items:center;gap:10px;">
                                        📄 ${escapeHtml(etapa.manual_nome)}
                                        <button onclick="ManualModule.baixar(${etapa.id})"
                                            style="background:#0b5b99;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;">
                                            <i class="fas fa-download"></i> Baixar
                                        </button>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>

                <div class="vis-card vis-card-full">
                    <div class="vis-card-header">
                        <i class="fas fa-gavel"></i> Política Interna
                    </div>
                    <div class="vis-card-body">
                        ${escapeHtml(etapa.politica_interna) || '<span class="vis-nao-informado">Não informado</span>'}
                        
                        ${etapa.politica_interna_url && etapa.politica_interna_url.trim() !== '' ? `
                            <div style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 6px; border-left: 3px solid #184145;">
                                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <i class="fas fa-file-pdf" style="color: #dc3545; font-size: 18px;"></i>
                                        <span style="font-size: 13px; color: #333;">${escapeHtml(etapa.politica_interna_nome || 'Documento da Política Interna')}</span>
                                    </div>
                                    <button onclick="PoliticaInternaModule.baixarArquivoPorUrl('${etapa.politica_interna_url}', '${escapeHtml(etapa.politica_interna_nome || 'documento.pdf')}')"
                                        style="background:#0b5b99;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;white-space:nowrap;">
                                        <i class="fas fa-download"></i> Baixar
                                    </button>
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
                
                <!-- Obrigações Regulatórias -->
                <div class="vis-card vis-card-full">
                    <div class="vis-card-header">
                        <i class="fas fa-balance-scale"></i> Obrigações Regulatórias
                    </div>
                    <div class="vis-card-body">
                        ${obrigacoesHtml}
                    </div>
                </div>
                
                <!-- Análises -->
                <div class="vis-card vis-card-full">
                    <div class="vis-card-header">
                        <i class="fas fa-clipboard-check"></i> Análises do Auditado
                    </div>
                    <div class="vis-card-body">
                        ${analisesHtml}
                    </div>
                </div>
                
            </div>
        `;
    },

    _renderizarObrigacoes(obrigacoesJson) {
        try {
            const dados = typeof obrigacoesJson === 'string' ? JSON.parse(obrigacoesJson) : (obrigacoesJson || {});
            
            // Verificar se tem políticas (novo formato)
            const politicas = dados.politicas || [];
            
            if (politicas.length === 0) {
                return '<span style="color:#999;">Nenhuma política ou obrigação cadastrada</span>';
            }
            
            return politicas.map(politica => {
                const tipoPolitica = politica.tipo === 'externa' 
                    ? '<span class="vis-badge vis-badge-warning"><i class="fas fa-external-link-alt"></i> Externa</span>'
                    : '<span class="vis-badge vis-badge-info"><i class="fas fa-building"></i> Interna</span>';
                
                const obrigacoesHtml = politica.obrigacoes && politica.obrigacoes.length > 0
                    ? politica.obrigacoes.map(obrigacao => this._renderizarObrigacao(obrigacao)).join('')
                    : '<div style="color:#999;font-size:13px;margin-top:8px;">Nenhuma obrigação cadastrada</div>';
                
                const arquivoPolitica = politica.arquivo_url && politica.arquivo_url.trim() !== ''
                    ? `
                        <div style="margin-top:8px;display:flex;align-items:center;gap:8px;">
                            <i class="fas fa-file-pdf" style="color:#dc3545;"></i>
                            <span style="font-size:12px;color:#333;">${escapeHtml(politica.arquivo_nome || 'Documento da Política')}</span>
                            <button onclick="PoliticasObrigacoesModule.baixarArquivoPorUrl('${politica.arquivo_url}', '${escapeHtml(politica.arquivo_nome || 'documento.pdf')}')"
                                style="background:#0b5b99;color:white;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:11px;white-space:nowrap;">
                                <i class="fas fa-download"></i> Baixar
                            </button>
                        </div>
                    ` : '';
                
                return `
                    <div style="background:#f8f9fa;border-radius:8px;padding:15px;margin-bottom:15px;border-left:3px solid #184145;">
                        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
                            <strong style="color:#184145;">
                                <i class="fas fa-file-contract"></i> ${escapeHtml(politica.titulo || 'INEXISTENTE')}
                            </strong>
                            ${tipoPolitica}
                        </div>
                        
                        ${arquivoPolitica}
                        
                        <div style="margin-top:12px;padding-top:12px;border-top:1px solid #e0e0e0;">
                            <strong style="font-size:13px;color:#666;">
                                <i class="fas fa-list-check"></i> Obrigações:
                            </strong>
                            <div style="margin-top:8px;">
                                ${obrigacoesHtml}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
        } catch (e) {
            console.error('Erro ao renderizar políticas:', e);
            return '<span style="color:#999;">Erro ao carregar</span>';
        }
    },

    // ⭐ Nova função para renderizar uma obrigação individual
    _renderizarObrigacao(obrigacao) {
        const arquivoObrigacao = obrigacao.arquivo_url && obrigacao.arquivo_url.trim() !== ''
            ? `
                <div style="margin-top:5px;display:flex;align-items:center;gap:8px;">
                    <i class="fas fa-file-pdf" style="color:#dc3545;font-size:12px;"></i>
                    <span style="font-size:12px;color:#333;">${escapeHtml(obrigacao.arquivo_nome || 'Documento')}</span>
                    <button onclick="PoliticasObrigacoesModule.baixarArquivoPorUrl('${obrigacao.arquivo_url}', '${escapeHtml(obrigacao.arquivo_nome || 'documento.pdf')}')"
                        style="background:#0b5b99;color:white;border:none;padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px;">
                        <i class="fas fa-download"></i> Baixar
                    </button>
                </div>
            ` : '';
        
        return `
            <div style="background:#fff;border-radius:6px;padding:10px;margin-bottom:8px;border:1px solid #e0e0e0;">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <strong style="font-size:13px;">${escapeHtml(obrigacao.titulo || 'INEXISTENTE')}</strong>
                    ${obrigacao.obrigatorio ? '<span style="font-size:11px;color:#dc3545;font-weight:600;">Obrigatória</span>' : ''}
                </div>
                
                ${obrigacao.orgao_regulador ? `<div style="font-size:12px;color:#666;margin-top:3px;"><i class="fas fa-building"></i> ${escapeHtml(obrigacao.orgao_regulador)}</div>` : ''}
                
                ${obrigacao.documento_necessario ? `<div style="font-size:12px;color:#666;margin-top:3px;"><i class="fas fa-file-alt"></i> ${escapeHtml(obrigacao.documento_necessario)}</div>` : ''}
                
                ${obrigacao.prazo ? `<div style="font-size:12px;color:#666;margin-top:3px;"><i class="fas fa-calendar-alt"></i> Prazo: ${formatarDataBR(obrigacao.prazo)}</div>` : ''}
                
                ${arquivoObrigacao}
            </div>
        `;
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

};