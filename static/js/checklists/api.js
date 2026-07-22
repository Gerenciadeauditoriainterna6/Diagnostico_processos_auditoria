import { processoIdAtual } from './estado.js';

export async function carregarAreas() {
    const select = document.getElementById('area_select');
    if (!select) return;
    
    try {
        const response = await fetchComAutenticacao('/api/areas');
        const areas = await response.json();
        select.innerHTML = '<option value="">Selecione uma área...</option>';
        areas.forEach(area => { 
            const option = document.createElement('option'); 
            option.value = area.id_area; 
            
            // ⭐ FORMATAR COM UNIDADE
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
        const response = await fetchComAutenticacao(`/api/auditorias-por-area?area_id=${areaId}`);
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
    if (!auditoriaId) { row.style.display = 'none'; return; }
    try {
        const response = await fetchComAutenticacao(`/api/relatorios/processos-por-auditoria?auditoria_id=${auditoriaId}`);
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

export async function carregarProgressoChecklists() {
    if (!processoIdAtual) return;
    try {
        const response = await fetchComAutenticacao(`/api/checklist/progresso?processo_id=${processoIdAtual}`);
        const data = await response.json();
        console.log('📊 Progresso recebido:', data);
        
        if (data.success && data.progresso) {
            for (const [tipo, info] of Object.entries(data.progresso)) {
                const statusEl = document.getElementById(`status-${tipo}`);
                const textEl = document.getElementById(`progresso-text-${tipo}`);
                const fillEl = document.getElementById(`progresso-fill-${tipo}`);
                if (statusEl) statusEl.textContent = info.status;
                if (textEl) textEl.textContent = `${info.respondidas} de ${info.total} perguntas`;
                if (fillEl) fillEl.style.width = `${(info.respondidas / info.total) * 100}%`;
            }
        }
    } catch (error) { 
        console.error('❌ Erro ao carregar progresso:', error); 
    }
}



export async function baixarAnexo(analiseId) {
    window.open(`/api/analise-auditor/${analiseId}/anexo`, '_blank');
}

export async function baixarAnexoAuditado(analiseId) {
    window.open(`/api/analise-auditado/${analiseId}/anexo`, '_blank');
}