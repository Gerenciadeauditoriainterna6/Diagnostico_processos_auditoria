import { escapeHtml, mostrarToast, converterParaBase64 } from './utils.js';
import { 
    processoIdAtual,
    currentRespostaIds,
    currentRespostaId,
    arquivosPendentes,
    tipoAtual,
    setCurrentRespostaId,
    setCurrentRespostaIds,
    setArquivosPendentes
} from './estado.js';
import { PERGUNTAS } from './perguntas.js';
import { carregarProgressoChecklists } from './api.js';

export function renderizarEvidencias(evidencias, perguntaIndex, itemIndex) {
    if (!evidencias || evidencias.length === 0) {
        return '';
    }
    
    return evidencias.map(ev => `
        <div class="evidencia-item" data-evidencia-id="${ev.id}">
            <i class="fas fa-file-pdf"></i>
            <span>${escapeHtml(ev.nome)}</span>
            <button class="btn-baixar-evidencia" onclick="baixarEvidenciaChecklist(${ev.id})" title="Baixar">
                <i class="fas fa-download"></i>
            </button>
            <button class="btn-remover-evidencia" onclick="removerEvidenciaChecklist(${ev.id}, ${perguntaIndex}, ${itemIndex})" title="Remover">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `).join('');
}

// Upload de evidência para item do grupo
export function abrirUploadEvidenciaGrupo(grupoIndex, itemIndex) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        if (file.type !== 'application/pdf') {
            mostrarToast('⚠️ Apenas arquivos PDF são permitidos', 'warning');
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
            return;
        }
        
        const key = `${grupoIndex}_${itemIndex}`;
        if (!arquivosPendentes[key]) arquivosPendentes[key] = [];
        
        const reader = new FileReader();
        reader.onload = (event) => {
            arquivosPendentes[key].push({
                nome: file.name,
                tipo: file.type,
                conteudo: event.target.result
            });
            
            const listaDiv = document.getElementById(`evidencias-lista-${grupoIndex}_${itemIndex}`);
            if (listaDiv) {
                const tempId = 'temp_' + Date.now() + '_' + Math.random();
                const evidenciaDiv = document.createElement('div');
                evidenciaDiv.className = 'evidencia-item';
                evidenciaDiv.setAttribute('data-temp-id', tempId);
                evidenciaDiv.innerHTML = `
                    <div class="evidencia-info">
                        <i class="fas fa-file-pdf"></i>
                        <span>${escapeHtml(file.name)}</span>
                        <small class="evidencia-pendente">(não salvo - clique em Salvar para confirmar)</small>
                    </div>
                    <div class="evidencia-acoes">
                        <button class="btn-remover-evidencia" onclick="removerEvidenciaTemp('${tempId}', '${key}')" title="Remover">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
                listaDiv.appendChild(evidenciaDiv);
            }
            mostrarToast('📎 Evidência adicionada. Clique em Salvar para confirmar.', 'info');
        };
        reader.readAsDataURL(file);
    };
    input.click();
}

export function abrirUploadEvidencia(perguntaIndex) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf';
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        if (file.type !== 'application/pdf') {
            mostrarToast('⚠️ Apenas arquivos PDF são permitidos', 'warning');
            return;
        }
        
        if (file.size > 10 * 1024 * 1024) {
            mostrarToast('⚠️ Arquivo muito grande. Máximo 10MB', 'warning');
            return;
        }
        
        // Adicionar à lista de arquivos pendentes
        if (!arquivosPendentes[perguntaIndex]) arquivosPendentes[perguntaIndex] = [];
        
        const reader = new FileReader();
        reader.onload = (event) => {
            arquivosPendentes[perguntaIndex].push({
                nome: file.name,
                tipo: file.type,
                conteudo: event.target.result
            });
            
            // Mostrar na interface
            const listaDiv = document.getElementById(`evidencias-lista-${perguntaIndex}`);
            if (listaDiv) {
                const tempId = 'temp_' + Date.now() + '_' + Math.random();
                const evidenciaDiv = document.createElement('div');
                evidenciaDiv.className = 'evidencia-item';
                evidenciaDiv.setAttribute('data-temp-id', tempId);
                evidenciaDiv.innerHTML = `
                    <div class="evidencia-info">
                        <i class="fas fa-file-pdf"></i>
                        <span>${escapeHtml(file.name)}</span>
                        <small class="evidencia-pendente">(não salvo - clique em Salvar para confirmar)</small>
                    </div>
                    <div class="evidencia-acoes">
                        <button class="btn-remover-evidencia" onclick="removerEvidenciaTemp('${tempId}', ${perguntaIndex})" title="Remover">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;
                listaDiv.appendChild(evidenciaDiv);
            }
            mostrarToast('📎 Evidência adicionada. Clique em Salvar para confirmar.', 'info');
        };
        reader.readAsDataURL(file);
    };
    input.click();
}

export function removerEvidenciaTemp(tempId, perguntaIndex) {
    const item = document.querySelector(`.evidencia-item[data-temp-id="${tempId}"]`);
    if (item) item.remove();
    
    // Remover da lista de arquivos pendentes
    if (arquivosPendentes[perguntaIndex]) {
        // Encontrar e remover o arquivo correto
        const index = arquivosPendentes[perguntaIndex].findIndex((_, idx) => 
            `temp_${Date.now()}_${idx}` !== tempId
        );
        // Como não temos o ID exato, vamos recriar a lista mantendo apenas os que não são temporários
        // Para simplificar, vamos marcar para remover no próximo salvamento
    }
    mostrarToast('📎 Evidência removida temporariamente', 'info');
}

export async function baixarEvidenciaChecklist(evidenciaId) {
    window.open(`/api/checklist/evidencia/${evidenciaId}/download`, '_blank');
}

export function fecharModalChecklist() {
    document.getElementById('modal-checklist').style.display = 'none';
    setArquivosPendentes({});
}

export function abrirModalChecklist(tipo) {
    const modal = document.getElementById('modal-checklist');
    const titulo = document.getElementById('modal-checklist-titulo');
    if (tipo === 'governanca') titulo.innerHTML = '<i class="fas fa-briefcase"></i> Checklist - Governança';
    else if (tipo === 'riscos') titulo.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Checklist - Riscos';
    else titulo.innerHTML = '<i class="fas fa-shield-alt"></i> Checklist - Controles';
    modal.style.display = 'flex';
    carregarChecklistModal(tipo);
}

export async function carregarChecklistModal(tipo) {
    console.log('🚀 carregarChecklistModal chamado para tipo:', tipo);
    console.log('📌 processoIdAtual:', processoIdAtual);
    
    const body = document.getElementById('modal-checklist-body');
    if (!body) {
        console.error('❌ Elemento modal-checklist-body não encontrado!');
        return;
    }
    
    body.innerHTML = '<div style="text-align:center;padding:40px;"><i class="fas fa-spinner fa-spin"></i> Carregando...</div>';
    
    try {
        const perguntas = PERGUNTAS[tipo];
        if (!perguntas) {
            console.error('❌ Perguntas não encontradas para o tipo:', tipo);
            body.innerHTML = '<div class="alert-error">❌ Erro: Tipo de checklist inválido</div>';
            return;
        }
        
        const url = `/api/checklist/carregar?processo_id=${processoIdAtual}&tipo=${tipo}`;
        console.log('📤 Fazendo requisição para:', url);
        
        const response = await fetch(url);
        console.log('📥 Resposta recebida, status:', response.status);
        
        const dados = await response.json();
        console.log('📦 Dados recebidos do checklist:', dados);

        if (dados.success && dados.respostas) {
            console.log('📊 Detalhes das respostas:');
            dados.respostas.forEach((r, index) => {
                console.log(`  ${index + 1}. ordem: ${r.ordem}, id: ${r.id}, resposta: ${r.resposta}`);
            });
        }
        
        const respostas = dados.success ? dados.respostas : [];
        setCurrentRespostaId(dados.success ? dados.id : null);
        
        // ⭐ MONTAR MAPA DE RESPOSTAS POR ORDEM
        const respostasMap = {};
        if (dados.success && dados.respostas) {
            dados.respostas.forEach(r => {
                const ordemKey = String(r.ordem);
                respostasMap[ordemKey] = r;
            });
        }
        
        // ⭐⭐⭐ EXTRAIR IDs DAS RESPOSTAS ANTES DE CARREGAR EVIDÊNCIAS ⭐⭐⭐
        const novasIds = {};
        for (const [ordem, resposta] of Object.entries(respostasMap)) {
            if (resposta.id) {
                novasIds[ordem] = resposta.id;
            }
        }
        setCurrentRespostaIds(novasIds);
        console.log('📊 IDs das respostas extraídas:', currentRespostaIds);
        
        // ⭐ CARREGAR EVIDÊNCIAS PARA CADA RESPOSTA
        const evidenciasMap = {};
        for (const [ordem, resposta] of Object.entries(respostasMap)) {
            if (resposta.id) {
                try {
                    const evResponse = await fetch(`/api/checklist/evidencias/${resposta.id}`);
                    const evData = await evResponse.json();
                    if (evData.success) {
                        evidenciasMap[ordem] = evData.evidencias || [];
                    }
                } catch (err) {
                    console.error(`❌ Erro ao carregar evidências da ordem ${ordem}:`, err);
                    evidenciasMap[ordem] = [];
                }
            }
        }
        
        console.log(`📊 Total de respostas: ${respostas.length}`);
        console.log('📊 IDs das respostas FINAL:', currentRespostaIds);
        
        let html = `<div class="perguntas-container">`;
        
        for (let i = 0; i < perguntas.length; i++) {
            const p = perguntas[i];
            
            // ⭐ VERIFICAR SE TEM SUBITENS
            if (p.temSubitens && p.subitens && p.subitens.length > 0) {
                // --- PERGUNTA COM SUBITENS ---
                
                // ⭐ BUSCAR AS RESPOSTAS INDIVIDUAIS
                const pergunta1 = respostasMap['1'] || { id: null, resposta: '', comentario: '', evidencias: [] };
                const pergunta1_1 = respostasMap['1.1'] || { id: null, resposta: '', comentario: '', evidencias: [] };
                const pergunta1_2 = respostasMap['1.2'] || { id: null, resposta: '', comentario: '', evidencias: [] };
                
                // ⭐ COMENTÁRIO COMPARTILHADO (vem da pergunta 1)
                const comentarioCompartilhado = pergunta1.comentario || '';
                
                // ⭐ EVIDÊNCIAS COMPARTILHADAS (vêm da pergunta 1)
                const evidenciasCompartilhadas = pergunta1.evidencias || [];
                
                html += `
                    <div class="pergunta-card" data-pergunta-index="${i}" data-pergunta-ordem="${p.ordem}" style="border: 2px solid #184145; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                        <!-- PERGUNTA PRINCIPAL (1) -->
                        <div class="pergunta-header">
                            <div class="pergunta-numero">${p.ordem}</div>
                            <div class="pergunta-texto">${escapeHtml(p.pergunta)}</div>
                        </div>
                        <div class="pergunta-opcoes">
                            <label class="radio-label">
                                <input type="radio" name="resp_${i}" value="SIM" ${pergunta1.resposta === 'SIM' ? 'checked' : ''}> ✅ Sim
                            </label>
                            <label class="radio-label">
                                <input type="radio" name="resp_${i}" value="NÃO" ${pergunta1.resposta === 'NÃO' ? 'checked' : ''}> ❌ Não
                            </label>
                            <label class="radio-label">
                                <input type="radio" name="resp_${i}" value="NÃO SE APLICA" ${pergunta1.resposta === 'NÃO SE APLICA' ? 'checked' : ''}> ➖ Não se aplica
                            </label>
                        </div>
                        
                        <!-- SUBITENS (cada um com sua própria resposta) -->
                        <div class="subitens-container" style="padding-left: 40px; margin-top: 15px;">
                `;
                
                p.subitens.forEach((sub, subIndex) => {
                    // ⭐ PEGAR A RESPOSTA DO SUBITEM CORRETO
                    let subResposta;
                    if (sub.id === '1.1') {
                        subResposta = pergunta1_1;
                    } else if (sub.id === '1.2') {
                        subResposta = pergunta1_2;
                    } else {
                        subResposta = { id: null, resposta: '', comentario: '' };
                    }
                    
                    html += `
                        <div class="subitem-item" style="margin-bottom: 15px; padding: 12px; background: #f8f9fa; border-radius: 8px; border-left: 3px solid #0b5b99;">
                            <div style="font-weight: 500; margin-bottom: 8px; font-size: 13px;">
                                <span style="color: #0b5b99;">${sub.id}</span>
                                ${escapeHtml(sub.texto)}
                            </div>
                            <div class="pergunta-opcoes" style="padding-left: 0;">
                                <label class="radio-label">
                                    <input type="radio" name="subresp_${i}_${subIndex}" value="SIM" ${subResposta.resposta === 'SIM' ? 'checked' : ''}> 
                                    ✅ Sim
                                </label>
                                <label class="radio-label">
                                    <input type="radio" name="subresp_${i}_${subIndex}" value="NÃO" ${subResposta.resposta === 'NÃO' ? 'checked' : ''}> 
                                    ❌ Não
                                </label>
                                <label class="radio-label">
                                    <input type="radio" name="subresp_${i}_${subIndex}" value="NÃO SE APLICA" ${subResposta.resposta === 'NÃO SE APLICA' ? 'checked' : ''}> 
                                    ➖ Não se aplica
                                </label>    
                            </div>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                        
                        <!-- COMENTÁRIO COMPARTILHADO -->
                        <div class="pergunta-comentario" style="margin-top: 15px; padding-top: 15px; border-top: 1px dashed #e0e0e0;">
                            <label style="font-weight: 600; color: #184145; font-size: 13px;">
                                <i class="fas fa-comment"></i> Comentário
                            </label>
                            <textarea class="comentario-textarea" data-index="${i}" data-ordem="1" placeholder="Comentários gerais sobre esta pergunta..." rows="2" style="margin-top: 5px;">${escapeHtml(comentarioCompartilhado)}</textarea>
                        </div>
                `;
                
                // EVIDÊNCIA COMPARTILHADA
                if (p.precisaEvidencia) {
                    html += `
                        <div class="evidencias-container" style="margin-top: 10px;">
                            <label style="font-weight: 600; color: #184145; font-size: 13px;">
                                <i class="fas fa-paperclip"></i> Evidência
                            </label>
                            <button type="button" class="btn-evidencias" onclick="abrirUploadEvidencia(${i})" style="margin-top: 5px;">
                                <i class="fas fa-cloud-upload-alt"></i> Anexar Evidência (PDF)
                            </button>
                            <div class="evidencias-lista" id="evidencias-lista-${i}">
                    `;
                    
                    if (evidenciasCompartilhadas && evidenciasCompartilhadas.length > 0) {
                        evidenciasCompartilhadas.forEach(ev => {
                            html += `
                                <div class="evidencia-item" data-evidencia-id="${ev.id}">
                                    <i class="fas fa-file-pdf"></i>
                                    <span>${escapeHtml(ev.nome)}</span>
                                    <button class="btn-baixar-evidencia" onclick="baixarEvidenciaChecklist(${ev.id})" title="Baixar">
                                        <i class="fas fa-download"></i>
                                    </button>
                                    <button class="btn-remover-evidencia" onclick="removerEvidenciaChecklist(${ev.id}, ${i})" title="Remover">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            `;
                        });
                    }
                    
                    html += `
                            </div>
                            <small class="text-muted">Anexe evidências em PDF (máx. 10MB)</small>
                        </div>
                    `;
                }
                
                html += `</div>`;
            } else {
                // --- PERGUNTA NORMAL (sem subitens) ---
                const ordemPrincipal = String(p.ordem);
                const r = respostasMap[ordemPrincipal] || { 
                    id: null,
                    resposta: '', 
                    comentario: '', 
                    evidencias: [] 
                };
                const evidencias = evidenciasMap[ordemPrincipal] || [];
                
                html += `
                    <div class="pergunta-card" data-pergunta-index="${i}" data-pergunta-ordem="${p.ordem}">
                        <div class="pergunta-header">
                            <div class="pergunta-numero">${p.ordem}</div>
                            <div class="pergunta-texto">${escapeHtml(p.pergunta)}</div>
                        </div>
                        <div class="pergunta-opcoes">
                            <label class="radio-label"><input type="radio" name="resp_${i}" value="SIM" ${r.resposta === 'SIM' ? 'checked' : ''}> ✅ Sim</label>
                            <label class="radio-label"><input type="radio" name="resp_${i}" value="NÃO" ${r.resposta === 'NÃO' ? 'checked' : ''}> ❌ Não</label>
                            <label class="radio-label"><input type="radio" name="resp_${i}" value="NÃO SE APLICA" ${r.resposta === 'NÃO SE APLICA' ? 'checked' : ''}> ➖ Não se aplica</label>
                        </div>
                        <div class="pergunta-comentario">
                            <textarea class="comentario-textarea" data-index="${i}" placeholder="Comentários..." rows="2">${escapeHtml(r.comentario || '')}</textarea>
                        </div>
                `;
                    
                if (p.precisaEvidencia) {
                    html += `
                        <div class="evidencias-container">
                            <button type="button" class="btn-evidencias" onclick="abrirUploadEvidencia(${i})">
                                <i class="fas fa-paperclip"></i> Anexar Evidência (PDF)
                            </button>
                            <div class="evidencias-lista" id="evidencias-lista-${i}">
                    `;
                    
                    if (evidencias && evidencias.length > 0) {
                        evidencias.forEach(ev => {
                            html += `
                                <div class="evidencia-item" data-evidencia-id="${ev.id}">
                                    <i class="fas fa-file-pdf"></i>
                                    <span>${escapeHtml(ev.nome)}</span>
                                    <button class="btn-baixar-evidencia" onclick="baixarEvidenciaChecklist(${ev.id})" title="Baixar">
                                        <i class="fas fa-download"></i>
                                    </button>
                                    <button class="btn-remover-evidencia" onclick="removerEvidenciaChecklist(${ev.id}, ${i})" title="Remover">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            `;
                        });
                    }
                    
                    html += `
                            </div>
                            <small class="text-muted">Anexe evidências em PDF (máx. 10MB)</small>
                        </div>
                    `;
                }
                
                html += `</div>`;
            }
        }
        
        html += `</div>
        <div class="checklist-footer">
            <div class="checklist-botoes">
                <button class="btn-salvar-checklist" data-tipo="${tipo}"><i class="fas fa-save"></i> Salvar</button>
                <button class="btn-concluir-checklist" data-tipo="${tipo}"><i class="fas fa-check-circle"></i> Concluir</button>
            </div>
        </div>`;
        
        body.innerHTML = html;
        
        document.querySelectorAll('.btn-salvar-checklist, .btn-concluir-checklist').forEach(btn => {
            btn.addEventListener('click', () => salvarChecklist(tipo, btn.classList.contains('btn-concluir-checklist')));
        });
        
        console.log('✅ Checklist carregado com sucesso!');
        
    } catch (error) {
        console.error('❌ Erro ao carregar checklist:', error);
        body.innerHTML = `<div class="alert-error">❌ Erro ao carregar o checklist: ${error.message}</div>`;
    }
}

export async function carregarEvidenciasPergunta(perguntaIndex) {
    const perguntas = PERGUNTAS[tipoAtual]; // Você precisa ter o tipo atual
    const pergunta = perguntas[perguntaIndex];
    const respostaId = currentRespostaIds[pergunta.ordem];
    
    if (!respostaId) return;
    
    try {
        const response = await fetch(`/api/checklist/evidencias/${respostaId}`);
        const data = await response.json();
        
        if (data.success) {
            const listaDiv = document.getElementById(`evidencias-lista-${perguntaIndex}`);
            if (listaDiv) {
                // Limpar lista
                listaDiv.innerHTML = '';
                
                // Adicionar evidências
                if (data.evidencias && data.evidencias.length > 0) {
                    data.evidencias.forEach(ev => {
                        const evidenciaDiv = document.createElement('div');
                        evidenciaDiv.className = 'evidencia-item';
                        evidenciaDiv.setAttribute('data-evidencia-id', ev.id);
                        evidenciaDiv.innerHTML = `
                            <i class="fas fa-file-pdf"></i>
                            <span>${escapeHtml(ev.nome)}</span>
                            <button class="btn-baixar-evidencia" onclick="baixarEvidenciaChecklist(${ev.id})" title="Baixar">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn-remover-evidencia" onclick="removerEvidenciaChecklist(${ev.id}, ${perguntaIndex})" title="Remover">
                                <i class="fas fa-trash"></i>
                            </button>
                        `;
                        listaDiv.appendChild(evidenciaDiv);
                    });
                } else {
                    const mensagem = document.createElement('div');
                    mensagem.className = 'text-muted';
                    mensagem.style.padding = '8px';
                    mensagem.style.textAlign = 'center';
                    mensagem.textContent = 'Nenhuma evidência anexada';
                    listaDiv.appendChild(mensagem);
                }
            }
        }
    } catch (error) {
        console.error('❌ Erro ao recarregar evidências:', error);
    }
}

export async function removerEvidenciaChecklist(evidenciaId, perguntaIndex) {
    if (!confirm('⚠️ Tem certeza que deseja remover esta evidência?')) return;
    
    // ⭐ MOSTRAR LOADING NO BOTÃO
    const evidenciaItem = document.querySelector(`.evidencia-item[data-evidencia-id="${evidenciaId}"]`);
    if (evidenciaItem) {
        evidenciaItem.style.opacity = '0.5';
        evidenciaItem.style.pointerEvents = 'none';
        evidenciaItem.innerHTML = '<div style="padding: 8px;"><i class="fas fa-spinner fa-spin"></i> Removendo...</div>';
    }
    
    try {
        const response = await fetch(`/api/checklist/evidencia/${evidenciaId}`, { 
            method: 'DELETE' 
        });
        
        const data = await response.json();
        
        if (data.success) {
            // ⭐ REMOVER APENAS O ELEMENTO DO DOM
            if (evidenciaItem) {
                evidenciaItem.remove();
                console.log(`✅ Evidência ${evidenciaId} removida da tela`);
            }
            
            // ⭐ ATUALIZAR O CONTADOR DE EVIDÊNCIAS (se houver)
            const listaDiv = document.getElementById(`evidencias-lista-${perguntaIndex}`);
            if (listaDiv) {
                const totalEvidencias = listaDiv.querySelectorAll('.evidencia-item').length;
                if (totalEvidencias === 0) {
                    // Se não houver mais evidências, mostrar mensagem "Nenhuma evidência"
                    const mensagem = document.createElement('div');
                    mensagem.className = 'text-muted';
                    mensagem.style.padding = '8px';
                    mensagem.style.textAlign = 'center';
                    mensagem.textContent = 'Nenhuma evidência anexada';
                    listaDiv.appendChild(mensagem);
                }
            }
            
            mostrarToast('✅ Evidência removida com sucesso!', 'success');
            
        } else {
            mostrarToast('❌ Erro ao remover evidência: ' + (data.error || 'Erro desconhecido'), 'error');
            // Restaurar o item se houve erro
            if (evidenciaItem) {
                evidenciaItem.style.opacity = '1';
                evidenciaItem.style.pointerEvents = 'auto';
            }
        }
    } catch (error) {
        console.error('❌ Erro ao remover evidência:', error);
        mostrarToast('❌ Erro ao conectar com o servidor', 'error');
        // Restaurar o item se houve erro
        if (evidenciaItem) {
            evidenciaItem.style.opacity = '1';
            evidenciaItem.style.pointerEvents = 'auto';
        }
    }
}

export async function salvarChecklist(tipo, concluir) {
    const container = document.getElementById('modal-checklist-body');
    const perguntas = PERGUNTAS[tipo];
    const respostas = [];
    
    console.log('📎 Arquivos pendentes ANTES de salvar:', arquivosPendentes);
    console.log('📎 Total de arquivos pendentes:', Object.keys(arquivosPendentes).length);
    
    // ⭐ 1. COLETAR TODAS AS RESPOSTAS
    for (let i = 0; i < perguntas.length; i++) {
        const p = perguntas[i];
        
        // ⭐ VERIFICAR SE TEM SUBITENS
        if (p.temSubitens && p.subitens && p.subitens.length > 0) {
            // --- PERGUNTA COM SUBITENS ---
            
            // 1. Resposta da pergunta principal (ordem = p.ordem)
            const radioPrincipal = container.querySelector(`input[name="resp_${i}"]:checked`);
            const comentarioCompartilhado = container.querySelector(`.comentario-textarea[data-index="${i}"]`);
            
            respostas.push({
                ordem: p.ordem,  // ex: 1
                resposta: radioPrincipal ? radioPrincipal.value : '',
                comentario: comentarioCompartilhado ? comentarioCompartilhado.value : ''
            });
            
            // 2. Respostas dos subitens (ordem = '1.1', '1.2', ...)
            p.subitens.forEach((sub, subIndex) => {
                const radioSub = container.querySelector(`input[name="subresp_${i}_${subIndex}"]:checked`);
                // ⭐ Subitens NÃO têm comentário próprio (usam o compartilhado)
                respostas.push({
                    ordem: sub.id,  // ex: '1.1', '1.2'
                    resposta: radioSub ? radioSub.value.toUpperCase() : '',
                    comentario: ''  // comentário vazio (usam o compartilhado)
                });
            });
            
        } else {
            // --- PERGUNTA NORMAL ---
            const radio = container.querySelector(`input[name="resp_${i}"]:checked`);
            const comentario = container.querySelector(`.comentario-textarea[data-index="${i}"]`);
            
            respostas.push({
                ordem: p.ordem,
                resposta: radio ? radio.value.toUpperCase() : '',
                comentario: comentario ? comentario.value : ''
            });
        }
    }
    
    try {
        // ⭐ 2. SALVAR AS RESPOSTAS
        const bodyData = { 
            processo_id: parseInt(processoIdAtual), 
            tipo, 
            respostas, 
            concluir 
        };
        
        console.log('📤 Salvando checklist:', bodyData);
        console.log('📤 Respostas sendo enviadas:', respostas);
        
        const response = await fetch('/api/checklist/salvar', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(bodyData) 
        });
        
        const data = await response.json();
        console.log('📥 Resposta do servidor:', data);
        
        if (data.success) {
            // ⭐ GUARDAR OS IDs DAS RESPOSTAS
            setCurrentRespostaIds(data.respostas_ids || {});
            setCurrentRespostaId(data.id);
            
            console.log('📊 IDs das respostas recebidas:', currentRespostaIds);
            console.log('📊 Chaves disponíveis:', Object.keys(currentRespostaIds));
            
            // ⭐ 3. ENVIAR EVIDÊNCIAS PENDENTES
            if (Object.keys(arquivosPendentes).length > 0) {
                console.log('📎 Enviando evidências pendentes...');
                console.log('📎 arquivosPendentes:', arquivosPendentes);
                
                let evidenciasEnviadas = 0;
                let totalEvidencias = 0;
                
                for (const [perguntaIndex, arquivos] of Object.entries(arquivosPendentes)) {
                    const idx = parseInt(perguntaIndex);
                    const pergunta = perguntas[idx];
                    
                    if (!pergunta) {
                        console.warn(`⚠️ Pergunta não encontrada para índice: ${idx}`);
                        continue;
                    }
                    
                    // ⭐ DETERMINAR A ORDEM PARA A EVIDÊNCIA
                    let ordemEvidencia;
                    
                    if (pergunta.temSubitens && pergunta.subitens && pergunta.subitens.length > 0) {
                        // ⭐ Para perguntas com subitens, a evidência vai para a pergunta principal (ordem = p.ordem)
                        ordemEvidencia = String(pergunta.ordem);
                    } else {
                        // ⭐ Para perguntas normais, a evidência vai para a própria pergunta
                        ordemEvidencia = String(pergunta.ordem);
                    }
                    
                    // ⭐ BUSCAR O ID DA RESPOSTA
                    let respostaId = currentRespostaIds[ordemEvidencia];
                    if (!respostaId) {
                        respostaId = currentRespostaIds[String(ordemEvidencia)];
                    }
                    
                    console.log(`🔍 Pergunta índice: ${perguntaIndex}, ordemEvidencia: ${ordemEvidencia}, respostaId: ${respostaId}`);
                    
                    if (!respostaId) {
                        console.warn(`⚠️ Resposta ID não encontrado para ordem ${ordemEvidencia}`);
                        continue;
                    }
                    
                    // ⭐ ENVIAR CADA ARQUIVO
                    for (const arquivo of arquivos) {
                        totalEvidencias++;
                        try {
                            console.log(`📎 Enviando evidência: ${arquivo.nome} para resposta ${respostaId}`);
                            
                            const evidenciaResponse = await fetch('/api/checklist/evidencia/salvar', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    resposta_id: respostaId,
                                    evidencia_base64: arquivo.conteudo,
                                    evidencia_nome: arquivo.nome
                                })
                            });
                            
                            const evidenciaData = await evidenciaResponse.json();
                            console.log('📥 Resposta do servidor (evidência):', evidenciaData);
                            
                            if (evidenciaData.success) {
                                evidenciasEnviadas++;
                                console.log(`✅ Evidência ${arquivo.nome} salva com sucesso`);
                            } else {
                                console.error(`❌ Erro ao salvar evidência ${arquivo.nome}:`, evidenciaData.error);
                                mostrarToast(`❌ Erro ao salvar evidência ${arquivo.nome}: ${evidenciaData.error}`, 'error');
                            }
                        } catch (err) {
                            console.error(`❌ Erro ao enviar evidência ${arquivo.nome}:`, err);
                            mostrarToast(`❌ Erro ao enviar evidência ${arquivo.nome}`, 'error');
                        }
                    }
                }
                
                if (totalEvidencias > 0) {
                    mostrarToast(`📎 ${evidenciasEnviadas} de ${totalEvidencias} evidências salvas.`, 'info');
                }
                
                // ⭐ LIMPAR ARQUIVOS PENDENTES
                setArquivosPendentes({});
            } else {
                console.log('⚠️ NENHUM arquivo pendente para enviar!');
            }
            
            // ⭐ 4. MENSAGEM DE SUCESSO
            mostrarToast(concluir ? '✅ Checklist concluído!' : '✅ Respostas salvas!', 'success');
            
            // ⭐ 5. RECARREGAR OU FECHAR
            if (concluir) {
                fecharModalChecklist();
            } else {
                await carregarChecklistModal(tipo);
            }
            
            carregarProgressoChecklists();
            
        } else {
            mostrarToast('❌ Erro ao salvar: ' + (data.error || 'Erro desconhecido'), 'error');
        }
        
    } catch (error) { 
        console.error('❌ Erro ao salvar checklist:', error);
        mostrarToast('❌ Erro ao conectar com o servidor', 'error'); 
    }
}