// ============================================================
// utils.js - FUNÇÕES UTILITÁRIAS GLOBAIS
// ============================================================

/**
 * Escapa HTML para evitar XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Converte arquivo para Base64
 */
function converterParaBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

/**
 * Retorna ícone Font Awesome baseado na extensão do arquivo
 */
function getIconeArquivo(nome) {
    const ext = (nome || '').split('.').pop()?.toLowerCase();
    const icones = {
        'pdf': 'fa-file-pdf',
        'doc': 'fa-file-word', 'docx': 'fa-file-word',
        'xls': 'fa-file-excel', 'xlsx': 'fa-file-excel',
        'jpg': 'fa-file-image', 'jpeg': 'fa-file-image',
        'png': 'fa-file-image', 'gif': 'fa-file-image',
        'txt': 'fa-file-alt',
        'zip': 'fa-file-archive', 'rar': 'fa-file-archive',
        'ppt': 'fa-file-powerpoint', 'pptx': 'fa-file-powerpoint'
    };
    return icones[ext] || 'fa-file';
}

/**
 * Formata bytes para exibição (KB, MB)
 */
function formatarTamanho(bytes) {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Limita o tamanho do texto
 */
function limitarTexto(texto, limite = 300) {
    if (!texto || texto.trim() === '') return '-';
    if (texto.length <= limite) return escapeHtml(texto);
    
    const textoTruncado = escapeHtml(texto.substring(0, limite)) + '...';
    const textoCompleto = escapeHtml(texto);
    const idUnico = 'texto-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    
    return `
        <span id="${idUnico}-resumo">${textoTruncado}</span>
        <span id="${idUnico}-completo" style="display: none;">${textoCompleto}</span>
        <button onclick="toggleTextoCompleto('${idUnico}')" 
                style="background: none; border: none; color: #0b5b99; cursor: pointer; font-size: 12px; padding: 0; margin-left: 5px; text-decoration: underline;">
            <span id="${idUnico}-btn">Ver mais</span>
        </button>
    `;
}

window.toggleTextoCompleto = function(id) {
    const resumo = document.getElementById(id + '-resumo');
    const completo = document.getElementById(id + '-completo');
    const btn = document.getElementById(id + '-btn');
    
    if (resumo && completo && btn) {
        if (resumo.style.display === 'none') {
            resumo.style.display = 'inline';
            completo.style.display = 'none';
            btn.textContent = 'Ver mais';
        } else {
            resumo.style.display = 'none';
            completo.style.display = 'inline';
            btn.textContent = 'Ver menos';
        }
    }
};

/**
 * Formata data ISO (YYYY-MM-DD) para formato brasileiro (DD/MM/YYYY)
 * @param {string} data - Data no formato ISO
 * @returns {string} Data formatada
 */
function formatarDataBR(data) {
    if (!data) return '-';
    const partes = data.split('-');
    if (partes.length === 3) {
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }
    // Se já estiver em outro formato, tenta converter
    const d = new Date(data);
    if (isNaN(d.getTime())) return data;
    return d.toLocaleDateString('pt-BR');
}

function spinnerHTML(mensagem = 'Carregando...') {
    return `
        <div style="text-align: center; padding: 20px;">
            <div class="dot-spinner">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <p style="margin-top: 15px; color: #666; font-size: 12px;">${mensagem}</p>
        </div>
    `;
}