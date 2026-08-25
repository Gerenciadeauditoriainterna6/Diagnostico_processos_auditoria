// ============================================================
// RelatoriosModule.js
// Módulo principal para geração de relatórios
// ============================================================

const RelatoriosModule = (() => {
    // ============================================================
    // VARIÁVEIS PRIVADAS
    // ============================================================
    
    let btnGerar = null;
    let btnLoading = null;
    let resultadoDiv = null;
    
    // ============================================================
    // FUNÇÕES PRIVADAS
    // ============================================================
    
    function obterDadosFormulario() {
        const area = AreasModule.getAreaSelecionada();
        const auditoria = AuditoriasModule.getAuditoriaSelecionada();
        const processo = ProcessosModule.getProcessoSelecionado();
        const orientacao = document.querySelector('input[name="orientacao"]:checked')?.value || 'RETRATO';
        const tipoRelatorio = document.getElementById('tipo_relatorio')?.value;
        
        return {
            areaId: area?.id || null,
            auditoriaId: auditoria?.id || null,
            processoId: processo?.id || null,
            orientacao: orientacao,
            tipoRelatorio: tipoRelatorio || null
        };
    }
    
    function validarDados(dados) {
        // Validações básicas
        if (!dados.areaId || !dados.auditoriaId) {
            mostrarToast('⚠️ Selecione a área e a auditoria primeiro', 'warning');
            return false;
        }
        
        if (!dados.tipoRelatorio) {
            mostrarToast('⚠️ Selecione o tipo de relatório', 'warning');
            return false;
        }
        
        // Para conclusão: abrir modal (não exige processo)
        if (dados.tipoRelatorio === 'conclusao') {
            ConclusoesModule.abrirModal();
            return false; // Não continua o fluxo normal
        }
        
        // Para parecer: processo é obrigatório
        if (dados.tipoRelatorio === 'parecer' && !dados.processoId) {
            mostrarToast('⚠️ Selecione um processo específico para gerar o Parecer', 'warning');
            
            const selectProcesso = document.getElementById('processo_relatorio');
            if (selectProcesso) {
                selectProcesso.style.borderColor = '#dc3545';
                setTimeout(() => {
                    selectProcesso.style.borderColor = '';
                }, 3000);
            }
            return false;
        }
        
        return true;
    }
    
    function configurarPayload(dados) {
        const bodyData = {
            area_id: dados.areaId,
            auditoria_id: dados.auditoriaId,
            orientacao: dados.orientacao
        };
        
        let url = '';
        let nomeBase = '';
        
        const incluirABR = document.getElementById('incluir_abr')?.checked || false;
        
        switch (dados.tipoRelatorio) {
            case 'panorama':
                url = '/api/relatorios/gerar-panorama';
                nomeBase = dados.processoId 
                    ? `relatorio_panorama_processo_${dados.processoId}` 
                    : 'relatorio_panorama_todos';
                if (dados.processoId) bodyData.processo_id = dados.processoId;
                break;
                
            case 'detalhamento':
                url = '/api/relatorios/gerar-detalhamento';
                nomeBase = dados.processoId 
                    ? `relatorio_detalhamento_processo_${dados.processoId}` 
                    : 'relatorio_detalhamento_todos';
                if (dados.processoId) bodyData.processo_id = dados.processoId;
                break;
                
            case 'parecer':
                url = '/api/relatorios/gerar-parecer';
                nomeBase = `parecer_auditoria_processo_${dados.processoId}`;
                bodyData.processo_id = dados.processoId;
                if (incluirABR) bodyData.incluir_abr = true;
                bodyData.incluir_checklists = document.getElementById('incluir_checklists')?.checked ?? true;
                break;
                
            case 'followup':
                url = '/api/relatorios/gerar-followup';
                nomeBase = dados.processoId 
                    ? `relatorio_followup_processo_${dados.processoId}` 
                    : 'relatorio_followup_todos';
                if (dados.processoId) bodyData.processo_id = dados.processoId;
                break;
                
            default:
                return null;
        }
        
        return { url, nomeBase, bodyData };
    }
    
    function mostrarLoading() {
        if (btnGerar) {
            btnGerar.disabled = true;
            const icon = btnGerar.querySelector('i');
            if (icon) icon.classList.add('d-none');
            if (btnLoading) btnLoading.style.display = 'inline-flex';
        }
    }
    
    function esconderLoading() {
        if (btnGerar) {
            btnGerar.disabled = false;
            const icon = btnGerar.querySelector('i');
            if (icon) icon.classList.remove('d-none');
            if (btnLoading) btnLoading.style.display = 'none';
        }
    }
    
    async function baixarArquivo(response, nomeBase) {
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        
        const contentDisposition = response.headers.get('Content-Disposition');
        let nomeArquivo = `${nomeBase}.pdf`;
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
    
    function mostrarResultado() {
        if (resultadoDiv) {
            resultadoDiv.style.display = 'block';
            setTimeout(() => {
                resultadoDiv.style.opacity = '1';
            }, 10);
        }
    }
    
    async function gerarRelatorio() {
        const dados = obterDadosFormulario();
        
        // Validar dados
        if (!validarDados(dados)) {
            return;
        }
        
        // Configurar payload
        const config = configurarPayload(dados);
        if (!config) {
            mostrarToast('⚠️ Tipo de relatório inválido', 'warning');
            return;
        }
        
        // Mostrar loading
        mostrarLoading();
        
        try {
            const response = await fetchComAutenticacao(config.url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config.bodyData)
            });
            
            if (response.ok) {
                await baixarArquivo(response, config.nomeBase);
                mostrarResultado();
                mostrarToast('✅ Relatório gerado e baixado com sucesso!', 'success');
            } else {
                const error = await response.json();
                mostrarToast('❌ Erro: ' + (error.error || 'Erro desconhecido'), 'error');
            }
        } catch (error) {
            console.error('❌ Erro:', error);
            mostrarToast('❌ Erro ao conectar com o servidor', 'error');
        } finally {
            esconderLoading();
        }
    }
    
    function configurarEventos() {
        // Evento do botão gerar
        if (btnGerar) {
            btnGerar.addEventListener('click', gerarRelatorio);
        }
        
        // Evento de mudança do tipo de relatório
        const selectTipo = document.getElementById('tipo_relatorio');
        if (selectTipo) {
            selectTipo.addEventListener('change', async () => {
                const dados = obterDadosFormulario();
                const rowProcesso = ProcessosModule.getRowProcesso();
               
                const checkboxChecklists = document.getElementById('checkbox-checklists-container');
                
                if (dados.tipoRelatorio === 'parecer') {
                    if (checkboxChecklists) checkboxChecklists.style.display = 'block';
                } else {
                    if (checkboxChecklists) checkboxChecklists.style.display = 'none';
                }
                                
                // Mostrar/esconder campo de processo
                if (dados.tipoRelatorio && dados.auditoriaId) {
                    if (dados.tipoRelatorio === 'parecer' || 
                        dados.tipoRelatorio === 'panorama' || 
                        dados.tipoRelatorio === 'detalhamento' || 
                        dados.tipoRelatorio === 'followup') {
                        
                        ProcessosModule.mostrarCampoProcesso();
                        await ProcessosModule.carregarPorAuditoria(dados.auditoriaId);
                        
                        // Se for parecer, destacar campo de processo
                        if (dados.tipoRelatorio === 'parecer') {
                            const selectProcesso = ProcessosModule.getSelectProcesso();
                            if (selectProcesso) {
                                selectProcesso.style.borderColor = '#184145';
                            }
                        }
                    } else {
                        // Para conclusão, esconde processo
                        ProcessosModule.ocultarCampoProcesso();
                    }
                } else {
                    ProcessosModule.ocultarCampoProcesso();
                }
                
                // Atualizar visibilidade ABR
                PermissoesModule.atualizarVisibilidadeABR();
            });
        }
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('📊 Inicializando RelatoriosModule...');
        
        // Buscar referências aos elementos do DOM
        btnGerar = document.getElementById('btn-gerar-relatorio');
        btnLoading = btnGerar?.querySelector('.btn-loading');
        resultadoDiv = document.getElementById('resultado-relatorio');
        
        if (!btnGerar) {
            console.warn('⚠️ Botão de gerar relatório não encontrado');
            return;
        }
        
        // Configurar eventos
        configurarEventos();
        
        console.log('✅ RelatoriosModule inicializado');
    }
    
    function gerar() {
        return gerarRelatorio();
    }
    
    // ============================================================
    // RETORNO PÚBLICO (API do módulo)
    // ============================================================
    
    return {
        init: init,
        gerar: gerar
    };
})();