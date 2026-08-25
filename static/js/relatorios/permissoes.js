const PermissoesModule = (() => {
    // ============================================================
    // VARIÁVEIS PRIVADAS
    // ============================================================
    
    let usuarioPerfil = '';
    let usuarioNome = '';
    let usuarioPodeABR = false;
    
    // ============================================================
    // FUNÇÕES PRIVADAS
    // ============================================================
    
    function obterDadosUsuario() {
        usuarioPerfil = window.usuarioPerfil || '';
        usuarioNome = window.usuarioNome || '';
        
        console.log('👤 Dados do usuário obtidos:', {
            perfil: usuarioPerfil,
            nome: usuarioNome
        });
    }
    
    function verificarPermissaoABR() {
        const isAdmin = usuarioPerfil === 'administrador' || 
                        usuarioPerfil === 'admin' || 
                        usuarioPerfil === 'Administrador';
        
        usuarioPodeABR = isAdmin;
        
        console.log('👑 É administrador?', isAdmin);
        console.log('📋 Pode ver ABR?', usuarioPodeABR);
        
        // ⭐ Chama a função privada de atualização
        atualizarCheckboxABR();
    }
    
    function atualizarCheckboxABR() {
        const checkboxContainer = document.getElementById('checkbox-abr-container');
        const checkboxIncluirAbr = document.getElementById('incluir_abr');
        const tipoRelatorio = document.getElementById('tipo_relatorio')?.value || '';
        
        if (!checkboxContainer) return;
        
        if (usuarioPodeABR && tipoRelatorio === 'parecer') {
            checkboxContainer.style.display = 'block';
        } else {
            checkboxContainer.style.display = 'none';
            if (checkboxIncluirAbr) {
                checkboxIncluirAbr.checked = false;
            }
        }
    }
    
    function configurarEventos() {
        const tipoRelatorio = document.getElementById('tipo_relatorio');
        if (tipoRelatorio) {
            tipoRelatorio.addEventListener('change', () => {
                atualizarCheckboxABR();
            });
        }
    }
    
    // ============================================================
    // FUNÇÕES PÚBLICAS
    // ============================================================
    
    function init() {
        console.log('🔐 Inicializando PermissoesModule...');
        
        obterDadosUsuario();
        verificarPermissaoABR();
        configurarEventos();
        
        console.log('✅ PermissoesModule inicializado');
    }
    
    function podeVerABR() {
        return usuarioPodeABR;
    }
    
    function atualizarVisibilidadeABR() {
        atualizarCheckboxABR();
    }
    
    function getUsuarioPerfil() {
        return usuarioPerfil;
    }
    
    function getUsuarioNome() {
        return usuarioNome;
    }
    
    return {
        init: init,
        podeVerABR: podeVerABR,
        atualizarVisibilidadeABR: atualizarVisibilidadeABR,
        getUsuarioPerfil: getUsuarioPerfil,
        getUsuarioNome: getUsuarioNome
    };
})();