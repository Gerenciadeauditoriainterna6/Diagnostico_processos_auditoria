import { mostrarToast, escapeHtml, formatarData, converterParaBase64 } from './utils.js';
import { 
    arquivoSelecionadoAuditadoEvidencia,
    anexoExistenteAuditadoEvidencia,
    processoIdAtual,
    setAnalisesAuditadoList,
    setArquivoSelecionadoAuditadoEvidencia,
    setAnexoExistenteAuditadoEvidencia
} from './estado.js';
import { 
    carregarHistoricoAndamento,
    carregarFollowUps,
    renderizarListaHistorico,
    renderizarListaFollowUps
} from './historico.js';
import { 
    toggleAnaliseEtapaCard,
    toggleAnaliseAuditadoCard
} from './main.js';

export function abrirModalNovaAnaliseAuditado(etapaId, etapaNome, categoria) {
    console.log('📝 Abrindo nova análise do auditado para:', categoria);
    
    // Limpar IDs
    document.getElementById('analise-auditado-id').value = '';
    document.getElementById('analise-auditado-etapa-id').value = etapaId;
    document.getElementById('analise-auditado-categoria').value = categoria;
    document.getElementById('analise-auditado-etapa-nome').value = etapaNome;
    
    // Nome da categoria para exibição
    let categoriaNome = '';
    if (categoria === 'governanca') categoriaNome = 'Governança';
    else if (categoria === 'riscos') categoriaNome = 'Riscos';
    else if (categoria === 'controles') categoriaNome = 'Controles';
    document.getElementById('analise-auditado-categoria-nome').value = categoriaNome;
    
    // Limpar campos principais
    document.getElementById('analise-auditado-texto').value = '';
    document.getElementById('analise-auditado-sugestao').value = '';
    document.getElementById('analise-auditado-necessidade').value = '';
    document.getElementById('analise-auditado-ganho').value = '';
    document.getElementById('analise-auditado-observacoes').value = '';
    
    // Marcar radio "Aguardando avaliação" (value="")
    const radios = document.querySelectorAll('#modal-analise-auditado input[name="sugestao-status-auditado-radio"]');
    console.log('📊 Abrindo modal - radios encontrados:', radios.length);
    
    radios.forEach((radio, idx) => {
        const deveEstarChecado = (radio.value === '');
        radio.checked = deveEstarChecado;
        console.log(`📊 Radio ${idx}: value="${radio.value}", checked set to ${deveEstarChecado}`);
    });
        
    // Atualizar título e abrir modal
    document.getElementById('modal-analise-auditado-titulo').innerHTML = 
        '<i class="fas fa-clipboard-list"></i> Nova Análise do Auditado - ' + categoriaNome;
    
    document.getElementById('modal-analise-auditado').style.display = 'flex';
}

// ============================================================
// FUNÇÃO PARA UPLOAD DE EVIDÊNCIA DO AUDITADO
// ============================================================

export function setupFileUploadEvidenciaAuditado() {
    const btnSelecionar = document.getElementById('btn-selecionar-evidencia-auditado');
    const inputFile = document.getElementById('anexo-evidencia-auditado');
    const evidenciaDiv = document.getElementById('evidencia-nome-auditado');
    const evidenciaTexto = document.getElementById('evidencia-nome-texto-auditado');
    const btnRemover = document.getElementById('btn-remover-evidencia-auditado');
    
    if (!btnSelecionar || !inputFile) {
        console.warn('⚠️ Elementos de upload de evidência do auditado não encontrados');
        return;
    }
    
    btnSelecionar.addEventListener('click', (e) => { 
        e.preventDefault(); 
        inputFile.click(); 
    });
    
    inputFile.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            if (file.type !== 'application/pdf') {
                mostrarToast('⚠️ Apenas arquivos PDF são permitidos', 'warning');
                inputFile.value = '';
                return;
            }
            if (file.size > 10 * 1024 * 1024) {
                mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
                inputFile.value = '';
                return;
            }
            arquivoSelecionadoAuditadoEvidencia = file;
            if (evidenciaTexto) evidenciaTexto.textContent = file.name;
            if (evidenciaDiv) evidenciaDiv.style.display = 'flex';
            setAnexoExistenteAuditadoEvidencia(analise.evidencia_nome);
            console.log('📎 Evidência do auditado selecionada:', file.name);
        }
    });
    
    if (btnRemover) {
        btnRemover.addEventListener('click', (e) => {
            e.preventDefault();
            inputFile.value = '';
            setArquivoSelecionadoAuditadoEvidencia(null);
            if (evidenciaDiv) evidenciaDiv.style.display = 'none';
            if (evidenciaTexto) evidenciaTexto.textContent = '';
            
            if (anexoExistenteAuditadoEvidencia) {
                let hidden = document.getElementById('remover-evidencia-auditado-hidden');
                if (!hidden) {
                    hidden = document.createElement('input');
                    hidden.type = 'hidden';
                    hidden.id = 'remover-evidencia-auditado-hidden';
                    hidden.value = 'true';
                    document.getElementById('modal-analise-auditado').querySelector('.modal-body').appendChild(hidden);
                } else {
                    hidden.value = 'true';
                }
                setAnexoExistenteAuditadoEvidencia(analise.evidencia_nome);
            }
            console.log('🗑️ Evidência do auditado removida');
        });
    }
}

export function fecharModalAnaliseAuditado() {
    document.getElementById('modal-analise-auditado').style.display = 'none';
}

// ============================================================
// FUNÇÃO PARA BAIXAR EVIDÊNCIA DO AUDITADO (CHECKLIST)
// ============================================================

export async function baixarEvidenciaAuditadoChecklist(analiseId, nomeArquivo) {
    try {
        console.log('📥 Baixando evidência do auditado (checklist):', analiseId, nomeArquivo);
        
        const response = await fetchComAutenticacao(`/api/analise-auditado/${analiseId}/evidencia`);
        
        if (!response.ok) {
            let errorMsg = 'Erro ao baixar evidência';
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
            } catch (e) {
                // Se não for JSON, usa o status
                errorMsg = `Erro ${response.status}: ${response.statusText}`;
            }
            mostrarToast('❌ ' + errorMsg, 'error');
            return;
        }
        
        // Obter o blob do arquivo
        const blob = await response.blob();
        
        // Verificar se o blob é válido
        if (blob.size === 0) {
            mostrarToast('❌ Arquivo vazio ou corrompido', 'error');
            return;
        }
        
        // Criar URL para download
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = nomeArquivo || 'evidencia.pdf';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Limpar URL após o download
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
        }, 100);
        
        mostrarToast('✅ Download iniciado!', 'success');
        
    } catch (error) {
        console.error('❌ Erro ao baixar evidência:', error);
        mostrarToast('❌ Erro ao baixar evidência: ' + error.message, 'error');
    }
}

export function abrirModalConfirmarImplantacaoAuditado(analiseId) {
    document.getElementById('confirmar-analise-id').value = analiseId;
    document.getElementById('confirmar-analise-id').setAttribute('data-tipo', 'auditado');
    document.getElementById('confirmar-status').value = 'true';
    document.getElementById('confirmar-data').value = new Date().toISOString().split('T')[0];
    document.getElementById('confirmar-comentario').value = '';
    document.getElementById('modal-confirmar-implantacao').style.display = 'flex';
}

export function setupSemSugestaoCheckbox() {
    const checkbox = document.getElementById('sem_sugestao_melhoria');
    const textarea = document.getElementById('analise-auditado-sugestao');
    const camposContainer = document.getElementById('campos-sugestao-melhoria'); // ⭐ ADICIONAR
    
    if (!checkbox || !textarea || !camposContainer) return;
    
    // ⭐ FUNÇÃO PARA ALTERNAR VISIBILIDADE DOS CAMPOS
    function toggleCamposSugestao() {
        if (checkbox.checked) {
            // ESCONDER CAMPOS
            camposContainer.style.display = 'none';
            const radios = camposContainer.querySelectorAll('input[type="radio"]');
            radios.forEach(radio => {
                radio.disabled = true;
                radio.checked = false;
            });
            const inputs = camposContainer.querySelectorAll('textarea, input:not([type="radio"])');
            inputs.forEach(input => {
                input.disabled = true;
                input.style.backgroundColor = '#f5f5f5';
                input.style.color = '#999';
            });
        } else {
            // MOSTRAR CAMPOS
            camposContainer.style.display = 'block';
            const radios = camposContainer.querySelectorAll('input[type="radio"]');
            radios.forEach(radio => {
                radio.disabled = false;
            });
            const inputs = camposContainer.querySelectorAll('textarea, input:not([type="radio"])');
            inputs.forEach(input => {
                input.disabled = false;
                input.style.backgroundColor = '';
                input.style.color = '';
            });
        }
    }
    
    // Quando o checkbox for marcado, preencher o textarea com "INEXISTENTE" e desabilitar
    checkbox.addEventListener('change', function() {
        if (this.checked) {
            textarea.value = 'INEXISTENTE';
            textarea.disabled = true;
            textarea.style.backgroundColor = '#f5f5f5';
            textarea.style.color = '#999';
        } else {
            textarea.value = '';
            textarea.disabled = false;
            textarea.style.backgroundColor = '';
            textarea.style.color = '';
            textarea.focus();
        }
        // ⭐ CHAMAR A FUNÇÃO PARA ALTERNAR OS CAMPOS
        toggleCamposSugestao();
    });
    
    // Se o usuário digitar algo no textarea, desmarcar o checkbox
    textarea.addEventListener('input', function() {
        if (this.value.trim() !== '' && this.value.trim().toUpperCase() !== 'INEXISTENTE') {
            checkbox.checked = false;
            // ⭐ CHAMAR A FUNÇÃO PARA ALTERNAR OS CAMPOS
            toggleCamposSugestao();
        }
    });
    
    // ⭐ SE O CHECKBOX JÁ ESTIVER MARCADO AO CARREGAR A PÁGINA
    if (checkbox.checked) {
        toggleCamposSugestao();
    }
}

export async function carregarAnalisesAuditado() {
    if (!processoIdAtual) return;
    
    const container = document.getElementById('analises-auditado-container');
    container.innerHTML = '<div style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin"></i> Carregando análises...</div>';
    
    try {
        const response = await fetchComAutenticacao(`/api/analises-criticas-por-processo?processo_id=${processoIdAtual}`);
        const data = await response.json();
        
        if (data.success && data.analises && data.analises.length > 0) {
            const etapas = {};
            data.analises.forEach(a => {
                const chave = a.codigo_etapa;
                if (!etapas[chave]) etapas[chave] = { nome_etapa: a.nome_etapa, analises: [] };
                etapas[chave].analises.push(a);
            });
            
            // Carregar histórico, follow-ups e plano de ação
            for (const [codigo, etapa] of Object.entries(etapas)) {
                for (let i = 0; i < etapa.analises.length; i++) {
                    const analise = etapa.analises[i];
                    const historico = await carregarHistoricoAndamento(analise.id);
                    const followUps = await carregarFollowUps(analise.id);
                    
                    // ⭐ CARREGAR PLANO DE AÇÃO SE HOUVER
                    let plano = null;
                    if (analise.sugestao_sera_implantada === true) {
                        try {
                            const planoResponse = await fetchComAutenticacao(`/api/planos-acao/${analise.id}`);
                            const planoData = await planoResponse.json();
                            if (planoData.success && planoData.plano) {
                                plano = planoData.plano;
                            }
                        } catch (err) {
                            console.warn(`⚠️ Erro ao carregar plano da análise ${analise.id}:`, err);
                        }
                    }
                    
                    etapa.analises[i].historico = historico;
                    etapa.analises[i].followUps = followUps;
                    etapa.analises[i].plano = plano;
                }
            }
            
            // Renderizar HTML com o novo formato
            let html = '';
            for (const [codigo, etapa] of Object.entries(etapas)) {
                html += `
                    <div class="analise-etapa-card">
                        <div class="analise-etapa-header" onclick="toggleAnaliseEtapaCard(this)">
                            <div class="analise-etapa-header-left">
                                <i class="fas fa-folder-open"></i>
                                <strong>Etapa ${codigo}: ${escapeHtml(etapa.nome_etapa)}</strong>
                            </div>
                            <i class="fas fa-chevron-down"></i>
                        </div>
                        <div class="analise-etapa-body" style="display: none;">
                `;
                
                for (const analise of etapa.analises) {
                    const categoriaIcon = analise.categoria === 'governanca' ? 'fa-briefcase' : (analise.categoria === 'riscos' ? 'fa-exclamation-triangle' : 'fa-shield-alt');
                    const categoriaClass = analise.categoria === 'governanca' ? 'categoria-governanca' : (analise.categoria === 'riscos' ? 'categoria-riscos' : 'categoria-controles');
                    const categoriaNome = analise.categoria === 'governanca' ? 'Governança' : (analise.categoria === 'riscos' ? 'Riscos' : 'Controles');
                    
                    // Verificar se tem sugestão de melhoria
                    const valoresSemSugestao = ['', ' ', 'null', 'undefined', 'inexistente', 'INEXISTENTE', 'não se aplica', 'NÃO SE APLICA'];
                    const temSugestaoMelhoria = analise.sugestao_melhoria && 
                                            typeof analise.sugestao_melhoria === 'string' && 
                                            !valoresSemSugestao.includes(analise.sugestao_melhoria.trim().toLowerCase());
                    
                    let badgeHtml = '';
                    if (temSugestaoMelhoria) {
                        if (analise.sugestao_sera_implantada === true) {
                            badgeHtml = '<span class="analise-auditado-badge badge-implantada"><i class="fas fa-check-circle"></i> Sugestão de melhoria será implantada</span>';
                        } else if (analise.sugestao_sera_implantada === false) {
                            badgeHtml = '<span class="analise-auditado-badge badge-nao-implantada"><i class="fas fa-times-circle"></i> Sugestão de melhoria não será implantada</span>';
                        } else {
                            badgeHtml = '<span class="analise-auditado-badge badge-pendente"><i class="fas fa-clock"></i> Sugestão de melhoria aguardando avaliação</span>';
                        }
                    }
                    
                    html += `
                        <div class="analise-auditado-card" data-analise-id="${analise.id}">
                            <div class="analise-auditado-header" onclick="toggleAnaliseAuditadoCard(this)">
                                <div class="analise-auditado-header-left">
                                    <i class="fas ${categoriaIcon} ${categoriaClass}"></i>
                                    <span class="analise-auditado-titulo">${categoriaNome}</span>
                                    ${badgeHtml}
                                </div>
                                <div class="analise-auditado-actions" onclick="event.stopPropagation()">
                                    <button class="btn-edit-analise-auditado" onclick="editarAnaliseAuditado(${analise.id})" title="Editar análise">
                                        <i class="fas fa-pencil-alt"></i> Editar
                                    </button>
                                    <i class="fas fa-chevron-down"></i>
                                </div>
                            </div>
                            <div class="analise-auditado-body">
                                <div class="analise-grid">
                                    <div class="analise-card-section">
                                        <h4><i class="fas fa-clipboard-list"></i> Ponto de Auditoria</h4>
                                        <div class="analise-texto">${escapeHtml(analise.analise_critica) || '-'}</div>
                                    </div>
                                    <div class="analise-card-section">
                                        <h4><i class="fas fa-lightbulb"></i> Sugestão de Melhoria</h4>
                                        <div class="analise-texto">${escapeHtml(analise.sugestao_melhoria) || '-'}</div>
                                    </div>
                                </div>
                                
                                <div class="analise-grid">
                                    <div class="analise-card-section">
                                        <h4><i class="fas fa-tasks"></i> Necessidade para Implantação</h4>
                                        <div class="analise-texto">${escapeHtml(analise.necessidade_implantacao) || '-'}</div>
                                    </div>
                                    <div class="analise-card-section">
                                        <h4><i class="fas fa-chart-line"></i> Ganho Previsto</h4>
                                        <div class="analise-texto">${escapeHtml(analise.ganho_previsto) || '-'}</div>
                                    </div>
                                </div>
                                
                                ${analise.observacoes ? `
                                <div class="analise-card-section">
                                    <h4><i class="fas fa-comment"></i> Recomendações GRC</h4>
                                    <div class="analise-texto">${escapeHtml(analise.observacoes)}</div>
                                </div>
                                ` : ''}

                                ${analise.evidencia_nome ? `
                                <div class="analise-card-section" style="margin-top: 15px; border-left: 3px solid #0b5b99; background: #f0f7ff;">
                                    <h4><i class="fas fa-paperclip" style="color: #0b5b99;"></i> Evidência da Análise</h4>
                                    <div style="display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: white; border-radius: 8px; border: 1px solid #e0e0e0;">
                                        <i class="fas fa-file-pdf" style="color: #dc3545; font-size: 20px;"></i>
                                        <span style="font-size: 13px; color: #333; flex: 1;">${escapeHtml(analise.evidencia_nome)}</span>
                                        <button onclick="event.stopPropagation(); baixarEvidenciaAuditadoChecklist(${analise.id}, '${escapeHtml(analise.evidencia_nome)}')" 
                                                class="btn-download-evidencia solid">
                                            <i class="fas fa-download"></i> Baixar
                                        </button>
                                    </div>
                                </div>
                                ` : ''}
                                
                                <!-- ⭐ PLANO DE AÇÃO 5W2H (NOVO) -->
                                ${analise.plano ? `
                                <div class="analise-card-section plano-acao-card">
                                    <h4><i class="fas fa-clipboard-check"></i> Plano de Ação 5W2H</h4>
                                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; background: white; padding: 12px; border-radius: 8px;">
                                        <div><strong>O que?</strong> ${escapeHtml(analise.plano.oque || '-')}</div>
                                        <div><strong>Por que?</strong> ${escapeHtml(analise.plano.por_que || '-')}</div>
                                        <div><strong>Onde?</strong> ${escapeHtml(analise.plano.onde || '-')}</div>
                                        <div><strong>Quando?</strong> ${analise.plano.data_prevista ? formatarData(analise.plano.data_prevista) : '-'}</div>
                                        <div><strong>Quem?</strong> ${escapeHtml(analise.plano.quem || '-')}</div>
                                        <div><strong>Como?</strong> ${escapeHtml(analise.plano.como || '-')}</div>
                                    </div>
                                    ${analise.plano.comentario ? `
                                        <div style="margin-top: 8px; padding: 8px; background: #f8f9fa; border-radius: 6px; font-size: 12px; color: #666;">
                                            <strong>Comentário:</strong> ${escapeHtml(analise.plano.comentario)}
                                        </div>
                                    ` : ''}
                                    ${analise.plano.quanto_custa ? `
                                        <div style="margin-top: 8px; font-size: 13px;">
                                            <strong>Quanto custa?</strong> R$ ${parseFloat(analise.plano.quanto_custa).toFixed(2)}
                                        </div>
                                    ` : ''}
                                </div>
                                ` : ''}
                                
                                ${analise.plano_de_acao_implantado === true ? `
                                <div class="analise-card-section" style="margin-top: 20px;">
                                    <h4><i class="fas fa-search"></i> Follow-ups Agendados</h4>
                                    <div class="followups-container">
                                        ${renderizarListaFollowUps(analise.followUps)}
                                    </div>
                                </div>
                                ` : (analise.sugestao_sera_implantada === true && !analise.plano_de_acao_implantado) ? `
                                <div class="analise-card-section" style="margin-top: 20px; text-align: center; background: #e8f4f8; border-left: 4px solid #0b5b99;">
                                    <div style="padding: 10px;">
                                        <i class="fas fa-check-circle" style="color: #0b5b99;"></i>
                                        <strong style="color: #0b5b99;">Aguardando confirmação de implantação</strong>
                                        <button class="btn-primary" onclick="abrirModalConfirmarImplantacaoAuditado(${analise.id})" style="margin-top: 8px;">
                                            <i class="fas fa-check-circle"></i> Confirmar Implantação
                                        </button>
                                    </div>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                    `;
                }
                html += `</div></div>`;
            }
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">Nenhuma análise do auditado encontrada.</div>';
        }
    } catch (error) {
        console.error('Erro ao carregar análises do auditado:', error);
        container.innerHTML = '<div class="alert-error" style="padding:20px;text-align:center;">Erro ao carregar análises.</div>';
    }
}

export async function editarAnaliseAuditado(id) {
    console.log('✏️ Editando análise do auditado ID:', id);
    
    try {
        const response = await fetchComAutenticacao(`/api/analises-criticas-por-processo?processo_id=${processoIdAtual}`);
        const data = await response.json();
        
        if (data.success) {
            const analise = data.analises.find(a => a.id === id);
            if (analise) {
                console.log('📊 Dados da análise:', analise);
                console.log('📊 sugestao_sera_implantada:', analise.sugestao_sera_implantada);
                
                // 1. Primeiro, limpar e preencher campos básicos
                document.getElementById('analise-auditado-id').value = analise.id;
                document.getElementById('analise-auditado-etapa-id').value = analise.etapa_id;
                document.getElementById('analise-auditado-categoria').value = analise.categoria;
                document.getElementById('analise-auditado-etapa-nome').value = analise.nome_etapa;
                
                let categoriaNome = '';
                if (analise.categoria === 'governanca') categoriaNome = 'Governança';
                else if (analise.categoria === 'riscos') categoriaNome = 'Riscos';
                else if (analise.categoria === 'controles') categoriaNome = 'Controles';
                document.getElementById('analise-auditado-categoria-nome').value = categoriaNome;
                
                document.getElementById('analise-auditado-texto').value = analise.analise_critica || '';
                document.getElementById('analise-auditado-sugestao').value = analise.sugestao_melhoria || '';
                document.getElementById('analise-auditado-necessidade').value = analise.necessidade_implantacao || '';
                document.getElementById('analise-auditado-ganho').value = analise.ganho_previsto || '';
                document.getElementById('analise-auditado-observacoes').value = analise.observacoes || '';
                
                // ⭐⭐⭐ NOVO: Verificar se o valor é "INEXISTENTE" para marcar o checkbox ⭐⭐⭐
                const checkbox = document.getElementById('sem_sugestao_melhoria');
                const textarea = document.getElementById('analise-auditado-sugestao');
                const camposContainer = document.getElementById('campos-sugestao-melhoria');
                
                if (checkbox && textarea) {
                    const sugestaoValue = analise.sugestao_melhoria || '';
                    if (sugestaoValue.trim().toUpperCase() === 'INEXISTENTE') {
                        checkbox.checked = true;
                        textarea.disabled = true;
                        textarea.style.backgroundColor = '#f5f5f5';
                        textarea.style.color = '#999';
                        
                        // ⭐⭐⭐ ESCONDER CAMPOS ⭐⭐⭐
                        if (camposContainer) {
                            camposContainer.style.display = 'none';
                            const radios = camposContainer.querySelectorAll('input[type="radio"]');
                            radios.forEach(radio => {
                                radio.disabled = true;
                                radio.checked = false;
                            });
                            const inputs = camposContainer.querySelectorAll('textarea, input:not([type="radio"])');
                            inputs.forEach(input => {
                                input.disabled = true;
                                input.style.backgroundColor = '#f5f5f5';
                                input.style.color = '#999';
                            });
                        }
                    } else {
                        checkbox.checked = false;
                        textarea.disabled = false;
                        textarea.style.backgroundColor = '';
                        textarea.style.color = '';
                        
                        // ⭐⭐⭐ MOSTRAR CAMPOS ⭐⭐⭐
                        if (camposContainer) {
                            camposContainer.style.display = 'block';
                            const radios = camposContainer.querySelectorAll('input[type="radio"]');
                            radios.forEach(radio => {
                                radio.disabled = false;
                            });
                            const inputs = camposContainer.querySelectorAll('textarea, input:not([type="radio"])');
                            inputs.forEach(input => {
                                input.disabled = false;
                                input.style.backgroundColor = '';
                                input.style.color = '';
                            });
                        }
                    }
                }
                // ⭐⭐⭐ FIM DO NOVO CÓDIGO ⭐⭐⭐
                
                // ⭐⭐⭐ CARREGAR EVIDÊNCIA EXISTENTE ⭐⭐⭐
                setArquivoSelecionadoAuditadoEvidencia(null);
                setAnexoExistenteAuditadoEvidencia(analise.evidencia_nome);
                
                const evidenciaDiv = document.getElementById('evidencia-nome-auditado');
                const evidenciaTexto = document.getElementById('evidencia-nome-texto-auditado');
                
                if (analise.evidencia_url && analise.evidencia_nome) {
                    setAnexoExistenteAuditadoEvidencia(analise.evidencia_nome);
                    
                    if (evidenciaDiv && evidenciaTexto) {
                        evidenciaTexto.textContent = analise.evidencia_nome;
                        evidenciaDiv.style.display = 'flex';
                    }
                    console.log('📎 Evidência existente carregada:', analise.evidencia_nome);
                } else {
                    if (evidenciaDiv) evidenciaDiv.style.display = 'none';
                    if (evidenciaTexto) evidenciaTexto.textContent = '';
                    console.log('📎 Nenhuma evidência encontrada para esta análise');
                }
                // ⭐⭐⭐ FIM DO NOVO CÓDIGO ⭐⭐⭐
                
                // 2. DEPOIS, configurar os radios e plano de ação
                const radios = document.querySelectorAll('#modal-analise-auditado input[name="sugestao-status-auditado-radio"]');
                
                // ⭐⭐⭐ CORREÇÃO: Desmarcar todos os radios primeiro ⭐⭐⭐
                radios.forEach(radio => {
                    radio.checked = false;
                });
                
                let valorParaMarcar = null;
                
                // ⭐⭐⭐ Só marcar se o valor for true ou false (não marcar se for null) ⭐⭐⭐
                if (analise.sugestao_sera_implantada === true) {
                    valorParaMarcar = 'true';
                    
                    if (analise.anexo_nome) {
                        anexoExistenteNomeAuditado = analise.anexo_nome;
                        const anexoDiv = document.getElementById('anexo-nome-auditado');
                        const anexoTexto = document.getElementById('anexo-nome-texto-auditado');
                        if (anexoDiv && anexoTexto) {
                            anexoTexto.textContent = analise.anexo_nome;
                            anexoDiv.style.display = 'flex';
                        }
                    }
                    
                } else if (analise.sugestao_sera_implantada === false) {
                    valorParaMarcar = 'false';
                    
                } else {
                    // ⭐⭐⭐ CASO NULL: NENHUM radio deve ser marcado ⭐⭐⭐
                    valorParaMarcar = null;
                    
                }
                
                // ⭐⭐⭐ Marcar o radio correspondente (se houver) ⭐⭐⭐
                if (valorParaMarcar !== null) {
                    radios.forEach(radio => {
                        if (radio.value === valorParaMarcar) {
                            radio.checked = true;
                        }
                    });
                }
                // Se for null, todos os radios permanecem desmarcados
                
                console.log('🎯 Radio selecionado:', valorParaMarcar);
                console.log('🎯 Radio checked após marcação:', document.querySelector('#modal-analise-auditado input[name="sugestao-status-auditado-radio"]:checked')?.value);
                
                document.getElementById('modal-analise-auditado-titulo').innerHTML = 
                    '<i class="fas fa-edit"></i> Editar Análise do Auditado - ' + categoriaNome;
                
                document.getElementById('modal-analise-auditado').style.display = 'flex';
                
            }
        }
    } catch (error) {
        console.error('Erro ao carregar análise para edição:', error);
        mostrarToast('Erro ao carregar dados da análise', 'error');
    }
}

export async function salvarAnaliseAuditado() {
    if (!processoIdAtual) {
        mostrarToast('Selecione um processo primeiro', 'warning');
        return;
    }
    
    const analiseId = document.getElementById('analise-auditado-id').value;
    const etapaId = document.getElementById('analise-auditado-etapa-id').value;
    const categoria = document.getElementById('analise-auditado-categoria').value;
    const analiseCritica = document.getElementById('analise-auditado-texto').value;
    const sugestaoMelhoria = document.getElementById('analise-auditado-sugestao').value.trim();
    
    if (!analiseCritica.trim()) {
        mostrarToast('O Ponto de Auditoria é obrigatório', 'warning');
        return;
    }
    
    // ⭐ VERIFICA SE TEM SUGESTÃO DE MELHORIA
    const valoresSemSugestao = ['', ' ', 'null', 'undefined', 'inexistente', 'INEXISTENTE', 'não se aplica', 'NÃO SE APLICA'];
    const temSugestaoMelhoria = sugestaoMelhoria.length > 0 && !valoresSemSugestao.includes(sugestaoMelhoria.trim().toLowerCase());
    
    // ⭐ BUSCAR O RADIO SELECIONADO
    const radioSelecionado = document.querySelector('#modal-analise-auditado input[name="sugestao-status-auditado-radio"]:checked');
    
    // ⭐⭐⭐ CORREÇÃO: Enviar como STRING para a API ⭐⭐⭐
    let sugestao_sera_implantada = null;
    
    if (radioSelecionado) {
        const valorRadio = radioSelecionado.value;
        console.log('📻 Valor do radio:', valorRadio);
        
        if (valorRadio === 'true') {
            sugestao_sera_implantada = 'true';  // ⭐ String
            console.log('✅ Será implantada (string "true")');
        } else if (valorRadio === 'false') {
            sugestao_sera_implantada = 'false';  // ⭐ String
            console.log('❌ Não será implantada (string "false")');
        } else if (valorRadio === '') {
            sugestao_sera_implantada = null;  // ⭐ Null
            console.log('⏳ Aguardando avaliação (null)');
        }
    } else {
        console.warn('⚠️ NENHUM radio selecionado!');
        if (temSugestaoMelhoria) {
            mostrarToast('⚠️ Selecione uma opção em "Status da sugestão de melhoria"', 'warning');
            return;
        }
    }
    
    console.log('🎯 sugestao_sera_implantada enviado:', sugestao_sera_implantada);
    console.log('🎯 Tipo:', typeof sugestao_sera_implantada);
    
    // ⭐ CRIAR PAYLOAD
    const payload = {
        processo_id: parseInt(processoIdAtual),
        etapa_id: parseInt(etapaId),
        categoria: categoria,
        analise_critica: analiseCritica,
        sugestao_melhoria: sugestaoMelhoria,
        necessidade_implantacao: document.getElementById('analise-auditado-necessidade').value || '',
        ganho_previsto: document.getElementById('analise-auditado-ganho').value || '',
        observacoes: document.getElementById('analise-auditado-observacoes').value || '',
        sugestao_sera_implantada: sugestao_sera_implantada  // ⭐ Envia 'true', 'false' ou null
    };
    
    // ⭐ Processar evidência
    const removerEvidencia = document.getElementById('remover-evidencia-auditado-hidden')?.value === 'true';
    
    if (arquivoSelecionadoAuditadoEvidencia) {
        try {
            const base64 = await converterParaBase64(arquivoSelecionadoAuditadoEvidencia);
            payload.evidencia_base64 = base64;
            payload.evidencia_nome = arquivoSelecionadoAuditadoEvidencia.name;
        } catch (error) {
            console.error('Erro ao converter evidência:', error);
            mostrarToast('❌ Erro ao processar evidência', 'error');
            return;
        }
    } else if (removerEvidencia) {
        payload.remover_evidencia = 'true';
    }
    
    const btnSalvar = document.getElementById('btn-salvar-analise-auditado');
    const textoOriginal = btnSalvar.innerHTML;
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    
    try {
        const url = analiseId ? `/api/analise-auditado/${analiseId}` : '/api/analise-auditado/salvar';
        const method = analiseId ? 'PUT' : 'POST';
        
        const response = await fetchComAutenticacao(url, { 
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        let data;
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            try {
                data = JSON.parse(text);
            } catch (e) {
                console.error('Resposta não é JSON:', text);
                data = { success: false, error: 'Resposta inválida do servidor' };
            }
        }
        
        if (data.success) {
            mostrarToast(analiseId ? '✅ Análise atualizada com sucesso!' : '✅ Análise salva com sucesso!', 'success');
            fecharModalAnaliseAuditado();
            await carregarAnalisesAuditado();
        } else {
            mostrarToast('❌ Erro ao salvar: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarToast('❌ Erro ao conectar com o servidor', 'error');
    } finally {
        btnSalvar.disabled = false;
        btnSalvar.innerHTML = textoOriginal;
    }
}