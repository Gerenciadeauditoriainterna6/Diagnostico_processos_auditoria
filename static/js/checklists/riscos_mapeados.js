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
            // ⭐ ABRIR CARD + HEADER + ABRIR CORPO
            html += `
                <div class="etapa-riscos-card">
                    <div class="etapa-header-riscos" data-etapa-id="${etapaId}">
                        <div class="etapa-header-riscos-left">
                            <i class="fas fa-folder-open" style="color: #0b5b99;"></i>
                            <strong>Etapa ${escapeHtml(etapa.codigo_etapa)}: ${escapeHtml(etapa.nome_etapa)}</strong>
                        </div>
                        <i class="fas fa-chevron-down etapa-chevron" style="transition: transform 0.3s;"></i>
                    </div>
                    <div class="etapa-riscos-body" id="etapa-riscos-${etapaId}" style="display: none;">
            `;
            
            // ⭐ ADICIONAR RISCOS DENTRO DO CORPO
            etapa.riscos.forEach(risco => {
                const controles = risco.controles || [];
                
                let controlesHtml = '';
                if (controles.length > 0) {
                    controlesHtml = `
                        <div style="margin-left: 24px; margin-bottom: 8px;">
                            ${controles.map(controle => `
                                <div style="display: flex; flex-direction: column; gap: 2px; margin-bottom: 4px;">
                                    <div style="display: flex; align-items: center; gap: 6px;">
                                        <i class="fas fa-shield-alt" style="color: #0b5b99; font-size: 12px;"></i>
                                        <span style="font-size: 14px; color: #666;">${escapeHtml(controle.nome_controle || '')}</span>
                                    </div>
                                    ${controle.descricao_tratamento ? `
                                    <span style="font-size: 12px; color: #999; margin-left: 16px;">
                                    Tratamento do risco: ${escapeHtml(controle.descricao_tratamento)}
                                    </span>
                                    ` : '<span style="font-size: 12px; color: #999; margin-left: 16px;">Não há descrição do tratamento do risco para este controle</span>'}
                                </div>
                            `).join('')}
                        </div>
                    `;
                } else {
                    controlesHtml = `
                        <div style="margin-left: 24px; margin-bottom: 8px;">
                            <span style="font-size: 14px; color: #999; font-style: italic;">Nenhum controle informado</span>
                        </div>
                    `;
                }
                
                html += `
                    <div style="background: #ffffff; border: 1px solid #e8ecf0; border-left: 4px solid #fd6a14; border-radius: 10px; padding: 15px; margin-bottom: 8px; margin-left: 20px;">
                        <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px;">
                            <i class="fas fa-exclamation-triangle" style="color: #fd6a14; font-size: 14px; margin-top: 2px;"></i>
                            <span style="font-size: 14px; color: #333; font-weight: 500;">${escapeHtml(risco.nome_risco || '')}</span>
                        </div>
                        
                        ${controlesHtml}
                        
                        <div style="margin-left: 24px;">
                            <label style="font-size: 13px; color: #666; font-weight: 600;">Parecer do Auditor:</label>
                            <small style="display: block; font-size: 12px; color: #d31616; margin-top: 2px; font-style: italic;">
                                Lembre-se de ao desenvolver o parecer, sugerir ação de controle
                            </small>
                            
                            <textarea class="parecer-risco-etapa auto-resize" data-risco-id="${risco.id}" 
                                placeholder="Digite seu parecer sobre este risco..."
                                style="width: 100%; padding: 8px 10px; border: 1px solid #e0e0e0; border-radius: 6px; font-size: 12px; margin-top: 4px; resize: vertical;" rows="2">${escapeHtml(risco.parecer_auditor || '')}</textarea>
                        </div>
                    </div>
                `;
            });
            
            // ⭐ FECHAR CORPO + CARD
            html += `
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
        
        // ⭐ VINCULAR EVENTO DE TOGGLE NOS HEADERS DE ETAPA
        container.querySelectorAll('.etapa-header-riscos').forEach(header => {
            header.addEventListener('click', () => {
                const etapaId = header.dataset.etapaId;
                const body = document.getElementById(`etapa-riscos-${etapaId}`);
                const chevron = header.querySelector('.etapa-chevron');
                
                if (body.style.display === 'none') {
                    body.style.display = 'block';
                    chevron.style.transform = 'rotate(180deg)';
                    
                    // ⭐ AJUSTAR TEXTAREAS DEPOIS DE MOSTRAR
                    body.querySelectorAll('.parecer-risco-etapa').forEach(textarea => {
                        textarea.style.height = 'auto';
                        textarea.style.height = textarea.scrollHeight + 'px';
                    });
                } else {
                    body.style.display = 'none';
                    chevron.style.transform = 'rotate(0deg)';
                }
            });
        });
        
        // ⭐ AUTO-RESIZE DAS TEXTAREAS
        container.querySelectorAll('.parecer-risco-etapa').forEach(textarea => {
            const ajustarAltura = () => {
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            };
            textarea.addEventListener('input', ajustarAltura);
            ajustarAltura();
        });
        
        // ⭐ Mostrar botão salvar
        if (btnSalvarContainer) btnSalvarContainer.style.display = 'block';
        
        // ⭐ VINCULAR EVENTO DO BOTÃO SALVAR
        const btnSalvar = document.getElementById('btn-salvar-pareceres');
        if (btnSalvar) {
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
