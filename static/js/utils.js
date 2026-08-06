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