
let currentRespostaIds = {};
let arquivoSelecionadoAuditor = null;  
let anexoExistenteNomeAuditor = null;  
let auditoriaIdAtual = null;
let processoIdAtual = null;
let analisesAuditorList = [];

// Variáveis para análises do auditado
let analisesAuditadoList = [];

// Variáveis para checklist
let currentRespostaId = null;
let arquivosPendentes = {};
// ⭐ Variáveis para evidência da análise do auditado
let arquivoSelecionadoAuditadoEvidencia = null;
let anexoExistenteAuditadoEvidencia = null;


// ============================================================
// FUNÇÕES AUXILIARES
// ============================================================

function getSugestaoImplantadaValue(selectValue) {
    if (selectValue === 'true') return true;
    if (selectValue === 'false') return false;
    return null;
}

function setSugestaoImplantadaSelect(selectElement, valor) {
    if (valor === true) selectElement.value = 'true';
    else if (valor === false) selectElement.value = 'false';
    else selectElement.value = '';
}

function formatarData(dataISO) {
    if (!dataISO) return '';
    const partes = dataISO.split('-');
    if (partes.length === 3) return `${partes[2]}/${partes[1]}/${partes[0]}`;
    return dataISO;
}

function escapeHtml(text) { 
    return text ? text.replace(/[&<>]/g, function(m) { 
        if (m === '&') return '&amp;'; 
        if (m === '<') return '&lt;'; 
        if (m === '>') return '&gt;'; 
        return m; 
    }) : ''; 
}

function mostrarToast(mensagem, tipo) { 
    alert(mensagem); 
}

function converterParaBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(new Error('Erro ao ler arquivo'));
        reader.readAsDataURL(file);
    });
}









// ============================================================
// ABRIR MODAL - NOVA ANÁLISE DO AUDITADO
// ============================================================

function abrirModalNovaAnaliseAuditado(etapaId, etapaNome, categoria) {
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
// MODAL DO AUDITOR
// ============================================================

function abrirModalNovaAnaliseAuditor() {
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
    arquivoSelecionadoAuditor = null;
    anexoExistenteNomeAuditor = null;
    
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

async function editarAnaliseAuditor(id) {
    console.log('✏️ editarAnaliseAuditor chamado para ID:', id);
    
    const response = await fetchComAutenticacao(`/api/analises-auditor/por-processo?processo_id=${processoIdAtual}`);
    const data = await response.json();
    
    if (data.success) analisesAuditorList = data.analises;
    
    const analise = analisesAuditorList.find(a => a.id === id);
    if (!analise) return;
    
    document.getElementById('modal-analise-titulo').innerHTML = '<i class="fas fa-edit"></i> Editar Análise do Auditor';
    document.getElementById('analise-auditor-id').value = analise.id;
    document.getElementById('analise-auditor-texto').value = analise.analise_critica || '';
    document.getElementById('analise-auditor-sugestao').value = analise.sugestao_melhoria || '';
    document.getElementById('analise-auditor-necessidade').value = analise.necessidade_implantacao || '';
    document.getElementById('analise-auditor-ganho').value = analise.ganho_previsto || '';
    document.getElementById('analise-auditor-observacoes').value = analise.observacoes || '';

    // Verificar se o valor é "INEXISTENTE" para marcar o checkbox
    const checkbox = document.getElementById('sem_sugestao_melhoria_auditor');
    const textarea = document.getElementById('analise-auditor-sugestao');
    
    if (checkbox && textarea) {
        const sugestaoValue = analise.sugestao_melhoria || '';
        if (sugestaoValue.trim().toUpperCase() === 'INEXISTENTE') {
            checkbox.checked = true;
            textarea.disabled = true;
            textarea.style.backgroundColor = '#f5f5f5';
            textarea.style.color = '#999';
        } else {
            checkbox.checked = false;
            textarea.disabled = false;
            textarea.style.backgroundColor = '';
            textarea.style.color = '';
        }
    }

    // Limpar estado anterior
    arquivoSelecionadoAuditor = null;
    anexoExistenteNomeAuditor = null;
    const evidenciaDiv = document.getElementById('evidencia-nome-auditor');
    const evidenciaTexto = document.getElementById('evidencia-nome-texto-auditor');
    
    if (analise.evidencias && analise.evidencias.length > 0) {
        const evidencia = analise.evidencias[0];
        anexoExistenteNomeAuditor = evidencia.nome_arquivo;
        
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
    
    // ⭐⭐⭐ CORREÇÃO: RADIOS ⭐⭐⭐
    const radios = document.querySelectorAll('#modal-analise-auditor input[name="sugestao-status-radio"]');
    let valorParaMarcar = '';
    
    console.log('📊 analise.sugestao_sera_implantada:', analise.sugestao_sera_implantada);
    
    if (analise.sugestao_sera_implantada === true) {
        valorParaMarcar = 'true';
    } else if (analise.sugestao_sera_implantada === false) {
        valorParaMarcar = 'false';
        limparCamposPlanoAcaoAuditor();
    } else {
        valorParaMarcar = '';
        limparCamposPlanoAcaoAuditor();
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
    
    // ⭐ ABRIR MODAL
    document.getElementById('modal-analise-auditor').style.display = 'flex';

}

async function salvarAnaliseAuditor() {
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
            arquivoSelecionadoAuditor = null;
            anexoExistenteNomeAuditor = null;
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

async function excluirAnaliseAuditor(id) {
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

function fecharModalAnaliseAuditor() {
    document.getElementById('modal-analise-auditor').style.display = 'none';
    
    // ⭐ NOVO: Limpar estado da evidência ao fechar o modal
    arquivoSelecionadoAuditor = null;
    anexoExistenteNomeAuditor = null;
    
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
// FUNÇÃO PARA UPLOAD DE EVIDÊNCIA DO AUDITADO
// ============================================================

function setupFileUploadEvidenciaAuditado() {
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
            anexoExistenteAuditadoEvidencia = null;
            console.log('📎 Evidência do auditado selecionada:', file.name);
        }
    });
    
    if (btnRemover) {
        btnRemover.addEventListener('click', (e) => {
            e.preventDefault();
            inputFile.value = '';
            arquivoSelecionadoAuditadoEvidencia = null;
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
                anexoExistenteAuditadoEvidencia = null;
            }
            console.log('🗑️ Evidência do auditado removida');
        });
    }
}

// ============================================================
// FUNÇÃO PARA UPLOAD DE EVIDÊNCIA DO AUDITOR
// ============================================================

function setupFileUploadEvidenciaAuditor() {
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
            arquivoSelecionadoAuditor = file;
            
            // Mostrar na interface
            if (evidenciaTexto) evidenciaTexto.textContent = file.name;
            if (evidenciaDiv) evidenciaDiv.style.display = 'flex';
            
            // Remover referência a arquivo existente
            anexoExistenteNomeAuditor = null;
            
            console.log('📎 Evidência selecionada:', file.name);
        }
    });
    
    // Botão para remover arquivo
    if (btnRemover) {
        btnRemover.addEventListener('click', (e) => {
            e.preventDefault();
            inputFile.value = '';
            arquivoSelecionadoAuditor = null;
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

function renderizarEvidencias(evidencias, perguntaIndex, itemIndex) {
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

// ============================================================
// FUNÇÕES DO CHECKLIST COM EVIDÊNCIAS
// ============================================================

async function carregarChecklistModal(tipo) {
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
        
        const response = await fetchComAutenticacao(url);
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
        currentRespostaId = dados.success ? dados.id : null;
        
        // ⭐ MONTAR MAPA DE RESPOSTAS POR ORDEM
        const respostasMap = {};
        if (dados.success && dados.respostas) {
            dados.respostas.forEach(r => {
                const ordemKey = String(r.ordem);
                respostasMap[ordemKey] = r;
            });
        }
        
        // ⭐⭐⭐ EXTRAIR IDs DAS RESPOSTAS ANTES DE CARREGAR EVIDÊNCIAS ⭐⭐⭐
        currentRespostaIds = {};
        for (const [ordem, resposta] of Object.entries(respostasMap)) {
            if (resposta.id) {
                currentRespostaIds[ordem] = resposta.id;
            }
        }
        console.log('📊 IDs das respostas extraídas:', currentRespostaIds);
        
        // ⭐ CARREGAR EVIDÊNCIAS PARA CADA RESPOSTA
        const evidenciasMap = {};
        for (const [ordem, resposta] of Object.entries(respostasMap)) {
            if (resposta.id) {
                try {
                    const evResponse = await fetchComAutenticacao(`/api/checklist/evidencias/${resposta.id}`);
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

// Upload de evidência para item do grupo
function abrirUploadEvidenciaGrupo(grupoIndex, itemIndex) {
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

function abrirUploadEvidencia(perguntaIndex) {
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

function removerEvidenciaTemp(tempId, perguntaIndex) {
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

async function carregarEvidenciasPergunta(perguntaIndex) {
    const perguntas = PERGUNTAS[tipoAtual]; // Você precisa ter o tipo atual
    const pergunta = perguntas[perguntaIndex];
    const respostaId = currentRespostaIds[pergunta.ordem];
    
    if (!respostaId) return;
    
    try {
        const response = await fetchComAutenticacao(`/api/checklist/evidencias/${respostaId}`);
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

async function removerEvidenciaChecklist(evidenciaId, perguntaIndex) {
    if (!confirm('⚠️ Tem certeza que deseja remover esta evidência?')) return;
    
    // ⭐ MOSTRAR LOADING NO BOTÃO
    const evidenciaItem = document.querySelector(`.evidencia-item[data-evidencia-id="${evidenciaId}"]`);
    if (evidenciaItem) {
        evidenciaItem.style.opacity = '0.5';
        evidenciaItem.style.pointerEvents = 'none';
        evidenciaItem.innerHTML = '<div style="padding: 8px;"><i class="fas fa-spinner fa-spin"></i> Removendo...</div>';
    }
    
    try {
        const response = await fetchComAutenticacao(`/api/checklist/evidencia/${evidenciaId}`, { 
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

async function baixarEvidenciaChecklist(evidenciaId) {
    window.open(`/api/checklist/evidencia/${evidenciaId}/download`, '_blank');
}

async function salvarChecklist(tipo, concluir) {
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
        
        const response = await fetchComAutenticacao('/api/checklist/salvar', { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(bodyData) 
        });
        
        const data = await response.json();
        console.log('📥 Resposta do servidor:', data);
        
        if (data.success) {
            // ⭐ GUARDAR OS IDs DAS RESPOSTAS
            currentRespostaIds = data.respostas_ids || {};
            currentRespostaId = data.id;
            
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
                            
                            const evidenciaResponse = await fetchComAutenticacao('/api/checklist/evidencia/salvar', {
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
                arquivosPendentes = {};
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

function fecharModalChecklist() {
    document.getElementById('modal-checklist').style.display = 'none';
    arquivosPendentes = {};
}

function abrirModalChecklist(tipo) {
    const modal = document.getElementById('modal-checklist');
    const titulo = document.getElementById('modal-checklist-titulo');
    if (tipo === 'governanca') titulo.innerHTML = '<i class="fas fa-briefcase"></i> Checklist - Governança';
    else if (tipo === 'riscos') titulo.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Checklist - Riscos';
    else titulo.innerHTML = '<i class="fas fa-shield-alt"></i> Checklist - Controles';
    modal.style.display = 'flex';
    carregarChecklistModal(tipo);
}

// ============================================================
// CARREGAR DADOS BÁSICOS
// ============================================================

async function carregarAreas() {
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

async function carregarAuditorias(areaId) {
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

async function carregarProcessos(auditoriaId) {
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

async function carregarProgressoChecklists() {
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

// ============================================================
// ANÁLISES DO AUDITADO - VERSÃO COMPLETA
// ============================================================

async function carregarAnalisesAuditado() {
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
                                
                                <!-- Histórico de Andamento -->
                                <div class="analise-card-section" style="margin-top: 20px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                        <h4 style="margin-bottom: 0; border-bottom: none; padding-bottom: 0;">
                                            <i class="fas fa-history"></i> Histórico de Andamento
                                        </h4>
                                        ${analise.sugestao_sera_implantada === true ? `
                                            <button class="btn-registrar-andamento" onclick="event.stopPropagation(); abrirModalHistoricoAndamento(${analise.id})">
                                                <i class="fas fa-plus"></i> Registrar
                                            </button>
                                        ` : ''}
                                    </div>
                                    <div class="historico-container">
                                        ${renderizarListaHistorico(analise.historico)}
                                    </div>
                                </div>
                                
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

// ============================================================
// EDITAR ANÁLISE DO AUDITADO
// ============================================================

async function editarAnaliseAuditado(id) {
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
                        
                        // ⭐ ESCONDER CAMPOS
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
                        
                        // ⭐ MOSTRAR CAMPOS
                        if (camposContainer) {
                            camposContainer.style.display = 'block';
                            const radios = camposContainer.querySelectorAll('input[type="radio"]');
                            radios.forEach(radio => radio.disabled = false);
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
                arquivoSelecionadoAuditadoEvidencia = null;
                anexoExistenteAuditadoEvidencia = null;
                
                const evidenciaDiv = document.getElementById('evidencia-nome-auditado');
                const evidenciaTexto = document.getElementById('evidencia-nome-texto-auditado');
                
                if (analise.evidencia_url && analise.evidencia_nome) {
                    anexoExistenteAuditadoEvidencia = analise.evidencia_nome;
                    
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
                    // Preencher campos do plano de ação
                    document.getElementById('plano-acao-auditado').value = analise.plano_acao || '';
                    document.getElementById('responsavel-implantacao-auditado').value = analise.responsavel_implantacao || '';
                    document.getElementById('data-inicio-implantacao-auditado').value = analise.data_inicio_implantacao || '';
                    document.getElementById('data-conclusao-prevista-auditado').value = analise.data_conclusao_prevista || '';
                    
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

// ============================================================
// SALVAR ANÁLISE DO AUDITADO
// ============================================================

async function salvarAnaliseAuditado() {
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

// ============================================================
// FECHAR MODAL DO AUDITADO
// ============================================================

window.fecharModalAnaliseAuditado = function() {
    document.getElementById('modal-analise-auditado').style.display = 'none';
}





// ============================================================
// ANÁLISES DO AUDITOR - RENDERIZAÇÃO
// ============================================================

async function renderizarAnalisesAuditor() {
    const container = document.getElementById('analises-auditor-container');
    
    if (analisesAuditorList.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 40px; color: #999;">Nenhuma análise do auditor cadastrada.<br><br>
            <button class="btn-primary" onclick="abrirModalNovaAnaliseAuditor()"><i class="fas fa-plus"></i> Nova Análise</button></div>`;
        return;
    }
    
    const analisesComDados = [];
    for (const analise of analisesAuditorList) {
        const historico = await carregarHistoricoAndamento(analise.id);
        const followUps = await carregarFollowUps(analise.id);
        analisesComDados.push({ ...analise, historico, followUps });
    }
    
    let html = '';
    analisesComDados.forEach((analise, index) => {
        const temPlanoAcao = analise.sugestao_sera_implantada === true && analise.plano_acao;
        const prazoExpirado = analise.sugestao_sera_implantada === true &&
                            !analise.plano_de_acao_implantado && 
                            analise.data_conclusao_prevista && 
                            new Date(analise.data_conclusao_prevista) < new Date();
        
        // ⭐ NOVO: Verificar se tem evidências
        const temEvidencia = analise.evidencias && analise.evidencias.length > 0;
        
        // ⭐⭐⭐ MELHORIA: Verificar se TEM sugestão de melhoria ⭐⭐⭐
        const valoresSemSugestao = ['', ' ', 'null', 'undefined', 'inexistente', 'INEXISTENTE', 'não se aplica', 'NÃO SE APLICA'];
        const temSugestaoMelhoria = analise.sugestao_melhoria && 
                                typeof analise.sugestao_melhoria === 'string' && 
                                !valoresSemSugestao.includes(analise.sugestao_melhoria.trim().toLowerCase());
        
        // ⭐ BADGE - APENAS SE HOUVER SUGESTÃO DE MELHORIA
        let badgeHtml = '';
        if (temSugestaoMelhoria) {
            if (analise.sugestao_sera_implantada === true) {
                badgeHtml = '<span class="analise-auditor-badge badge-implantada"><i class="fas fa-check-circle"></i>Sugestão de melhoria será implantada</span>';
            } else if (analise.sugestao_sera_implantada === false) {
                badgeHtml = '<span class="analise-auditor-badge badge-nao-implantada"><i class="fas fa-times-circle"></i> Sugestão de melhoria não será implantada</span>';
            } else {
                // Só mostra "aguardando avaliação" se tiver sugestão
                badgeHtml = '<span class="analise-auditor-badge badge-pendente"><i class="fas fa-clock"></i> Sugestão de melhorias aguardando avaliação</span>';
            }
        }
        // Se não tiver sugestão ou for "INEXISTENTE", badgeHtml permanece vazio
        
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
                    <div class="analise-card-section"><h4><i class="fas fa-clipboard-list"></i> Ponto de Auditoria</h4><div class="analise-texto">${escapeHtml(analise.analise_critica) || '-'}</div></div>
                    <div class="analise-card-section"><h4><i class="fas fa-lightbulb"></i> Sugestão de Melhoria</h4><div class="analise-texto">${escapeHtml(analise.sugestao_melhoria) || '-'}</div></div>
                </div>
                
                <!-- ⭐ NOVO: Exibir evidências -->
                ${temEvidencia ? `
                <div class="analise-card-section" style="margin-top: 20px; border-left: 3px solid #0b5b99; background: #f0f7ff;">
                    <h4><i class="fas fa-paperclip"></i> Evidências da Análise</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px;">
                        ${analise.evidencias.map(ev => `
                            <div style="display: flex; align-items: center; gap: 8px; background: white; padding: 8px 12px; border-radius: 8px; border: 1px solid #e0e0e0;">
                                <i class="fas fa-file-pdf" style="color: #dc3545;"></i>
                                <span style="font-size: 13px;">${escapeHtml(ev.nome_arquivo)}</span>
                                <button class="btn-download-anexo" onclick="event.stopPropagation(); baixarEvidenciaAnaliseAuditor(${ev.id}, '${escapeHtml(ev.nome_arquivo)}')" style="padding: 4px 10px; font-size: 11px; background: #0b5b99; border-radius: 6px; border: none; color: white; cursor: pointer;">
                                    <i class="fas fa-download"></i>
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
                    <div class="analise-card-section"><h4><i class="fas fa-tasks"></i> Necessidade para Implantação</h4><div class="analise-texto">${escapeHtml(analise.necessidade_implantacao) || '-'}</div></div>
                    <div class="analise-card-section"><h4><i class="fas fa-chart-line"></i> Ganho Previsto</h4><div class="analise-texto">${escapeHtml(analise.ganho_previsto) || '-'}</div></div>
                </div>
                ${analise.observacoes ? `<div class="analise-card-section"><h4><i class="fas fa-comment"></i> Recomendações GRC</h4><div class="analise-texto">${escapeHtml(analise.observacoes)}</div></div>` : ''}
                
                <!-- ⭐ BOTÃO DE CONFIRMAÇÃO DE IMPLANTAÇÃO -->
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
                
                <!-- ⭐ BOTÃO DE PRAZO EXPIRADO -->
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
                
                <!-- ⭐ FOLLOW-UPS (APENAS SE IMPLANTADA) -->
                ${analise.plano_de_acao_implantado === true ? `
                <div class="analise-card-section" style="margin-top: 20px;">
                    <h4><i class="fas fa-search"></i> Follow-ups Agendados</h4>
                    <div class="followups-container">
                        ${renderizarListaFollowUps(analise.followUps)}
                    </div>
                </div>
                ` : ''}
                
                <div class="analise-card-section">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h4><i class="fas fa-history"></i> Histórico de Andamento</h4>
                        ${analise.sugestao_sera_implantada === true ? `<button class="btn-registrar-andamento" onclick="event.stopPropagation(); abrirModalHistoricoAndamento(${analise.id})"><i class="fas fa-plus"></i> Registrar</button>` : ''}
                    </div>
                    <div class="historico-container">${renderizarListaHistorico(analise.historico)}</div>
                </div>
            </div>
        </div>`;
    });
    container.innerHTML = html;
}

function renderizarListaHistorico(historico) {
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

function renderizarListaFollowUps(followUps) {
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

function toggleAnaliseAuditorCard(header) {
    const card = header.closest('.analise-auditor-card');
    card.classList.toggle('expanded');
    const icon = header.querySelector('.fa-chevron-down');
    icon.style.transform = card.classList.contains('expanded') ? 'rotate(180deg)' : 'rotate(0deg)';
}

function toggleAnaliseEtapaCard(header) {
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

function toggleAnaliseAuditadoCard(header) {
    const card = header.closest('.analise-auditado-card');
    card.classList.toggle('expanded');
    const icon = header.querySelector('.fa-chevron-down');
    icon.style.transform = card.classList.contains('expanded') ? 'rotate(180deg)' : 'rotate(0deg)';
}

async function baixarAnexo(analiseId) {
    window.open(`/api/analise-auditor/${analiseId}/anexo`, '_blank');
}

async function baixarAnexoAuditado(analiseId) {
    window.open(`/api/analise-auditado/${analiseId}/anexo`, '_blank');
}

// ============================================================
// FUNÇÃO PARA BAIXAR EVIDÊNCIA DO AUDITADO (CHECKLIST)
// ============================================================

async function baixarEvidenciaAuditadoChecklist(analiseId, nomeArquivo) {
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

// ============================================================
// FUNÇÃO PARA BAIXAR EVIDÊNCIA DA ANÁLISE DO AUDITOR
// ============================================================

async function baixarEvidenciaAnaliseAuditor(evidenciaId, nomeArquivo) {
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

// ============================================================
// HISTÓRICO DE ANDAMENTO E FOLLOW-UPS
// ============================================================

async function carregarHistoricoAndamento(analiseId) {
    try {
        const response = await fetchComAutenticacao(`/api/analise-historico/${analiseId}`);
        const data = await response.json();
        return data.success ? data.historico : [];
    } catch (error) {
        console.error('Erro ao carregar histórico:', error);
        return [];
    }
}

async function carregarFollowUps(analiseId) {
    try {
        const response = await fetchComAutenticacao(`/api/analise-follow-ups/${analiseId}`);
        const data = await response.json();
        return data.success ? data.follow_ups : [];
    } catch (error) {
        console.error('Erro ao carregar follow-ups:', error);
        return [];
    }
}

function abrirModalHistoricoAndamento(analiseId) {
    document.getElementById('historico-analise-id').value = analiseId;
    document.getElementById('historico-status').value = 'Em andamento';
    document.getElementById('historico-comentario').value = '';
    document.getElementById('modal-historico-andamento').style.display = 'flex';
}

function fecharModalHistorico() {
    document.getElementById('modal-historico-andamento').style.display = 'none';
}

async function salvarHistoricoAndamento() {
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
        const response = await fetchComAutenticacao('/api/analise-historico/salvar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ analise_id: analiseId, status: status, comentario: comentario })
        });
        const data = await response.json();
        if (data.success) {
            mostrarToast('✅ Andamento registrado com sucesso!', 'success');
            fecharModalHistorico();
            await carregarAnalisesAuditor();
            await carregarAnalisesAuditado();
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

function abrirModalFollowUp(followUpId, etapa) {
    document.getElementById('followup-id').value = followUpId;
    document.getElementById('modal-followup-titulo').innerHTML = `<i class="fas fa-search"></i> Registrar ${etapa}`;
    document.getElementById('followup-status').value = 'Aderente';
    document.getElementById('followup-comentario').value = '';
    document.getElementById('modal-follow-up').style.display = 'flex';
}

function fecharModalFollowUp() {
    document.getElementById('modal-follow-up').style.display = 'none';
}

async function salvarFollowUp() {
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
        const response = await fetchComAutenticacao(`/api/analise-follow-up/${followUpId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: status, comentario: comentario })
        });
        const data = await response.json();
        if (data.success) {
            mostrarToast('✅ Follow-up registrado com sucesso!', 'success');
            fecharModalFollowUp();
            await carregarAnalisesAuditor();
            await carregarAnalisesAuditado();
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
// CONFIRMAR IMPLANTAÇÃO
// ============================================================

function abrirModalConfirmarImplantacao(analiseId) {
    document.getElementById('confirmar-analise-id').value = analiseId;
    document.getElementById('confirmar-analise-id').setAttribute('data-tipo', 'auditor');
    document.getElementById('confirmar-status').value = 'true';
    document.getElementById('confirmar-data').value = new Date().toISOString().split('T')[0];
    document.getElementById('confirmar-comentario').value = '';
    document.getElementById('modal-confirmar-implantacao').style.display = 'flex';
}

function abrirModalConfirmarImplantacaoAuditado(analiseId) {
    document.getElementById('confirmar-analise-id').value = analiseId;
    document.getElementById('confirmar-analise-id').setAttribute('data-tipo', 'auditado');
    document.getElementById('confirmar-status').value = 'true';
    document.getElementById('confirmar-data').value = new Date().toISOString().split('T')[0];
    document.getElementById('confirmar-comentario').value = '';
    document.getElementById('modal-confirmar-implantacao').style.display = 'flex';
}

function fecharModalConfirmarImplantacao() {
    document.getElementById('modal-confirmar-implantacao').style.display = 'none';
}

async function confirmarImplantacao() {
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

async function criarFollowUpsAutomaticos(analiseId, dataImplantacaoEfetiva) {
    console.log('📅 Criando follow-ups para análise:', analiseId);
    if (!analiseId || !dataImplantacaoEfetiva) return;
    
    try {
        const checkResponse = await fetchComAutenticacao(`/api/analise-follow-ups/${analiseId}`);
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
        const response = await fetchComAutenticacao('/api/analise-follow-ups/criar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ analise_id: analiseId, follow_ups: followUps })
        });
        const data = await response.json();
        if (data.success) console.log('✅ Follow-ups criados com sucesso');
    } catch (error) { console.error('❌ Erro ao criar follow-ups:', error); }
}

// ============================================================
// CARREGAR ANÁLISES DO AUDITOR
// ============================================================

async function carregarAnalisesAuditor() {
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
            }
            
            analisesAuditorList = data.analises;
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

async function salvarAnaliseAuditor() {
    if (!processoIdAtual) {
        mostrarToast('❌ Selecione um processo primeiro', 'warning');
        return;
    }
    
    const analiseId = document.getElementById('analise-auditor-id').value;
    const radioSelecionado = document.querySelector('#modal-analise-auditor input[name="sugestao-status-radio"]:checked');
    
    // ⭐ LOG PARA DEBUG
    console.log('📻 Radio selecionado:', radioSelecionado);
    console.log('📻 Radio value:', radioSelecionado?.value);
    
    let seraImplantada = null;
    if (radioSelecionado) {
        if (radioSelecionado.value === 'true') seraImplantada = true;
        else if (radioSelecionado.value === 'false') seraImplantada = false;
        else seraImplantada = null;
    } else {
        mostrarToast('⚠️ Selecione uma opção em "Status da sugestão de melhoria"', 'warning');
        const statusGroup = document.querySelector('#modal-analise-auditor .status-radio-group');
        if (statusGroup) {
            statusGroup.style.border = '2px solid #dc3545';
            statusGroup.style.borderRadius = '8px';
            statusGroup.style.padding = '10px';
            setTimeout(() => {
                statusGroup.style.border = '';
                statusGroup.style.padding = '';
            }, 3000);
        }
        return;
    }
    
    const analiseCritica = document.getElementById('analise-auditor-texto').value;
    if (!analiseCritica.trim()) {
        mostrarToast('⚠️ O Ponto de Auditoria é obrigatório', 'warning');
        return;
    }
    
    // ⭐⭐⭐ CORREÇÃO: USAR JSON EM VEZ DE FormData ⭐⭐⭐
    const payload = {
        processo_id: parseInt(processoIdAtual),
        analise_critica: analiseCritica,
        sugestao_melhoria: document.getElementById('analise-auditor-sugestao').value || '',
        necessidade_implantacao: document.getElementById('analise-auditor-necessidade').value || '',
        ganho_previsto: document.getElementById('analise-auditor-ganho').value || '',
        observacoes: document.getElementById('analise-auditor-observacoes').value || '',
        sugestao_sera_implantada: seraImplantada
    };
    
    // ⭐ REMOVER CAMPOS ANTIGOS que não existem mais na tabela
    // NÃO enviar: plano_acao, responsavel_implantacao, data_inicio_implantacao, data_conclusao_prevista
    
    // ⭐ Processar evidência (arquivo)
    // Se tiver arquivo de evidência, processar separadamente
    let evidenciaBase64 = null;
    let evidenciaNome = null;
    
    if (arquivoSelecionadoAuditor) {
        try {
            const base64 = await converterParaBase64(arquivoSelecionadoAuditor);
            evidenciaBase64 = base64;
            evidenciaNome = arquivoSelecionadoAuditor.name;
            payload.evidencia_base64 = evidenciaBase64;
            payload.evidencia_nome = evidenciaNome;
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
    
    console.log('📦 Payload final:', payload);
    
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
            arquivoSelecionadoAuditor = null;
            anexoExistenteNomeAuditor = null;
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

function setupSemSugestaoCheckbox() {
    const checkbox = document.getElementById('sem_sugestao_melhoria');
    const textarea = document.getElementById('analise-auditado-sugestao');
    
    if (!checkbox || !textarea) return;
    
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
    });
    
    // Se o usuário digitar algo no textarea, desmarcar o checkbox
    textarea.addEventListener('input', function() {
        if (this.value.trim() !== '' && this.value.trim().toUpperCase() !== 'INEXISTENTE') {
            checkbox.checked = false;
        }
    });
}

// ============================================================
// CONTROLE DO CHECKBOX "SEM SUGESTÃO DE MELHORIA" - AUDITOR
// ============================================================

function setupSemSugestaoCheckboxAuditor() {
    const checkbox = document.getElementById('sem_sugestao_melhoria_auditor');
    const textarea = document.getElementById('analise-auditor-sugestao');
    
    if (!checkbox || !textarea) return;
    
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
    });
    
    // Se o usuário digitar algo no textarea, desmarcar o checkbox
    textarea.addEventListener('input', function() {
        if (this.value.trim() !== '' && this.value.trim().toUpperCase() !== 'INEXISTENTE') {
            checkbox.checked = false;
        }
    });
}

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
            processoIdAtual = selectProcesso.value;
            auditoriaIdAtual = selectAuditoria.value;
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

