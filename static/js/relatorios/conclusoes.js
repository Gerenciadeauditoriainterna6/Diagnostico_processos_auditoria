// ============================================================
// ConclusoesModule.js
// Módulo para gerenciar conclusões (CRUD, modal, relatórios)
// ============================================================

const ConclusoesModule = (() => {
    // ============================================================
    // VARIÁVEIS PRIVADAS
    // ============================================================
    
    let conclusaoAtual = null;
    let isAdmin = false;
    let modalConclusao = null;
    
    // Elementos do formulário
    let campoTexto = null;
    let campoForca = null;
    let campoFraqueza = null;
    let campoOportunidade = null;
    let campoAmeaca = null;
    
    // ============================================================
    // FUNÇÕES PRIVADAS
    // ============================================================
    
    function obterDadosSelecionados() {
        const area = AreasModule.getAreaSelecionada();
        const auditoria = AuditoriasModule.getAuditoriaSelecionada();
        
        return {
            areaId: area?.id || null,
            auditoriaId: auditoria?.id || null
        };
    }
    
    function obterOrientacao() {
        return document.querySelector('input[name="orientacao"]:checked')?.value || 'RETRATO';
    }
    
    function limparCampos() {
        if (campoTexto) campoTexto.value = '';
        if (campoForca) campoForca.value = '';
        if (campoFraqueza) campoFraqueza.value = '';
        if (campoOportunidade) campoOportunidade.value = '';
        if (campoAmeaca) campoAmeaca.value = '';
    }
    
    function preencherCampos(dados) {
        if (campoTexto) campoTexto.value = dados.conclusao || '';
        if (campoForca) campoForca.value = dados.forca || '';
        if (campoFraqueza) campoFraqueza.value = dados.fraqueza || '';
        if (campoOportunidade) campoOportunidade.value = dados.oportunidades || '';
        if (campoAmeaca) campoAmeaca.value = dados.ameacas || '';
    }
    
    async function buscarConclusaoExistente() {
        const { areaId, auditoriaId } = obterDadosSelecionados();
        
        if (!areaId || !auditoriaId) return;
        
        try {
            const response = await fetchComAutenticacao(
                `/api/conclusoes/buscar?auditoria_id=${auditoriaId}&area_id=${areaId}`
            );
            const data = await response.json();
            
            console.log('📥 Dados da conclusão:', data);
            
            if (data.success && data.conclusao) {
                conclusaoAtual = data.conclusao;
                const dados = data.conclusao.texto || {};
                preencherCampos(dados);
                console.log('✅ Conclusão carregada:', dados);
            } else {
                limparCampos();
            }
            
            // Carregar histórico
            await carregarHistoricoConclusoes(auditoriaId, areaId);
            
        } catch (error) {
            console.error('❌ Erro ao buscar conclusão:', error);
            mostrarToast('Erro ao buscar conclusão.', 'error');
        }
    }
    
    async function carregarHistoricoConclusoes(auditoriaId, areaId) {
        try {
            const response = await fetchComAutenticacao(
                `/api/conclusoes/historico?auditoria_id=${auditoriaId}&area_id=${areaId}`
            );
            const data = await response.json();
            
            console.log('📋 Histórico de conclusões:', data);
            
            const container = document.getElementById('lista-historico-conclusoes');
            const historicoDiv = document.getElementById('historico-conclusoes');
            
            if (!container || !historicoDiv) {
                console.warn('⚠️ Elementos de histórico não encontrados');
                return;
            }
            
            if (data.success && data.conclusoes && data.conclusoes.length > 0) {
                isAdmin = data.is_admin || false;
                const usuarioLogado = data.usuario_logado || '';
                
                container.innerHTML = data.conclusoes.map(item => {
                    return renderizarItemHistorico(item, usuarioLogado);
                }).join('');
                
                historicoDiv.style.display = 'block';
            } else {
                container.innerHTML = '<div style="color: #999; font-size: 13px; padding: 10px; text-align: center;">Nenhuma conclusão encontrada</div>';
                historicoDiv.style.display = 'block';
            }
        } catch (error) {
            console.error('❌ Erro ao carregar histórico:', error);
            const historicoDiv = document.getElementById('historico-conclusoes');
            if (historicoDiv) historicoDiv.style.display = 'none';
        }
    }
    
    function renderizarItemHistorico(item, usuarioLogado) {
        const isOwn = item.usuario_nome === usuarioLogado;
        const dados = item.conclusao || {};
        
        // Construir texto para exibição
        let textoExibicao = '';
        
        if (dados.conclusao) {
            textoExibicao += dados.conclusao;
        }
        
        const hasSwot = dados.forca || dados.fraqueza || dados.oportunidades || dados.ameacas;
        if (hasSwot) {
            textoExibicao += '\n\nANÁLISE SWOT:\n';
            if (dados.forca) textoExibicao += `✅ Forças: ${dados.forca}\n`;
            if (dados.fraqueza) textoExibicao += `❌ Fraquezas: ${dados.fraqueza}\n`;
            if (dados.oportunidades) textoExibicao += `💡 Oportunidades: ${dados.oportunidades}\n`;
            if (dados.ameacas) textoExibicao += `⚠️ Ameaças: ${dados.ameacas}\n`;
        }
        
        if (!textoExibicao.trim()) {
            textoExibicao = '(Nenhuma conclusão preenchida)';
        }
        
        const isOwnLabel = isOwn ? ' <span style="color: #0b5b99; font-weight: 600;">(Sua conclusão)</span>' : '';
        
        return `
            <div class="conclusao-historico-item" style="${isOwn ? 'background: #e8f4f8; border-left-color: #0b5b99;' : ''}">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span class="usuario">Atualizado por: ${escapeHtml(item.usuario_nome)}${isOwnLabel}</span>
                        <span class="data">Data/Hora da última atualização: ${item.updated_at || ''}</span>
                    </div>
                </div>
                <div class="texto" style="margin-top: 6px; white-space: pre-wrap;">${escapeHtml(textoExibicao)}</div>
            </div>
        `;
    }
    
    async function baixarConclusaoPorId(conclusaoId, usuarioNome) {
        const { areaId, auditoriaId } = obterDadosSelecionados();
        const orientacao = obterOrientacao();
        
        console.log(`📥 Baixando conclusão ID: ${conclusaoId} do usuário: ${usuarioNome}`);
        
        try {
            const response = await fetchComAutenticacao('/api/relatorios/gerar-conclusao', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    area_id: areaId,
                    auditoria_id: auditoriaId,
                    orientacao: orientacao,
                    conclusao_id: conclusaoId
                })
            });
            
            if (response.ok) {
                await baixarArquivo(response, `relatorio_conclusao_${usuarioNome.replace(' ', '_')}.pdf`);
                mostrarToast(`✅ Relatório de ${usuarioNome} baixado com sucesso!`, 'success');
            } else {
                const error = await response.json();
                mostrarToast(`❌ Erro: ${error.error || 'Erro desconhecido'}`, 'error');
            }
        } catch (error) {
            console.error('❌ Erro:', error);
            mostrarToast('❌ Erro ao baixar relatório', 'error');
        }
    }
    
    async function baixarArquivo(response, nomePadrao) {
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        
        const contentDisposition = response.headers.get('Content-Disposition');
        let nomeArquivo = nomePadrao;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (match && match[1]) {
                nomeArquivo = match[1].replace(/['"]/g, '');
            }
        }
        
        a.download = nomeArquivo;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
    }
    
    function configurarEventos() {
        // Eventos do modal
        const btnFecharModal = document.getElementById('btn-fechar-modal-conclusao');
        const btnCancelar = document.getElementById('btn-cancelar-conclusao');
        const btnSalvar = document.getElementById('btn-salvar-conclusao');
        
        if (btnFecharModal) {
            btnFecharModal.addEventListener('click', () => fecharModal());
        }
        
        if (btnCancelar) {
            btnCancelar.addEventListener('click', () => fecharModal());
        }
        
        if (btnSalvar) {
            btnSalvar.addEventListener('click', async () => {
                const salvou = await salvar();
                if (salvou) {
                    fecharModal();
                    await gerarRelatorio();
                }
            });
        }
        
        // Fechar modal clicando fora
        if (modalConclusao) {
            modalConclusao.addEventListener('click', (e) => {
                if (e.target === modalConclusao) {
                    fecharModal();
                }
            });
        }
        
        // Evento do seletor de usuários (admin)
        const seletorUsuario = document.getElementById('seletor-usuario');
        if (seletorUsuario) {
            seletorUsuario.addEventListener('change', function() {
                const usuarioSelecionado = this.value;
                if (usuarioSelecionado) {
                    carregarConclusaoDeUsuario(usuarioSelecionado);
                } else {
                    // Voltar para a própria conclusão
                    if (campoTexto) {
                        campoTexto.disabled = false;
                        campoTexto.style.background = '';
                    }
                    const btnSalvar = document.getElementById('btn-salvar-conclusao');
                    if (btnSalvar) btnSalvar.style.display = 'inline-flex';
                    
                    const btnBaixar = document.getElementById('btn-baixar-conclusao');
                    if (btnBaixar) btnBaixar.style.display = 'none';
                    
                    buscarConclusaoExistente();
                }
            });
        }
    }
    
    async function carregarConclusaoDeUsuario(usuarioSelecionado) {
        // Implementar quando necessário
        // Por enquanto, apenas log
        console.log('👤 Carregando conclusão do usuário:', usuarioSelecionado);
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('📝 Inicializando ConclusoesModule...');
        
        // Buscar referências aos elementos do DOM
        modalConclusao = document.getElementById('modal-conclusao');
        campoTexto = document.getElementById('conclusao_texto');
        campoForca = document.getElementById('swot_forca');
        campoFraqueza = document.getElementById('swot_fraqueza');
        campoOportunidade = document.getElementById('swot_oportunidade');
        campoAmeaca = document.getElementById('swot_ameaca');
        
        if (!modalConclusao || !campoTexto) {
            console.warn('⚠️ Elementos de conclusão não encontrados');
            return;
        }
        
        // Configurar eventos
        configurarEventos();
        
        console.log('✅ ConclusoesModule inicializado');
    }
    
    function abrirModal() {
        if (!modalConclusao) return;
        
        // Resetar estado
        if (campoTexto) {
            campoTexto.disabled = false;
            campoTexto.style.background = '';
        }
        
        const btnSalvar = document.getElementById('btn-salvar-conclusao');
        if (btnSalvar) btnSalvar.style.display = 'inline-flex';
        
        // Limpar campos
        limparCampos();
        
        // Buscar conclusão existente e histórico
        buscarConclusaoExistente();
        
        // Mostrar modal
        modalConclusao.style.display = 'flex';
        void modalConclusao.offsetWidth;
        modalConclusao.style.opacity = '1';
    }
    
    function fecharModal() {
        if (modalConclusao) {
            modalConclusao.style.display = 'none';
            modalConclusao.style.opacity = '0';
        }
    }
    
    async function salvar() {
        // Pegar todos os campos
        const texto = campoTexto?.value.trim() || '';
        const forca = campoForca?.value.trim() || '';
        const fraqueza = campoFraqueza?.value.trim() || '';
        const oportunidades = campoOportunidade?.value.trim() || '';
        const ameacas = campoAmeaca?.value.trim() || '';
        
        // Validação: pelo menos um campo preenchido
        if (!texto && !forca && !fraqueza && !oportunidades && !ameacas) {
            mostrarToast('⚠️ Preencha pelo menos um campo da conclusão', 'warning');
            
            if (campoTexto) {
                campoTexto.style.borderColor = '#dc3545';
                setTimeout(() => {
                    campoTexto.style.borderColor = '';
                }, 3000);
            }
            return false;
        }
        
        const { areaId, auditoriaId } = obterDadosSelecionados();
        
        if (!areaId || !auditoriaId) {
            mostrarToast('⚠️ Selecione a área e auditoria primeiro', 'warning');
            return false;
        }
        
        try {
            const response = await fetchComAutenticacao('/api/conclusoes/salvar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    auditoria_id: parseInt(auditoriaId),
                    area_id: parseInt(areaId),
                    conclusao: texto,
                    forca: forca,
                    fraqueza: fraqueza,
                    oportunidades: oportunidades,
                    ameacas: ameacas
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                mostrarToast('✅ ' + data.message, 'success');
                return true;
            } else {
                mostrarToast('❌ ' + (data.error || 'Erro ao salvar conclusão'), 'error');
                return false;
            }
        } catch (error) {
            console.error('❌ Erro ao salvar conclusão:', error);
            mostrarToast('❌ Erro ao salvar conclusão', 'error');
            return false;
        }
    }
    
    async function gerarRelatorio() {
        const { areaId, auditoriaId } = obterDadosSelecionados();
        const orientacao = obterOrientacao();
        const textoConclusao = campoTexto?.value.trim() || '';
        
        if (!textoConclusao) {
            mostrarToast('⚠️ Conclusão não pode estar vazia', 'warning');
            return;
        }
        
        const btnGerar = document.getElementById('btn-gerar-relatorio');
        const btnLoading = btnGerar?.querySelector('.btn-loading');
        
        if (btnGerar) {
            btnGerar.disabled = true;
            btnGerar.querySelector('i')?.classList.add('d-none');
            if (btnLoading) btnLoading.style.display = 'inline-flex';
        }
        
        try {
            const response = await fetchComAutenticacao('/api/relatorios/gerar-conclusao', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    area_id: areaId,
                    auditoria_id: auditoriaId,
                    orientacao: orientacao,
                    conclusao: textoConclusao
                })
            });
            
            if (response.ok) {
                await baixarArquivo(response, 'relatorio_conclusao.pdf');
                
                const resultadoDiv = document.getElementById('resultado-relatorio');
                if (resultadoDiv) {
                    resultadoDiv.style.display = 'block';
                    setTimeout(() => {
                        resultadoDiv.style.opacity = '1';
                    }, 10);
                }
                
                mostrarToast('✅ Relatório de Conclusão gerado e baixado com sucesso!', 'success');
            } else {
                const error = await response.json();
                mostrarToast('❌ Erro: ' + (error.error || 'Erro desconhecido'), 'error');
            }
        } catch (error) {
            console.error('❌ Erro:', error);
            mostrarToast('❌ Erro ao conectar com o servidor', 'error');
        } finally {
            if (btnGerar) {
                btnGerar.disabled = false;
                btnGerar.querySelector('i')?.classList.remove('d-none');
                if (btnLoading) btnLoading.style.display = 'none';
            }
        }
    }
    
    // ============================================================
    // RETORNO PÚBLICO (API do módulo)
    // ============================================================
    
    return {
        init: init,
        abrirModal: abrirModal,
        fecharModal: fecharModal,
        salvar: salvar,
        gerarRelatorio: gerarRelatorio
    };
})();