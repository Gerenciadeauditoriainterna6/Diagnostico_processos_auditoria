import os
from reportlab.lib.units import cm
from PIL import Image as PILImage
import io
from reportlab.lib.utils import ImageReader
from pathlib import Path

from pathlib import Path
import os

# Simular
root_dir = Path("C:/Users/Audi-02/OneDrive - Universidade de Vassouras (1)/Auditoria Interna FUSVE/PROJETO AUTOMACAO PYTHON/GERADOR DE DADOS/utils/relatorios/logos.py").parent.parent.parent
print(f"Root dir: {root_dir}")

logo1 = os.path.join(root_dir, "static", "assets", "logo_fusve.png")
logo2 = os.path.join(root_dir, "static", "assets", "logo_auditoria-removebg-preview.png")
logo3 = os.path.join(root_dir, "static", "assets", "logo_iia.png")

# ====== FUNÇÃO PARA DESENHAR OS LOGOS ======
def desenhar_logos(canvas, pagesize, root_dir=None):
    """Desenha os três logos no cabeçalho do relatório"""
    if root_dir is None:
        root_dir = Path(__file__).parent.parent.parent
    
    logo1_path = os.path.join(root_dir, "static", "assets", "logo_fusve.png")
    logo2_path = os.path.join(root_dir, "static", "assets", "logo_auditoria-removebg-preview.png")
    logo3_path = os.path.join(root_dir, "static", "assets", "logo_iia.png")
    
    y_logo = 0.8 * cm
    altura_max_logo = 5 * cm
    
    def desenhar_png(caminho, x, y, largura_max, altura_max):
        if not os.path.exists(caminho):
            return False
        try:
            pil_img = PILImage.open(caminho)
            if pil_img.mode != 'RGBA':
                pil_img = pil_img.convert('RGBA')
            img_width, img_height = pil_img.size
            proporcao = img_width / img_height
            largura = min(largura_max, 5*cm)
            altura = largura / proporcao
            if altura > altura_max:
                altura = altura_max
                largura = altura * proporcao
            buffer_temp = io.BytesIO()
            pil_img.save(buffer_temp, format='PNG')
            buffer_temp.seek(0)
            img = ImageReader(buffer_temp)
            canvas.drawImage(img, x - largura/2, y - altura/2, 
                           width=largura, height=altura, mask='auto', 
                           preserveAspectRatio=True)
            return True
        except Exception as e:
            print(f"Erro ao desenhar logo {caminho}: {e}")
            return False
    
    espacamento = pagesize[0] / 4
    x1 = espacamento
    x2 = pagesize[0] / 2
    x3 = pagesize[0] - espacamento
    
    desenhar_png(logo1_path, x2, y_logo, 2.5*cm, altura_max_logo)
    desenhar_png(logo2_path, x1, y_logo, 3.5*cm, 3.5*cm)
    desenhar_png(logo3_path, x3, y_logo, 3*cm, 3*cm)