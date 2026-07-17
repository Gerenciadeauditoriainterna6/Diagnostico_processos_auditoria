document.addEventListener('DOMContentLoaded', function() {
    // ====== ELEMENTOS DO DOM ======
    const filtroAno = document.getElementById('filtro_ano');
    const btnCarregar = document.getElementById('btn-carregar');
    const btnLimpar = document.getElementById('btn-limpar');
    const conteudoPrincipal = document.getElementById('conteudo-principal');
    const btnDownloadPdf = document.getElementById('btn-download-pdf');
    const pdfNaoEncontrado = document.getElementById('pdf-nao-encontrado');
    const fundamentosContainer = document.getElementById('fundamentos-container');
    const contadorAuditorias = document.getElementById('contador-auditorias');

    // ====== VARIÁVEIS GLOBAIS ======
    let anoSelecionado = null;
    let dadosAuditorias = []; // ⭐ NOVO: armazena os dados das auditorias para edição

    // ====== FUNÇÕES AUXILIARES ======
    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function mostrarToast(mensagem, tipo = 'info') {
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 999999;
            `;
            document.body.appendChild(toastContainer);
        }
        
        const cores = {
            success: { bg: '#d4edda', border: '#28a745', text: '#155724', icon: '✅' },
            error: { bg: '#f8d7da', border: '#dc3545', text: '#721c24', icon: '❌' },
            warning: { bg: '#fff3cd', border: '#ffc107', text: '#856404', icon: '⚠️' },
            info: { bg: '#d1ecf1', border: '#17a2b8', text: '#0c5460', icon: 'ℹ️' }
        };
        
        const cor = cores[tipo] || cores.info;
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            background: ${cor.bg};
            border-left: 4px solid ${cor.border};
            color: ${cor.text};
            padding: 12px 16px;
            margin-bottom: 10px;
            border-radius: 8px;
            font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            animation: slideIn 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        `;
        toast.innerHTML = `
            <span style="font-size: 18px;">${cor.icon}</span>
            <span>${mensagem}</span>
            <span style="margin-left: auto; cursor: pointer; opacity: 0.7;" onclick="this.parentElement.remove()">✕</span>
        `;
        
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            if (toast && toast.parentElement) {
                toast.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => toast.remove(), 300);
            }
        }, 4000);
    }

    // ====== VERIFICAR EXISTÊNCIA DO PDF ======
    async function verificarPdf(ano) {
        try {
            // Buscar o PDF do plano anual pelo ano
            const response = await fetch(`/api/plano-anual-pdf?ano=${ano}&tipo=plano`);
            console.log('Status da resposta:', response.status);
            
            // Atualizar textos com o ano
            document.getElementById('ano-selecionado').textContent = ano;
            document.getElementById('ano-pdf-nao-encontrado').textContent = ano;
            document.getElementById('ano-fundamentos').textContent = ano;
            
            if (response.ok) {
                console.log('✅ PDF encontrado - mostrando botão');
                btnDownloadPdf.style.display = 'inline-flex';
                pdfNaoEncontrado.style.display = 'none';
                return true;
            } else {
                const errorData = await response.json();
                console.log('❌ PDF NÃO encontrado');
                btnDownloadPdf.style.display = 'none';
                pdfNaoEncontrado.style.display = 'block';
                pdfNaoEncontrado.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${errorData.error || 'Arquivo PDF não encontrado para o ano ' + ano}`;
                return false;
            }
        } catch (error) {
            console.error('Erro ao verificar PDF:', error);
            btnDownloadPdf.style.display = 'none';
            pdfNaoEncontrado.style.display = 'block';
            pdfNaoEncontrado.innerHTML = `<i class="fas fa-exclamation-triangle"></i> Erro ao verificar arquivo PDF.`;
            return false;
        }
    }

    // ====== DOWNLOAD DO PDF ======
    function baixarPdf() {
        if (anoSelecionado) {
            window.open(`/api/plano-anual-pdf?ano=${anoSelecionado}&tipo=plano`, '_blank');
        }
    }

    // ====== CARREGAR FUNDAMENTOS POR ANO (COM EDIÇÃO) ======
    async function carregarFundamentosPorAno(ano) {
        fundamentosContainer.innerHTML = `
            <div class="empty-message">
                <i class="fas fa-spinner fa-spin"></i> Carregando fundamentos...
            </div>
        `;

        try {
            const response = await fetch(`/api/fundamentos-por-ano?ano=${ano}`);
            const data = await response.json();

            console.log('📦 Dados recebidos:', data);

            if (!data.success) {
                fundamentosContainer.innerHTML = `
                    <div class="empty-message">
                        <i class="fas fa-exclamation-triangle"></i> Erro ao carregar fundamentos: ${data.error || 'Erro desconhecido'}
                    </div>
                `;
                return;
            }

            // ⭐ Salvar dados globais para edição
            dadosAuditorias = data.auditorias || [];
            renderizarFundamentos(dadosAuditorias);

        } catch (error) {
            console.error('Erro ao carregar fundamentos:', error);
            fundamentosContainer.innerHTML = `
                <div class="empty-message">
                    <i class="fas fa-exclamation-triangle"></i> Erro ao carregar fundamentos: ${error.message}
                </div>
            `;
        }
    }

    // ====== RENDERIZAR FUNDAMENTOS COM EDIÇÃO ======
    function renderizarFundamentos(auditorias) {
        if (!fundamentosContainer) return;
        
        contadorAuditorias.textContent = auditorias.length;

        if (auditorias.length === 0) {
            fundamentosContainer.innerHTML = `
                <div class="empty-message">
                    <i class="fas fa-info-circle"></i> Nenhuma auditoria planejada encontrada para este ano.
                </div>
            `;
            return;
        }

        // Filtrar apenas auditorias que têm fundamentos OU permitir adicionar
        const auditoriasComFundamentos = auditorias.filter(aud => 
            aud.fundamentos && 
            Array.isArray(aud.fundamentos) && 
            aud.fundamentos.length > 0
        );

        // Se não tem nenhuma com fundamentos, mostrar todas com opção de adicionar
        const auditoriasParaMostrar = auditoriasComFundamentos.length > 0 ? auditoriasComFundamentos : auditorias;

        fundamentosContainer.innerHTML = auditoriasParaMostrar.map((aud, audIdx) => `
            <div class="auditoria-fundamento-card" data-auditoria-id="${aud.id}" data-auditoria-idx="${audIdx}">
                <div class="auditoria-header">
                    <div>
                        <h4>
                            <i class="fas fa-clipboard-list"></i> 
                            ${escapeHtml(aud.codigo_auditoria || 'Sem código')}
                            <span style="font-weight: normal; font-size: 14px; color: #666; margin-left: 8px;">
                                ${escapeHtml(aud.titulo || 'Sem título')}
                            </span>
                        </h4>
                        <div style="font-size: 12px; color: #999; margin-top: 4px;">
                            ${aud.area_nome || 'Sem área'} • ${aud.ano}/${aud.trimestre}º trimestre
                        </div>
                    </div>
                    <div>
                        <button class="btn-adicionar-risco" data-auditoria-id="${aud.id}" data-auditoria-idx="${audIdx}" title="Adicionar risco a esta auditoria">
                            <i class="fas fa-plus-circle"></i> Adicionar Risco
                        </button>
                    </div>
                </div>
                
                <div class="riscos-container" data-auditoria-idx="${audIdx}">
                    ${(aud.fundamentos && aud.fundamentos.length > 0) ? aud.fundamentos.map((fundamento, fIdx) => `
                        <div class="risco-item" data-fundamento-idx="${fIdx}">
                            <div class="risco-header-edit">
                                <div class="risco-titulo" style="flex: 1; margin: 0;">
                                    <i class="fas fa-exclamation-triangle"></i> 
                                    <input type="text" class="risco-titulo-input" value="${escapeHtml(fundamento.titulo || 'Risco não definido')}" 
                                        placeholder="Descreva o risco..." data-auditoria-idx="${audIdx}" data-fundamento-idx="${fIdx}">
                                </div>
                                <div class="risco-acoes">
                                    <button class="btn-remover-risco" data-auditoria-idx="${audIdx}" data-fundamento-idx="${fIdx}" title="Remover risco">
                                        <i class="fas fa-trash-alt"></i>
                                    </button>
                                </div>
                            </div>
                            
                            <div class="pontos-container">
                                <label class="pontos-label"><i class="fas fa-list"></i> Pontos:</label>
                                <div class="pontos-lista-edit" data-auditoria-idx="${audIdx}" data-fundamento-idx="${fIdx}">
                                    ${(fundamento.pontos || []).filter(p => p && p.trim() !== '').map((ponto, pIdx) => `
                                        <div class="ponto-item-edit">
                                            <span class="ponto-numero">${pIdx + 1}.</span>
                                            <input type="text" class="ponto-input" value="${escapeHtml(ponto)}" 
                                                placeholder="Descreva o ponto..." 
                                                data-auditoria-idx="${audIdx}" data-fundamento-idx="${fIdx}" data-ponto-idx="${pIdx}">
                                            <button class="btn-remover-ponto" data-auditoria-idx="${audIdx}" data-fundamento-idx="${fIdx}" data-ponto-idx="${pIdx}" title="Remover ponto">
                                                <i class="fas fa-times"></i>
                                            </button>
                                        </div>
                                    `).join('')}
                                </div>
                                <button class="btn-adicionar-ponto" data-auditoria-idx="${audIdx}" data-fundamento-idx="${fIdx}">
                                    <i class="fas fa-plus"></i> Adicionar ponto
                                </button>
                            </div>
                        </div>
                    `).join('') : `
                        <div class="empty-riscos">
                            <i class="fas fa-info-circle"></i> Nenhum risco cadastrado para esta auditoria.
                            <button class="btn-adicionar-risco-inline" data-auditoria-id="${aud.id}" data-auditoria-idx="${audIdx}" style="margin-left: 10px;">
                                <i class="fas fa-plus-circle"></i> Adicionar primeiro risco
                            </button>
                        </div>
                    `}
                </div>
                
                <div class="salvar-auditoria-actions">
                    <button class="btn-salvar-auditoria" data-auditoria-id="${aud.id}" data-auditoria-idx="${audIdx}">
                        <i class="fas fa-save"></i> Salvar Fundamentos desta Auditoria
                    </button>
                </div>
            </div>
        `).join('');
        
        // Adicionar eventos de edição
        adicionarEventosEdicao();
    }

    // ====== ADICIONAR EVENTOS DE EDIÇÃO ======
    function adicionarEventosEdicao() {
        // Adicionar Risco
        document.querySelectorAll('.btn-adicionar-risco, .btn-adicionar-risco-inline').forEach(btn => {
            btn.removeEventListener('click', handleAdicionarRisco);
            btn.addEventListener('click', handleAdicionarRisco);
        });
        
        // Remover Risco
        document.querySelectorAll('.btn-remover-risco').forEach(btn => {
            btn.removeEventListener('click', handleRemoverRisco);
            btn.addEventListener('click', handleRemoverRisco);
        });
        
        // Adicionar Ponto
        document.querySelectorAll('.btn-adicionar-ponto').forEach(btn => {
            btn.removeEventListener('click', handleAdicionarPonto);
            btn.addEventListener('click', handleAdicionarPonto);
        });
        
        // Remover Ponto
        document.querySelectorAll('.btn-remover-ponto').forEach(btn => {
            btn.removeEventListener('click', handleRemoverPonto);
            btn.addEventListener('click', handleRemoverPonto);
        });
        
        // Salvar Auditoria
        document.querySelectorAll('.btn-salvar-auditoria').forEach(btn => {
            btn.removeEventListener('click', handleSalvarAuditoria);
            btn.addEventListener('click', handleSalvarAuditoria);
        });
    }

    // ====== HANDLERS DE EDIÇÃO ======
    function handleAdicionarRisco(e) {
        const btn = e.target.closest('.btn-adicionar-risco, .btn-adicionar-risco-inline');
        const auditoriaIdx = parseInt(btn.getAttribute('data-auditoria-idx'));
        const auditoria = dadosAuditorias[auditoriaIdx];
        
        if (!auditoria) return;
        
        if (!auditoria.fundamentos) {
            auditoria.fundamentos = [];
        }
        
        auditoria.fundamentos.push({
            titulo: '',
            pontos: ['']
        });
        
        renderizarFundamentos(dadosAuditorias);
    }

    function handleRemoverRisco(e) {
        const btn = e.target.closest('.btn-remover-risco');
        const auditoriaIdx = parseInt(btn.getAttribute('data-auditoria-idx'));
        const fundamentoIdx = parseInt(btn.getAttribute('data-fundamento-idx'));
        const auditoria = dadosAuditorias[auditoriaIdx];
        
        if (!auditoria || !auditoria.fundamentos) return;
        
        auditoria.fundamentos.splice(fundamentoIdx, 1);
        renderizarFundamentos(dadosAuditorias);
    }

    function handleAdicionarPonto(e) {
        const btn = e.target.closest('.btn-adicionar-ponto');
        const auditoriaIdx = parseInt(btn.getAttribute('data-auditoria-idx'));
        const fundamentoIdx = parseInt(btn.getAttribute('data-fundamento-idx'));
        const auditoria = dadosAuditorias[auditoriaIdx];
        
        if (!auditoria || !auditoria.fundamentos || !auditoria.fundamentos[fundamentoIdx]) return;
        
        auditoria.fundamentos[fundamentoIdx].pontos.push('');
        renderizarFundamentos(dadosAuditorias);
    }

    function handleRemoverPonto(e) {
        const btn = e.target.closest('.btn-remover-ponto');
        const auditoriaIdx = parseInt(btn.getAttribute('data-auditoria-idx'));
        const fundamentoIdx = parseInt(btn.getAttribute('data-fundamento-idx'));
        const pontoIdx = parseInt(btn.getAttribute('data-ponto-idx'));
        const auditoria = dadosAuditorias[auditoriaIdx];
        
        if (!auditoria || !auditoria.fundamentos || !auditoria.fundamentos[fundamentoIdx]) return;
        
        auditoria.fundamentos[fundamentoIdx].pontos.splice(pontoIdx, 1);
        renderizarFundamentos(dadosAuditorias);
    }

    async function handleSalvarAuditoria(e) {
        const btn = e.target.closest('.btn-salvar-auditoria');
        const auditoriaId = parseInt(btn.getAttribute('data-auditoria-id'));
        const auditoriaIdx = parseInt(btn.getAttribute('data-auditoria-idx'));
        const auditoria = dadosAuditorias[auditoriaIdx];
        
        if (!auditoria) return;
        
        // Coletar dados dos inputs
        const card = btn.closest('.auditoria-fundamento-card');
        const riscosInputs = card.querySelectorAll('.risco-titulo-input');
        const pontosInputs = card.querySelectorAll('.ponto-input');
        
        // Atualizar dados da auditoria com os valores dos inputs
        riscosInputs.forEach(input => {
            const fIdx = parseInt(input.getAttribute('data-fundamento-idx'));
            if (auditoria.fundamentos && auditoria.fundamentos[fIdx]) {
                auditoria.fundamentos[fIdx].titulo = input.value;
            }
        });
        
        pontosInputs.forEach(input => {
            const fIdx = parseInt(input.getAttribute('data-fundamento-idx'));
            const pIdx = parseInt(input.getAttribute('data-ponto-idx'));
            if (auditoria.fundamentos && auditoria.fundamentos[fIdx] && auditoria.fundamentos[fIdx].pontos[pIdx] !== undefined) {
                auditoria.fundamentos[fIdx].pontos[pIdx] = input.value;
            }
        });
        
        // Filtrar fundamentos vazios
        const fundamentosFiltrados = (auditoria.fundamentos || []).filter(f => {
            if (!f.titulo || f.titulo.trim() === '') return false;
            const pontosValidos = (f.pontos || []).filter(p => p && p.trim() !== '');
            return pontosValidos.length > 0;
        });
        
        // Salvar
        try {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
            
            const response = await fetch(`/api/auditoria/${auditoriaId}/fundamentos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fundamentos: fundamentosFiltrados })
            });
            
            const result = await response.json();
            
            if (result.success) {
                mostrarToast('✅ Fundamentos salvos com sucesso!', 'success');
                // Atualizar dados locais
                auditoria.fundamentos = fundamentosFiltrados;
            } else {
                mostrarToast('❌ Erro ao salvar: ' + (result.error || 'Tente novamente'), 'error');
            }
        } catch (error) {
            console.error('Erro ao salvar:', error);
            mostrarToast('❌ Erro de conexão', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-save"></i> Salvar Fundamentos desta Auditoria';
        }
    }

    // ====== CARREGAR DADOS COMPLETOS ======
    async function carregarDados(ano) {
        if (!ano) {
            mostrarToast('⚠️ Selecione um ano primeiro', 'warning');
            return;
        }

        anoSelecionado = ano;
        conteudoPrincipal.style.display = 'block';

        // Atualizar títulos com o ano
        document.getElementById('ano-selecionado').textContent = ano;
        document.getElementById('ano-pdf-nao-encontrado').textContent = ano;
        document.getElementById('ano-fundamentos').textContent = ano;

        // Carregar PDF
        await verificarPdf(ano);

        // Carregar fundamentos
        await carregarFundamentosPorAno(ano);
    }

    // ====== LIMPAR DADOS ======
    function limparDados() {
        anoSelecionado = null;
        conteudoPrincipal.style.display = 'none';
        filtroAno.value = '';
        btnDownloadPdf.style.display = 'none';
        pdfNaoEncontrado.style.display = 'none';
        fundamentosContainer.innerHTML = `
            <div class="empty-message">
                <i class="fas fa-info-circle"></i> Selecione um ano para visualizar os fundamentos.
            </div>
        `;
        contadorAuditorias.textContent = '0';
    }

    // ====== EVENTOS ======
    if (btnCarregar) {
        btnCarregar.addEventListener('click', () => {
            const ano = filtroAno.value;
            if (ano) {
                carregarDados(ano);
            } else {
                mostrarToast('⚠️ Selecione um ano primeiro', 'warning');
            }
        });
    }

    if (btnLimpar) {
        btnLimpar.addEventListener('click', limparDados);
    }

    if (btnDownloadPdf) {
        btnDownloadPdf.addEventListener('click', baixarPdf);
    }

    // ====== INICIALIZAÇÃO ======
    console.log('🚀 Página de Plano Anual carregada');

    // Adicionar CSS de animação se não existir
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
})

