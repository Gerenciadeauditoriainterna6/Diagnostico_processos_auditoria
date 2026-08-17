// ============================================================
// riscos-mapeados.js - RISCOS MAPEADOS E PARECER DO AUDITOR
// ============================================================

import { mostrarToast, escapeHtml } from './utils.js';
import { processoIdAtual } from './estado.js';

export async function carregarRiscosMapeados() {
    if (!processoIdAtual) return;
    
    console.log('🎯 Carregando riscos das etapas do processo:', processoIdAtual);
    
    const container = document.getElementById('riscos-mapeados-container');
    const secao = document.getElementById('secao-riscos-mapeados');
    const btnSalvarContainer = document.getElementById('btn-salvar-pareceres-container');
    
    if (!container || !secao) return;
    
    secao.style.display = 'block';
    container.innerHTML = '<div style="text-align: center; padding: 40px;"><i class="fas fa-spinner fa-spin"></i> Carregando riscos...</div>';
    
    try {
        const response = await fetchComAutenticacao(`/api/processo/${processoIdAtual}/riscos-mapeados`);
        const data = await response.json();
        
        if (!data.success) {
            container.innerHTML = `<div class="alert-error">❌ Erro ao carregar riscos: ${data.error || ''}</div>`;
            return;
        }
        
        const riscosEtapas = data.riscos_etapas || [];
        
        if (riscosEtapas.length === 0) {
            container.innerHTML = `<div style="text-align: center; padding: 40px; color: #999;">Nenhum risco mapeado para este processo.</div>`;
            if (btnSalvarContainer) btnSalvarContainer.style.display = 'none';
            return;
        }
        
        // Agrupar por etapa
        const etapasMap = {};
        riscosEtapas.forEach(risco => {
            const key = risco.etapa_id;
            if (!etapasMap[key]) {
                etapasMap[key] = {
                    etapa_id: risco.etapa_id,
                    codigo_etapa: risco.codigo_etapa,
                    nome_etapa: risco.nome_etapa,
                    riscos: []
                };
            }
            etapasMap[key].riscos.push(risco);
        });
        
        let html = '';
        
        for (const [etapaId, etapa] of Object.entries(etapasMap)) {
            html += `
                <div style="margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px; padding: 8px 12px; background: #e8f4f8; border-radius: 8px;">
                        <i class="fas fa-folder-open" style="color: #fd6a14;"></i>
                        <strong style="color: #184145; font-size: 13px;">${escapeHtml(etapa.codigo_etapa)}</strong>
                        <span style="color: #666; font-size: 13px;">${escapeHtml(etapa.nome_etapa)}</span>
                    </div>
            `;
            
            etapa.riscos.forEach(risco => {
                // ⭐ Pegar controles do risco
                const controles = risco.controles || [];
                
                // ⭐ Montar HTML dos controles
                let controlesHtml = '';
                if (controles.length > 0) {
                    controlesHtml = `
                        <div style="margin-left: 24px; margin-bottom: 8px;">
                            ${controles.map(controle => `
                                <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                                    <i class="fas fa-shield-alt" style="color: #0b5b99; font-size: 10px;"></i>
                                    <span style="font-size: 11px; color: #666;">${escapeHtml(controle.nome_controle || '')}</span>
                                </div>
                            `).join('')}
                        </div>
                    `;
                } else {
                    controlesHtml = `
                        <div style="margin-left: 24px; margin-bottom: 8px;">
                            <span style="font-size: 11px; color: #999; font-style: italic;">Nenhum controle informado</span>
                        </div>
                    `;
                }
                
                html += `
                    <div style="background: #ffffff; border: 1px solid #e8ecf0; border-left: 4px solid #fd6a14; border-radius: 10px; padding: 15px; margin-bottom: 8px; margin-left: 20px;">
                        <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px;">
                            <i class="fas fa-exclamation-triangle" style="color: #fd6a14; font-size: 14px; margin-top: 2px;"></i>
                            <span style="font-size: 13px; color: #333; font-weight: 500;">${escapeHtml(risco.nome_risco || '')}</span>
                        </div>
                        
                        ${controlesHtml}
                        
                        <div style="margin-left: 24px;">
                            <label style="font-size: 11px; color: #666; font-weight: 600;">Parecer do Auditor:</label>
                            <textarea class="parecer-risco-etapa" data-risco-id="${risco.id}" 
                                placeholder="Digite seu parecer sobre este risco..."
                                style="width: 100%; padding: 8px 10px; border: 1px solid #e0e0e0; border-radius: 6px; font-size: 12px; margin-top: 4px; resize: vertical;" rows="2">${escapeHtml(risco.parecer_auditor || '')}</textarea>
                        </div>
                    </div>
                `;
            });
            
            html += `</div>`;
        }
        
        container.innerHTML = html;
        
        // ⭐ Mostrar botão salvar
        if (btnSalvarContainer) btnSalvarContainer.style.display = 'block';
        
        // ⭐ VINCULAR EVENTO DO BOTÃO SALVAR
        const btnSalvar = document.getElementById('btn-salvar-pareceres');
        if (btnSalvar) {
            // Remover listener antigo (evita duplicação)
            btnSalvar.replaceWith(btnSalvar.cloneNode(true));
            const novoBtn = document.getElementById('btn-salvar-pareceres');
            novoBtn.addEventListener('click', salvarPareceres);
        }
        
    } catch (error) {
        console.error('❌ Erro ao carregar riscos mapeados:', error);
        container.innerHTML = `<div class="alert-error">❌ Erro ao carregar riscos</div>`;
    }
}

// ⭐ FUNÇÃO PARA SALVAR TODOS OS PARECERES
async function salvarPareceres() {
    console.log('💾 Salvando pareceres...');
    
    const pareceres = document.querySelectorAll('.parecer-risco-etapa');
    
    if (pareceres.length === 0) {
        mostrarToast('⚠️ Nenhum parecer para salvar', 'warning');
        return;
    }
    
    let salvos = 0;
    let erros = 0;
    
    // Desabilitar botão durante salvamento
    const btnSalvar = document.getElementById('btn-salvar-pareceres');
    if (btnSalvar) {
        btnSalvar.disabled = true;
        btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
    }
    
    for (const textarea of pareceres) {
        const riscoId = textarea.dataset.riscoId;
        const parecer = textarea.value.trim();
        
        try {
            const response = await fetchComAutenticacao(`/api/risco-etapa/${riscoId}/parecer`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ parecer: parecer })
            });
            
            const data = await response.json();
            
            if (data.success) {
                salvos++;
            } else {
                erros++;
                console.error(`❌ Erro no risco ${riscoId}:`, data.error);
            }
        } catch (error) {
            erros++;
            console.error(`❌ Erro de conexão no risco ${riscoId}:`, error);
        }
    }
    
    // Restaurar botão
    if (btnSalvar) {
        btnSalvar.disabled = false;
        btnSalvar.innerHTML = '<i class="fas fa-save"></i> Salvar Pareceres';
    }
    
    if (erros === 0) {
        mostrarToast(`✅ ${salvos} parecer(es) salvos com sucesso!`, 'success');
    } else {
        mostrarToast(`⚠️ ${salvos} salvos, ${erros} com erro`, 'warning');
    }
}