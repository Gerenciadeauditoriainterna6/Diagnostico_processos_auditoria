# routes/__init__.py
from flask import Blueprint

# ⭐ CRIA TODOS OS BLUEPRINTS
conclusao_bp = Blueprint('conclusao', __name__, url_prefix='/api')
plano_acao_bp = Blueprint('plano_acao', __name__, url_prefix='/api')
analise_bp = Blueprint('analise', __name__, url_prefix='/api')  

# ⭐ IMPORTA TODAS AS ROTAS
from . import conclusao_routes
from . import plano_acao_routes
from . import analise_routes  

def register_blueprints(app):
    print("🔵 Registrando blueprints...")
    app.register_blueprint(conclusao_bp)
    app.register_blueprint(plano_acao_bp)
    app.register_blueprint(analise_bp)  
    print("✅ Blueprints registrados!")