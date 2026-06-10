# converter_senhas.py
from database import engine
from sqlalchemy import text
from werkzeug.security import generate_password_hash

def converter_senhas():
    with engine.connect() as conn:
        # Busca usuários com senha em texto puro (não hash)
        query = text("SELECT id, login, senha FROM usuarios WHERE senha NOT LIKE '$%'")
        usuarios = conn.execute(query).fetchall()
        
        if not usuarios:
            print("✅ Nenhum usuário precisa ser convertido!")
            return
        
        for user in usuarios:
            user_id = user[0]
            user_login = user[1]
            senha_antiga = user[2]
            
            # Gera o hash da senha antiga
            nova_hash = generate_password_hash(senha_antiga)
            
            # Atualiza no banco
            update = text("UPDATE usuarios SET senha = :hash WHERE id = :id")
            conn.execute(update, {'hash': nova_hash, 'id': user_id})
            print(f"✅ Usuário {user_login} convertido")
        
        conn.commit()
        print(f"🎉 {len(usuarios)} usuários convertidos com sucesso!")

if __name__ == "__main__":
    converter_senhas()