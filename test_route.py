# test_route.py
from routes import register_blueprints
from flask import Flask

app = Flask(__name__)

register_blueprints(app)

# Listar todas as rotas registradas
print("=" * 50)
print("📋 ROTAS REGISTRADAS:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.endpoint}: {rule.methods} {rule.rule}")
print("=" * 50)