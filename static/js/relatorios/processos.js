// ============================================================
// ProcessosModule.js
// Módulo para gerenciar carregamento de processos
// ============================================================

const ProcessosModule = (() => {
    // ============================================================
    // VARIÁVEIS PRIVADAS
    // ============================================================
    
    let selectProcesso = null;
    let rowProcesso = null;
    let processosCarregados = false;
    
    // ============================================================
    // FUNÇÕES PRIVADAS
    // ============================================================
    
    async function carregarProcessos(auditoriaId) {
        if (!selectProcesso || !rowProcesso) return;
        
        const tipoRelatorio = document.getElementById('tipo_relatorio')?.value || '';
        
        // Mostrar campo de processo
        rowProcesso.style.display = 'flex';
        
        // Estado de carregamento
        selectProcesso.innerHTML = '<option value="">Carregando processos...</option>';
        selectProcesso.disabled = true;
        processosCarregados = false;
        
        try {
            const response = await fetchComAutenticacao(
                `/api/relatorios/processos-por-auditoria?auditoria_id=${auditoriaId}`
            );
            const data = await response.json();
            
            if (data.success && data.processos && data.processos.length > 0) {
                // Para parecer: NÃO mostra opção "Todos"
                if (tipoRelatorio === 'parecer') {
                    selectProcesso.innerHTML = '<option value="">Selecione um processo...</option>';
                } else {
                    // Para panorama, detalhamento e follow-up: mostra "Todos"
                    selectProcesso.innerHTML = '<option value="">Todos os processos da auditoria</option>';
                }
                
                // Adicionar processos
                data.processos.forEach(proc => {
                    const option = document.createElement('option');
                    option.value = proc.id;
                    option.textContent = `${proc.codigo_processo} - ${proc.nome_processo}`;
                    selectProcesso.appendChild(option);
                });
                
                selectProcesso.disabled = false;
                processosCarregados = true;
                
            } else {
                selectProcesso.innerHTML = '<option value="">Nenhum processo encontrado</option>';
                selectProcesso.disabled = true;
                
                if (data.message) {
                    mostrarToast(data.message, 'warning');
                }
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar processos:', error);
            selectProcesso.innerHTML = '<option value="">Erro ao carregar</option>';
            selectProcesso.disabled = true;
            
            mostrarToast('Erro ao carregar processos.', 'error');
        }
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('📝 Inicializando ProcessosModule...');
        
        // Buscar referências aos elementos do DOM
        selectProcesso = document.getElementById('processo_relatorio');
        rowProcesso = document.getElementById('row_processo');
        
        if (!selectProcesso || !rowProcesso) {
            console.warn('⚠️ Elementos de processo não encontrados');
            return;
        }
        
        console.log('✅ ProcessosModule inicializado');
    }
    
    function carregarPorAuditoria(auditoriaId) {
        if (!auditoriaId) {
            limparSelecao();
            return;
        }
        
        return carregarProcessos(auditoriaId);
    }
    
    function getProcessoSelecionado() {
        if (!selectProcesso) return null;
        
        const processoId = selectProcesso.value;
        const processoTexto = selectProcesso.options[selectProcesso.selectedIndex]?.textContent || '';
        
        return {
            id: processoId || null,
            texto: processoTexto || null
        };
    }
    
    function getSelectProcesso() {
        return selectProcesso;
    }
    
    function getRowProcesso() {
        return rowProcesso;
    }
    
    function temProcessosCarregados() {
        return processosCarregados;
    }
    
    function mostrarCampoProcesso() {
        if (rowProcesso) {
            rowProcesso.style.display = 'flex';
        }
    }
    
    function ocultarCampoProcesso() {
        if (rowProcesso) {
            rowProcesso.style.display = 'none';
        }
        
        if (selectProcesso) {
            selectProcesso.value = '';
            selectProcesso.disabled = true;
        }
        
        processosCarregados = false;
    }
    
    function limparSelecao() {
        if (selectProcesso) {
            selectProcesso.innerHTML = '<option value="">Selecione uma auditoria primeiro...</option>';
            selectProcesso.disabled = true;
        }
        
        processosCarregados = false;
    }
    
    // ============================================================
    // RETORNO PÚBLICO (API do módulo)
    // ============================================================
    
    return {
        init: init,
        carregarPorAuditoria: carregarPorAuditoria,
        getProcessoSelecionado: getProcessoSelecionado,
        getSelectProcesso: getSelectProcesso,
        getRowProcesso: getRowProcesso,
        temProcessosCarregados: temProcessosCarregados,
        mostrarCampoProcesso: mostrarCampoProcesso,
        ocultarCampoProcesso: ocultarCampoProcesso,
        limparSelecao: limparSelecao
    };
})();