# routes/__init__.py
from flask import Blueprint

# ⭐ CRIAR O BLUEPRINT PRIMEIRO
conclusao_bp = Blueprint('conclusao', __name__)

# ⭐ DEPOIS importar as rotas (que vão usar o blueprint)
from . import conclusao_routes  

def register_blueprints(app):
    app.register_blueprint(conclusao_bp, url_prefix='/api')
    