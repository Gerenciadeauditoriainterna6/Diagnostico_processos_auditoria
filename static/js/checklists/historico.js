// ============================================================
// IMPORTS
// ============================================================

import { escapeHtml, mostrarToast } from './utils.js';
import { carregarAnalisesAuditor } from './analises-auditor.js';
import { carregarAnalisesAuditado } from './analises-auditado.js';

export function renderizarListaHistorico(historico) {
    if (!historico || historico.length === 0) return '<div style="color: #999; font-size: 12px; text-align: center; padding: 10px;">Nenhum registro de andamento</div>';
    let html = '';
    historico.forEach(item => {
        const statusClass = { 'Em andamento': '🟡', 'Parcialmente implementado': '🟠', 'Concluído': '✅', 'Atrasado': '🔴' }[item.status] || '📌';
        html += `<div style="padding: 8px; border-bottom: 1px solid #eee; font-size: 12px;">
            <div style="display: flex; justify-content: space-between;"><span><strong>${statusClass} ${item.status || 'Registrado'}</strong></span><span style="color: #999;">${item.data_registro ? new Date(item.data_registro).toLocaleDateString('pt-BR') : ''}</span></div>
            <div style="margin-top: 4px; color: #555;">${escapeHtml(item.comentario)}</div>
            <div style="margin-top: 4px; font-size: 11px; color: #999;">Por: ${escapeHtml(item.created_by || 'Sistema')}</div>
        </div>`;
    });
    return html;
}

export function renderizarListaFollowUps(followUps) {
    if (!followUps || followUps.length === 0) return '<div style="color: #999; font-size: 12px; text-align: center; padding: 10px;">Nenhum follow-up agendado</div>';
    const textoEtapa = { 'FOLLOW_UP_30': 'Passados 30 dias da implementação, está aderente?', 'FOLLOW_UP_60': 'Passados 60 dias da implementação, está aderente?', 'FOLLOW_UP_90': 'Passados 90 dias da implementação, está aderente?' };
    let html = '<div style="display: flex; flex-direction: column; gap: 8px;">';
    followUps.forEach(fu => {
        const dataPrevista = new Date(fu.data_prevista);
        const hoje = new Date();
        const estaAtrasado = dataPrevista < hoje && fu.status === 'Pendente';
        const statusIcon = { 'Pendente': '⏳', 'Aderente': '✅', 'Não aderente': '❌', 'Parcialmente aderente': '🟡' }[fu.status] || '⏳';
        let statusColor = { 'Pendente': '#856404', 'Aderente': '#155724', 'Não aderente': '#721c24', 'Parcialmente aderente': '#856404' }[fu.status] || '#666';
        if (estaAtrasado) statusColor = '#dc3545';
        const textoExibicao = textoEtapa[fu.etapa] || fu.etapa;
        html += `<div style="padding: 8px; background: #f8f9fa; border-radius: 6px; font-size: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span><strong>${textoExibicao}</strong></span>
                <span style="color: ${statusColor};">${statusIcon} ${fu.status || 'Pendente'}</span>
            </div>
            <div style="margin-top: 4px; color: #666;">Data prevista: ${fu.data_prevista ? new Date(fu.data_prevista).toLocaleDateString('pt-BR') : '-'}</div>
            ${fu.comentario ? `<div style="margin-top: 4px; font-size: 11px;">${escapeHtml(fu.comentario)}</div>` : ''}
            ${fu.status === 'Pendente' ? `<button class="btn-registrar-followup" onclick="event.stopPropagation(); abrirModalFollowUp(${fu.id}, '${textoExibicao}')" style="margin-top: 6px; background: #184145; color: white; border: none; padding: 3px 8px; border-radius: 4px; cursor: pointer; font-size: 10px;"><i class="fas fa-edit"></i> Registrar</button>` : ''}
        </div>`;
    });
    html += '</div>';
    return html;
}

// ============================================================
// HISTÓRICO DE ANDAMENTO E FOLLOW-UPS
// ============================================================

export async function carregarHistoricoAndamento(analiseId) {
    try {
        const response = await fetch(`/api/analise-historico/${analiseId}`);
        const data = await response.json();
        return data.success ? data.historico : [];
    } catch (error) {
        console.error('Erro ao carregar histórico:', error);
        return [];
    }
}

export async function carregarFollowUps(analiseId) {
    try {
        const response = await fetch(`/api/analise-follow-ups/${analiseId}`);
        const data = await response.json();
        return data.success ? data.follow_ups : [];
    } catch (error) {
        console.error('Erro ao carregar follow-ups:', error);
        return [];
    }
}

export function abrirModalHistoricoAndamento(analiseId) {
    document.getElementById('historico-analise-id').value = analiseId;
    document.getElementById('historico-status').value = 'Em andamento';
    document.getElementById('historico-comentario').value = '';
    document.getElementById('modal-historico-andamento').style.display = 'flex';
}

export function fecharModalHistorico() {
    document.getElementById('modal-historico-andamento').style.display = 'none';
}

export async function salvarHistoricoAndamento() {
    const analiseId = document.getElementById('historico-analise-id').value;
    const status = document.getElementById('historico-status').value;
    const comentario = document.getElementById('historico-comentario').value;
    
    if (!comentario.trim()) {
        mostrarToast('⚠️ O comentário é obrigatório', 'warning');
        return;
    }
    
    const btnSalvar = document.getElementById('btn-salvar-historico');
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    
    try {
        const response = await fetch('/api/analise-historico/salvar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ analise_id: analiseId, status: status, comentario: comentario })
        });
        const data = await response.json();
        if (data.success) {
            mostrarToast('✅ Andamento registrado com sucesso!', 'success');
            fecharModalHistorico();
            if (window.carregarAnalisesAuditor) {
                await window.carregarAnalisesAuditor();
            }
            if (window.carregarAnalisesAuditado) {
                await window.carregarAnalisesAuditado();
            }
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

export function abrirModalFollowUp(followUpId, etapa) {
    document.getElementById('followup-id').value = followUpId;
    document.getElementById('modal-followup-titulo').innerHTML = `<i class="fas fa-search"></i> Registrar ${etapa}`;
    document.getElementById('followup-status').value = 'Aderente';
    document.getElementById('followup-comentario').value = '';
    document.getElementById('modal-follow-up').style.display = 'flex';
}

export function fecharModalFollowUp() {
    document.getElementById('modal-follow-up').style.display = 'none';
}

export async function salvarFollowUp() {
    const followUpId = document.getElementById('followup-id').value;
    const status = document.getElementById('followup-status').value;
    const comentario = document.getElementById('followup-comentario').value;
    
    if (!comentario.trim()) {
        mostrarToast('⚠️ O comentário é obrigatório', 'warning');
        return;
    }
    
    const btnSalvar = document.getElementById('btn-salvar-followup');
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    
    try {
        const response = await fetch(`/api/analise-follow-up/${followUpId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status, comentario: comentario })
        });
        const data = await response.json();
        if (data.success) {
            mostrarToast('✅ Follow-up registrado com sucesso!', 'success');
            fecharModalFollowUp();
            if (window.carregarAnalisesAuditor) {
                await window.carregarAnalisesAuditor();
            }
            if (window.carregarAnalisesAuditado) {
                await window.carregarAnalisesAuditado();
            }
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

export async function criarFollowUpsAutomaticos(analiseId, dataImplantacaoEfetiva) {
    console.log('📅 Criando follow-ups para análise:', analiseId);
    if (!analiseId || !dataImplantacaoEfetiva) return;
    
    try {
        const checkResponse = await fetch(`/api/analise-follow-ups/${analiseId}`);
        const checkData = await checkResponse.json();
        if (checkData.success && checkData.follow_ups && checkData.follow_ups.length > 0) {
            console.log('✅ Follow-ups já existem');
            return;
        }
    } catch (error) { console.warn('Erro ao verificar follow-ups:', error); }
    
    const dataImplantacaoObj = new Date(dataImplantacaoEfetiva);
    if (isNaN(dataImplantacaoObj.getTime())) return;
    
    const data30 = new Date(dataImplantacaoObj); data30.setDate(data30.getDate() + 30);
    const data60 = new Date(dataImplantacaoObj); data60.setDate(data60.getDate() + 60);
    const data90 = new Date(dataImplantacaoObj); data90.setDate(data90.getDate() + 90);
    
    const followUps = [
        { etapa: 'FOLLOW_UP_30', data_prevista: data30.toISOString().split('T')[0] },
        { etapa: 'FOLLOW_UP_60', data_prevista: data60.toISOString().split('T')[0] },
        { etapa: 'FOLLOW_UP_90', data_prevista: data90.toISOString().split('T')[0] }
    ];
    
    try {
        const response = await fetch('/api/analise-follow-ups/criar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ analise_id: analiseId, follow_ups: followUps })
        });
        const data = await response.json();
        if (data.success) console.log('✅ Follow-ups criados com sucesso');
    } catch (error) { console.error('❌ Erro ao criar follow-ups:', error); }
}