import { 
    mostrarToast,
    escapeHtml,
    formatarData,
    converterParaBase64
} from './utils.js';

import { 
    processoIdAtual,
    analisesAuditorList,
    arquivoSelecionadoAuditor,
    anexoExistenteNomeAuditor,
    setAnalisesAuditorList,
    setArquivoSelecionadoAuditor,
    setAnexoExistenteNomeAuditor
} from './estado.js';

import { 
    carregarHistoricoAndamento,
    carregarFollowUps,
    renderizarListaHistorico,
    renderizarListaFollowUps
} from './historico.js';

import { 
    toggleAnaliseAuditorCard
} from './main.js';

export function abrirModalNovaAnaliseAuditor() {
    document.getElementById('modal-analise-titulo').innerHTML = '<i class="fas fa-user-check"></i> Nova Análise do Auditor';
    document.getElementById('analise-auditor-id').value = '';
    document.getElementById('analise-auditor-texto').value = '';
    document.getElementById('analise-auditor-sugestao').value = '';
    document.getElementById('analise-auditor-necessidade').value = '';
    document.getElementById('analise-auditor-ganho').value = '';
    document.getElementById('analise-auditor-observacoes').value = '';

    // ⭐ Resetar checkbox "Sem sugestão"
    const checkbox = document.getElementById('sem_sugestao_melhoria_auditor');
    const textarea = document.getElementById('analise-auditor-sugestao');
    if (checkbox) checkbox.checked = false;
    if (textarea) {
        textarea.disabled = false;
        textarea.style.backgroundColor = '';
        textarea.style.color = '';
        textarea.value = '';
    }
    

    // ⭐ NOVO: Limpar evidência ao abrir nova análise
    setArquivoSelecionadoAuditor(null);
    setAnexoExistenteNomeAuditor(null);
    
    const inputFile = document.getElementById('anexo-evidencia-auditor');
    if (inputFile) inputFile.value = '';
    
    const evidenciaDiv = document.getElementById('evidencia-nome-auditor');
    if (evidenciaDiv) evidenciaDiv.style.display = 'none';
    
    const removerHidden = document.getElementById('remover-evidencia-hidden');
    if (removerHidden) removerHidden.remove();
    
    const analiseIdInput = document.getElementById('analise-auditor-id');
    if (analiseIdInput) analiseIdInput.removeAttribute('data-evidencia-id');
    
    // ⭐ LIMPAR PLANO DE AÇÃO 5W2H DO AUDITOR
   
    const resumoPlano = document.getElementById('resumo-plano-acao-auditor');
    if (resumoPlano) resumoPlano.style.display = 'none';
    const semPlano = document.getElementById('sem-plano-acao-auditor');
    if (semPlano) semPlano.style.display = 'block';
    const secaoPlano = document.getElementById('secao-plano-acao');
    if (secaoPlano) secaoPlano.style.display = 'none';
    
    // ⭐ Desmarcar TODOS os radios
    const radios = document.querySelectorAll('#modal-analise-auditor input[name="sugestao-status-radio"]');
    radios.forEach(radio => {
        radio.checked = false;
    });
    
    document.getElementById('modal-analise-auditor').style.display = 'flex';
}

export async function editarAnaliseAuditor(id) {
    console.log('✏️ editarAnaliseAuditor chamado para ID:', id);
    
    const response = await fetchComAutenticacao(`/api/analises-auditor/por-processo?processo_id=${processoIdAtual}`);
    const data = await response.json();
    
    if (data.success) setAnalisesAuditorList(data.analises);
    
    const analise = analisesAuditorList.find(a => a.id === id);
    if (!analise) return;
    
    document.getElementById('modal-analise-titulo').innerHTML = '<i class="fas fa-edit"></i> Editar Análise do Auditor';
    document.getElementById('analise-auditor-id').value = analise.id;
    document.getElementById('analise-auditor-texto').value = analise.analise_critica || '';
    document.getElementById('analise-auditor-sugestao').value = analise.sugestao_melhoria || '';
    document.getElementById('analise-auditor-necessidade').value = analise.necessidade_implantacao || '';
    document.getElementById('analise-auditor-ganho').value = analise.ganho_previsto || '';
    document.getElementById('analise-auditor-observacoes').value = analise.observacoes || '';

    // Verificar se o valor é "NÃO APLICÁVEL NO MOMENTO" para marcar o checkbox
    const checkbox = document.getElementById('sem_sugestao_melhoria_auditor');
    const textarea = document.getElementById('analise-auditor-sugestao');
    const camposContainer = document.getElementById('campos-sugestao-melhoria-auditor');
    
    function toggleCamposSugestaoAuditor() {
        if (!camposContainer) return;
        
        if (checkbox && checkbox.checked) {
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
    
    if (checkbox && textarea) {
        const sugestaoValue = analise.sugestao_melhoria || '';
        if (sugestaoValue.trim().toUpperCase() === 'NÃO APLICÁVEL NO MOMENTO') {
            checkbox.checked = true;
            textarea.disabled = true;
            textarea.style.backgroundColor = '#f5f5f5';
            textarea.style.color = '#999';
            toggleCamposSugestaoAuditor();
        } else {
            checkbox.checked = false;
            textarea.disabled = false;
            textarea.style.backgroundColor = '';
            textarea.style.color = '';
            toggleCamposSugestaoAuditor();
        }
    }

    // Limpar estado anterior
    setArquivoSelecionadoAuditor(null);
    setAnexoExistenteNomeAuditor(null);
    const evidenciaDiv = document.getElementById('evidencia-nome-auditor');
    const evidenciaTexto = document.getElementById('evidencia-nome-texto-auditor');
    
    if (analise.evidencias && analise.evidencias.length > 0) {
        const evidencia = analise.evidencias[0];
        setAnexoExistenteNomeAuditor(evidencia.nome_arquivo);
        
        if (evidenciaDiv && evidenciaTexto) {
            evidenciaTexto.textContent = evidencia.nome_arquivo;
            evidenciaDiv.style.display = 'flex';
        }
        
        document.getElementById('analise-auditor-id').setAttribute('data-evidencia-id', evidencia.id);
    } else {
        if (evidenciaDiv) evidenciaDiv.style.display = 'none';
        if (evidenciaTexto) evidenciaTexto.textContent = '';
        document.getElementById('analise-auditor-id').removeAttribute('data-evidencia-id');
    }
    
    // RADIOS
    const radios = document.querySelectorAll('#modal-analise-auditor input[name="sugestao-status-radio"]');
    let valorParaMarcar = '';
    
    console.log('📊 analise.sugestao_sera_implantada:', analise.sugestao_sera_implantada);
    
    if (analise.sugestao_sera_implantada === true) {
        valorParaMarcar = 'true';
    } else if (analise.sugestao_sera_implantada === false) {
        valorParaMarcar = 'false';
    } else {
        valorParaMarcar = '';
    }
    
    // Desmarcar todos
    radios.forEach(radio => {
        radio.checked = false;
    });
    
    // Marcar o correto
    radios.forEach(radio => {
        if (radio.value === valorParaMarcar) {
            radio.checked = true;
        }
    });
    
    console.log('🎯 valorParaMarcar:', valorParaMarcar);
    console.log('🎯 Radio checked:', document.querySelector('#modal-analise-auditor input[name="sugestao-status-radio"]:checked')?.value);
    
    // ABRIR MODAL
    document.getElementById('modal-analise-auditor').style.display = 'flex';
}

export async function excluirAnaliseAuditor(id) {
    if (!confirm('⚠️ Tem certeza que deseja excluir esta análise?')) return;
    try {
        const response = await fetchComAutenticacao(`/api/analise-auditor/${id}`, { method: 'DELETE' });
        const data = await response.json();
        if (data.success) {
            mostrarToast('✅ Análise excluída!', 'success');
            await carregarAnalisesAuditor();
        } else {
            mostrarToast('❌ Erro ao excluir', 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarToast('❌ Erro ao conectar', 'error');
    }
}

export function fecharModalAnaliseAuditor() {
    document.getElementById('modal-analise-auditor').style.display = 'none';
    
    // ⭐ NOVO: Limpar estado da evidência ao fechar o modal
    setArquivoSelecionadoAuditor(null);
    setAnexoExistenteNomeAuditor(null);
    
    // Limpar o campo de arquivo
    const inputFile = document.getElementById('anexo-evidencia-auditor');
    if (inputFile) inputFile.value = '';
    
    // Esconder a div de nome do arquivo
    const evidenciaDiv = document.getElementById('evidencia-nome-auditor');
    if (evidenciaDiv) evidenciaDiv.style.display = 'none';
    
    // Remover o hidden de remover evidência se existir
    const removerHidden = document.getElementById('remover-evidencia-hidden');
    if (removerHidden) removerHidden.remove();
    
    // Remover o atributo data-evidencia-id
    const analiseIdInput = document.getElementById('analise-auditor-id');
    if (analiseIdInput) analiseIdInput.removeAttribute('data-evidencia-id');
}

// ============================================================
// FUNÇÃO PARA UPLOAD DE EVIDÊNCIA DO AUDITOR
// ============================================================

export function setupFileUploadEvidenciaAuditor() {
    const btnSelecionar = document.getElementById('btn-selecionar-evidencia-auditor');
    const inputFile = document.getElementById('anexo-evidencia-auditor');
    const evidenciaDiv = document.getElementById('evidencia-nome-auditor');
    const evidenciaTexto = document.getElementById('evidencia-nome-texto-auditor');
    const btnRemover = document.getElementById('btn-remover-evidencia-auditor');
    
    if (!btnSelecionar || !inputFile) {
        console.warn('⚠️ Elementos de upload de evidência não encontrados');
        return;
    }
    
    // Botão para abrir seletor de arquivo
    btnSelecionar.addEventListener('click', (e) => { 
        e.preventDefault(); 
        inputFile.click(); 
    });
    
    // Quando selecionar um arquivo
    inputFile.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            // Validar tipo
            if (file.type !== 'application/pdf') {
                mostrarToast('⚠️ Apenas arquivos PDF são permitidos', 'warning');
                inputFile.value = '';
                return;
            }
            
            // Validar tamanho (10MB)
            if (file.size > 10 * 1024 * 1024) {
                mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
                inputFile.value = '';
                return;
            }
            
            // Armazenar o arquivo
            setArquivoSelecionadoAuditor(file);
            
            // Mostrar na interface
            if (evidenciaTexto) evidenciaTexto.textContent = file.name;
            if (evidenciaDiv) evidenciaDiv.style.display = 'flex';
            
            // Remover referência a arquivo existente
            setAnexoExistenteNomeAuditor(null);
            
            console.log('📎 Evidência selecionada:', file.name);
        }
    });
    
    // Botão para remover arquivo
    if (btnRemover) {
        btnRemover.addEventListener('click', (e) => {
            e.preventDefault();
            inputFile.value = '';
            setArquivoSelecionadoAuditor(null);
            if (evidenciaDiv) evidenciaDiv.style.display = 'none';
            if (evidenciaTexto) evidenciaTexto.textContent = '';
            
            // Marcar para remover anexo existente
            if (!document.getElementById('remover-evidencia-hidden')) {
                const hidden = document.createElement('input');
                hidden.type = 'hidden';
                hidden.id = 'remover-evidencia-hidden';
                hidden.value = 'true';
                document.getElementById('modal-analise-auditor').querySelector('.modal-body').appendChild(hidden);
            } else {
                document.getElementById('remover-evidencia-hidden').value = 'true';
            }
            
            console.log('🗑️ Evidência removida');
        });
    }
}

// ============================================================
// FUNÇÕES DE RISCOS E CONTROLES
// ============================================================

export function renderizarRiscosControles(analise) {
    const riscosControles = analise.riscos_controles || [];
    
    if (riscosControles.length === 0) {
        return `
            <div style="text-align: center; padding: 15px; color: #999; font-size: 13px;">
                Nenhum risco ou controle registrado nesta análise.
            </div>
        `;
    }
    
    let html = '<div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">';
    
    riscosControles.forEach((item, index) => {
        html += `
            <div style="background: #fafbfc; border: 1px solid #e8ecf0; border-radius: 10px; padding: 12px 15px;">
                <div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 6px;">
                    <!-- ⭐ ICONE NO LUGAR DO R1, R2... -->
                    <i class="fas fa-exclamation-triangle" style="color: #fd6a14; font-size: 14px; margin-top: 2px; flex-shrink: 0;"></i>
                    <span style="font-size: 13px; color: #333; font-weight: 500;">${escapeHtml(item.risco)}</span>
                </div>
                ${item.controles && item.controles.length > 0 ? `
                    <div style="margin-left: 24px; display: flex; flex-direction: column; gap: 4px;">
                        ${item.controles.map((controle) => `
                            <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #555;">
                                <i class="fas fa-shield-alt" style="color: #0b5b99; font-size: 10px;"></i>
                                <span>${escapeHtml(controle)}</span>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <div style="margin-left: 24px; font-size: 11px; color: #999; font-style: italic;">Nenhum controle sugerido</div>
                `}
            </div>
        `;
    });
    
    html += '</div>';
    return html;
}

export function toggleEditorRiscos(analiseId) {
    const editorDiv = document.getElementById(`editor-riscos-${analiseId}`);
    if (!editorDiv) return;
    
    if (editorDiv.style.display === 'block') {
        editorDiv.style.display = 'none';
        return;
    }
    
    const analise = analisesAuditorList.find(a => a.id === analiseId);
    if (!analise) return;
    
    const riscosControles = analise.riscos_controles || [];
    
    let html = `
        <div style="background: #fafbfc; border-radius: 10px; padding: 15px; border: 1px solid #e8ecf0;">
            <h5 style="margin-bottom: 12px; color: #184145;">Editar Riscos e Controles</h5>
            <div id="lista-riscos-${analiseId}">
    `;
    
    if (riscosControles.length === 0) {
        html += `<div style="text-align: center; color: #999; padding: 10px; font-size: 13px;">Nenhum risco cadastrado. Adicione abaixo.</div>`;
    }
    
    html += `
            </div>
            <button class="btn-adicionar-risco" data-analise="${analiseId}" style="margin-top: 10px; background: #fd6a14; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                <i class="fas fa-plus"></i> Adicionar Risco
            </button>
            <div style="margin-top: 15px; text-align: right; border-top: 1px solid #e0e0e0; padding-top: 12px;">
                <button class="btn-cancelar-editor" data-analise="${analiseId}" style="background: #6c757d; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; margin-right: 8px;">
                    Cancelar
                </button>
                <button class="btn-salvar-riscos" data-analise="${analiseId}" style="background: #184145; color: white; border: none; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px;">
                    <i class="fas fa-save"></i> Salvar
                </button>
            </div>
        </div>
    `;
    
    editorDiv.innerHTML = html;
    editorDiv.style.display = 'block';
    
    // ⭐ Vincular botões principais (só uma vez)
    const btnAddRisco = editorDiv.querySelector('.btn-adicionar-risco');
    if (btnAddRisco) btnAddRisco.addEventListener('click', () => adicionarRisco(analiseId));
    
    const btnCancelar = editorDiv.querySelector('.btn-cancelar-editor');
    if (btnCancelar) btnCancelar.addEventListener('click', () => toggleEditorRiscos(analiseId));
    
    const btnSalvar = editorDiv.querySelector('.btn-salvar-riscos');
    if (btnSalvar) btnSalvar.addEventListener('click', () => salvarRiscosControles(analiseId));
    
    // ⭐ Preencher riscos existentes (cada um vincula seus próprios eventos)
    riscosControles.forEach((item, index) => {
        adicionarRiscoNaLista(analiseId, index, item.risco, item.controles || []);
    });
    
    // ❌ REMOVA TODO O BLOCO ABAIXO (duplicação):
    // editorDiv.querySelectorAll('.btn-remover-risco')...
    // editorDiv.querySelectorAll('.btn-adicionar-controle')...
    // editorDiv.querySelectorAll('.btn-remover-controle')...
}

export function adicionarRisco(analiseId) {
    if (!window.contadorRiscosTemp) window.contadorRiscosTemp = {};
    if (!window.contadorRiscosTemp[analiseId]) window.contadorRiscosTemp[analiseId] = 0;
    const index = window.contadorRiscosTemp[analiseId];
    window.contadorRiscosTemp[analiseId]++;
    adicionarRiscoNaLista(analiseId, index, '', []);
}

export function adicionarRiscoNaLista(analiseId, index, riscoTexto, controles) {
    const lista = document.getElementById(`lista-riscos-${analiseId}`);
    if (!lista) return;
    
    const emptyMsg = lista.querySelector('div[style*="color: #999"]');
    if (emptyMsg) emptyMsg.remove();
    
    if (!window.contadorRiscosTemp) window.contadorRiscosTemp = {};
    if (!window.contadorRiscosTemp[analiseId] || window.contadorRiscosTemp[analiseId] <= index) {
        window.contadorRiscosTemp[analiseId] = index + 1;
    }
    
    const div = document.createElement('div');
    div.id = `risco-item-${analiseId}-${index}`;
    div.dataset.riscoIndex = index;
    div.style.cssText = 'background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;';
    div.innerHTML = `
        <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 6px;">
            <i class="fas fa-exclamation-triangle" style="color: #fd6a14; font-size: 14px; flex-shrink: 0;"></i>
            <textarea class="risco-input" data-analise="${analiseId}" data-index="${index}" 
                placeholder="Descreva o risco identificado..." 
                style="flex: 1; padding: 6px 10px; border: 1px solid #e0e0e0; border-radius: 6px; font-size: 12px; resize: vertical; min-height: 60px; font-family: inherit;"
            >${escapeHtml(riscoTexto)}</textarea>
            <button class="btn-remover-risco" data-analise="${analiseId}" data-index="${index}" 
                style="background: none; border: none; color: #dc3545; cursor: pointer; font-size: 14px;">
                <i class="fas fa-trash-alt"></i>
            </button>
        </div>
        <div id="controles-risco-${analiseId}-${index}" class="controles-container" 
            data-analise="${analiseId}" data-risco="${index}" 
            style="margin-left: 24px;">
            ${controles.map((c, cIndex) => `
                <div class="controle-item" data-controle="${cIndex}" style="display: flex; gap: 6px; align-items: center; margin-bottom: 4px;">
                    <i class="fas fa-shield-alt" style="color: #0b5b99; font-size: 10px;"></i>
                    <textarea class="controle-input" data-analise="${analiseId}" data-risco="${index}" data-controle="${cIndex}"
                        placeholder="Descreva o controle sugerido..."
                        style="flex: 1; padding: 5px 8px; border: 1px solid #e0e0e0; border-radius: 4px; font-size: 11px; resize: vertical; min-height: 50px; font-family: inherit; line-height: 1.4;"
                    >${escapeHtml(c)}</textarea>
                    <button class="btn-remover-controle" data-analise="${analiseId}" data-risco="${index}" data-controle="${cIndex}"
                        style="background: none; border: none; color: #dc3545; cursor: pointer; font-size: 12px;">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `).join('')}
        </div>
        <button class="btn-adicionar-controle" data-analise="${analiseId}" data-risco="${index}"
            style="margin-left: 24px; background: none; border: 1px dashed #0b5b99; color: #0b5b99; padding: 3px 10px; border-radius: 4px; cursor: pointer; font-size: 11px;">
            <i class="fas fa-plus"></i> Controle
        </button>
    `;
    
    lista.appendChild(div);
    
    // ⭐ Vincular eventos
    const btnRemoverRisco = div.querySelector('.btn-remover-risco');
    if (btnRemoverRisco) {
        btnRemoverRisco.addEventListener('click', function() {
            const idx = parseInt(this.dataset.index);
            removerRisco(analiseId, idx);
        });
    }
    
    const btnAddControle = div.querySelector('.btn-adicionar-controle');
    if (btnAddControle) {
        btnAddControle.addEventListener('click', function() {
            const riscoIdx = parseInt(this.dataset.risco);
            adicionarControle(analiseId, riscoIdx);
        });
    }
    
    // ⭐ Vincula remover controle
    div.querySelectorAll('.btn-remover-controle').forEach(btn => {
        btn.addEventListener('click', function() {
            const riscoIdx = parseInt(this.dataset.risco);
            const controleIdx = parseInt(this.dataset.controle);
            // ⭐ Remove APENAS o elemento pai (o controle específico)
            this.closest('.controle-item').remove();
        });
    });
}

export function removerRisco(analiseId, index) {
    const item = document.getElementById(`risco-item-${analiseId}-${index}`);
    if (item) item.remove();
}

export function adicionarControle(analiseId, riscoIndex) {
    const key = `${analiseId}-${riscoIndex}`;
    if (!window.contadorControlesTemp) window.contadorControlesTemp = {};
    if (!window.contadorControlesTemp[key]) window.contadorControlesTemp[key] = 0;
    const cIndex = window.contadorControlesTemp[key];
    window.contadorControlesTemp[key]++;
    
    const container = document.getElementById(`controles-risco-${analiseId}-${riscoIndex}`);
    if (!container) return;
    
    const div = document.createElement('div');
    div.className = 'controle-item';
    div.dataset.controle = cIndex;  // ⭐ data-controle (não data-controle-index)
    div.style.cssText = 'display: flex; gap: 6px; align-items: center; margin-bottom: 4px;';
    div.innerHTML = `
        <i class="fas fa-shield-alt" style="color: #0b5b99; font-size: 10px;"></i>
        <textarea class="controle-input auto-resize" data-analise="${analiseId}" data-risco="${riscoIndex}" data-controle="${cIndex}"
            placeholder="Descreva o controle sugerido..."
            style="flex: 1; padding: 5px 8px; border: 1px solid #e0e0e0; border-radius: 4px; font-size: 11px; resize: vertical; min-height: 50px; max-height: 150px; font-family: inherit; line-height: 1.4; overflow: hidden;"
        ></textarea>
        <button class="btn-remover-controle" data-analise="${analiseId}" data-risco="${riscoIndex}" data-controle="${cIndex}"
            style="background: none; border: none; color: #dc3545; cursor: pointer; font-size: 12px;">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(div);
    
    // ⭐ Vincula remover - remove APENAS o próprio controle
    const btnRemover = div.querySelector('.btn-remover-controle');
    if (btnRemover) {
        btnRemover.addEventListener('click', function() {
            // Remove apenas o elemento pai (o controle específico)
            this.closest('.controle-item').remove();
        });
    }
}

export function removerControle(analiseId, riscoIndex, controleIndex) {
    const container = document.getElementById(`controles-risco-${analiseId}-${riscoIndex}`);
    if (!container) return;
    
    // ⭐ Buscar TODOS os controles deste risco
    const controles = container.querySelectorAll('.controle-item');
    
    // ⭐ Encontrar o controle específico pelo data-controle
    controles.forEach(controle => {
        if (controle.dataset.controleIndex === String(controleIndex)) {
            controle.remove();
        }
    });
}

export async function salvarRiscosControles(analiseId) {
    console.log('💾 Salvando riscos e controles da análise:', analiseId);
    
    const riscosContainer = document.getElementById(`lista-riscos-${analiseId}`);
    if (!riscosContainer) return;
    
    const riscos = [];
    const riscoInputs = riscosContainer.querySelectorAll('.risco-input');
    
    riscoInputs.forEach(input => {
        const riscoTexto = input.value.trim();
        const riscoIndex = input.dataset.index;
        if (!riscoTexto) return;
        
        const controlesContainer = document.getElementById(`controles-risco-${analiseId}-${riscoIndex}`);
        const controles = [];
        
        if (controlesContainer) {
            controlesContainer.querySelectorAll('.controle-input').forEach(cInput => {
                const controleTexto = cInput.value.trim();
                if (controleTexto) controles.push(controleTexto);
            });
        }
        
        riscos.push({ risco: riscoTexto, controles: controles });
    });
    
    try {
        const response = await fetchComAutenticacao(`/api/analise-auditor/${analiseId}/riscos-controles`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ riscos_controles: riscos })
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarToast('✅ Riscos e controles salvos!', 'success');
            toggleEditorRiscos(analiseId);
            await carregarAnalisesAuditor();
        } else {
            mostrarToast('❌ Erro: ' + (data.error || 'Tente novamente'), 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao salvar:', error);
        mostrarToast('❌ Erro de conexão', 'error');
    }
}

// ============================================================
// ANÁLISES DO AUDITOR - RENDERIZAÇÃO
// ============================================================

export async function renderizarAnalisesAuditor() {
    const container = document.getElementById('analises-auditor-container');

    console.log('📊 analisesAuditorList:', analisesAuditorList);
    
    if (analisesAuditorList.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 40px; color: #999;">Nenhuma análise do auditor cadastrada.<br><br>
            <button class="btn-primary" onclick="abrirModalNovaAnaliseAuditor()"><i class="fas fa-plus"></i> Nova Análise</button></div>`;
        return;
    }
    
    const analisesComDados = [];
    for (const analise of analisesAuditorList) {
        analisesComDados.push({ 
            ...analise, 
            historico: [], 
            followUps: [] 
        });
    }
    
    let html = '';
    analisesComDados.forEach((analise, index) => {
        const temPlanoAcao = analise.sugestao_sera_implantada === true && analise.plano_acao;
        const prazoExpirado = analise.sugestao_sera_implantada === true &&
                            !analise.plano_de_acao_implantado && 
                            analise.data_conclusao_prevista && 
                            new Date(analise.data_conclusao_prevista) < new Date();
        
        // ⭐⭐⭐ CORREÇÃO AQUI ⭐⭐⭐
        // Verificar tanto o array 'evidencias' quanto os campos individuais
        const temEvidenciaArray = analise.evidencias && analise.evidencias.length > 0;
        const temEvidenciaIndividual = analise.evidencia_url && analise.evidencia_url.trim() !== '';
        const temEvidencia = temEvidenciaArray || temEvidenciaIndividual;
        
        console.log(`📊 Análise ${analise.id}: temEvidenciaArray=${temEvidenciaArray}, temEvidenciaIndividual=${temEvidenciaIndividual}, temEvidencia=${temEvidencia}`);
        
        // ⭐⭐⭐ CONSTRUIR LISTA DE EVIDÊNCIAS ⭐⭐⭐
        let listaEvidencias = [];
        if (temEvidenciaArray) {
            listaEvidencias = analise.evidencias;
        } else if (temEvidenciaIndividual) {
            listaEvidencias = [{
                id: analise.id,
                nome_arquivo: analise.evidencia_nome || 'evidencia.pdf',
                caminho_arquivo: analise.evidencia_url
            }];
        }
        
        const valoresSemSugestao = ['', ' ', 'null', 'undefined', 'inexistente', 'INEXISTENTE', 'não se aplica', 'NÃO SE APLICA', 'NÃO APLICÁVEL NO MOMENTO'];
        const temSugestaoMelhoria = analise.sugestao_melhoria && 
                                typeof analise.sugestao_melhoria === 'string' && 
                                !valoresSemSugestao.includes(analise.sugestao_melhoria.trim().toLowerCase());
        
        let badgeHtml = '';
        if (temSugestaoMelhoria) {
            if (analise.sugestao_sera_implantada === true) {
                badgeHtml = '<span class="analise-auditor-badge badge-implantada"><i class="fas fa-check-circle"></i>Sugestão de melhoria será implantada</span>';
            } else if (analise.sugestao_sera_implantada === false) {
                badgeHtml = '<span class="analise-auditor-badge badge-nao-implantada"><i class="fas fa-times-circle"></i> Sugestão de melhoria não será implantada</span>';
            } else {
                badgeHtml = '<span class="analise-auditor-badge badge-pendente"><i class="fas fa-clock"></i> Sugestão de melhorias aguardando avaliação</span>';
            }
        }
        
        html += `<div class="analise-auditor-card" data-analise-id="${analise.id}">
            <div class="analise-auditor-header" onclick="toggleAnaliseAuditorCard(this)">
                <div class="analise-auditor-header-left">
                    <span class="analise-auditor-titulo"><i class="fas fa-file-alt"></i> Análise ${index + 1}</span>
                    <span class="analise-auditor-data"><i class="far fa-calendar-alt"></i> ${new Date(analise.created_at).toLocaleDateString('pt-BR')}</span>
                    ${badgeHtml}
                    ${temEvidencia ? '<span style="color: #0b5b99; font-size: 12px;"><i class="fas fa-paperclip"></i> Evidência</span>' : ''}
                </div>
                <div class="analise-auditor-actions" onclick="event.stopPropagation()">
                    <button class="btn-edit-analise-auditor" onclick="editarAnaliseAuditor(${analise.id})" title="Editar análise"><i class="fas fa-pencil-alt"></i></button>
                    <button class="btn-delete-analise-auditor" onclick="excluirAnaliseAuditor(${analise.id})" title="Excluir análise"><i class="fas fa-trash-alt"></i></button>
                    <i class="fas fa-chevron-down" style="color: white; margin-left: 5px;"></i>
                </div>
            </div>
            <div class="analise-auditor-body">
                <div class="analise-grid">
                    <div class="analise-card-section"><h4 class="cor-ponto-de-auditoria"><i class="fas fa-clipboard-list"></i> Ponto de Auditoria</h4><div class="analise-texto">${escapeHtml(analise.analise_critica) || '-'}</div></div>
                    <div class="analise-card-section"><h4 class="cor-sugestao-de-melhoria"><i class="fas fa-lightbulb"></i> Sugestão de Melhoria</h4><div class="analise-texto">${escapeHtml(analise.sugestao_melhoria) || '-'}</div></div>
                </div>
                
                ${temEvidencia ? `
                <div class="analise-card-section" style="margin-top: 20px; border-left: 3px solid #0b5b99; background: #f0f7ff; padding: 15px; border-radius: 8px;">
                    <h4 style="margin-bottom: 10px; color: #0b5b99;">
                        <i class="fas fa-paperclip"></i> Evidências da Análise
                    </h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px;">
                        ${listaEvidencias.map(ev => `
                            <div style="display: flex; align-items: center; gap: 8px; background: white; padding: 8px 12px; border-radius: 8px; border: 1px solid #e0e0e0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                                <i class="fas fa-file-pdf" style="color: #dc3545; font-size: 16px;"></i>
                                <span style="font-size: 13px; color: #333; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(ev.nome_arquivo)}">
                                    ${escapeHtml(ev.nome_arquivo)}
                                </span>
                                <button class="btn-download-anexo" 
                                        data-evidencia-id="${ev.id}" 
                                        data-nome-arquivo="${escapeHtml(ev.nome_arquivo)}"
                                        style="padding: 4px 12px; font-size: 11px; background: #0b5b99; border-radius: 6px; border: none; color: white; cursor: pointer;">
                                    <i class="fas fa-download"></i>
                                </button>
                                <!-- ⭐ BOTÃO DE REMOVER -->
                                <button class="btn-remove-evidencia" 
                                        data-analise-id="${ev.id}"
                                        style="padding: 4px 12px; font-size: 11px; background: #dc3545; border-radius: 6px; border: none; color: white; cursor: pointer;">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
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
                
                <div class="analise-grid">
                    <div class="analise-card-section"><h4 class="cor-necessidade-para-implantacao"><i class="fas fa-tasks"></i> Necessidade para implantação da sugestão de melhoria</h4><div class="analise-texto">${escapeHtml(analise.necessidade_implantacao) || '-'}</div></div>
                    <div class="analise-card-section"><h4 class="cor-ganho-previsto"><i class="fas fa-chart-line"></i> Ganho Previsto</h4><div class="analise-texto">${escapeHtml(analise.ganho_previsto) || '-'}</div></div>
                </div>
                ${analise.observacoes ? `<div class="analise-card-section"><h4><i class="fas fa-comment"></i> Recomendações GRC</h4><div class="analise-texto">${escapeHtml(analise.observacoes)}</div></div>` : ''}
                
                ${analise.sugestao_sera_implantada === true && !analise.plano_de_acao_implantado ? `
                <div class="analise-card-section" style="margin-top: 20px; text-align: center; background: #e8f4f8; border-left: 4px solid #0b5b99; border-radius: 12px;">
                    <div style="padding: 15px;">
                        <i class="fas fa-check-circle" style="color: #0b5b99; font-size: 24px;"></i>
                        <p style="margin: 10px 0; color: #0b5b99; font-weight: 500;">Esta melhoria está aguardando confirmação de implantação</p>
                        <button class="btn-primary" onclick="abrirModalConfirmarImplantacao(${analise.id})" style="background: #0b5b99; border-radius: 30px;">
                            <i class="fas fa-check-circle"></i> Confirmar Implantação
                        </button>
                    </div>
                </div>
                ` : ''}
                
                ${prazoExpirado ? `
                <div class="analise-card-section" style="margin-top: 20px; text-align: center; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 12px;">
                    <div style="padding: 15px;">
                        <i class="fas fa-clock" style="color: #856404; font-size: 24px;"></i>
                        <p style="margin: 10px 0; color: #856404; font-weight: 500;">Prazo de implantação expirado em ${formatarData(analise.data_conclusao_prevista)}</p>
                        <button class="btn-primary" onclick="abrirModalConfirmarImplantacao(${analise.id})" style="background: #856404; border-radius: 30px;">
                            <i class="fas fa-check-circle"></i> Confirmar Situação
                        </button>
                    </div>
                </div>
                ` : ''}
                
                ${analise.plano_de_acao_implantado === true ? `
                <div class="analise-card-section" style="margin-top: 20px;">
                    <h4><i class="fas fa-search"></i> Follow-ups Agendados</h4>
                    <div class="followups-container">
                        ${renderizarListaFollowUps(analise.followUps)}
                    </div>
                </div>
                ` : ''}

                <!-- ⭐ NOVA SEÇÃO: Riscos e Controles -->
                <div class="analise-card-section" style="border-left: 3px solid #fd6a14; margin-top: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h4 style="margin: 0;"><i class="fas fa-exclamation-triangle"></i> Riscos Identificados e Controles Sugeridos pelo Auditor</h4>
                        <button class="btn-primary" onclick="event.stopPropagation(); window.toggleEditorRiscos(${analise.id})" style="font-size: 12px; padding: 6px 12px;">
                            <i class="fas fa-plus"></i> Gerenciar
                        </button>
                    </div>
                    ${renderizarRiscosControles(analise)}
                    <div id="editor-riscos-${analise.id}" style="display: none; margin-top: 12px;"></div>
                </div>

            </div>
        </div>`;
    });
    container.innerHTML = html;

    // ⭐ ADICIONAR EVENT LISTENERS PARA OS BOTÕES DE DOWNLOAD
    container.querySelectorAll('.btn-download-anexo').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const evidenciaId = this.dataset.evidenciaId;
            const nomeArquivo = this.dataset.nomeArquivo;
            console.log('🔽 Clique no download:', evidenciaId, nomeArquivo);
            baixarEvidenciaAnaliseAuditor(evidenciaId, nomeArquivo);
        });
    });

    // ⭐ ADICIONAR EVENT LISTENERS PARA OS BOTÕES DE REMOVER
    container.querySelectorAll('.btn-remove-evidencia').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const analiseId = this.dataset.analiseId;
            console.log('🗑️ Clique em remover evidência (auditor):', analiseId);
            removerEvidenciaAnaliseAuditor(analiseId);
        });
    });
}

// ============================================================
// FUNÇÃO PARA BAIXAR EVIDÊNCIA DA ANÁLISE DO AUDITOR
// ============================================================

export async function baixarEvidenciaAnaliseAuditor(evidenciaId, nomeArquivo) {
    try {
        console.log('📥 Baixando evidência:', evidenciaId, nomeArquivo);
        
        // ⭐ MOSTRAR LOADING
        mostrarToast('⏳ Baixando arquivo...', 'info');
        
        const response = await fetchComAutenticacao(`/api/analise-auditor/evidencia/${evidenciaId}/download`);
        
        console.log('📥 Status da resposta:', response.status);
        console.log('📥 Headers:', response.headers);
        
        if (!response.ok) {
            let errorMsg = 'Erro ao baixar evidência';
            try {
                const errorData = await response.json();
                errorMsg = errorData.error || errorMsg;
                console.log('❌ Erro do servidor:', errorData);
            } catch (e) {
                const text = await response.text();
                console.log('❌ Resposta não-JSON:', text);
                errorMsg = `Erro ${response.status}: ${response.statusText}`;
            }
            mostrarToast('❌ ' + errorMsg, 'error');
            return;
        }
        
        // ⭐ VERIFICAR O TIPO DE CONTEÚDO
        const contentType = response.headers.get('content-type') || '';
        console.log('📄 Content-Type:', contentType);
        
        // Se a resposta for JSON, é um erro
        if (contentType.includes('application/json')) {
            const errorData = await response.json();
            mostrarToast('❌ ' + (errorData.error || 'Erro ao baixar'), 'error');
            return;
        }
        
        // ⭐ OBTER O BLOB
        const blob = await response.blob();
        console.log('📄 Tamanho do blob:', blob.size, 'bytes');
        console.log('📄 Tipo do blob:', blob.type);
        
        // Verificar se o blob é válido
        if (blob.size === 0) {
            mostrarToast('❌ Arquivo vazio ou corrompido', 'error');
            return;
        }
        
        // Verificar se o blob parece ser um PDF
        if (blob.type && !blob.type.includes('pdf')) {
            console.warn('⚠️ Content-Type não é PDF:', blob.type);
            // Ainda tenta baixar, mas com aviso
        }
        
        // ⭐ CRIAR URL PARA DOWNLOAD
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = nomeArquivo || `evidencia_${evidenciaId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Limpar URL após o download
        setTimeout(() => {
            window.URL.revokeObjectURL(url);
        }, 1000);
        
        mostrarToast('✅ Download iniciado!', 'success');
        
    } catch (error) {
        console.error('❌ Erro ao baixar evidência:', error);
        mostrarToast('❌ Erro ao baixar evidência: ' + error.message, 'error');
    }
}

export function abrirModalConfirmarImplantacao(analiseId) {
    document.getElementById('confirmar-analise-id').value = analiseId;
    document.getElementById('confirmar-analise-id').setAttribute('data-tipo', 'auditor');
    document.getElementById('confirmar-status').value = 'true';
    document.getElementById('confirmar-data').value = new Date().toISOString().split('T')[0];
    document.getElementById('confirmar-comentario').value = '';
    document.getElementById('modal-confirmar-implantacao').style.display = 'flex';
}

export function fecharModalConfirmarImplantacao() {
    document.getElementById('modal-confirmar-implantacao').style.display = 'none';
}

export async function confirmarImplantacao() {
    const analiseId = document.getElementById('confirmar-analise-id').value;
    const tipoAnalise = document.getElementById('confirmar-analise-id').getAttribute('data-tipo') || 'auditor';
    const foiImplantada = document.getElementById('confirmar-status').value === 'true';
    const dataImplantacao = document.getElementById('confirmar-data').value;
    const comentario = document.getElementById('confirmar-comentario').value;
    
    if (!dataImplantacao) {
        mostrarToast('⚠️ Informe a data da implantação', 'warning');
        return;
    }
    
    const btnConfirmar = document.getElementById('btn-confirmar-implantacao');
    const textoOriginal = btnConfirmar.innerHTML;
    btnConfirmar.disabled = true;
    btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Confirmando...';
    
    const url = tipoAnalise === 'auditado' ? `/api/analise-auditado/${analiseId}/confirmar-implantacao` : `/api/analise-auditor/${analiseId}/confirmar-implantacao`;
    
    try {
        const response = await fetchComAutenticacao(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                plano_de_acao_implantado: foiImplantada, 
                data_execucao_plano_acao: dataImplantacao, 
                comentario_implantacao: comentario 
            })
        });
        const data = await response.json();
        if (data.success) {
            mostrarToast(foiImplantada ? '✅ Implantação confirmada! Follow-ups liberados.' : '❌ Implantação não confirmada.', 'success');
            fecharModalConfirmarImplantacao();
            // ⭐ REMOVIDO: criarFollowUpsAutomaticos (backend já faz isso)
            if (tipoAnalise === 'auditado') await carregarAnalisesAuditado();
            else await carregarAnalisesAuditor();
        } else {
            mostrarToast('❌ Erro ao confirmar: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarToast('❌ Erro ao conectar com o servidor', 'error');
    } finally {
        btnConfirmar.disabled = false;
        btnConfirmar.innerHTML = textoOriginal;
        document.getElementById('confirmar-analise-id').removeAttribute('data-tipo');
    }
}

export async function carregarAnalisesAuditor() {
    if (!processoIdAtual) return;
    const container = document.getElementById('analises-auditor-container');
    container.innerHTML = '<div style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin"></i> Carregando análises...</div>';
    try {
        const response = await fetchComAutenticacao(`/api/analises-auditor/por-processo?processo_id=${processoIdAtual}`);
        const data = await response.json();
        if (data.success && data.analises && data.analises.length > 0) {
            // ⭐ BUSCAR PLANO DE AÇÃO PARA CADA ANÁLISE
            for (const analise of data.analises) {
                if (analise.sugestao_sera_implantada === true) {
                    try {
                        const planoResponse = await fetchComAutenticacao(`/api/planos-acao/${analise.id}`);
                        const planoData = await planoResponse.json();
                        if (planoData.success && planoData.plano) {
                            analise.plano = planoData.plano;
                        }
                    } catch (err) {
                        console.warn(`⚠️ Erro ao carregar plano da análise ${analise.id}:`, err);
                    }
                }
                
                // ⭐⭐⭐ NOVO: CARREGAR EVIDÊNCIAS DA ANÁLISE ⭐⭐⭐
                try {
                    const evidenciaResponse = await fetchComAutenticacao(`/api/analise-auditor/${analise.id}/evidencias`);
                    const evidenciaData = await evidenciaResponse.json();
                    if (evidenciaData.success && evidenciaData.evidencias) {
                        analise.evidencias = evidenciaData.evidencias;
                    } else {
                        analise.evidencias = [];
                    }
                } catch (err) {
                    console.warn(`⚠️ Erro ao carregar evidências da análise ${analise.id}:`, err);
                    analise.evidencias = [];
                }
            }
            
            setAnalisesAuditorList(data.analises);
            renderizarAnalisesAuditor();
        } else {
            container.innerHTML = `<div style="text-align: center; padding: 40px; color: #999;">Nenhuma análise do auditor cadastrada.<br><br>
                <button class="btn-primary" onclick="abrirModalNovaAnaliseAuditor()"><i class="fas fa-plus"></i> Nova Análise</button></div>`;
        }
    } catch (error) {
        console.error('❌ Erro ao carregar análises do auditor:', error);
        container.innerHTML = `<div class="alert-error">❌ Erro ao carregar análises: ${error.message}</div>`;
    }
}



// ============================================================
// CONTROLE DO CHECKBOX "SEM SUGESTÃO DE MELHORIA" - AUDITOR
// ============================================================

export function setupSemSugestaoCheckboxAuditor() {
    const checkbox = document.getElementById('sem_sugestao_melhoria_auditor');
    const textarea = document.getElementById('analise-auditor-sugestao');
    const camposContainer = document.getElementById('campos-sugestao-melhoria-auditor');
    
    if (!checkbox || !textarea || !camposContainer) return;
    
    function toggleCamposSugestaoAuditor() {
        if (checkbox.checked) {
            // ⭐ ESCONDER CAMPOS
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
            // ⭐ MOSTRAR CAMPOS
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
    
    checkbox.addEventListener('change', function() {
        if (this.checked) {
            textarea.value = 'NÃO APLICÁVEL NO MOMENTO';
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
        toggleCamposSugestaoAuditor();
    });
    
    textarea.addEventListener('input', function() {
        if (this.value.trim() !== '' && this.value.trim().toUpperCase() !== 'NÃO APLICÁVEL NO MOMENTO') {
            checkbox.checked = false;
            toggleCamposSugestaoAuditor();
        }
    });
    
    // Se o checkbox já estiver marcado ao carregar
    if (checkbox.checked) {
        toggleCamposSugestaoAuditor();
    }
}

export async function salvarAnaliseAuditor() {
    if (!processoIdAtual) {
        mostrarToast('❌ Selecione um processo primeiro', 'warning');
        return;
    }
    
    const analiseId = document.getElementById('analise-auditor-id').value;
    const radioSelecionado = document.querySelector('#modal-analise-auditor input[name="sugestao-status-radio"]:checked');
    
    let seraImplantada = null;
    if (radioSelecionado) {
        if (radioSelecionado.value === 'true') seraImplantada = true;
        else if (radioSelecionado.value === 'false') seraImplantada = false;
        else seraImplantada = null;
    }
    
    const analiseCritica = document.getElementById('analise-auditor-texto').value;
    if (!analiseCritica.trim()) {
        mostrarToast('⚠️ O Ponto de Auditoria é obrigatório', 'warning');
        return;
    }
    
    // ⭐⭐⭐ USAR JSON EM VEZ DE FormData ⭐⭐⭐
    const payload = {
        processo_id: parseInt(processoIdAtual),
        analise_critica: analiseCritica,
        sugestao_melhoria: document.getElementById('analise-auditor-sugestao').value || '',
        necessidade_implantacao: document.getElementById('analise-auditor-necessidade').value || '',
        ganho_previsto: document.getElementById('analise-auditor-ganho').value || '',
        observacoes: document.getElementById('analise-auditor-observacoes').value || '',
        sugestao_sera_implantada: seraImplantada  // ⭐ PODE SER true, false OU null
    };
    
    
    // ⭐ REMOVER CAMPOS ANTIGOS (plano_acao, responsavel_implantacao, etc.)
    // Eles não existem mais na tabela analises_criticas
    
    // ⭐ Processar evidência (se houver)
    if (arquivoSelecionadoAuditor) {
        try {
            const base64 = await converterParaBase64(arquivoSelecionadoAuditor);
            payload.evidencia_base64 = base64;
            payload.evidencia_nome = arquivoSelecionadoAuditor.name;
        } catch (error) {
            console.error('Erro ao converter evidência:', error);
            mostrarToast('❌ Erro ao processar evidência', 'error');
            return;
        }
    }
    
    // ⭐ Remover evidência se solicitado
    const removerEvidencia = document.getElementById('remover-evidencia-hidden')?.value === 'true';
    if (removerEvidencia) {
        payload.remover_evidencia = true;
    }
    
    const btnSalvar = document.getElementById('btn-salvar-analise-auditor');
    const textoOriginal = btnSalvar.innerHTML;
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    
    try {
        const url = analiseId ? `/api/analise-auditor/${analiseId}` : '/api/analise-auditor/salvar';
        const method = analiseId ? 'PUT' : 'POST';
        
        // ⭐ USAR JSON EM VEZ DE FormData
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
            mostrarToast(analiseId ? '✅ Análise atualizada!' : '✅ Análise salva!', 'success');
            fecharModalAnaliseAuditor();
            
            // Limpar estado da evidência
            setArquivoSelecionadoAuditor(null);
            setAnexoExistenteNomeAuditor(null);
            document.getElementById('remover-evidencia-hidden')?.remove();
            
            await carregarAnalisesAuditor();
        } else {
            mostrarToast('❌ Erro: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarToast('❌ Erro ao conectar: ' + error.message, 'error');
    } finally {
        btnSalvar.disabled = false;
        btnSalvar.innerHTML = textoOriginal;
    }
}

// ============================================================
// FUNÇÃO PARA REMOVER EVIDÊNCIA DO AUDITOR
// ============================================================

export async function removerEvidenciaAnaliseAuditor(analiseId) {
    if (!confirm('⚠️ Tem certeza que deseja remover esta evidência?')) return;
    
    try {
        mostrarToast('⏳ Removendo evidência...', 'info');
        
        const response = await fetchComAutenticacao(`/api/analise-auditor/${analiseId}/evidencia`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            mostrarToast('✅ Evidência removida com sucesso!', 'success');
            
            // ⭐ RECARREGAR AS ANÁLISES
            await carregarAnalisesAuditor();
        } else {
            mostrarToast('❌ Erro ao remover evidência: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao remover evidência:', error);
        mostrarToast('❌ Erro ao conectar com o servidor', 'error');
    }
}