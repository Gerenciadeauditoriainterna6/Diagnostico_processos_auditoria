// ============================================================
// IMPORTS
// ============================================================

import { 
    carregarAreas,
    carregarAuditorias,
    carregarProcessos,
    carregarProgressoChecklists
} from './api.js';

import { 
    processoIdAtual,
    auditoriaIdAtual,
    setProcessoId,
    setAuditoriaId
} from './estado.js';

import { mostrarToast } from './utils.js';

import { 
    carregarAnalisesAuditado,
    salvarAnaliseAuditado,
    setupSemSugestaoCheckbox,
    setupFileUploadEvidenciaAuditado,
    editarAnaliseAuditado,
    abrirModalConfirmarImplantacaoAuditado,
    baixarEvidenciaAuditadoChecklist
} from './analises-auditado.js';

import { 
    carregarAnalisesAuditor,
    salvarAnaliseAuditor,
    abrirModalNovaAnaliseAuditor,
    setupSemSugestaoCheckboxAuditor,
    setupFileUploadEvidenciaAuditor,
    confirmarImplantacao,
    editarAnaliseAuditor,
    excluirAnaliseAuditor,
    fecharModalAnaliseAuditor,
    abrirModalConfirmarImplantacao
} from './analises-auditor.js';

import { 
    salvarHistoricoAndamento,
    salvarFollowUp,
    abrirModalHistoricoAndamento,
    fecharModalHistorico,
    abrirModalFollowUp,
    fecharModalFollowUp
} from './historico.js';

import { 
    abrirModalChecklist,
    fecharModalChecklist,
    abrirUploadEvidencia,
    removerEvidenciaTemp,
    removerEvidenciaChecklist,
    baixarEvidenciaChecklist
 } from './checklist.js';

export function toggleAnaliseAuditorCard(header) {
    const card = header.closest('.analise-auditor-card');
    card.classList.toggle('expanded');
    const icon = header.querySelector('.fa-chevron-down');
    icon.style.transform = card.classList.contains('expanded') ? 'rotate(180deg)' : 'rotate(0deg)';
}

export function toggleAnaliseEtapaCard(header) {
    const card = header.closest('.analise-etapa-card');
    const body = card.querySelector('.analise-etapa-body');
    const icon = header.querySelector('.fa-chevron-down');
    if (body.style.display === 'none') {
        body.style.display = 'block';
        icon.style.transform = 'rotate(180deg)';
    } else {
        body.style.display = 'none';
        icon.style.transform = 'rotate(0deg)';
    }
}

export function toggleAnaliseAuditadoCard(header) {
    const card = header.closest('.analise-auditado-card');
    card.classList.toggle('expanded');
    const icon = header.querySelector('.fa-chevron-down');
    icon.style.transform = card.classList.contains('expanded') ? 'rotate(180deg)' : 'rotate(0deg)';
}

window.fecharModalChecklist = fecharModalChecklist;
window.toggleAnaliseAuditorCard = toggleAnaliseAuditorCard;
window.toggleAnaliseEtapaCard = toggleAnaliseEtapaCard;
window.toggleAnaliseAuditadoCard = toggleAnaliseAuditadoCard;
window.editarAnaliseAuditado = editarAnaliseAuditado;
window.abrirModalNovaAnaliseAuditor = abrirModalNovaAnaliseAuditor;
window.fecharModalAnaliseAuditor = fecharModalAnaliseAuditor;
window.editarAnaliseAuditor = editarAnaliseAuditor;
window.excluirAnaliseAuditor = excluirAnaliseAuditor;
window.abrirModalConfirmarImplantacao = abrirModalConfirmarImplantacao;
window.abrirModalConfirmarImplantacaoAuditado = abrirModalConfirmarImplantacaoAuditado;
window.baixarEvidenciaAuditadoChecklist = baixarEvidenciaAuditadoChecklist;
window.abrirUploadEvidencia = abrirUploadEvidencia;
window.removerEvidenciaTemp = removerEvidenciaTemp;
window.removerEvidenciaChecklist = removerEvidenciaChecklist;
window.baixarEvidenciaChecklist = baixarEvidenciaChecklist;
window.abrirModalHistoricoAndamento = abrirModalHistoricoAndamento;
window.fecharModalHistorico = fecharModalHistorico;
window.abrirModalFollowUp = abrirModalFollowUp;
window.fecharModalFollowUp = fecharModalFollowUp;

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
    await carregarAreas();
    
    const selectArea = document.getElementById('area_select');
    const selectAuditoria = document.getElementById('auditoria_select');
    const selectProcesso = document.getElementById('processo_select');
    
    selectArea.addEventListener('change', () => { 
        carregarAuditorias(selectArea.value); 
        document.getElementById('conteudo-principal').style.display = 'none'; 
    });
    
    selectAuditoria.addEventListener('change', async () => { 
        if (selectAuditoria.value) await carregarProcessos(selectAuditoria.value); 
        else document.getElementById('row-processo').style.display = 'none'; 
    });
    
    selectProcesso.addEventListener('change', async () => {
        if (selectProcesso.value && selectAuditoria.value) {
            console.log('Tentando atribuir:', selectProcesso.value);
            console.log('processoIdAtual antes:', processoIdAtual);
            
            setProcessoId(selectProcesso.value);
            setAuditoriaId(selectAuditoria.value);
            
            console.log('processoIdAtual depois:', processoIdAtual);
            document.getElementById('conteudo-principal').style.display = 'block';
            await carregarProgressoChecklists();
            await carregarAnalisesAuditado();
            await carregarAnalisesAuditor();
        } else {
            document.getElementById('conteudo-principal').style.display = 'none';
        }
    });
    
    document.querySelectorAll('.btn-checklist').forEach(btn => { 
        btn.addEventListener('click', () => { 
            if (processoIdAtual) abrirModalChecklist(btn.getAttribute('data-tipo')); 
            else mostrarToast('Selecione um processo primeiro', 'warning'); 
        }); 
    });
    
    document.getElementById('btn-nova-analise-auditor')?.addEventListener('click', abrirModalNovaAnaliseAuditor);
    document.getElementById('btn-salvar-analise-auditor')?.addEventListener('click', salvarAnaliseAuditor);
    document.getElementById('btn-salvar-analise-auditado')?.addEventListener('click', salvarAnaliseAuditado);
    document.getElementById('btn-salvar-historico')?.addEventListener('click', salvarHistoricoAndamento);
    document.getElementById('btn-salvar-followup')?.addEventListener('click', salvarFollowUp);
    document.getElementById('btn-confirmar-implantacao')?.addEventListener('click', confirmarImplantacao);
    
    setupSemSugestaoCheckbox();

    setupSemSugestaoCheckboxAuditor();

    setupFileUploadEvidenciaAuditor();
    setupFileUploadEvidenciaAuditado();

});