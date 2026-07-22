// static/js/auditorias_emergenciais.js

document.addEventListener('DOMContentLoaded', function() {

    console.log('👤 Usuário:', USUARIO_NOME);
    console.log('🔑 Perfil:', USUARIO_PERFIL);
    console.log('👑 É admin?', IS_ADMIN);

    // ====== ELEMENTOS DO DOM ======
    const filtroAreaSelect = document.getElementById('filtro_area_select');
    const btnFiltrar = document.getElementById('btn-filtrar');
    const btnLimparFiltros = document.getElementById('btn-limpar-filtros');
    const tabelaBody = document.querySelector('#tabela-emergenciais tbody');
    const contadorEmergenciais = document.getElementById('contador-emergenciais');

    // ====== ELEMENTOS DO MODAL ======
    const modalDetalhes = document.getElementById('modal-detalhes');
    const fundamentosContainerModal = document.getElementById('fundamentos-container-modal');
    const btnAdicionarFundamentoModal = document.getElementById('btn-adicionar-fundamento-modal');
    const btnSalvarFundamentosModal = document.getElementById('btn-salvar-fundamentos-modal');
    const btnDownloadPdf = document.getElementById('btn-download-pdf');
    const pdfNaoEncontrado = document.getElementById('pdf-nao-encontrado');
    const contadorRiscosModal = document.getElementById('contador-riscos-modal');

    // ====== VARIÁVEIS GLOBAIS ======
    let auditoriaAtualId = null;
    let auditoriaAtualCodigo = null;
    let fundamentosLista = [];
    let usuarioAutorizado = false;

    // ====== FUNÇÃO PARA FORMATAR DATA ======
    function formatarData(dataISO) {
        if (!dataISO || dataISO === '-') return '-';
        try {
            if (dataISO.includes('/')) return dataISO;
            
            const data = new Date(dataISO);
            if (isNaN(data.getTime())) {
                return dataISO;
            }
            
            const dia = String(data.getDate()).padStart(2, '0');
            const mes = String(data.getMonth() + 1).padStart(2, '0');
            const ano = data.getFullYear();
            return `${dia}/${mes}/${ano}`;
        } catch (error) {
            console.error('Erro ao formatar data:', error);
            return dataISO;
        }
    }

    // ====== ESCAPE HTML ======
    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // ====== TOAST ======
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

    // ====== VERIFICAR PERMISSÃO EM MASSA ======
    async function carregarEmergenciais(areaId = null) {
        tabelaBody.innerHTML = '<tr><td colspan="8" class="loading-message"><i class="fas fa-spinner fa-spin"></i> Carregando...</td>';

        try {
            let url = '/api/auditorias-emergenciais';
            if (areaId) {
                url += `?area_id=${areaId}`;
            }

            const response = await fetchComAutenticacao(url);
            const data = await response.json();

            if (!data.success) {
                tabelaBody.innerHTML = `<tr><td colspan="8" class="loading-message">Erro: ${data.error || 'Erro ao carregar'}</td>`;
                return;
            }

            const auditorias = data.auditorias || [];

            contadorEmergenciais.textContent = auditorias.length;

            if (auditorias.length === 0) {
                tabelaBody.innerHTML = '<tr><td colspan="8" class="loading-message">Nenhuma auditoria emergencial encontrada</td>';
                return;
            }

            const auditoriasComPermissao = await Promise.all(auditorias.map(async (aud) => {
                if (IS_ADMIN) {
                    return { ...aud, temPermissao: true };
                }
                
                try {
                    const resp = await fetchComAutenticacao(`/api/auditoria/${aud.id}/responsavel`);
                    const dataResp = await resp.json();
                    return { ...aud, temPermissao: dataResp.autorizado || false };
                } catch (error) {
                    console.error(`Erro ao verificar permissão para auditoria ${aud.id}:`, error);
                    return { ...aud, temPermissao: false };
                }
            }));

            renderizarTabela(auditoriasComPermissao);

        } catch (error) {
            console.error('Erro ao carregar auditorias emergenciais:', error);
            tabelaBody.innerHTML = `<tr><td colspan="8" class="loading-message">Erro ao carregar: ${error.message}</td>`;
        }
    }

    // ====== RENDERIZAR TABELA ======
    function renderizarTabela(auditorias) {
        tabelaBody.innerHTML = auditorias.map(aud => {
            let statusClass = '';
            const status = aud.status || '';

            if (status === 'Planejamento') statusClass = 'status-planejamento';
            else if (status === 'Em Execução') statusClass = 'status-execucao';
            else if (status === 'Eficácia Validada') statusClass = 'status-eficacia';
            else if (status === 'Follow-up') statusClass = 'status-followup';
            else if (status === 'Concluída') statusClass = 'status-concluida';
            else if (status === 'Em Atraso') statusClass = 'status-atraso';
            else if (status === 'Inconclusiva') statusClass = 'status-inconclusiva';
            else if (status === 'Cancelada') statusClass = 'status-cancelada';
            else statusClass = 'status-planejamento';

            const tituloTruncado = aud.titulo && aud.titulo.length > 40 
                ? aud.titulo.substring(0, 40) + '...' 
                : (aud.titulo || '-');

            const botaoVisualizar = aud.temPermissao ? `
                <button class="btn-visualizar-icon" onclick="abrirModalDetalhes(${aud.id}, '${aud.codigo_auditoria}', '${escapeHtml(aud.titulo || '')}')" title="Visualizar detalhes">
                    <i class="fas fa-ellipsis"></i>
                </button>
            ` : `
                <span title="Sem permissão para visualizar" style="color: #999; font-size: 14px;">
                    <i class="fas fa-lock"></i>
                </span>
            `;

            return `
                <tr>
                    <td><strong>${aud.codigo_auditoria || '-'}</strong></td>
                    <td title="${aud.titulo || ''}">${tituloTruncado}</td>
                    <td>${aud.area_nome || '-'}</td>
                    <td>${aud.ano}/${aud.trimestre}º</td>
                    <td>${formatarData(aud.data_inicio)}<br/><small>a</small><br/>${formatarData(aud.data_fim)}</td>
                    <td><span class="status-badge ${statusClass}">${status || '-'}</span></td>
                    <td>${aud.unidade || '-'}</td>
                    <td>
                        <div class="btn-group">
                            ${botaoVisualizar}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // ====== VERIFICAR SE USUÁRIO É RESPONSÁVEL ======
    async function verificarResponsavel(auditoriaId) {
        try {
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
            const data = await response.json();
            return data.autorizado || false;
        } catch (error) {
            console.error('Erro ao verificar responsável:', error);
            return false;
        }
    }

    // ====== ABRIR MODAL DETALHES ======
    window.abrirModalDetalhes = async function(id, codigo, titulo) {
        console.log('👁️ Abrindo modal - ID:', id, 'Código:', codigo);
        
        auditoriaAtualId = id;
        auditoriaAtualCodigo = codigo;
        
        document.getElementById('modal-codigo').textContent = codigo;
        document.getElementById('modal-titulo').textContent = titulo;
        
        btnDownloadPdf.style.display = 'none';
        pdfNaoEncontrado.style.display = 'none';
        
        modalDetalhes.style.display = 'flex';
        
        await verificarPermissaoAuditoria(id);
        
        if (usuarioAutorizado) {
            await verificarPdf(codigo);
            await carregarFundamentos(id);
            await carregarEvidencias(id);
        } else {
            fundamentosContainerModal.innerHTML = `
                <div class="empty-message" style="border-left: 4px solid #dc3545;">
                    <i class="fas fa-lock" style="color: #dc3545;"></i>
                    <strong>Acesso negado!</strong><br>
                    Você não tem permissão para visualizar os detalhes desta auditoria.
                    Apenas o gestor responsável e administradores têm acesso.
                </div>
            `;
            btnDownloadPdf.style.display = 'none';
            pdfNaoEncontrado.style.display = 'none';
            
            const evidenciasContainer = document.getElementById('evidencias-container');
            if (evidenciasContainer) {
                evidenciasContainer.innerHTML = `
                    <div class="empty-message" style="border-left: 4px solid #dc3545;">
                        <i class="fas fa-lock" style="color: #dc3545;"></i>
                        <strong>Acesso negado!</strong><br>
                        Você não tem permissão para visualizar as evidências desta auditoria.
                    </div>
                `;
            }
        }
    }

    // ====== FECHAR MODAL DETALHES ======
    window.fecharModalDetalhes = function () {
        modalDetalhes.style.display = 'none';
        auditoriaAtualId = null;
        auditoriaAtualCodigo = null;
        fundamentosLista = [];
    }

    // ====== APLICAR PERMISSÕES NO MODAL ======
    function aplicarPermissoesModal() {
        const btnAdicionarRisco = document.querySelectorAll('.btn-adicionar-risco, .btn-adicionar-risco-inline');
        const btnRemoverRisco = document.querySelectorAll('.btn-remover-risco');
        const btnAdicionarPonto = document.querySelectorAll('.btn-adicionar-ponto');
        const btnRemoverPonto = document.querySelectorAll('.btn-remover-ponto');
        const btnSalvar = document.querySelectorAll('.btn-salvar-auditoria');
        const inputs = document.querySelectorAll('.risco-titulo-input, .ponto-input');
        
        if (!usuarioAutorizado) {
            btnAdicionarRisco.forEach(btn => btn.style.display = 'none');
            btnRemoverRisco.forEach(btn => btn.style.display = 'none');
            btnAdicionarPonto.forEach(btn => btn.style.display = 'none');
            btnRemoverPonto.forEach(btn => btn.style.display = 'none');
            btnSalvar.forEach(btn => btn.style.display = 'none');
            inputs.forEach(input => {
                input.disabled = true;
                input.style.backgroundColor = '#f8f9fa';
                input.style.cursor = 'not-allowed';
            });
            
            const sectionHeader = document.querySelector('.fundamentos-section .section-header');
            if (sectionHeader && !document.querySelector('.readonly-indicator')) {
                const indicator = document.createElement('span');
                indicator.className = 'readonly-indicator';
                indicator.innerHTML = '<i class="fas fa-eye"></i> Modo somente leitura';
                indicator.style.cssText = `
                    display: inline-block;
                    background: #e9ecef;
                    color: #666;
                    padding: 4px 12px;
                    border-radius: 20px;
                    font-size: 11px;
                    margin-left: 15px;
                `;
                sectionHeader.appendChild(indicator);
            }
        } else {
            btnAdicionarRisco.forEach(btn => btn.style.display = '');
            btnRemoverRisco.forEach(btn => btn.style.display = '');
            btnAdicionarPonto.forEach(btn => btn.style.display = '');
            btnRemoverPonto.forEach(btn => btn.style.display = '');
            btnSalvar.forEach(btn => btn.style.display = '');
            inputs.forEach(input => {
                input.disabled = false;
                input.style.backgroundColor = 'white';
                input.style.cursor = 'text';
            });
            
            const indicator = document.querySelector('.readonly-indicator');
            if (indicator) indicator.remove();
        }
    }

    // ====== VERIFICAR PERMISSÃO ======
    async function verificarPermissaoAuditoria(auditoriaId) {
        try {
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
            const data = await response.json();
            
            console.log('🔍 Verificação de permissão:', data);
            
            if (IS_ADMIN) {
                usuarioAutorizado = true;
                console.log('✅ Administrador - acesso total');
            } else if (data.autorizado) {
                usuarioAutorizado = true;
                console.log('✅ Usuário é responsável - acesso total');
            } else {
                usuarioAutorizado = false;
                console.log('❌ Usuário NÃO autorizado');
            }
            
            aplicarPermissoesModal();
            return usuarioAutorizado;
            
        } catch (error) {
            console.error('Erro ao verificar permissão:', error);
            usuarioAutorizado = false;
            aplicarPermissoesModal();
            return false;
        }
    }

    // ====== VERIFICAR EXISTÊNCIA DO PDF ======
    async function verificarPdf(codigoAuditoria) {
        try {
            const response = await fetchComAutenticacao(`/api/plano-anual-pdf?codigo=${codigoAuditoria}&tipo=emergencial`);
            console.log('Status da resposta:', response.status);
            
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
                pdfNaoEncontrado.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${errorData.error || 'Arquivo PDF não encontrado'}`;
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
        if (auditoriaAtualCodigo) {
            window.open(`/api/plano-anual-pdf?codigo=${auditoriaAtualCodigo}&tipo=emergencial`, '_blank');
        }
    }

    // ====== CARREGAR FUNDAMENTOS ======
    async function carregarFundamentos(auditoriaId) {
        console.log('🔍 Carregando fundamentos para auditoria ID:', auditoriaId);
        
        try {
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/fundamentos`);
            const data = await response.json();
            
            console.log('📦 Dados recebidos da API:', data);
            
            if (typeof data.fundamentos === 'string') {
                try {
                    fundamentosLista = JSON.parse(data.fundamentos);
                } catch(e) {
                    fundamentosLista = [];
                }
            } else if (Array.isArray(data.fundamentos)) {
                fundamentosLista = data.fundamentos;
            } else {
                fundamentosLista = [];
            }
            
            renderizarFundamentos();
            
        } catch (error) {
            console.error('Erro ao carregar fundamentos:', error);
            fundamentosLista = [];
            renderizarFundamentos();
        }
    }

    // ====== RENDERIZAR FUNDAMENTOS ======
    function renderizarFundamentos() {
        if (!fundamentosContainerModal) return;
        
        contadorRiscosModal.textContent = fundamentosLista.length;
        
        if (fundamentosLista.length === 0) {
            fundamentosContainerModal.innerHTML = `
                <div class="empty-message">
                    <i class="fas fa-info-circle"></i> Nenhum fundamento para esta auditoria emergencial cadastrado. 
                    <br>Clique em <strong>"Adicionar Risco"</strong> para começar.
                </div>
            `;
            return;
        }
        
        fundamentosContainerModal.innerHTML = fundamentosLista.map((fundamento, idx) => `
            <div class="risco-card" data-fundamento-idx="${idx}">
                <div class="risco-header">
                    <div class="risco-titulo">
                        <label><i class="fas fa-exclamation-triangle"></i> Risco ${idx + 1}:</label>
                        <textarea class="risco-titulo-input" rows="2" placeholder="Descreva brevemente o risco que fundamentou a auditoria emergencial..." data-idx="${idx}">${escapeHtml(fundamento.titulo || '')}</textarea>
                    </div>
                    <div class="risco-actions">
                        <button class="btn-remover-risco" data-idx="${idx}" title="Remover risco">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </div>
                
                <div class="pontos-container">
                    <label class="pontos-label"><i class="fas fa-list"></i> Pontos que fundamentam o risco:</label>
                    <div class="pontos-list" data-idx="${idx}">
                        ${(fundamento.pontos || []).map((ponto, pIdx) => `
                            <div class="ponto-item">
                                <span class="ponto-numero">${pIdx + 1}.</span>
                                <input type="text" class="ponto-input" placeholder="Ex: Não conformidade com a Lei 123/2026..." 
                                    data-idx="${idx}" data-pidx="${pIdx}" value="${escapeHtml(ponto)}">
                                <button class="btn-remover-ponto" data-idx="${idx}" data-pidx="${pIdx}" title="Remover ponto">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        `).join('')}
                    </div>
                    <button class="btn-adicionar-ponto" data-idx="${idx}">
                        <i class="fas fa-plus"></i> Adicionar ponto
                    </button>
                </div>
            </div>
        `).join('');
        
        adicionarEventosFundamentos();
        adicionarEventosEdicao();
        
        if (!usuarioAutorizado) {
            aplicarPermissoesModal();
        }
    }

    // ====== ADICIONAR EVENTOS DE EDIÇÃO ======
    function adicionarEventosEdicao() {
        document.querySelectorAll('#fundamentos-container-modal .btn-adicionar-risco, #fundamentos-container-modal .btn-adicionar-risco-inline').forEach(btn => {
            btn.removeEventListener('click', handleAdicionarRisco);
            btn.addEventListener('click', handleAdicionarRisco);
        });
        
        document.querySelectorAll('#fundamentos-container-modal .btn-remover-risco').forEach(btn => {
            btn.removeEventListener('click', handleRemoverRisco);
            btn.addEventListener('click', handleRemoverRisco);
        });
        
        document.querySelectorAll('#fundamentos-container-modal .btn-adicionar-ponto').forEach(btn => {
            btn.removeEventListener('click', handleAdicionarPonto);
            btn.addEventListener('click', handleAdicionarPonto);
        });
        
        document.querySelectorAll('#fundamentos-container-modal .btn-remover-ponto').forEach(btn => {
            btn.removeEventListener('click', handleRemoverPonto);
            btn.addEventListener('click', handleRemoverPonto);
        });
        
        document.querySelectorAll('#fundamentos-container-modal .btn-salvar-auditoria').forEach(btn => {
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
        
        const card = btn.closest('.auditoria-fundamento-card');
        const riscosInputs = card.querySelectorAll('.risco-titulo-input');
        const pontosInputs = card.querySelectorAll('.ponto-input');
        
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
        
        const fundamentosFiltrados = (auditoria.fundamentos || []).filter(f => {
            if (!f.titulo || f.titulo.trim() === '') return false;
            const pontosValidos = (f.pontos || []).filter(p => p && p.trim() !== '');
            return pontosValidos.length > 0;
        });
        
        try {
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
            
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/fundamentos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fundamentos: fundamentosFiltrados })
            });
            
            const result = await response.json();
            
            if (result.success) {
                mostrarToast('✅ Fundamentos salvos com sucesso!', 'success');
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

    // ====== ADICIONAR EVENTOS FUNDAMENTOS ======
    function adicionarEventosFundamentos() {
        document.querySelectorAll('#fundamentos-container-modal .risco-titulo-input').forEach(input => {
            input.removeEventListener('input', handleTituloChange);
            input.addEventListener('input', handleTituloChange);
        });
        
        document.querySelectorAll('#fundamentos-container-modal .btn-remover-risco').forEach(btn => {
            btn.removeEventListener('click', handleRemoverRisco);
            btn.addEventListener('click', handleRemoverRisco);
        });
        
        document.querySelectorAll('#fundamentos-container-modal .ponto-input').forEach(input => {
            input.removeEventListener('input', handlePontoChange);
            input.addEventListener('input', handlePontoChange);
        });
        
        document.querySelectorAll('#fundamentos-container-modal .btn-remover-ponto').forEach(btn => {
            btn.removeEventListener('click', handleRemoverPonto);
            btn.addEventListener('click', handleRemoverPonto);
        });
        
        document.querySelectorAll('#fundamentos-container-modal .btn-adicionar-ponto').forEach(btn => {
            btn.removeEventListener('click', handleAdicionarPonto);
            btn.addEventListener('click', handleAdicionarPonto);
        });
    }

    function handleTituloChange(e) {
        const idx = parseInt(e.target.getAttribute('data-idx'));
        if (fundamentosLista[idx]) {
            fundamentosLista[idx].titulo = e.target.value;
        }
    }

    function handleRemoverRisco(e) {
        const idx = parseInt(e.target.closest('.btn-remover-risco').getAttribute('data-idx'));
        fundamentosLista.splice(idx, 1);
        renderizarFundamentos();
    }

    function handlePontoChange(e) {
        const idx = parseInt(e.target.getAttribute('data-idx'));
        const pIdx = parseInt(e.target.getAttribute('data-pidx'));
        if (fundamentosLista[idx] && fundamentosLista[idx].pontos[pIdx] !== undefined) {
            fundamentosLista[idx].pontos[pIdx] = e.target.value;
        }
    }

    function handleRemoverPonto(e) {
        const idx = parseInt(e.target.closest('.btn-remover-ponto').getAttribute('data-idx'));
        const pIdx = parseInt(e.target.closest('.btn-remover-ponto').getAttribute('data-pidx'));
        if (fundamentosLista[idx] && fundamentosLista[idx].pontos) {
            fundamentosLista[idx].pontos.splice(pIdx, 1);
            renderizarFundamentos();
        }
    }

    function handleAdicionarPonto(e) {
        const idx = parseInt(e.target.closest('.btn-adicionar-ponto').getAttribute('data-idx'));
        if (fundamentosLista[idx]) {
            if (!fundamentosLista[idx].pontos) {
                fundamentosLista[idx].pontos = [];
            }
            fundamentosLista[idx].pontos.push('');
            renderizarFundamentos();
        }
    }

    // ====== ADICIONAR FUNDAMENTO ======
    function adicionarFundamento() {
        fundamentosLista.push({
            titulo: '',
            pontos: ['']
        });
        renderizarFundamentos();
    }

    // ====== SALVAR FUNDAMENTOS ======
    async function salvarFundamentos() {
        if (!auditoriaAtualId) {
            mostrarToast('❌ Nenhuma auditoria selecionada', 'error');
            return;
        }
        
        const fundamentosFiltrados = fundamentosLista.filter(f => {
            if (!f.titulo || f.titulo.trim() === '') return false;
            const pontosValidos = (f.pontos || []).filter(p => p && p.trim() !== '');
            return pontosValidos.length > 0;
        });
        
        const payload = {
            fundamentos: fundamentosFiltrados
        };
        
        try {
            const btnSalvar = btnSalvarFundamentosModal;
            const textoOriginal = btnSalvar.innerHTML;
            btnSalvar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Salvando...';
            btnSalvar.disabled = true;
            
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaAtualId}/fundamentos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (result.success) {
                mostrarToast('✅ Fundamentos salvos com sucesso!', 'success');
            } else {
                mostrarToast('❌ Erro ao salvar: ' + (result.error || 'Tente novamente'), 'error');
            }
            
            btnSalvar.innerHTML = textoOriginal;
            btnSalvar.disabled = false;
            
        } catch (error) {
            console.error('Erro ao salvar fundamentos:', error);
            mostrarToast('❌ Erro de conexão', 'error');
            btnSalvarFundamentosModal.innerHTML = '<i class="fas fa-save"></i> Salvar Todos os Fundamentos';
            btnSalvarFundamentosModal.disabled = false;
        }
    }

    // ====== FUNÇÕES DE EVIDÊNCIAS ======

    // ====== CARREGAR EVIDÊNCIAS ======
    async function carregarEvidencias(auditoriaId) {
        console.log('📎 Carregando evidências para auditoria ID:', auditoriaId);
        
        const evidenciasContainer = document.getElementById('evidencias-container');
        if (!evidenciasContainer) return;
        
        try {
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/evidencias`);
            const data = await response.json();
            
            console.log('📦 Evidências recebidas:', data);
            
            if (data.success) {
                renderizarEvidencias(data.evidencias);
            } else {
                evidenciasContainer.innerHTML = `
                    <div class="empty-message">
                        <i class="fas fa-exclamation-triangle"></i> Erro ao carregar evidências: ${data.error || 'Erro desconhecido'}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Erro ao carregar evidências:', error);
            evidenciasContainer.innerHTML = `
                <div class="empty-message">
                    <i class="fas fa-exclamation-triangle"></i> Erro ao carregar evidências
                </div>
            `;
        }
    }

    // ====== RENDERIZAR EVIDÊNCIAS ======
    function renderizarEvidencias(evidencias) {
        const evidenciasContainer = document.getElementById('evidencias-container');
        if (!evidenciasContainer) return;
        
        if (!evidencias || evidencias.length === 0) {
            evidenciasContainer.innerHTML = `
                <div class="empty-message">
                    <i class="fas fa-info-circle"></i> Nenhuma evidência anexada.
                </div>
            `;
            return;
        }
        
        evidenciasContainer.innerHTML = `
            <div class="evidencias-grid">
                ${evidencias.map((ev, idx) => `
                    <div class="evidencia-card" data-idx="${idx}">
                        <div class="evidencia-icon">
                            ${getIconByTipo(ev.tipo)}
                        </div>
                        <div class="evidencia-info">
                            <div class="evidencia-nome" title="${escapeHtml(ev.nome)}">${escapeHtml(ev.nome)}</div>
                            <div class="evidencia-tamanho">${formatarTamanho(ev.tamanho)}</div>
                        </div>
                        <div class="evidencia-actions">
                            <button class="btn-baixar-evidencia" onclick="baixarEvidencia('${ev.url}')" title="Baixar">
                                <i class="fas fa-download"></i>
                            </button>
                            <button class="btn-remover-evidencia" onclick="removerEvidencia(${idx})" title="Remover">
                                <i class="fas fa-trash-alt"></i>
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // ====== ÍCONE POR TIPO DE ARQUIVO ======
    function getIconByTipo(tipo) {
        if (!tipo) return '<i class="fas fa-file"></i>';
        
        if (tipo.includes('pdf')) return '<i class="fas fa-file-pdf" style="color: #dc3545;"></i>';
        if (tipo.includes('word') || tipo.includes('doc')) return '<i class="fas fa-file-word" style="color: #2b579a;"></i>';
        if (tipo.includes('excel') || tipo.includes('sheet')) return '<i class="fas fa-file-excel" style="color: #217346;"></i>';
        if (tipo.includes('image')) return '<i class="fas fa-file-image" style="color: #17a2b8;"></i>';
        if (tipo.includes('zip') || tipo.includes('rar')) return '<i class="fas fa-file-archive" style="color: #ffc107;"></i>';
        return '<i class="fas fa-file" style="color: #6c757d;"></i>';
    }

    // ====== FORMATAR TAMANHO ======
    function formatarTamanho(bytes) {
        if (!bytes) return 'Desconhecido';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
        return (bytes / 1073741824).toFixed(1) + ' GB';
    }

    // ====== UPLOAD DE EVIDÊNCIA ======
    async function uploadEvidencia(file) {
        const formData = new FormData();
        formData.append('arquivo', file);
        
        try {
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaAtualId}/upload-evidencia`, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                mostrarToast(`✅ Arquivo "${file.name}" enviado com sucesso!`, 'success');
                await carregarEvidencias(auditoriaAtualId);
            } else {
                mostrarToast(`❌ Erro ao enviar "${file.name}": ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Erro no upload:', error);
            mostrarToast(`❌ Erro ao enviar "${file.name}"`, 'error');
        }
    }

    // ====== BAIXAR EVIDÊNCIA ======
    window.baixarEvidencia = async function(caminho) {
        try {
            const response = await fetchComAutenticacao(`/api/evidencia/${encodeURIComponent(caminho)}`);
            const data = await response.json();
            
            if (data.success) {
                window.open(data.url, '_blank');
            } else {
                mostrarToast('❌ Erro ao baixar evidência', 'error');
            }
        } catch (error) {
            console.error('Erro ao baixar:', error);
            mostrarToast('❌ Erro ao baixar evidência', 'error');
        }
    }

    // ====== REMOVER EVIDÊNCIA ======
    window.removerEvidencia = async function(idx) {
        if (!confirm('Tem certeza que deseja remover esta evidência?')) return;
        
        try {
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaAtualId}/evidencias`);
            const data = await response.json();
            
            if (!data.success) {
                mostrarToast('❌ Erro ao buscar evidências', 'error');
                return;
            }
            
            const evidencias = data.evidencias;
            const evidencia = evidencias[idx];
            
            if (!evidencia) return;
            
            const deleteResponse = await fetchComAutenticacao(`/api/auditoria/${auditoriaAtualId}/evidencia`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ caminho: evidencia.url })
            });
            
            const deleteData = await deleteResponse.json();
            
            if (deleteData.success) {
                mostrarToast('✅ Evidência removida com sucesso!', 'success');
                await carregarEvidencias(auditoriaAtualId);
            } else {
                mostrarToast(`❌ ${deleteData.error}`, 'error');
            }
        } catch (error) {
            console.error('Erro ao remover evidência:', error);
            mostrarToast('❌ Erro ao remover evidência', 'error');
        }
    }

    // ====== FECHAR MODAL COM ESC ======
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modalDetalhes.style.display === 'flex') {
            fecharModalDetalhes();
        }
    });

    // ====== EVENTOS ======
    if (btnFiltrar) {
        btnFiltrar.addEventListener('click', () => {
            const areaId = filtroAreaSelect.value;
            carregarEmergenciais(areaId || null);
        });
    }

    if (btnLimparFiltros) {
        btnLimparFiltros.addEventListener('click', () => {
            filtroAreaSelect.value = '';
            carregarEmergenciais(null);
        });
    }

    if (filtroAreaSelect) {
        filtroAreaSelect.addEventListener('change', () => {
            const areaId = filtroAreaSelect.value;
            carregarEmergenciais(areaId || null);
        });
    }

    if (btnAdicionarFundamentoModal) {
        btnAdicionarFundamentoModal.addEventListener('click', adicionarFundamento);
    }

    if (btnSalvarFundamentosModal) {
        btnSalvarFundamentosModal.addEventListener('click', salvarFundamentos);
    }

    if (btnDownloadPdf) {
        btnDownloadPdf.addEventListener('click', baixarPdf);
    }

    // ====== INICIALIZAÇÃO ======
    console.log('🚀 Página de Auditorias Emergenciais carregada');
    
    // Carregar auditorias
    carregarEmergenciais(null);
    
    // ====== EVENTOS DE EVIDÊNCIAS ======
    const btnAnexarEvidencia = document.getElementById('btn-anexar-evidencia');
    const inputEvidencia = document.getElementById('input-evidencia');
    
    if (btnAnexarEvidencia && inputEvidencia) {
        btnAnexarEvidencia.addEventListener('click', () => {
            inputEvidencia.click();
        });
        
        inputEvidencia.addEventListener('change', async (e) => {
            const files = e.target.files;
            if (files.length === 0) return;
            
            mostrarToast(`📤 Enviando ${files.length} arquivo(s)...`, 'info');
            
            for (const file of files) {
                await uploadEvidencia(file);
            }
            
            inputEvidencia.value = '';
        });
    }

});