// ============================================================
// AuditoriasModule.js
// Módulo para gerenciar carregamento de auditorias e permissões
// ============================================================

const AuditoriasModule = (() => {
    // ============================================================
    // VARIÁVEIS PRIVADAS
    // ============================================================
    
    let selectAuditoria = null;
    let infoBox = null;
    let infoMsg = null;
    let auditoriasCarregadas = false;
    let usuarioAutorizado = false;
    
    // ============================================================
    // FUNÇÕES PRIVADAS
    // ============================================================
    
    async function carregarAuditorias(areaId) {
        if (!selectAuditoria) return;
        
        // Mostrar estado de carregamento
        selectAuditoria.innerHTML = '<option value="">Carregando auditorias...</option>';
        selectAuditoria.disabled = true;
        auditoriasCarregadas = false;
        usuarioAutorizado = false;
        
        // Ocultar info box
        if (infoBox) infoBox.style.display = 'none';
        
        try {
            const response = await fetchComAutenticacao(`/api/relatorios/auditorias-por-area?area_id=${areaId}`);
            const data = await response.json();
            
            if (data.success && data.auditorias && data.auditorias.length > 0) {
                // Limpar e popular o select
                selectAuditoria.innerHTML = '<option value="">Selecione uma auditoria...</option>';
                
                data.auditorias.forEach(aud => {
                    const option = document.createElement('option');
                    option.value = aud.id;
                    option.textContent = `${aud.codigo_auditoria} - ${aud.titulo} (${aud.ano}) ${aud.trimestre}º trim) - ${aud.unidade || ''}`;
                    selectAuditoria.appendChild(option);
                });
                
                selectAuditoria.disabled = false;
                auditoriasCarregadas = true;
                
            } else {
                selectAuditoria.innerHTML = '<option value="">Nenhuma auditoria encontrada</option>';
                selectAuditoria.disabled = true;
                
                if (infoBox && infoMsg) {
                    infoMsg.textContent = 'Nenhuma auditoria cadastrada para esta área.';
                    infoBox.style.display = 'flex';
                }
            }
            
        } catch (error) {
            console.error('❌ Erro ao carregar auditorias:', error);
            selectAuditoria.innerHTML = '<option value="">Erro ao carregar</option>';
            selectAuditoria.disabled = true;
            
            mostrarToast('Erro ao carregar auditorias.', 'error');
        }
    }
    
    async function verificarPermissaoAuditoria(auditoriaId) {
        const btnGerar = document.getElementById('btn-gerar-relatorio');
        
        try {
            const response = await fetchComAutenticacao(`/api/auditoria/${auditoriaId}/responsavel`);
            const data = await response.json();
            
            if (data.autorizado) {
                usuarioAutorizado = true;
                
                // Habilitar botão de gerar
                if (btnGerar) {
                    btnGerar.disabled = false;
                }
                
                // Ocultar info box
                if (infoBox) {
                    infoBox.style.display = 'none';
                }
                
            } else {
                usuarioAutorizado = false;
                
                // Desabilitar botão de gerar
                if (btnGerar) {
                    btnGerar.disabled = true;
                }
                
                // Mostrar mensagem de permissão negada
                if (infoBox && infoMsg) {
                    infoBox.style.display = 'flex';
                    infoBox.className = 'alert-error';
                    infoMsg.innerHTML = '<i class="fas fa-lock"></i> Você não tem permissão para gerar relatórios desta auditoria.';
                }
            }
            
        } catch (error) {
            console.error('❌ Erro ao verificar permissão:', error);
            usuarioAutorizado = false;
            
            if (btnGerar) {
                btnGerar.disabled = true;
            }
            
            mostrarToast('Erro ao verificar permissão.', 'error');
        }
    }
    
    function configurarEventos() {
        if (!selectAuditoria) return;
        
        selectAuditoria.addEventListener('change', async () => {
            const auditoriaId = selectAuditoria.value;
            const tipoRelatorio = document.getElementById('tipo_relatorio')?.value || 'gerencial';
            const rowProcesso = document.getElementById('row_processo');
            const btnGerar = document.getElementById('btn-gerar-relatorio');
            
            if (!auditoriaId) {
                // Nenhuma auditoria selecionada
                if (btnGerar) btnGerar.disabled = true;
                if (infoBox) infoBox.style.display = 'none';
                if (rowProcesso) rowProcesso.style.display = 'none';
                usuarioAutorizado = false;
                return;
            }
            
            // Mostrar processo apenas para certos tipos de relatório
            if (tipoRelatorio === 'parecer' || tipoRelatorio === 'panorama' || 
                tipoRelatorio === 'detalhamento' || tipoRelatorio === 'followup') {
                if (rowProcesso) rowProcesso.style.display = 'flex';
                
                // Carregar processos da auditoria
                if (typeof ProcessosModule !== 'undefined') {
                    await ProcessosModule.carregarPorAuditoria(auditoriaId);
                }
            } else {
                // Para conclusão, esconde o campo de processo
                if (rowProcesso) rowProcesso.style.display = 'none';
            }
            
            // Verificar permissão do usuário
            await verificarPermissaoAuditoria(auditoriaId);
        });
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('📋 Inicializando AuditoriasModule...');
        
        // Buscar referências aos elementos do DOM
        selectAuditoria = document.getElementById('auditoria_relatorio');
        infoBox = document.getElementById('info-box');
        infoMsg = document.getElementById('info-mensagem');
        
        if (!selectAuditoria) {
            console.warn('⚠️ Elemento #auditoria_relatorio não encontrado');
            return;
        }
        
        // Configurar eventos
        configurarEventos();
        
        console.log('✅ AuditoriasModule inicializado');
    }
    
    function carregarPorArea(areaId) {
        return carregarAuditorias(areaId);
    }
    
    function getAuditoriaSelecionada() {
        if (!selectAuditoria) return null;
        
        const auditoriaId = selectAuditoria.value;
        const auditoriaTexto = selectAuditoria.options[selectAuditoria.selectedIndex]?.textContent || '';
        
        return {
            id: auditoriaId || null,
            texto: auditoriaTexto || null
        };
    }
    
    function isUsuarioAutorizado() {
        return usuarioAutorizado;
    }
    
    function getSelectAuditoria() {
        return selectAuditoria;
    }
    
    function temAuditoriasCarregadas() {
        return auditoriasCarregadas;
    }
    
    function limparSelecao() {
        if (!selectAuditoria) return;
        
        selectAuditoria.innerHTML = '<option value="">Selecione uma área primeiro...</option>';
        selectAuditoria.disabled = true;
        auditoriasCarregadas = false;
        usuarioAutorizado = false;
        
        // Desabilitar botão de gerar
        const btnGerar = document.getElementById('btn-gerar-relatorio');
        if (btnGerar) btnGerar.disabled = true;
    }
    
    // ============================================================
    // RETORNO PÚBLICO (API do módulo)
    // ============================================================
    
    return {
        init: init,
        carregarPorArea: carregarPorArea,
        getAuditoriaSelecionada: getAuditoriaSelecionada,
        isUsuarioAutorizado: isUsuarioAutorizado,
        getSelectAuditoria: getSelectAuditoria,
        temAuditoriasCarregadas: temAuditoriasCarregadas,
        limparSelecao: limparSelecao
    };
})();