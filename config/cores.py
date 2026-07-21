CORES = {
    # ====== CORES PRINCIPAIS ======
    'primary_dark': '#184145',
    'primary_blue': '#0b5b99',
    
    # ====== VARIAÇÕES ======
    'primary_light': '#2a6b6f',
    'primary_lighter': '#3d8f94',
    'primary_lightest': '#83c3c0',
    
    'blue_light': '#1a7fc4',
    'blue_lighter': '#4a9fd4',
    'blue_lightest': '#d4e8f5',
        
    # ====== CORES DE FUNDO ======
    'bg_page': '#f8f9fa',
    'bg_card': '#ffffff',
    'bg_hover': '#e8f4f8',
    
    # ====== CORES DE TEXTO ======
    'text_primary': '#184145',
    'text_secondary': '#0b5b99',
    'text_muted': '#6c757d',
    'text_light': '#ffffff',
    
    # ====== BORDAS E SOMBRAS ======
    'border_color': '#e0e0e0',
    'shadow_card': '0 2px 12px rgba(0, 0, 0, 0.06)',
    'shadow_hover': '0 8px 28px rgba(0, 0, 0, 0.10)',
    
    # ====== GRADIENTES ======
    'gradient_header': 'linear-gradient(135deg, #184145 40%, #0b5b99 100%)',
    'gradient_card_hover': 'linear-gradient(135deg, #e8f4f8, #d4e8f5)',
    'gradient_progress': 'linear-gradient(90deg, #184145, #0b5b99)',

    # ====================================
    # ====== DASHBOARD ===================
    # ====================================

    # ====== CORES DE STATUS SITUAÇÃO DAS AUDITORIAS ======
    'status_eficacia_validada': '#ffc107',
    'status_execucao': '#17a2b8',
    'status_concluido': '#28a745',
    'status_inconclusivo': '#dc3545',
    'status_followup': '#fd7e14',
}



# Também disponibiliza como variáveis de ambiente (opcional)
CORES_ENV = {k.upper(): v for k, v in CORES.items()}