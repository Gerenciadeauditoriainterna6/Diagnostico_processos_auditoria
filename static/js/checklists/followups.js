// ============================================================
// IMPORTS
// ============================================================

import { mostrarToast, formatarData, escapeHtml } from './utils.js';
import { 
    processoIdAtual,
    setProcessoId,
    setAuditoriaId
} from './estado.js';

// ============================================================
// VARIÁVEIS
// ============================================================

let analisesData = [];

// ============================================================
// CARREGAR FILTROS (Área, Auditoria, Processo)
// ============================================================

export async function carregarAreas() {
    const select = document.getElementById('area_select');
    if (!select) return;
    
    try {
        const response = await fetch('/api/areas');
        const areas = await response.json();
        select.innerHTML = '<option value="">Selecione uma área...</option>';
        areas.forEach(area => { 
            const option = document.createElement('option'); 
            option.value = area.id_area; 
            
            let nomeExibicao = area.nome_area;
            if (area.loc_unidade && area.loc_unidade.trim()) {
                nomeExibicao = `${area.nome_area} - ${area.loc_unidade}`;
            }
            option.textContent = nomeExibicao;
            select.appendChild(option); 
        });
    } catch (error) { 
        console.error(error); 
    }
}

export async function carregarAuditorias(areaId) {
    const select = document.getElementById('auditoria_select');
    if (!areaId) { 
        select.innerHTML = '<option value="">Selecione uma área primeiro...</option>'; 
        select.disabled = true; 
        return; 
    }
    select.innerHTML = '<option value="">Carregando...</option>';
    try {
        const response = await fetch(`/api/auditorias-por-area?area_id=${areaId}`);
        const data = await response.json();
        if (data.auditorias && data.auditorias.length > 0) {
            select.innerHTML = '<option value="">Selecione uma auditoria...</option>';
            data.auditorias.forEach(aud => { 
                const option = document.createElement('option'); 
                option.value = aud.id; 
                option.textContent = `${aud.codigo_auditoria} - ${aud.titulo}`; 
                select.appendChild(option); 
            });
            select.disabled = false;
        } else { 
            select.innerHTML = '<option value="">Nenhuma auditoria</option>'; 
            select.disabled = true; 
        }
    } catch (error) { console.error(error); }
}

export async function carregarProcessos(auditoriaId) {
    const select = document.getElementById('processo_select');
    const row = document.getElementById('row-processo');
    if (!auditoriaId) { 
        row.style.display = 'none'; 
        return; 
    }
    try {
        const response = await fetch(`/api/relatorios/processos-por-auditoria?auditoria_id=${auditoriaId}`);
        const data = await response.json();
        if (data.success && data.processos && data.processos.length > 0) {
            select.innerHTML = '<option value="">Selecione um processo...</option>';
            data.processos.forEach(proc => { 
                const option = document.createElement('option'); 
                option.value = proc.id; 
                option.textContent = `${proc.codigo_processo} - ${proc.nome_processo}`; 
                select.appendChild(option); 
            });
            select.disabled = false;
            row.style.display = 'flex';
        } else { 
            select.innerHTML = '<option value="">Nenhum processo</option>'; 
            select.disabled = true; 
            row.style.display = 'flex'; 
        }
    } catch (error) { console.error(error); }
}

// ============================================================
// FUNÇÃO AUXILIAR - AGRUPAR FOLLOW-UPS POR ANÁLISE
// ============================================================

function agruparAnalisesPorFollowups(followups) {
    const analisesMap = {};
    
    followups.forEach(fu => {
        const analiseId = fu.analise_id;
        
        // Se a análise ainda não existe no mapa, criar
        if (!analisesMap[analiseId]) {
            analisesMap[analiseId] = {
                id: analiseId,
                analise_critica: fu.analise_critica || 'Análise sem título',
                categoria: fu.categoria || '',
                codigo_processo: fu.codigo_processo || '',
                nome_processo: fu.nome_processo || '',
                tipo_analise: fu.tipo_analise || 'auditor',
                follow_ups: []
            };
        }
        
        // Adicionar o follow-up à análise
        analisesMap[analiseId].follow_ups.push({
            id: fu.id,
            etapa: fu.etapa,
            data_prevista: fu.data_prevista,
            data_realizada: fu.data_realizada,
            status: fu.status,
            comentario: fu.comentario,
            responsavel: fu.responsavel
        });
    });
    
    return Object.values(analisesMap);
}

// ============================================================
// CARREGAR ANÁLISES COM SUGESTÃO "SERÁ IMPLANTADA"
// ============================================================

export async function carregarAnalises(processoId = null) {
    const container = document.getElementById('followups-container');
    container.innerHTML = '<div style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin"></i> Carregando análises...</div>';
    
    try {
        let url = '/followups/api/todos';
        if (processoId) {
            url += `?processo_id=${processoId}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        console.log('📦 Dados recebidos:', data);
        console.log('📦 data.success:', data.success);
        console.log('📦 data.analises:', data.analises);
        console.log('📦 data.analises.length:', data.analises ? data.analises.length : 'undefined');
        
        if (data.success) {
            const analises = data.analises || [];
            
            console.log('📊 Análises encontradas:', analises.length);
            
            if (analises.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 60px; color: #999;">
                        <i class="fas fa-check-circle" style="font-size: 48px; color: #28a745;"></i>
                        <h3 style="margin-top: 20px;">Tudo em dia!</h3>
                        <p>Nenhuma sugestão de melhoria aguardando acompanhamento.</p>
                    </div>
                `;
                return;
            }
            
            console.log('📊 Chamando renderizarAnalises com:', analises);
            analisesData = analises;
            renderizarAnalises(analises);
    
        } else {
            container.innerHTML = '<div style="text-align: center; padding: 40px; color: #999;">Nenhuma sugestão de melhoria aguardando acompanhamento.</div>';
        }
    } catch (error) {
        console.error('❌ Erro ao carregar análises:', error);
        container.innerHTML = '<div class="alert-error">❌ Erro ao carregar análises</div>';
    }
}

// ============================================================
// RENDERIZAR ANÁLISES
// ============================================================

function renderizarAnalises(analises) {
    const container = document.getElementById('followups-container');
    
    if (!analises || analises.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 60px; color: #999;">
                <i class="fas fa-check-circle" style="font-size: 48px; color: #28a745;"></i>
                <h3 style="margin-top: 20px;">Tudo em dia!</h3>
                <p>Nenhuma sugestão de melhoria aguardando acompanhamento.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    analises.forEach(analise => {
        const temFollowUps = analise.follow_ups && analise.follow_ups.length > 0;
        const todosConcluidos = temFollowUps && analise.follow_ups.every(fu => fu.status !== 'Pendente');
        
        let statusBadge = '';
        let statusClass = '';
        let acoes = '';
        
        if (!temFollowUps) {
            statusBadge = '<span class="status-badge nao-iniciado">Não iniciado</span>';
            statusClass = 'nao-iniciado';
            acoes = `
                <button class="btn-iniciar-acompanhamento" onclick="window.iniciarAcompanhamento(${analise.id}, '${escapeHtml(analise.analise_critica)}')">
                    <i class="fas fa-play"></i> Iniciar Acompanhamento
                </button>
            `;
        } else if (todosConcluidos) {
            statusBadge = '<span class="status-badge concluido">Concluído</span>';
            statusClass = 'concluido';
            acoes = `
                <span style="font-size: 13px; color: #28a745;">
                    <i class="fas fa-check-circle"></i> Acompanhamento concluído
                </span>
            `;
        } else {
            statusBadge = '<span class="status-badge em-andamento">Em andamento</span>';
            statusClass = 'em-andamento';
            acoes = `
                <button class="btn-registrar-followup" onclick="window.abrirModalFollowupRegistro(${analise.id}, '${escapeHtml(analise.analise_critica)}')">
                    <i class="fas fa-eye"></i> Visualizar Follow-up
                </button>
            `;
        }
        
        // Mostrar progresso dos follow-ups
        let progressoHtml = '';
        if (temFollowUps) {
            const total = analise.follow_ups.length;
            const concluidos = analise.follow_ups.filter(fu => fu.status !== 'Pendente').length;
            const porcentagem = Math.round((concluidos / total) * 100);
            
            progressoHtml = `
                <div class="card-progresso">
                    <div class="progress-text">${concluidos} de ${total} etapas concluídas</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${porcentagem}%; background: #28a745;"></div>
                    </div>
                </div>
            `;
        }
        
        html += `
            <div class="followup-card ${statusClass}">
                <div class="followup-header">
                    <div class="followup-info">
                        <h4>Sugestão de Melhoria: ${escapeHtml(analise.analise_critica || 'Análise sem título')}</h4>
                        <div class="followup-detalhes">
                            <span><strong>Etapa:</strong> ${escapeHtml(analise.codigo_etapa || '-')}</span>
                            <span style="margin-left: 15px;"><strong>Categoria da Análise:</strong> ${analise.tipo_analise === 'auditor' ? 'Auditor' : 'Auditado'}</span>
                            ${analise.codigo_processo ? `<span style="margin-left: 15px;"><strong>Processo:</strong> ${escapeHtml(analise.codigo_processo)}</span>` : ''}
                        </div>
                    </div>
                    <div class="followup-status-wrapper">
                        ${statusBadge}
                    </div>
                </div>
                
                ${progressoHtml}
                
                ${temFollowUps ? `
                <div class="followup-body">
                    <div style="font-size: 13px; color: #555; margin-bottom: 8px;">
                        <strong>Etapas de Follow-Up:</strong>
                    </div>
                    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                        ${analise.follow_ups.map(fu => {
                            const statusIcon = {
                                'Pendente': '⏳',
                                'Aderente': '✅',
                                'Nao aderente': '❌',
                                'Parcialmente aderente': '🟡'
                            }[fu.status] || '⏳';
                            
                            const statusClass = {
                                'Pendente': 'pendente',
                                'Aderente': 'aderente',
                                'Nao aderente': 'nao-aderente',
                                'Parcialmente aderente': 'parcialmente-aderente'
                            }[fu.status] || 'pendente';
                            
                            const textoEtapa = {
                                'FOLLOW_UP_30': '30 dias',
                                'FOLLOW_UP_60': '60 dias',
                                'FOLLOW_UP_90': '90 dias'
                            }[fu.etapa] || fu.etapa;
                            
                            return `
                                <div class="followup-etapa">
                                    <span class="etapa-status ${statusClass}">${statusIcon}</span>
                                    <span style="font-size: 12px;">${textoEtapa}</span>
                                    ${fu.data_prevista ? `<span style="font-size: 11px; color: #999;">${formatarData(fu.data_prevista)}</span>` : ''}
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
                ` : ''}
                
                <div class="followup-acoes">
                    ${acoes}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}


// ============================================================
// INICIAR ACOMPANHAMENTO
// ============================================================

export async function iniciarAcompanhamento(analiseId, analiseTexto) {
    if (!confirm(`Deseja iniciar o acompanhamento para:\n\n"${analiseTexto}"\n\nSerão criados follow-ups de 30, 60 e 90 dias.`)) {
        return;
    }
    
    const btn = document.querySelector(`.btn-iniciar-acompanhamento[onclick*="${analiseId}"]`);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Criando...';
    }
    
    try {
        const response = await fetch('/followups/api/iniciar-acompanhamento', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ analise_id: analiseId })
        });
        const data = await response.json();
        
        if (data.success) {
            mostrarToast('✅ Acompanhamento iniciado! Follow-ups de 30, 60 e 90 dias criados.', 'success');
            const processoId = document.getElementById('processo_select')?.value;
            await carregarAnalises(processoId);
        } else {
            mostrarToast('❌ Erro ao iniciar acompanhamento: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarToast('❌ Erro ao conectar com o servidor', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play"></i> Iniciar Acompanhamento';
        }
    }
}

// ============================================================
// MODAL - REGISTRAR FOLLOW-UP
// ============================================================

export function abrirModalFollowupRegistro(analiseId, analiseTexto) {
    document.getElementById('followup-registro-analise-id').value = analiseId;
    document.getElementById('followup-registro-analise').textContent = analiseTexto || 'Análise sem título';
    
    // Carregar os follow-ups pendentes desta análise
    carregarFollowupsPendentes(analiseId);
    
    document.getElementById('modal-followup-registro').style.display = 'flex';
}

// ⭐ ADICIONE ESTA FUNÇÃO:
export function fecharModalFollowupRegistro() {
    document.getElementById('modal-followup-registro').style.display = 'none';
}

async function carregarFollowupsPendentes(analiseId) {
    const container = document.getElementById('followup-registro-lista');
    container.innerHTML = '<div style="text-align: center; padding: 20px;"><i class="fas fa-spinner fa-spin"></i> Carregando...</div>';
    
    try {
        const response = await fetch(`/followups/api/por-analise/${analiseId}`);
        const data = await response.json();
        
        if (data.success && data.follow_ups) {
            const followUps = data.follow_ups;
            
            if (followUps.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">Nenhum follow-up encontrado.</div>';
                return;
            }
            
            let html = '<div style="display: flex; flex-direction: column; gap: 12px;">';
            
            followUps.forEach(fu => {
                const textoEtapa = {
                    'FOLLOW_UP_30': '30 dias após implantação',
                    'FOLLOW_UP_60': '60 dias após implantação',
                    'FOLLOW_UP_90': '90 dias após implantação'
                }[fu.etapa] || fu.etapa;
                
                const statusIcon = {
                    'Pendente': '⏳',
                    'Aderente': '✅',
                    'Nao aderente': '❌',
                    'Parcialmente aderente': '🟡'
                }[fu.status] || '⏳';
                
                const statusClass = {
                    'Pendente': 'pendente',
                    'Aderente': 'aderente',
                    'Nao aderente': 'nao-aderente',
                    'Parcialmente aderente': 'parcialmente-aderente'
                }[fu.status] || 'pendente';
                
                const dataRealizada = fu.data_realizada ? formatarData(fu.data_realizada) : 'Não realizada';
                const temComentario = fu.comentario && fu.comentario !== 'Aguardando registro';
                
                html += `
                    <div class="followup-item-card" style="padding: 14px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid ${fu.status === 'Pendente' ? '#ffc107' : '#28a745'};">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">
                            <div style="flex: 1;">
                                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                                    <span style="font-weight: 500;">${textoEtapa}</span>
                                    <span style="font-size: 12px; padding: 2px 8px; border-radius: 12px; background: ${fu.status === 'Pendente' ? '#fff3cd' : '#d4edda'}; color: ${fu.status === 'Pendente' ? '#856404' : '#155724'};">
                                        ${statusIcon} ${fu.status || 'Pendente'}
                                    </span>
                                </div>
                                <div style="font-size: 12px; color: #666; margin-top: 4px;">
                                    Prevista: ${fu.data_prevista ? formatarData(fu.data_prevista) : '-'} | 
                                    Realizada: ${dataRealizada}
                                    ${fu.responsavel ? ` | Por: ${escapeHtml(fu.responsavel)}` : ''}
                                </div>
                                ${temComentario ? `
                                    <div style="font-size: 13px; color: #333; margin-top: 6px; padding: 6px 10px; background: white; border-radius: 4px; border: 1px solid #e0e0e0;">
                                        💬 ${escapeHtml(fu.comentario)}
                                    </div>
                                ` : ''}
                            </div>
                            <div style="display: flex; gap: 8px; flex-shrink: 0;">
                                <button class="btn-primary btn-sm" onclick="window.abrirModalFollowupEditar(${fu.id})" style="padding: 4px 12px; font-size: 12px;">
                                    <i class="fas fa-edit"></i> Editar
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            container.innerHTML = html;
        }
    } catch (error) {
        console.error('Erro ao carregar follow-ups:', error);
        container.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">Erro ao carregar follow-ups.</div>';
    }
}

// ============================================================
// MODAL - EDITAR FOLLOW-UP
// ============================================================

export function abrirModalFollowupEditar(followUpId) {
    fetch(`/followups/api/follow-up/${followUpId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.follow_up) {
                const fu = data.follow_up;
                const textoEtapa = {
                    'FOLLOW_UP_30': '30 dias após implantação',
                    'FOLLOW_UP_60': '60 dias após implantação',
                    'FOLLOW_UP_90': '90 dias após implantação'
                }[fu.etapa] || fu.etapa;
                
                document.getElementById('followup-editar-id').value = fu.id;
                document.getElementById('followup-editar-etapa').textContent = textoEtapa;
                document.getElementById('followup-editar-data').textContent = fu.data_prevista ? formatarData(fu.data_prevista) : '-';
                document.getElementById('followup-editar-status').value = fu.status || 'Pendente';
                document.getElementById('followup-editar-comentario').value = fu.comentario || '';
                document.getElementById('modal-followup-editar').style.display = 'flex';
            }
        })
        .catch(error => {
            console.error('Erro ao buscar follow-up:', error);
            mostrarToast('❌ Erro ao carregar dados do follow-up', 'error');
        });
}

export function fecharModalFollowupEditar() {
    document.getElementById('modal-followup-editar').style.display = 'none';
}

export async function salvarFollowupEditar() {
    const followUpId = document.getElementById('followup-editar-id').value;
    const status = document.getElementById('followup-editar-status').value;
    const comentario = document.getElementById('followup-editar-comentario').value;
    
    if (!comentario.trim()) {
        mostrarToast('⚠️ O comentário é obrigatório', 'warning');
        return;
    }
    
    const btnSalvar = document.getElementById('btn-salvar-followup-editar');
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    
    try {
        const response = await fetch(`/followups/api/atualizar/${followUpId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, comentario })
        });
        const data = await response.json();
        
        if (data.success) {
            mostrarToast('✅ Follow-up atualizado com sucesso!', 'success');
            fecharModalFollowupEditar();
            const analiseId = document.getElementById('followup-registro-analise-id').value;
            await carregarFollowupsPendentes(analiseId);
            const processoId = document.getElementById('processo_select')?.value;
            await carregarAnalises(processoId);
        } else {
            mostrarToast('❌ Erro ao salvar: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarToast('❌ Erro ao conectar com o servidor', 'error');
    } finally {
        btnSalvar.disabled = false;
        btnSalvar.innerHTML = '<i class="fas fa-save"></i> Salvar';
    }
}

// ============================================================
// MODAL - REGISTRAR ITEM DE FOLLOW-UP
// ============================================================

export function abrirModalFollowupItem(followUpId, analiseTexto, dataPrevista) {
    document.getElementById('followup-item-id').value = followUpId;
    document.getElementById('followup-item-analise').textContent = analiseTexto || 'Análise sem título';
    document.getElementById('followup-item-data').textContent = dataPrevista ? formatarData(dataPrevista) : '-';
    document.getElementById('followup-item-status').value = 'Aderente';
    document.getElementById('followup-item-comentario').value = '';
    document.getElementById('modal-followup-item').style.display = 'flex';
}

export function fecharModalFollowupItem() {
    document.getElementById('modal-followup-item').style.display = 'none';
}

export async function salvarFollowupItem() {
    const followUpId = document.getElementById('followup-item-id').value;
    const status = document.getElementById('followup-item-status').value;
    const comentario = document.getElementById('followup-item-comentario').value;
    
    if (!comentario.trim()) {
        mostrarToast('⚠️ O comentário é obrigatório', 'warning');
        return;
    }
    
    const btnSalvar = document.getElementById('btn-salvar-followup-item');
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    
    try {
        const response = await fetch(`/followups/api/atualizar/${followUpId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, comentario })
        });
        const data = await response.json();
        
        if (data.success) {
            mostrarToast('✅ Follow-up registrado com sucesso!', 'success');
            fecharModalFollowupItem();
            const analiseId = document.getElementById('followup-registro-analise-id').value;
            await carregarFollowupsPendentes(analiseId);
            
            // Recarregar a lista principal
            const processoId = document.getElementById('processo_select')?.value;
            await carregarAnalises(processoId);
        } else {
            mostrarToast('❌ Erro ao salvar: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    } catch (error) {
        console.error('Erro:', error);
        mostrarToast('❌ Erro ao conectar com o servidor', 'error');
    } finally {
        btnSalvar.disabled = false;
        btnSalvar.innerHTML = '<i class="fas fa-save"></i> Salvar';
    }
}

// ============================================================
// FILTROS
// ============================================================

export function aplicarFiltros() {
    const status = document.getElementById('filtro-status').value;
    
    let filtrados = [...analisesData];
    
    if (status !== 'todos') {
        filtrados = filtrados.filter(analise => {
            const temFollowUps = analise.follow_ups && analise.follow_ups.length > 0;
            const todosConcluidos = temFollowUps && analise.follow_ups.every(fu => fu.status !== 'Pendente');
            
            if (status === 'nao_iniciado') return !temFollowUps;
            if (status === 'em_andamento') return temFollowUps && !todosConcluidos;
            if (status === 'concluido') return todosConcluidos;
            return true;
        });
    }
    
    renderizarAnalises(filtrados);
    
}

// ============================================================
// EXPORTA PARA O ESCOPO GLOBAL
// ============================================================

window.abrirModalFollowupRegistro = abrirModalFollowupRegistro;
window.fecharModalFollowupRegistro = fecharModalFollowupRegistro;
window.abrirModalFollowupItem = abrirModalFollowupItem;
window.fecharModalFollowupItem = fecharModalFollowupItem;
window.salvarFollowupItem = salvarFollowupItem;
window.iniciarAcompanhamento = iniciarAcompanhamento;
window.aplicarFiltros = aplicarFiltros;
window.carregarAnalises = carregarAnalises;
window.abrirModalFollowupEditar = abrirModalFollowupEditar;
window.fecharModalFollowupEditar = fecharModalFollowupEditar;
window.salvarFollowupEditar = salvarFollowupEditar;

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Inicializando página de follow-ups...');
    
    await carregarAreas();
    
    const selectArea = document.getElementById('area_select');
    const selectAuditoria = document.getElementById('auditoria_select');
    const selectProcesso = document.getElementById('processo_select');
    
    selectArea.addEventListener('change', () => { 
        carregarAuditorias(selectArea.value); 
        document.getElementById('conteudo-principal').style.display = 'none'; 
    });
    
    selectAuditoria.addEventListener('change', async () => { 
        if (selectAuditoria.value) {
            await carregarProcessos(selectAuditoria.value); 
        } else {
            document.getElementById('row-processo').style.display = 'none'; 
        }
    });
    
    selectProcesso.addEventListener('change', async () => {
        if (selectProcesso.value && selectAuditoria.value) {
            setProcessoId(selectProcesso.value);
            setAuditoriaId(selectAuditoria.value);
            document.getElementById('conteudo-principal').style.display = 'block';
            await carregarAnalises(selectProcesso.value);
        } else {
            document.getElementById('conteudo-principal').style.display = 'none';
        }
    });
    
    document.getElementById('btn-salvar-followup-item')?.addEventListener('click', salvarFollowupItem);
        
    console.log('✅ Página de follow-ups inicializada!');
});