# routes/followups/__init__.py

from flask import Blueprint

# Criar o Blueprint
followups_bp = Blueprint('followups', __name__, url_prefix='/followups')

# Importar as rotas depois de criar o Blueprint
from . import routes, api