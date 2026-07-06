"""
Arquivo principal para aplicação Flask
Sistema de Auditoria Interna - FUSVE
"""

import os
from datetime import datetime, timedelta, date
import json
import io
from supabase import create_client

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file, flash
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from database import (
    engine, 
    SessionLocal,
    Checklist,
    ChecklistResposta,
    ChecklistEvidencia,
    criar_tabelas
)


from logic import (validar_login_no_banco, gerar_relatorio_gerencial_area, gerar_relatorio_parecer_auditoria, listar_areas,
                   listar_funcionarios_area, gerar_validacao_relatorio_detalhamento, gerar_validacao_relatorio_panorama)

# ============================================================
# CARREGAR CONFIGURAÇÕES
# ============================================================

# Carrega .env apenas em desenvolvimento (local)
# No Render, as variáveis já estão no ambiente
if not os.environ.get('RENDER'):
    load_dotenv()

# ============================================================
# IMPORTAR FUNÇÕES AUXILIARES
# ============================================================

from logic import validar_login_no_banco, gerar_relatorio_gerencial_area

# ============================================================
# FUNÇÕES DE UTILIDADE
# ============================================================

def upload_evidencia_storage(analise_id, evidencia_base64, evidencia_nome, bucket_name=None):
    """Salva evidência no bucket privado do Supabase Storage"""
    import base64
    import uuid
    from datetime import datetime
    
    if not evidencia_base64 or not evidencia_nome:
        return None
    
    try:
        # Remover prefixo do base64
        if ',' in evidencia_base64:
            evidencia_base64 = evidencia_base64.split(',')[1]
        
        # Decodificar base64
        try:
            file_bytes = base64.b64decode(evidencia_base64)
        except Exception as e:
            print(f"❌ Erro ao decodificar base64: {e}")
            return None
        
        # Gerar nome único para o arquivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        storage_filename = f"analises_auditor/{analise_id}/evidencia_{analise_id}_{unique_id}.pdf"
        
        # ⭐ USAR O SINGLETON - UMA ÚNICA CONEXÃO!
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket = bucket_name or "evidencia_analises_auditor"
        
        print(f"📎 Upload: bucket={bucket}, path={storage_filename}")
        
        # Upload
        response = supabase.storage.from_(bucket).upload(
            storage_filename,
            file_bytes,
            file_options={"content-type": "application/pdf"}
        )
        
        if response:
            # Gerar URL assinada (válida por 1 ano)
            signed_url = supabase.storage.from_(bucket).create_signed_url(
                storage_filename, 31536000
            )
            return signed_url.get('signedURL') if signed_url else None
        
        return None
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return None

def upload_evidencia_checklist(checklist_id, pergunta_ordem, evidencia_base64, evidencia_nome, bucket_name=None):
    """Salva evidência do checklist no bucket privado do Supabase Storage"""
    import base64
    import uuid
    from datetime import datetime
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if not evidencia_base64 or not evidencia_nome:
        print("❌ Evidência ou nome vazio")
        return None
    
    try:
        # Remover prefixo
        if ',' in evidencia_base64:
            evidencia_base64 = evidencia_base64.split(',')[1]
        
        # Decodificar base64
        try:
            file_bytes = base64.b64decode(evidencia_base64)
        except Exception as e:
            print(f"❌ Erro ao decodificar base64: {e}")
            return None
        
        # Gerar nome único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        storage_filename = f"checklists/{checklist_id}/pergunta_{pergunta_ordem}/{timestamp}_{unique_id}_{evidencia_nome}"
        
        # SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()

        bucket = bucket_name or "matriz_eficacia"
        
        print(f"📎 Upload: bucket={bucket}, path={storage_filename}")
        
        # Upload
        response = supabase.storage.from_(bucket).upload(
            storage_filename,
            file_bytes,
            file_options={"content-type": "application/pdf"}
        )
        
        if response:
            print("✅ Upload realizado com sucesso!")
            # ⭐ RETORNAR O CAMINHO (NÃO A URL ASSINADA)
            return storage_filename  # ← IMPORTANTE: retornar o caminho, não a URL
        
        print("❌ Upload falhou")
        return None
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return None


def remover_evidencia_checklist(caminho_arquivo, bucket_name=None):
    """Remove uma evidência do bucket"""
    if not caminho_arquivo:
        return False
    
    try:
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket = bucket_name or "matriz_eficacia"
        
        # Remover o arquivo
        response = supabase.storage.from_(bucket).remove([caminho_arquivo])
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao remover evidência: {e}")
        return False


def baixar_evidencia_checklist(caminho_arquivo, bucket_name=None):
    """Baixa uma evidência do bucket"""
    if not caminho_arquivo:
        return None
    
    try:
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket = bucket_name or "matriz_eficacia"
        
        # Baixar o arquivo
        response = supabase.storage.from_(bucket).download(caminho_arquivo)
        
        return response
        
    except Exception as e:
        print(f"❌ Erro ao baixar evidência: {e}")
        return None

def excluir_arquivo_storage(arquivo_url, bucket_name=None):
    """
    Exclui um arquivo do Supabase Storage a partir da URL
    """
    from urllib.parse import urlparse, unquote
    
    if not arquivo_url or arquivo_url.strip() == '':
        print("⚠️ URL vazia, nada para excluir")
        return True
    
    print(f"📎 Excluindo arquivo: {arquivo_url}")
    
    try:
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        # Extrair o caminho do arquivo da URL
        parsed_url = urlparse(arquivo_url)
        path = unquote(parsed_url.path)
        
        # 🔥 Extrair o caminho após "detalhamento_etapas"
        if 'detalhamento_etapas' in path:
            parts = path.split('detalhamento_etapas/')
            if len(parts) == 2:
                file_path = parts[1]
                # Remover parâmetros de consulta (token, etc)
                file_path = file_path.split('?')[0]
                
                bucket_name = "detalhamento_etapas"
                
                print(f"📎 Bucket: {bucket_name}")
                print(f"📎 File path: {file_path}")
                
                # Excluir do storage
                response = supabase.storage.from_(bucket_name).remove([file_path])
                
                print(f"📎 Resposta da exclusão: {response}")
                return True
            else:
                print(f"❌ Formato de URL inesperado: {path}")
                return False
        else:
            print(f"❌ 'detalhamento_etapas' não encontrado na URL: {path}")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao excluir arquivo do storage: {e}")
        import traceback
        traceback.print_exc()
        return False


def upload_para_bucket_detalhamento(arquivo, nome_unico, tipo, etapa_id):
    """
    Salva arquivo no bucket detalhamento_etapas do Supabase Storage
    """
    import uuid
    from datetime import datetime
    
    if not arquivo:
        return None
    
    try:
        # Ler o arquivo (se for um objeto File/Stream)
        if hasattr(arquivo, 'read'):
            file_bytes = arquivo.read()
        else:
            # Se for caminho ou bytes
            file_bytes = arquivo if isinstance(arquivo, bytes) else open(arquivo, 'rb').read()
        
        # Nome do arquivo no storage
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        
        # Organizar por pastas
        if tipo == 'obrigacao':
            pasta = 'obrigacoes'
        elif tipo == 'manual':
            pasta = 'manuais'
        else:
            pasta = 'outros'
        
        # Caminho: detalhamento_etapas/{pasta}/{etapa_id}/{timestamp}_{unique_id}_{nome_original}
        storage_filename = f"{pasta}/{etapa_id}/{timestamp}_{unique_id}.pdf"
        
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket_name = "detalhamento_etapas"
        
        print(f"📎 Upload para bucket: {bucket_name}, path: {storage_filename}")
        
        # Upload para o bucket
        response = supabase.storage.from_(bucket_name).upload(
            storage_filename,
            file_bytes,
            file_options={"content-type": "application/pdf"}
        )
        
        if response:
            # Gerar URL assinada (válida por 1 ano = 31536000 segundos)
            signed_url = supabase.storage.from_(bucket_name).create_signed_url(
                storage_filename, 31536000
            )
            
            if signed_url and signed_url.get('signedURL'):
                print(f"✅ Upload concluído: {signed_url['signedURL']}")
                return signed_url['signedURL']
            
            # Fallback: tentar URL pública
            public_url = supabase.storage.from_(bucket_name).get_public_url(storage_filename)
            if public_url:
                print(f"✅ Upload concluído (público): {public_url}")
                return public_url
        
        return None
        
    except Exception as e:
        print(f"❌ Erro no upload para bucket detalhamento_etapas: {e}")
        import traceback
        traceback.print_exc()
        return None

def atualizar_obrigacao_com_arquivo(etapa_id, indice_obrigacao, arquivo_url, arquivo_nome, arquivo_tamanho):
    """
    Atualiza a obrigação com a URL do arquivo
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            # Buscar as obrigações atuais
            query = text("""
                SELECT obrigacoes_regulatorias 
                FROM etapas_processo 
                WHERE id = :etapa_id
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result or not result[0]:
                print(f"❌ Nenhuma obrigação encontrada para etapa {etapa_id}")
                return False
            
            # Parsear o JSON
            try:
                obrigacoes = json.loads(result[0])
            except json.JSONDecodeError as e:
                print(f"❌ Erro ao parsear JSON: {e}")
                return False
            
            # Verificar se o índice existe
            if indice_obrigacao >= len(obrigacoes):
                print(f"❌ Índice {indice_obrigacao} não encontrado (total: {len(obrigacoes)})")
                return False
            
            # Atualizar o arquivo na obrigação
            obrigacoes[indice_obrigacao]['arquivo_url'] = arquivo_url
            obrigacoes[indice_obrigacao]['arquivo_nome'] = arquivo_nome
            obrigacoes[indice_obrigacao]['arquivo_tamanho'] = arquivo_tamanho
            
            # Salvar de volta
            update_query = text("""
                UPDATE etapas_processo 
                SET obrigacoes_regulatorias = :obrigacoes::text
                WHERE id = :etapa_id
            """)
            
            conn.execute(update_query, {
                'obrigacoes': json.dumps(obrigacoes, ensure_ascii=False),
                'etapa_id': etapa_id
            })
            conn.commit()
            
            print(f"✅ Obrigação {indice_obrigacao} atualizada com arquivo: {arquivo_nome}")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao atualizar obrigação: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def baixar_arquivo_obrigacao(etapa_id, indice_obrigacao):
    """
    Retorna a URL assinada do arquivo da obrigação
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            # Buscar as obrigações
            query = text("""
                SELECT obrigacoes_regulatorias 
                FROM etapas_processo 
                WHERE id = :etapa_id
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result or not result[0]:
                return None
            
            obrigacoes = json.loads(result[0])
            
            if indice_obrigacao >= len(obrigacoes):
                return None
            
            obrigacao = obrigacoes[indice_obrigacao]
            arquivo_url = obrigacao.get('arquivo_url', '')
            
            if not arquivo_url:
                return None
            
            # Retornar a URL assinada (já está na obrigação)
            return arquivo_url
            
    except Exception as e:
        print(f"❌ Erro ao buscar arquivo: {e}")
        return None

def calcular_tempo(data_inicio):
    """Calcula tempo decorrido desde a data de início até hoje"""
    if not data_inicio:
        return "Não informado"
    
    if isinstance(data_inicio, str):
        try:
            data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        except:
            return "Data inválida"
    
    hoje = date.today()
    anos = hoje.year - data_inicio.year
    meses = hoje.month - data_inicio.month
    
    if meses < 0:
        anos -= 1
        meses += 12
    
    if anos == 0 and meses == 0:
        return "Menos de 1 mês"
    elif anos == 0:
        return f"{meses} {'mês' if meses == 1 else 'meses'}"
    elif meses == 0:
        return f"{anos} {'ano' if anos == 1 else 'anos'}"
    else:
        return f"{anos} {'ano' if anos == 1 else 'anos'} e {meses} {'mês' if meses == 1 else 'meses'}"

# ============================================================
# CRIAÇÃO DA APLICAÇÃO FLASK
# ============================================================

app = Flask(__name__, static_folder='static')

# Configurações da sessão
app.secret_key = os.getenv('SECRET_KEY', 'chave-padrao-em-producao-mude')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=int(os.getenv('SESSION_TIMEOUT_SECONDS', 1800)))
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ============================================================
# MIDDLEWARE PARA AUDITORIA
# ============================================================

from flask import request, g
from database import engine
from sqlalchemy import text

@app.before_request
def configurar_auditoria():
    """
    Configura variáveis no PostgreSQL para auditoria
    """
    
    # Só configura se o usuário estiver autenticado
    if not session.get('autenticado'):
        return
    
    # Pega os dados do usuário da sessão
    usuario_id = session.get('usuario_id')
    usuario_nome = session.get('usuario_nome')
    
    # Se não tiver, usa padrão
    if not usuario_id:
        usuario_id = 0
    if not usuario_nome:
        usuario_nome = 'Sistema'
    
    # Pega o IP real do cliente
    ip_origem = request.headers.get('X-Forwarded-For')
    if ip_origem:
        ip_origem = ip_origem.split(',')[0].strip()
    else:
        ip_origem = request.remote_addr or '127.0.0.1'
    
    # Guarda na sessão do Flask
    g.usuario_id = usuario_id
    g.usuario_nome = usuario_nome
    g.ip_origem = ip_origem
    
    # ✅ NOVA ABORDAGEM: Chama a função PostgreSQL
    try:
        with engine.connect() as conn:
            conn.execute(
                text("SELECT set_app_user(:uid, :uname, :ip)"),
                {'uid': usuario_id, 'uname': usuario_nome, 'ip': ip_origem}
            )
            conn.commit()
            print(f"✅ [AUDITORIA] Usuário configurado: {usuario_id} - {usuario_nome} - {ip_origem}")
    except Exception as e:
        print(f"⚠️ [AUDITORIA] Erro: {e}")

@app.route('/api/verificar-perfil')
def verificar_perfil():
    """Endpoint para verificar o perfil do usuário atual"""
    try:
        if 'usuario_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        perfil = session.get('usuario_perfil', 'usuario')
        return jsonify({'perfil': perfil})
    except Exception as e:
        return jsonify({'error': str(e)}), 50

@app.route('/api/obrigacao/upload', methods=['POST'])
def api_upload_obrigacao():
    """Faz upload do arquivo de uma obrigação regulatória"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    etapa_id = data.get('etapa_id')
    indice = data.get('indice')
    arquivo_base64 = data.get('arquivo_base64')
    nome_arquivo = data.get('nome_arquivo')
    
    # Validações
    if not etapa_id:
        return jsonify({'success': False, 'error': 'etapa_id é obrigatório'}), 400
    
    if indice is None:
        return jsonify({'success': False, 'error': 'indice é obrigatório'}), 400
    
    if not arquivo_base64:
        return jsonify({'success': False, 'error': 'arquivo_base64 é obrigatório'}), 400
    
    if not nome_arquivo:
        return jsonify({'success': False, 'error': 'nome_arquivo é obrigatório'}), 400
    
    # Validar tamanho (10MB)
    import base64
    try:
        # Calcular tamanho aproximado
        if ',' in arquivo_base64:
            arquivo_base64_clean = arquivo_base64.split(',')[1]
        else:
            arquivo_base64_clean = arquivo_base64
        
        tamanho_bytes = len(arquivo_base64_clean) * 3 / 4  # Aproximado
        if tamanho_bytes > 10 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'Arquivo muito grande. Máximo 10MB'}), 400
    except:
        pass
    
    try:
        from logic import upload_obrigacao_storage, atualizar_obrigacao_com_arquivo
        
        # Fazer upload
        arquivo_url = upload_obrigacao_storage(
            etapa_id, 
            indice, 
            arquivo_base64, 
            nome_arquivo
        )
        
        if not arquivo_url:
            return jsonify({'success': False, 'error': 'Erro ao fazer upload do arquivo'}), 500
        
        # Atualizar a obrigação com a URL
        sucesso = atualizar_obrigacao_com_arquivo(
            etapa_id, 
            indice, 
            arquivo_url, 
            nome_arquivo,
            int(tamanho_bytes) if 'tamanho_bytes' in locals() else 0
        )
        
        if not sucesso:
            return jsonify({'success': False, 'error': 'Erro ao atualizar obrigação'}), 500
        
        return jsonify({
            'success': True,
            'arquivo_url': arquivo_url,
            'arquivo_nome': nome_arquivo,
            'message': 'Arquivo anexado com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


def excluir_obrigacao_completa(etapa_id, indice_obrigacao, arquivo_url=None):
    """
    Exclui uma obrigação regulatória completa:
    - Remove do banco de dados
    - Remove o arquivo do storage (se existir)
    
    Args:
        etapa_id (int): ID da etapa
        indice_obrigacao (int): Índice da obrigação no array JSON
        arquivo_url (str, optional): URL do arquivo para excluir
    
    Returns:
        dict: Resultado da operação
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        print(f"🗑️ Excluindo obrigação {indice_obrigacao} da etapa {etapa_id}")
        
        with engine.connect() as conn:
            # Buscar a etapa atual
            query_busca = text("""
                SELECT obrigacoes_regulatorias FROM etapas_processo WHERE id = :etapa_id
            """)
            result = conn.execute(query_busca, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return {'success': False, 'error': 'Etapa não encontrada'}
            
            # Parse do JSON
            obrigacoes_str = result[0]
            if obrigacoes_str:
                obrigacoes = json.loads(obrigacoes_str)
            else:
                obrigacoes = []
            
            # Verificar se o índice existe
            if indice_obrigacao >= len(obrigacoes):
                return {'success': False, 'error': 'Obrigação não encontrada'}
            
            # Remover a obrigação do array
            obrigacao_removida = obrigacoes.pop(indice_obrigacao)
            
            # 🔥 Se tiver URL, excluir do storage
            url_para_excluir = None
            
            # Prioridade 1: URL passada como parâmetro
            if arquivo_url and arquivo_url.strip() != '':
                url_para_excluir = arquivo_url
            # Prioridade 2: URL da obrigação removida
            elif obrigacao_removida and obrigacao_removida.get('arquivo_url'):
                url_para_excluir = obrigacao_removida.get('arquivo_url')
            
            if url_para_excluir and url_para_excluir.strip() != '':
                print(f"📎 Excluindo arquivo do storage: {url_para_excluir}")
                excluir_arquivo_storage(url_para_excluir)
            else:
                print("ℹ️ Nenhum arquivo para excluir do storage")
            
            # Atualizar o campo no banco
            obrigacoes_json = json.dumps(obrigacoes, ensure_ascii=False)
            
            query_update = text("""
                UPDATE etapas_processo 
                SET obrigacoes_regulatorias = :obrigacoes, updated_at = NOW()
                WHERE id = :etapa_id
            """)
            conn.execute(query_update, {
                'obrigacoes': obrigacoes_json,
                'etapa_id': etapa_id
            })
            conn.commit()
            
            print(f"✅ Obrigação {indice_obrigacao} excluída com sucesso")
            
            return {
                'success': True,
                'message': 'Obrigação excluída com sucesso',
                'total_restantes': len(obrigacoes)
            }
            
    except Exception as e:
        print(f"❌ Erro ao excluir obrigação: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}


@app.route('/api/obrigacao/excluir', methods=['DELETE'])
def api_excluir_obrigacao():
    """
    Exclui uma obrigação regulatória da etapa
    Remove do banco de dados E do storage
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        data = request.json
        etapa_id = data.get('etapa_id')
        indice_obrigacao = data.get('indice')  # Índice da obrigação no array
        arquivo_url = data.get('arquivo_url')  # URL do arquivo para excluir do storage
        
        if not etapa_id:
            return jsonify({'success': False, 'error': 'ID da etapa é obrigatório'}), 400
        
        if indice_obrigacao is None:
            return jsonify({'success': False, 'error': 'Índice da obrigação é obrigatório'}), 400
        
        print(f"🗑️ Excluindo obrigação {indice_obrigacao} da etapa {etapa_id}")
        
        with engine.connect() as conn:
            # Buscar a etapa atual
            query_busca = text("""
                SELECT obrigacoes_regulatorias FROM etapas_processo WHERE id = :etapa_id
            """)
            result = conn.execute(query_busca, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
            
            # Parse do JSON
            obrigacoes_str = result[0]
            if obrigacoes_str:
                obrigacoes = json.loads(obrigacoes_str)
            else:
                obrigacoes = []
            
            # Verificar se o índice existe
            if indice_obrigacao >= len(obrigacoes):
                return jsonify({'success': False, 'error': 'Obrigação não encontrada'}), 404
            
            # 🔥 Remover a obrigação do array
            obrigacao_removida = obrigacoes.pop(indice_obrigacao)
            
            # 🔥 Se tiver URL, excluir do storage
            if arquivo_url and arquivo_url.strip() != '':
               
                print(f"📎 Excluindo arquivo do storage: {arquivo_url}")
                excluir_arquivo_storage(arquivo_url)
            elif obrigacao_removida and obrigacao_removida.get('arquivo_url'):
                # Se não veio a URL no payload, mas a obrigação tem URL
                url_para_excluir = obrigacao_removida.get('arquivo_url')
                if url_para_excluir and url_para_excluir.strip() != '':
                   
                    print(f"📎 Excluindo arquivo do storage: {url_para_excluir}")
                    excluir_arquivo_storage(url_para_excluir)
            
            # Atualizar o campo no banco
            obrigacoes_json = json.dumps(obrigacoes, ensure_ascii=False)
            
            query_update = text("""
                UPDATE etapas_processo 
                SET obrigacoes_regulatorias = :obrigacoes, updated_at = NOW()
                WHERE id = :etapa_id
            """)
            conn.execute(query_update, {
                'obrigacoes': obrigacoes_json,
                'etapa_id': etapa_id
            })
            conn.commit()
            
            print(f"✅ Obrigação {indice_obrigacao} excluída com sucesso")
            
            return jsonify({
                'success': True,
                'message': 'Obrigação excluída com sucesso',
                'total_restantes': len(obrigacoes)
            })
            
    except Exception as e:
        print(f"❌ Erro ao excluir obrigação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/obrigacao/remover-arquivo', methods=['POST'])
def api_obrigacao_remover_arquivo():
    """
    Remove apenas o arquivo de uma obrigação (mantém a obrigação)
    """
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        data = request.json
        etapa_id = data.get('etapa_id')
        indice_obrigacao = data.get('indice')
        arquivo_url = data.get('arquivo_url')
        
        if not etapa_id:
            return jsonify({'success': False, 'error': 'ID da etapa é obrigatório'}), 400
        
        if indice_obrigacao is None:
            return jsonify({'success': False, 'error': 'Índice da obrigação é obrigatório'}), 400
        
        print(f"🗑️ Removendo arquivo da obrigação {indice_obrigacao} da etapa {etapa_id}")
        print(f"📎 URL do arquivo: {arquivo_url}")
        
        with engine.connect() as conn:
            # Buscar a etapa atual
            query_busca = text("""
                SELECT obrigacoes_regulatorias FROM etapas_processo WHERE id = :etapa_id
            """)
            result = conn.execute(query_busca, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
            
            # Parse do JSON
            obrigacoes_str = result[0]
            if obrigacoes_str:
                obrigacoes = json.loads(obrigacoes_str)
            else:
                obrigacoes = []
            
            # Verificar se o índice existe
            if indice_obrigacao >= len(obrigacoes):
                return jsonify({'success': False, 'error': 'Obrigação não encontrada'}), 404
            
            # 🔥 Se tiver URL, excluir do storage
            if arquivo_url and arquivo_url.strip() != '':
           
                print(f"📎 Excluindo arquivo do storage: {arquivo_url}")
                excluir_arquivo_storage(arquivo_url)
            else:
                print("⚠️ Nenhuma URL fornecida para excluir")
                return jsonify({'success': False, 'error': 'URL do arquivo não fornecida'}), 400
            
            # 🔥 Limpar os campos de arquivo na obrigação
            obrigacoes[indice_obrigacao]['arquivo_url'] = ''
            obrigacoes[indice_obrigacao]['arquivo_nome'] = ''
            obrigacoes[indice_obrigacao]['arquivo_tamanho'] = 0
            
            # Atualizar o campo no banco
            obrigacoes_json = json.dumps(obrigacoes, ensure_ascii=False)
            
            query_update = text("""
                UPDATE etapas_processo 
                SET obrigacoes_regulatorias = :obrigacoes, updated_at = NOW()
                WHERE id = :etapa_id
            """)
            conn.execute(query_update, {
                'obrigacoes': obrigacoes_json,
                'etapa_id': etapa_id
            })
            conn.commit()
            
            print(f"✅ Arquivo removido com sucesso da obrigação {indice_obrigacao}")
            
            return jsonify({
                'success': True,
                'message': 'Arquivo removido com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao remover arquivo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# ROTAS PÚBLICAS (SEM AUTENTICAÇÃO)
# ============================================================

@app.route('/cadastro', methods=["GET", "POST"])
def cadastro():
    """Tela de cadastro de novos usuários"""
    if request.method == 'GET':
        return render_template('cadastro.html')

    # POST - processar cadastro
    data = request.json
    login = data.get('login')
    nome = data.get('nome')
    senha = data.get('senha')

    if not login or not nome or not senha:
        return jsonify({'success': False, 'error': 'Todos os campos são obrigatórios'}), 400
    
    from database import engine
    from sqlalchemy import text
    from werkzeug.security import generate_password_hash

    try:
        with engine.connect() as conn:
            # Verifica se email já existe
            check_query = text("SELECT id FROM usuarios WHERE login = :login")
            existing = conn.execute(check_query, {'login': login}).fetchone()

            if existing:
                return jsonify({'success': False, 'error': 'E-mail já cadastrado. Faça login ou recupere sua senha.'}), 400

            # Hash da senha
            senha_hash = generate_password_hash(senha)

            # Inserir novo usuário (ativo = false, perfil 'auditor', area = 'Gerência de Auditoria Interna')
            insert_query = text("""
                INSERT INTO usuarios (login, senha, nome, area, ativo, perfil)
                VALUES (:login, :senha, :nome, :area, :ativo, :perfil)
            """)

            conn.execute(insert_query, {
                'login': login,
                'senha': senha_hash,
                'nome': nome,
                'area': 'Gerência de Auditoria Interna',
                'ativo': False,
                'perfil': 'auditor'
            })
            conn.commit()

            return jsonify({'success': True, 'message': 'Cadastro realizado! Aguarde aprovação do administrador.'})
        
    except Exception as e:
        print(f"❌ Erro ao cadastrar usuário: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/login', methods=["GET", "POST"])
def login():
    if session.get('autenticado'):
        return redirect(url_for('home'))
    
    if request.method == 'GET':
        return render_template('login.html', mostrar_botao_esqueci=False)
    
    data = request.json
    usuario = data.get('usuario')
    senha = data.get('senha')
    
    resultado = validar_login_no_banco(usuario, senha)
    
    # Desempacota (agora pode ter 8 valores)
    if len(resultado) == 8:
        sucesso, usuario_id, usuario_nome, usuario_perfil, tentativas_restantes, bloqueado, minutos_restantes, precisa_trocar = resultado
    else:
        sucesso, usuario_id, usuario_nome, usuario_perfil, tentativas_restantes, bloqueado, minutos_restantes = resultado
        precisa_trocar = False
    
    if sucesso:
        if precisa_trocar:
            # Login com senha temporária - força troca
            session['trocar_senha'] = True
            session['usuario_id_temp'] = usuario_id
            session['usuario_nome_temp'] = usuario_nome
            return jsonify({'success': True, 'trocar_senha': True, 'redirect': url_for('trocar_senha')})
        
        # Login normal
        session['autenticado'] = True
        session['usuario_logado'] = usuario
        session['usuario_nome'] = usuario_nome
        session['usuario_id'] = usuario_id
        session['usuario_perfil'] = usuario_perfil
        session.permanent = True
        return jsonify({'success': True, 'redirect': url_for('home')})
    
    if bloqueado:
        return jsonify({
            'success': False, 
            'bloqueado': True, 
            'minutos': minutos_restantes,
            'error': f'Conta bloqueada por {minutos_restantes} minutos.'
        })
    
    if tentativas_restantes > 0:
        mostrar_esqueci = tentativas_restantes <= 1
        return jsonify({
            'success': False, 
            'tentativas_restantes': tentativas_restantes,
            'error': f'Usuário ou senha incorretos. Você tem mais {tentativas_restantes} tentativa(s).',
            'mostrar_esqueci': mostrar_esqueci
        })
    
    return jsonify({'success': False, 'error': 'Usuário ou senha incorretos'})

@app.route('/trocar-senha', methods=['GET', 'POST'])
def trocar_senha():
    """Página para forçar troca de senha"""
    if not session.get('trocar_senha'):
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('trocar_senha.html', nome=session.get('usuario_nome_temp', 'Usuário'))
    
    # POST - processar nova senha
    from database import engine
    from sqlalchemy import text
    from werkzeug.security import generate_password_hash
    
    data = request.json
    nova_senha = data.get('nova_senha')
    confirmar_senha = data.get('confirmar_senha')
    
    if not nova_senha or not confirmar_senha:
        return jsonify({'success': False, 'message': 'Preencha todos os campos'}), 400
    
    if nova_senha != confirmar_senha:
        return jsonify({'success': False, 'message': 'As senhas não coincidem'}), 400
    
    if len(nova_senha) < 6:
        return jsonify({'success': False, 'message': 'A senha deve ter no mínimo 6 caracteres'}), 400
    
    try:
        usuario_id = session.get('usuario_id_temp')
        nova_senha_hash = generate_password_hash(nova_senha)
        
        print(f"🔍 DEBUG - Usuário ID: {usuario_id}")
        
        with engine.connect() as conn:
            # Verificar estado ANTES
            before = conn.execute(text("SELECT solicitou_recuperacao, forcar_troca_senha, senha_temporaria FROM usuarios WHERE id = :id"), {'id': usuario_id}).fetchone()
            print(f"🔍 ANTES: solicitou_recuperacao={before[0]}, forcar_troca_senha={before[1]}, senha_temporaria={before[2]}")
            
            # ⭐ ATUALIZAR todos os campos de recuperação
            update = text("""
                UPDATE usuarios 
                SET senha = :senha, 
                    forcar_troca_senha = FALSE, 
                    senha_temporaria = NULL,
                    solicitou_recuperacao = FALSE,
                    tentativas_login = 0,
                    bloqueado_ate = NULL
                WHERE id = :id
            """)
            result = conn.execute(update, {
                'senha': nova_senha_hash, 
                'id': usuario_id
            })
            conn.commit()
            print(f"🔍 Linhas afetadas: {result.rowcount}")
            
            # Verificar estado DEPOIS
            after = conn.execute(text("SELECT solicitou_recuperacao, forcar_troca_senha, senha_temporaria FROM usuarios WHERE id = :id"), {'id': usuario_id}).fetchone()
            print(f"🔍 DEPOIS: solicitou_recuperacao={after[0]}, forcar_troca_senha={after[1]}, senha_temporaria={after[2]}")
        
        # Limpa sessão temporária
        session.pop('trocar_senha', None)
        session.pop('usuario_id_temp', None)
        session.pop('usuario_nome_temp', None)
        
        return jsonify({'success': True, 'message': 'Senha alterada com sucesso! Faça login.'})
        
    except Exception as e:
        print(f"Erro ao trocar senha: {e}")
        return jsonify({'success': False, 'message': 'Erro ao processar solicitação'}), 500

@app.route('/logout')
def logout():
    """Remove os dados da sessão e desloga o usuário"""
    session.clear()
    return redirect(url_for('login'))



@app.route('/admin/usuario/<int:usuario_id>/resetar-senha', methods=['POST'])
def admin_resetar_senha(usuario_id):
    # Verifica se é ADMIN
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'error': 'Acesso negado'}), 403
    
    from werkzeug.security import generate_password_hash
    
    senha_temp = f"temp{usuario_id}{datetime.now().strftime('%d%m')}"
    senha_hash = generate_password_hash(senha_temp)
    
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE usuarios 
            SET senha = :senha, 
                forcar_troca_senha = TRUE,
                senha_temporaria = :temp
            WHERE id = :id
        """), {'senha': senha_hash, 'temp': senha_temp, 'id': usuario_id})
        conn.commit()
    
    return jsonify({'success': True, 'senha_temporaria': senha_temp})

@app.route('/solicitar-recuperacao', methods=['POST'])
def solicitar_recuperacao():
    """Usuário solicita recuperação de senha"""
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'message': 'E-mail é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Verifica se email existe
            user = conn.execute(text("SELECT id FROM usuarios WHERE login = :email"), {'email': email}).fetchone()
            
            if not user:
                # Por segurança, não informamos que o email não existe
                return jsonify({'success': True, 'message': 'Solicitação enviada ao administrador.'})
            
            # Marca que o usuário solicitou recuperação
            conn.execute(text("""
                UPDATE usuarios 
                SET solicitou_recuperacao = TRUE 
                WHERE id = :id
            """), {'id': user[0]})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Solicitação enviada ao administrador.'})
            
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'success': False, 'message': 'Erro ao processar solicitação'}), 500

@app.route('/ping')
def ping():
    """Health check para o UptimeRobot"""
    return "OK", 200

# ============================================================
# ROTAS PRINCIPAIS (PÁGINAS)
# ============================================================

@app.route('/')
def index():
    """Redireciona para login ou home"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return redirect(url_for('home'))  # Agora redireciona para /home

@app.route('/home')
def home():
    """Redireciona para a home"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/plano-anual')
def plano_anual():
    """Página do Plano Anual de Auditoria"""
    from database import engine
    from sqlalchemy import text
    import os
    
    # Buscar anos disponíveis dos PDFs
    pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'pdfs', 'plano_anual')
    anos_disponiveis = []
    
    if os.path.exists(pdf_dir):
        for arquivo in os.listdir(pdf_dir):
            if arquivo.startswith('plano_anual_') and arquivo.endswith('.pdf'):
                try:
                    ano = arquivo.replace('plano_anual_', '').replace('.pdf', '')
                    if ano.isdigit():
                        anos_disponiveis.append(int(ano))
                except:
                    pass
    
    # Ordenar anos do mais recente para o mais antigo
    anos_disponiveis = sorted(set(anos_disponiveis), reverse=True)
    
    # Se não encontrou PDFs, buscar anos do banco de dados
    if not anos_disponiveis:
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT DISTINCT ano FROM auditorias ORDER BY ano DESC"))
                anos_disponiveis = [row[0] for row in result if row[0]]
        except:
            pass
    
    return render_template('plano_anual.html', anos_disponiveis=anos_disponiveis)

@app.route('/auditorias-emergenciais')
def auditorias_emergenciais():
    """Página de Auditorias Emergenciais"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id_area, nome_area 
                FROM informacoes_area 
                ORDER BY nome_area
            """))
            areas = {row.nome_area: row.id_area for row in result}
        
        return render_template('auditorias_emergenciais.html', areas=areas)
    except Exception as e:
        print(f"❌ Erro ao carregar página de auditorias emergenciais: {e}")
        return render_template('auditorias_emergenciais.html', areas={})

@app.route('/dashboard')
def dashboard():
    """Dashboard principal - apenas administradores podem acessar"""
    
    # 1. Verificar se o usuário está logado
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    # 2. Verifica se o usuário é administrador
    usuario_perfil = session.get('usuario_perfil')
    if usuario_perfil not in ['administrador', 'admin']:
        # Se não for admin, redireciona para home com mensagem de erro
        flash('Acesso negado. Apenas administradores podem visualizar o dashboard', 'error')
        return redirect(url_for('home'))
    
    # 3. Se for admin, mostra a página
    return render_template('dashboard.html')

@app.route('/auditorias')
def auditorias():
    """Página de cadastro de auditorias"""
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    # Verificar se é administrador (opcional)
    if session.get('usuario_perfil') not in ['administrador', 'admin', 'auditor']:
        flash('Acesso negado. Apenas administradores e auditores podem acessar.', 'error')
        return redirect(url_for('home'))
    
    return render_template('auditorias.html')

# ============================================================
# API - PLANO ANUNAL
# ============================================================

@app.route('/api/fundamentos-por-ano')
def api_fundamentos_por_ano():
    """Retorna todas as auditorias não emergenciais de um ano com seus fundamentos"""
    from database import engine
    from sqlalchemy import text
    import json
    
    ano = request.args.get('ano')
    if not ano:
        return jsonify({'success': False, 'error': 'Ano é obrigatório'}), 400
    
    try:
        query = text("""
            SELECT 
                a.id,
                a.codigo_auditoria,
                a.titulo,
                a.ano,
                a.trimestre,
                a.fundamentos,
                ar.nome_area as area_nome
            FROM auditorias a
            LEFT JOIN informacoes_area ar ON a.id_area = ar.id_area
            WHERE a.ano = :ano 
                AND (a.emergencial = false OR a.emergencial IS NULL)
            ORDER BY a.trimestre ASC, a.codigo_auditoria ASC
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"ano": ano})
            auditorias = []
            
            for row in result:
                aud = dict(row._mapping)
                
                # Parse dos fundamentos (se for string JSON)
                if aud.get('fundamentos'):
                    if isinstance(aud['fundamentos'], str):
                        try:
                            aud['fundamentos'] = json.loads(aud['fundamentos'])
                        except:
                            aud['fundamentos'] = []
                    elif not isinstance(aud['fundamentos'], list):
                        aud['fundamentos'] = []
                else:
                    aud['fundamentos'] = []
                
                auditorias.append(aud)
        
        return jsonify({
            'success': True,
            'auditorias': auditorias,
            'total': len(auditorias)
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar fundamentos por ano: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'auditorias': [],
            'total': 0
        }), 500

@app.route('/api/plano-anual-pdf')
def api_plano_anual_pdf():
    """Retorna o PDF do plano anual ou da auditoria emergencial"""
    import os
    from flask import send_file
    
    ano = request.args.get('ano')
    tipo = request.args.get('tipo', 'plano')
    
    # ====== AUDITORIAS EMERGENCIAIS ======
    if tipo == 'emergencial':
        codigo = request.args.get('codigo')
        if not codigo:
            return jsonify({'error': 'Código é obrigatório'}), 400
        
        # Buscar na pasta static/emergenciais/
        pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'emergenciais')
        arquivo_pdf = os.path.join(pdf_dir, f"{codigo}.pdf")
        
        # Se não encontrar, tentar buscar qualquer arquivo que comece com o código
        if not os.path.exists(arquivo_pdf) and os.path.exists(pdf_dir):
            for arquivo in os.listdir(pdf_dir):
                if arquivo.startswith(codigo) and arquivo.endswith('.pdf'):
                    arquivo_pdf = os.path.join(pdf_dir, arquivo)
                    break
        
        if os.path.exists(arquivo_pdf):
            return send_file(arquivo_pdf, as_attachment=True, download_name=os.path.basename(arquivo_pdf))
        else:
            return jsonify({'error': f'Arquivo PDF não encontrado para a auditoria {codigo}'}), 404
    
    # ====== PLANO ANUAL ======
    if not ano:
        return jsonify({'error': 'Ano é obrigatório'}), 400
    
    # ⭐ Buscar direto na pasta static (estrutura simplificada)
    pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'planejada')
    
    # Buscar arquivo plano_anual_{ano}.pdf
    arquivo_pdf = os.path.join(pdf_dir, f"plano_anual_{ano}.pdf")
    
    # Se não encontrar, tentar buscar qualquer arquivo que termine com o ano
    if not os.path.exists(arquivo_pdf):
        for arquivo in os.listdir(pdf_dir):
            if arquivo.endswith(f"_{ano}.pdf") or arquivo.endswith(f"-{ano}.pdf"):
                arquivo_pdf = os.path.join(pdf_dir, arquivo)
                break
    
    if os.path.exists(arquivo_pdf):
        return send_file(arquivo_pdf, as_attachment=True, download_name=os.path.basename(arquivo_pdf))
    else:
        return jsonify({'error': f'Arquivo PDF do Plano Anual para {ano} não encontrado'}), 404

@app.route('/api/auditoria/<int:auditoria_id>/fundamentos', methods=['GET'])
def api_buscar_fundamentos_auditoria(auditoria_id):
    """Busca a lista de fundamentos da auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT fundamentos
                FROM auditorias
                WHERE id = :auditoria_id
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            fundamentos_raw = result[0]
            
            # ⭐ LOG PARA DEBUG ⭐
            print(f"🔍 fundamentos_raw: {fundamentos_raw}")
            print(f"🔍 tipo: {type(fundamentos_raw)}")
            
            # ⭐ TRATAMENTO CORRETO ⭐
            if fundamentos_raw is None:
                fundamentos = []
            elif isinstance(fundamentos_raw, str):
                if fundamentos_raw == '':
                    fundamentos = []
                else:
                    try:
                        fundamentos = json.loads(fundamentos_raw)
                    except json.JSONDecodeError as e:
                        print(f"❌ Erro ao fazer parse do JSON: {e}")
                        fundamentos = []
            elif isinstance(fundamentos_raw, list):
                fundamentos = fundamentos_raw
            else:
                fundamentos = []
            
            print(f"🔍 fundamentos retornados: {fundamentos}")
            print(f"🔍 tipo retornado: {type(fundamentos)}")
            
            return jsonify({
                'success': True,
                'fundamentos': fundamentos
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar fundamentos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auditoria/<int:auditoria_id>/fundamentos', methods=['POST', 'PUT'])
def api_salvar_fundamentos_auditoria(auditoria_id):
    """Salva a lista de fundamentos da auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        dados = request.json
        fundamentos = dados.get('fundamentos', [])
        
        # Converter para JSON string
        if isinstance(fundamentos, (list, dict)):
            fundamentos_json = json.dumps(fundamentos)
        else:
            fundamentos_json = fundamentos
        
        with engine.connect() as conn:
            query = text("""
                UPDATE auditorias 
                SET fundamentos = :fundamentos,
                    updated_at = NOW()
                WHERE id = :auditoria_id
            """)
            
            result = conn.execute(query, {
                'fundamentos': fundamentos_json,
                'auditoria_id': auditoria_id
            })
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            return jsonify({'success': True})
            
    except Exception as e:
        print(f"❌ Erro ao salvar fundamentos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================================================
# FIM API PLANO ANUNAL
# ============================================================

@app.route('/diagnostico')
def diagnostico():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    
    return render_template('diagnostico.html', areas=areas, usuario_perfil=usuario_perfil)

@app.route('/detalhamento')
def detalhamento():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    
    return render_template('detalhamento.html', areas=areas, usuario_perfil=usuario_perfil)

@app.route('/visao-geral')
def visao_geral():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('visao_geral.html')

@app.route('/checklists')
def checklists():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('checklists.html')

@app.route('/relatorios')
def relatorios():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    return render_template('relatorios.html')

@app.route('/areas')
def areas():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    usuario_perfil = session.get('usuario_perfil', 'auditor')
    return render_template('areas.html', usuario_perfil=usuario_perfil)

@app.route('/log-alteracoes')
def log_alteracoes():
    """
    Página de visualização do histórico de alterações
    Apenas administradores podem acessar
    """

    # 1. Verificar se o usuário está logado
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    # 2. Verifica se o usuário é adminsitrador
    usuario_perfil = session.get('usuario_perfil')
    if usuario_perfil not in ['administrador', 'admin']:
        # Se nã for admin, redireciona para home com mensagem de erro
        # Usando o sistema de toast que já temos
        flash('Acesso negado. Apenas administradores podem visualizar o histórico de alterações', 'error')
        return redirect(url_for('home'))
    
    # 3. Se for admin, mostra a página
    return render_template('log_alteracoes.html')
    
    



@app.route('/api/processo/<int:processo_id>/etapas')
def api_processo_etapas(processo_id):
    """Retorna todas as etapas de um processo"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # ⭐ ADICIONAR manual_em_andamento NO SELECT
            query = text("""
                SELECT ep.id, ep.codigo_etapa, ep.nome_etapa, ep.descricao_etapa,
                    ep.como_e_feito, ep.objetivo_etapa, ep.status_etapa, ep.criticidade_etapa,
                    ep.politica_interna, ep.analise_critica, ep.sugestao_melhoria,
                    ep.necessidade_implantacao, ep.ganho_previsto, ep.obrigacoes_regulatorias,
                    ep.executores_etapa,
                    ep.manual_nome, ep.created_at, ep.auditoria_id,
                    -- ⭐ NOVO CAMPO
                    ep.manual_em_andamento,
                    EXISTS(
                        SELECT 1 FROM analises_criticas ac 
                        WHERE ac.etapa_id = ep.id AND ac.tipo = 'auditado'
                    ) as tem_analise_auditado,
                    EXISTS(
                        SELECT 1 FROM analises_criticas ac 
                        WHERE ac.etapa_id = ep.id AND ac.tipo = 'auditor'
                    ) as tem_analise_auditor
                FROM etapas_processo ep
                WHERE ep.processo_id = :processo_id
                ORDER BY ep.codigo_etapa
            """)
            
            result = conn.execute(query, {'processo_id': processo_id}).fetchall()

            etapas = []
            for row in result:
                etapas.append({
                    'id': row[0],
                    'codigo_etapa': row[1] or '',
                    'nome_etapa': row[2] or '',
                    'descricao_etapa': row[3] or '',
                    'como_e_feito': row[4] or '',
                    'objetivo_etapa': row[5] or '',
                    'status_etapa': row[6] or 'Ativa',
                    'criticidade_etapa': row[7] or 'Em aprovação',
                    'politica_interna': row[8] or '',
                    'analise_critica': row[9] or '',
                    'sugestao_melhoria': row[10] or '',
                    'necessidade_implantacao': row[11] or '',
                    'ganho_previsto': row[12] or '',
                    'obrigacoes_regulatorias': row[13] or '',
                    'executores_etapa': row[14] or '',
                    'manual_nome': row[15] or '',                    
                    'created_at': row[16].isoformat() if row[16] else '',
                    'auditoria_id': row[17] if len(row) > 17 else None,
                    # ⭐ NOVO CAMPO
                    'manual_em_andamento': row[18] if len(row) > 18 else False,
                    'tem_analise_auditado': row[19] if len(row) > 19 else False,
                    'tem_analise_auditor': row[20] if len(row) > 20 else False,
                })
            
            return jsonify({'success': True, 'etapas': etapas})
        
    except Exception as e:
        print(f"❌ Erro ao buscar etapas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/detalhamento_etapas')
def detalhamento_etapas():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    return render_template('detalhamento_etapas.html')

@app.route('/api/controle-etapa/salvar', methods=['POST'])
def api_controle_etapa_salvar():
    """Salva um novo controle de etapa ou atualiza existente"""
    from database import engine
    from sqlalchemy import text
    
    data = request.json
    controle_id = data.get('id')
    risco_id = data.get('risco_id')
    auditoria_id = data.get('auditoria_id')
    
    
    # Dados do controle
    nome_controle = data.get('nome_controle', '')
    como_executado = data.get('como_executado', '')
    objetivo_controle = data.get('objetivo_controle', '')
    periodicidade_execucao = data.get('periodicidade_execucao', '')
    natureza = data.get('natureza', '')
    forma_execucao = data.get('forma_execucao', '')
    status_controle = data.get('status_controle', '')
    evidencia_realizacao = data.get('evidencia_realizacao', '')
    responsaveis_tratamento = data.get('responsaveis_tratamento', '')
    risco_avaliacao = data.get('risco_avaliacao', '')
    causa_motivo = data.get('causa_motivo', '')
    frequencia_evidencia = data.get('frequencia_evidencia', '')
    local_evidencia = data.get('local_evidencia', '')
    lgpd = data.get('lgpd', '')
    
    # Validação básica
    if not risco_id:
        return jsonify({'success': False, 'error': 'ID do risco é obrigatório'}), 400
    
    if not nome_controle:
        return jsonify({'success': False, 'error': 'Nome do controle é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            if controle_id:
                # EDIÇÃO: atualizar controle existente
                query = text("""
                    UPDATE controles_etapa
                    SET nome_controle = :nome_controle,
                        como_executado = :como_executado,
                        objetivo_controle = :objetivo_controle,
                        periodicidade_execucao = :periodicidade_execucao,
                        natureza = :natureza,
                        forma_execucao = :forma_execucao,
                        status_controle = :status_controle,
                        evidencia_realizacao = :evidencia_realizacao,
                        local_evidencia = :local_evidencia,
                        lgpd = :lgpd,
                        responsaveis_tratamento = :responsaveis_tratamento,
                        risco_avaliacao = :risco_avaliacao,
                        causa_motivo = :causa_motivo,
                        frequencia_evidencia = :frequencia_evidencia,
                        updated_at = CURRENT_DATE
                    WHERE id = :controle_id
                """)
                
                conn.execute(query, {
                    'controle_id': controle_id,
                    'nome_controle': nome_controle,
                    'como_executado': como_executado,
                    'objetivo_controle': objetivo_controle,
                    'periodicidade_execucao': periodicidade_execucao,
                    'natureza': natureza,
                    'forma_execucao': forma_execucao,
                    'status_controle': status_controle,
                    'evidencia_realizacao': evidencia_realizacao,
                    'local_evidencia': local_evidencia,     
                    'lgpd': lgpd,                            
                    'frequencia_evidencia': frequencia_evidencia,
                    'responsaveis_tratamento': responsaveis_tratamento,
                    'risco_avaliacao': risco_avaliacao,
                    'causa_motivo': causa_motivo
                })
                
                print(f"✏️ Controle {controle_id} atualizado!")
                
            else:
                # NOVO CONTROLE: inserir
                query = text("""
                    INSERT INTO controles_etapa (
                        risco_id, auditoria_id, nome_controle,
                        como_executado, objetivo_controle,
                        periodicidade_execucao, natureza, forma_execucao,
                        status_controle, evidencia_realizacao,
                        responsaveis_tratamento, risco_avaliacao, causa_motivo,
                        local_evidencia, lgpd,
                        frequencia_evidencia, created_at, updated_at
                    ) VALUES (
                        :risco_id, :auditoria_id, :nome_controle,
                        :como_executado, :objetivo_controle,
                        :periodicidade_execucao, :natureza, :forma_execucao,
                        :status_controle, :evidencia_realizacao,
                        :responsaveis_tratamento, :risco_avaliacao, :causa_motivo,
                        :local_evidencia, :lgpd,
                        :frequencia_evidencia, CURRENT_TIMESTAMP, CURRENT_DATE
                    )
                    RETURNING id
                """)
                
                result = conn.execute(query, {
                    'risco_id': risco_id,
                    'auditoria_id': auditoria_id,
                    'nome_controle': nome_controle,
                    'como_executado': como_executado,
                    'objetivo_controle': objetivo_controle,
                    'periodicidade_execucao': periodicidade_execucao,
                    'natureza': natureza,
                    'forma_execucao': forma_execucao,
                    'status_controle': status_controle,
                    'evidencia_realizacao': evidencia_realizacao,
                    'responsaveis_tratamento': responsaveis_tratamento,
                    'local_evidencia': local_evidencia,
                    'lgpd': lgpd,
                    'risco_avaliacao': risco_avaliacao,
                    'causa_motivo': causa_motivo,
                    'frequencia_evidencia': frequencia_evidencia
                })
                
                novo_id = result.fetchone()[0]
                print(f"✅ Novo controle criado! ID: {novo_id}")
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Controle salvo com sucesso',
                'controle_id': controle_id or novo_id
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar controle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500   
    
@app.route('/api/controle-etapa/<int:controle_id>', methods=['DELETE'])
def api_controle_etapa_excluir(controle_id):
    """Remove um controle (soft delete)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Como sua tabela não tem coluna 'ativo', vamos deletar mesmo
            # Se quiser manter soft delete, teria que adicionar a coluna 'ativo'
            query = text("DELETE FROM controles_etapa WHERE id = :controle_id")
            conn.execute(query, {'controle_id': controle_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Controle excluído com sucesso'})
    except Exception as e:
        print(f"❌ Erro ao excluir controle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/controle-etapa/<int:controle_id>', methods=['GET'])
def api_controle_etapa_detalhes(controle_id):
    """Retorna os dados de um controle específico para edição"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, risco_id, nome_controle, como_executado, objetivo_controle,
                       periodicidade_execucao, natureza, forma_execucao, status_controle,
                       evidencia_realizacao, responsaveis_tratamento, risco_avaliacao, causa_motivo,
                       frequencia_evidencia, local_evidencia, lgpd
                FROM controles_etapa
                WHERE id = :controle_id
            """)
            
            result = conn.execute(query, {'controle_id': controle_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Controle não encontrado'}), 404
            
            controle = {
                'id': result[0],
                'risco_id': result[1],
                'nome_controle': result[2] or '',
                'como_executado': result[3] or '',
                'objetivo_controle': result[4] or '',
                'periodicidade_execucao': result[5] or '',
                'natureza': result[6] or '',
                'forma_execucao': result[7] or '',
                'status_controle': result[8] or '',
                'evidencia_realizacao': result[9] or '',
                'responsaveis_tratamento': result[10] or '',
                'risco_avaliacao': result[11] or '',
                'causa_motivo': result[12] or '',
                'frequencia_evidencia': result[13] or '',
                'local_evidencia': result[14] or '',
                'lgpd': result[15] or ''
            }
            
            return jsonify({'success': True, 'controle': controle})
            
    except Exception as e:
        print(f"❌ Erro ao buscar controle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================================================
# ROTAS DE API (BACKEND)
# ============================================================

@app.route('/api/auditorias-emergenciais')
def api_auditorias_emergenciais():
    """Retorna apenas as auditorias emergenciais"""
    from database import engine
    from sqlalchemy import text
    
    area_id = request.args.get('area_id')
    
    # Construir a query base
    query = text("""
        SELECT 
            a.id, 
            a.codigo_auditoria, 
            a.titulo, 
            a.trimestre, 
            a.ano, 
            a.status, 
            a.unidade,
            a.data_inicio,
            a.data_fim,
            a.emergencial,
            ar.nome_area as area_nome
        FROM auditorias a
        LEFT JOIN informacoes_area ar ON a.id_area = ar.id_area
        WHERE a.emergencial = true
    """)
    
    # Adicionar filtro por área se fornecido
    if area_id:
        query = text("""
            SELECT 
                a.id, 
                a.codigo_auditoria, 
                a.titulo, 
                a.trimestre, 
                a.ano, 
                a.status, 
                a.unidade,
                a.data_inicio,
                a.data_fim,
                a.emergencial,
                ar.nome_area as area_nome
            FROM auditorias a
            LEFT JOIN informacoes_area ar ON a.id_area = ar.id_area
            WHERE a.emergencial = true AND a.id_area = :area_id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"area_id": area_id})
            auditorias = [dict(row._mapping) for row in result]
    else:
        with engine.connect() as conn:
            result = conn.execute(query)
            auditorias = [dict(row._mapping) for row in result]
    
    return jsonify({
        'success': True,
        'auditorias': auditorias,
        'total': len(auditorias)
    })

@app.route('/api/auditoria-emergencial-pdf')
def api_auditoria_emergencial_pdf():
    """Retorna o PDF da auditoria emergencial"""
    import os
    from flask import send_file
    
    codigo = request.args.get('codigo')
    if not codigo:
        return jsonify({'error': 'Código da auditoria é obrigatório'}), 400
    
    # Caminho onde os PDFs das auditorias emergenciais estão armazenados
    pdf_dir = os.path.join(os.path.dirname(__file__), 'static', 'pdfs', 'emergenciais')
    
    # Buscar arquivo com o nome exato do código
    arquivo_pdf = os.path.join(pdf_dir, f"{codigo}.pdf")
    
    if os.path.exists(arquivo_pdf):
        return send_file(arquivo_pdf, as_attachment=True, download_name=f"{codigo}.pdf")
    else:
        return jsonify({'error': 'Arquivo PDF não encontrado'}), 404

@app.route('/api/auditorias-por-area')
def api_auditorias_por_area():
    """Retorna as auditorias de uma área"""
    from database import engine
    from sqlalchemy import text
    
    area_id = request.args.get('area_id')
    if not area_id:
        return jsonify({'error': 'area_id é obrigatório'}), 400
    
    query = text("""
        SELECT id, codigo_auditoria, titulo, trimestre, ano, status, unidade, emergencial
        FROM auditorias
        WHERE id_area = :area_id
        ORDER BY ano DESC, trimestre DESC
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {"area_id": area_id})
        auditorias = [dict(row._mapping) for row in result]
    
    return jsonify({'auditorias': auditorias})

@app.route('/api/auditoria/<int:auditoria_id>/responsavel')
def api_auditoria_responsavel(auditoria_id):
    """Verifica se o usuário logado é responsável pela auditoria ou é administrador"""
    from database import engine
    from sqlalchemy import text

    usuario_nome = session.get('usuario_nome')
    usuario_perfil = session.get('usuario_perfil')

    if not usuario_nome:
        return jsonify({'autorizado': False, 'error': 'Usuário não logado'}), 401
    
    # ADMINISTRADOR tem acesso total
    if usuario_perfil == 'administrador' or usuario_perfil == 'admin':
        return jsonify({
            'autorizado': True,
            'usuario': usuario_nome,
            'perfil': usuario_perfil,
            'motivo': 'Administrador tem acesso total'
        })
    
    query = text("""
        SELECT responsavel_equipe FROM auditorias WHERE id = :id
    """)

    with engine.connect() as conn:
        result = conn.execute(query, {'id': auditoria_id}).fetchone()

        if not result:
            return jsonify({'autorizado': False, 'error': 'Auditoria não encontrada'}), 404
        
        responsaveis = result[0] or []

        autorizado = usuario_nome in responsaveis if responsaveis else False

        return jsonify({
            'autorizado': autorizado,
            'usuario': usuario_nome,
            'perfil': usuario_perfil,
            'responsaveis': responsaveis
        })

@app.route('/api/auditoria/<int:auditoria_id>/upload-evidencia', methods=['POST'])
def api_upload_evidencia(auditoria_id):
    """Faz upload de uma evidência para o Supabase Storage"""
    import os
    from datetime import datetime
    import json
    
    try:
        # Verificar se o arquivo foi enviado
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'success': False, 'error': 'Nome do arquivo vazio'}), 400
        
        # Buscar código da auditoria
        from database import engine
        from sqlalchemy import text
        
        query = text("SELECT codigo_auditoria FROM auditorias WHERE id = :auditoria_id")
        with engine.connect() as conn:
            result = conn.execute(query, {"auditoria_id": auditoria_id})
            row = result.fetchone()
            if not row:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            codigo_auditoria = row.codigo_auditoria
        
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        # Gerar nome único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_original = arquivo.filename
        extensao = nome_original.rsplit('.', 1)[-1] if '.' in nome_original else ''
        nome_arquivo = f"{codigo_auditoria}_{timestamp}.{extensao}" if extensao else f"{codigo_auditoria}_{timestamp}"
        
        # Caminho no Storage
        caminho_storage = f"auditorias/emergenciais/{codigo_auditoria}/{nome_arquivo}"
        
        # Ler o arquivo
        arquivo_bytes = arquivo.read()
        
        # Upload usando o bucket 'evidencias_auditorias'
        bucket_name = 'evidencias_auditorias'
        supabase.storage.from_(bucket_name).upload(
            path=caminho_storage,
            file=arquivo_bytes,
            file_options={"content-type": arquivo.content_type}
        )
        
        # Gerar URL assinada
        url_assinada = supabase.storage.from_(bucket_name).create_signed_url(
            path=caminho_storage,
            expires_in=604800  # 7 dias
        )
        
        # Buscar evidências existentes
        query = text("SELECT evidencias FROM auditorias WHERE id = :auditoria_id")
        with engine.connect() as conn:
            result = conn.execute(query, {"auditoria_id": auditoria_id})
            row = result.fetchone()
            if row and row.evidencias:
                if isinstance(row.evidencias, str):
                    evidencias = json.loads(row.evidencias)
                else:
                    evidencias = row.evidencias or []
            else:
                evidencias = []
        
        # Adicionar nova evidência
        nova_evidencia = {
            'nome': nome_original,
            'url': caminho_storage,
            'url_signed': url_assinada['signedURL'] if isinstance(url_assinada, dict) else url_assinada,
            'tamanho': len(arquivo_bytes),
            'tipo': arquivo.content_type,
            'data_upload': datetime.now().isoformat()
        }
        evidencias.append(nova_evidencia)
        
        # Salvar no banco
        evidencias_json = json.dumps(evidencias)
        query = text("""
            UPDATE auditorias 
            SET evidencias = :evidencias
            WHERE id = :auditoria_id
        """)
        
        with engine.connect() as conn:
            conn.execute(query, {
                "evidencias": evidencias_json,
                "auditoria_id": auditoria_id
            })
            conn.commit()
        
        return jsonify({
            'success': True,
            'evidencia': nova_evidencia,
            'message': 'Arquivo enviado com sucesso'
        })
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auditoria/<int:auditoria_id>/evidencia', methods=['DELETE'])
def api_remover_evidencia(auditoria_id):
    """Remove uma evidência da auditoria e do Storage"""
    from database import engine
    from sqlalchemy import text
    import json
    import os
    
    try:
        data = request.json
        caminho = data.get('caminho')
        
        if not caminho:
            return jsonify({'success': False, 'error': 'Caminho do arquivo é obrigatório'}), 400
        
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket_name = 'evidencias_auditorias'
        
        # Buscar evidências existentes
        query = text("SELECT evidencias FROM auditorias WHERE id = :auditoria_id")
        with engine.connect() as conn:
            result = conn.execute(query, {"auditoria_id": auditoria_id})
            row = result.fetchone()
            if row and row.evidencias:
                if isinstance(row.evidencias, str):
                    evidencias = json.loads(row.evidencias)
                else:
                    evidencias = row.evidencias or []
            else:
                evidencias = []
        
        # Remover a evidência da lista
        evidencias = [e for e in evidencias if e.get('url') != caminho]
        
        # Remover do Storage
        supabase.storage.from_(bucket_name).remove([caminho])
        
        # Salvar no banco
        evidencias_json = json.dumps(evidencias)
        query = text("""
            UPDATE auditorias 
            SET evidencias = :evidencias
            WHERE id = :auditoria_id
        """)
        
        with engine.connect() as conn:
            conn.execute(query, {
                "evidencias": evidencias_json,
                "auditoria_id": auditoria_id
            })
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Evidência removida com sucesso'
        })
        
    except Exception as e:
        print(f"❌ Erro ao remover evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/auditoria/<int:auditoria_id>/evidencias')
def api_get_evidencias(auditoria_id):
    """Retorna a lista de evidências de uma auditoria"""
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        query = text("""
            SELECT evidencias 
            FROM auditorias 
            WHERE id = :auditoria_id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {"auditoria_id": auditoria_id})
            row = result.fetchone()
            
            if row and row.evidencias:
                if isinstance(row.evidencias, str):
                    evidencias = json.loads(row.evidencias)
                else:
                    evidencias = row.evidencias
            else:
                evidencias = []
        
        # ⭐ RENOVAR URLS ASSINADAS (se necessário)
        if evidencias:
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            bucket_name = 'evidencias_auditorias'
            
            for ev in evidencias:
                if ev.get('url'):
                    try:
                        url_assinada = supabase.storage.from_(bucket_name).create_signed_url(
                            ev['url'],
                            expires_in=604800  # 7 dias
                        )
                        if isinstance(url_assinada, dict) and 'signedURL' in url_assinada:
                            ev['url_signed'] = url_assinada['signedURL']
                        else:
                            ev['url_signed'] = url_assinada
                    except:
                        pass
        
        return jsonify({
            'success': True,
            'evidencias': evidencias
        })
        
    except Exception as e:
        print(f"❌ Erro ao buscar evidências: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'evidencias': []
        }), 500

# ============================================================
# MATRIZ DE ACHADOS (COMENTÁRIOS COM ANEXOS)
# ============================================================

@app.route('/api/auditoria/<int:auditoria_id>/achados', methods=['GET'])
def api_get_achados(auditoria_id):
    """Lista todos os achados (comentários) de uma auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    a.id,
                    a.texto,
                    a.data_criacao,
                    a.data_edicao,
                    a.anexos,
                    a.usuario_id,
                    u.nome as usuario_nome
                FROM matriz_achados a
                JOIN usuarios u ON a.usuario_id = u.id
                WHERE a.auditoria_id = :auditoria_id
                ORDER BY a.data_criacao DESC
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            achados = []
            
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            for row in result:
                # Parse dos anexos (JSON)
                anexos = []
                if row[4]:
                    if isinstance(row[4], str):
                        anexos = json.loads(row[4])
                    else:
                        anexos = row[4] or []
                
                # Gerar URLs assinadas para cada anexo
                if anexos:
                    for anexo in anexos:
                        try:
                            caminho = anexo.get('caminho')
                            if caminho:
                                signed_url = supabase.storage.from_('matriz_achados_anexos').create_signed_url(
                                    path=caminho,
                                    expires_in=86400  # 24 horas
                                )
                                anexo['url'] = signed_url['signedURL'] if isinstance(signed_url, dict) else signed_url
                        except Exception as e:
                            print(f"⚠️ Erro ao gerar URL assinada: {e}")
                            anexo['url'] = None
                
                achados.append({
                    'id': row[0],
                    'texto': row[1],
                    'data_criacao': row[2].isoformat() if row[2] else None,
                    'data_edicao': row[3].isoformat() if row[3] else None,
                    'anexos': anexos,
                    'usuario_id': row[5],
                    'usuario_nome': row[6] or 'Usuário',
                    'pode_editar': row[5] == session.get('usuario_id') or session.get('usuario_perfil') in ['administrador', 'admin']
                })
            
            return jsonify({'success': True, 'achados': achados})
            
    except Exception as e:
        print(f"❌ Erro ao buscar achados: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auditoria/<int:auditoria_id>/achados', methods=['POST'])
def api_adicionar_achado(auditoria_id):
    """Adiciona um novo achado (comentário) com anexos"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import os
    import base64
    import json
    from datetime import datetime
    
    try:
        data = request.get_json()
        texto = data.get('texto', '').strip()
        anexos = data.get('anexos', [])
        
        if not texto:
            return jsonify({'success': False, 'error': 'Texto do achado é obrigatório'}), 400
        
        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({'success': False, 'error': 'Usuário não autenticado'}), 401
        
        # Validar limite de anexos
        if len(anexos) > 5:
            return jsonify({'success': False, 'error': 'Máximo de 5 anexos por achado'}), 400
        
        with engine.connect() as conn:
            # 1. INSERIR ACHADO
            query = text("""
                INSERT INTO matriz_achados (auditoria_id, usuario_id, texto, data_criacao, anexos)
                VALUES (:auditoria_id, :usuario_id, :texto, NOW(), '[]'::jsonb)
                RETURNING id
            """)
            result = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'usuario_id': usuario_id,
                'texto': texto
            })
            achado_id = result.fetchone()[0]
            
            # 2. PROCESSAR ANEXOS (UPLOAD PARA STORAGE)
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            anexos_salvos = []
            
            for anexo in anexos:
                nome_arquivo = anexo.get('nome')
                tipo_arquivo = anexo.get('tipo', 'application/octet-stream')
                tamanho = anexo.get('tamanho', 0)
                base64_data = anexo.get('base64')
                
                if not base64_data or not nome_arquivo:
                    continue
                
                # Decodificar Base64
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                arquivo_bytes = base64.b64decode(base64_data)
                
                # Validar tamanho (10MB)
                if len(arquivo_bytes) > 10 * 1024 * 1024:
                    continue
                
                # Gerar caminho único no Storage
                timestamp = int(datetime.now().timestamp())
                caminho_storage = f"matriz_achados_auditoria/{auditoria_id}/{achado_id}/{timestamp}_{nome_arquivo}"
                
                # Upload para o Storage
                try:
                    supabase.storage.from_('matriz_achados_anexos').upload(
                        path=caminho_storage,
                        file=arquivo_bytes,
                        file_options={"content-type": tipo_arquivo}
                    )
                    
                    anexos_salvos.append({
                        'nome': nome_arquivo,
                        'caminho': caminho_storage,
                        'tipo': tipo_arquivo,
                        'tamanho': tamanho,
                        'data_upload': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"⚠️ Erro no upload do anexo {nome_arquivo}: {e}")
            
            # 3. ATUALIZAR O CAMPO ANEXOS COM OS DADOS SALVOS
            if anexos_salvos:
                anexos_json = json.dumps(anexos_salvos)
                query_update = text("""
                    UPDATE matriz_achados 
                    SET anexos = CAST(:anexos AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                """)
                conn.execute(query_update, {
                    'anexos': anexos_json,
                    'id': achado_id
                })
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'achado_id': achado_id,
                'message': 'Achado adicionado com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao adicionar achado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/achado/<int:achado_id>', methods=['PUT'])
def api_editar_achado(achado_id):
    """Edita um achado existente (texto e anexos)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import os
    import base64
    import json
    from datetime import datetime
    
    try:
        data = request.get_json()
        texto = data.get('texto', '').strip()
        novos_anexos = data.get('anexos', [])
        
        if not texto:
            return jsonify({'success': False, 'error': 'Texto do achado é obrigatório'}), 400
        
        usuario_id = session.get('usuario_id')
        is_admin = session.get('usuario_perfil') in ['administrador', 'admin']
        
        with engine.connect() as conn:
            # 1. VERIFICAR PERMISSÃO
            query_check = text("""
                SELECT usuario_id, anexos
                FROM matriz_achados
                WHERE id = :achado_id
            """)
            result_check = conn.execute(query_check, {'achado_id': achado_id}).fetchone()
            
            if not result_check:
                return jsonify({'success': False, 'error': 'Achado não encontrado'}), 404
            
            autor_id = result_check[0]
            anexos_existentes = []
            if result_check[1]:
                if isinstance(result_check[1], str):
                    anexos_existentes = json.loads(result_check[1])
                else:
                    anexos_existentes = result_check[1] or []
            
            # Verificar se é o autor ou admin
            if autor_id != usuario_id and not is_admin:
                return jsonify({'success': False, 'error': 'Sem permissão para editar este achado'}), 403
            
            # 2. ATUALIZAR TEXTO
            query_update = text("""
                UPDATE matriz_achados 
                SET texto = :texto,
                    data_edicao = NOW(),
                    updated_at = NOW()
                WHERE id = :id
            """)
            conn.execute(query_update, {
                'texto': texto,
                'id': achado_id
            })
            
            # 3. PROCESSAR NOVOS ANEXOS
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            anexos_salvos = anexos_existentes.copy()
            
            for anexo in novos_anexos:
                nome_arquivo = anexo.get('nome')
                tipo_arquivo = anexo.get('tipo', 'application/octet-stream')
                tamanho = anexo.get('tamanho', 0)
                base64_data = anexo.get('base64')
                
                if not base64_data or not nome_arquivo:
                    continue
                
                # Decodificar Base64
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                arquivo_bytes = base64.b64decode(base64_data)
                
                # Validar tamanho (10MB)
                if len(arquivo_bytes) > 10 * 1024 * 1024:
                    continue
                
                # Gerar caminho único no Storage
                timestamp = int(datetime.now().timestamp())
                caminho_storage = f"matriz_achados_auditoria/{achado_id}/{timestamp}_{nome_arquivo}"
                
                # Upload para o Storage
                try:
                    supabase.storage.from_('matriz_achados_anexos').upload(
                        path=caminho_storage,
                        file=arquivo_bytes,
                        file_options={"content-type": tipo_arquivo}
                    )
                    
                    anexos_salvos.append({
                        'nome': nome_arquivo,
                        'caminho': caminho_storage,
                        'tipo': tipo_arquivo,
                        'tamanho': tamanho,
                        'data_upload': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"⚠️ Erro no upload do anexo {nome_arquivo}: {e}")
            
            # 4. ATUALIZAR CAMPO ANEXOS
            if anexos_salvos:
                anexos_json = json.dumps(anexos_salvos)
                query_update_anexos = text("""
                    UPDATE matriz_achados 
                    SET anexos = CAST(:anexos AS jsonb)
                    WHERE id = :id
                """)
                conn.execute(query_update_anexos, {
                    'anexos': anexos_json,
                    'id': achado_id
                })
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Achado atualizado com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao editar achado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/achado/<int:achado_id>', methods=['DELETE'])
def api_excluir_achado(achado_id):
    """Exclui um achado e seus anexos do Storage"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import os
    import json
    
    try:
        usuario_id = session.get('usuario_id')
        usuario_perfil = session.get('usuario_perfil')
        is_admin = usuario_perfil in ['administrador', 'admin']
        
        with engine.connect() as conn:
            # 1. VERIFICAR PERMISSÃO
            query_check = text("""
                SELECT usuario_id, anexos
                FROM matriz_achados
                WHERE id = :achado_id
            """)
            result_check = conn.execute(query_check, {'achado_id': achado_id}).fetchone()
            
            if not result_check:
                return jsonify({'success': False, 'error': 'Achado não encontrado'}), 404
            
            autor_id = result_check[0]
            anexos_json = result_check[1]
            
            # Verificar se é o autor ou admin
            if autor_id != usuario_id and not is_admin:
                return jsonify({'success': False, 'error': 'Sem permissão para excluir este achado'}), 403
            
            # 2. REMOVER ANEXOS DO STORAGE
            anexos = []
            if anexos_json:
                if isinstance(anexos_json, str):
                    anexos = json.loads(anexos_json)
                else:
                    anexos = anexos_json or []
            
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            if anexos:
                try:
                    caminhos = [a.get('caminho') for a in anexos if a.get('caminho')]
                    if caminhos:
                        supabase.storage.from_('matriz_achados_anexos').remove(caminhos)
                        print(f"🗑️ Removidos {len(caminhos)} arquivos do Storage")
                except Exception as e:
                    print(f"⚠️ Erro ao remover arquivos do Storage: {e}")
            
            # 3. REMOVER DO BANCO
            query_delete = text("DELETE FROM matriz_achados WHERE id = :achado_id")
            conn.execute(query_delete, {'achado_id': achado_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Achado excluído com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir achado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/achado/<int:achado_id>/anexo/<int:anexo_index>', methods=['DELETE'])
def api_remover_anexo(achado_id, anexo_index):
    """Remove um anexo específico de um achado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import os
    import json
    
    try:
        usuario_id = session.get('usuario_id')
        is_admin = session.get('usuario_perfil') in ['administrador', 'admin']
        
        with engine.connect() as conn:
            # 1. VERIFICAR PERMISSÃO
            query_check = text("""
                SELECT usuario_id, anexos
                FROM matriz_achados
                WHERE id = :achado_id
            """)
            result_check = conn.execute(query_check, {'achado_id': achado_id}).fetchone()
            
            if not result_check:
                return jsonify({'success': False, 'error': 'Achado não encontrado'}), 404
            
            autor_id = result_check[0]
            
            # Verificar se é o autor ou admin
            if autor_id != usuario_id and not is_admin:
                return jsonify({'success': False, 'error': 'Sem permissão'}), 403
            
            # 2. BUSCAR ANEXOS
            anexos = []
            if result_check[1]:
                if isinstance(result_check[1], str):
                    anexos = json.loads(result_check[1])
                else:
                    anexos = result_check[1] or []
            
            if anexo_index >= len(anexos):
                return jsonify({'success': False, 'error': 'Anexo não encontrado'}), 404
            
            anexo_removido = anexos[anexo_index]
            caminho_storage = anexo_removido.get('caminho')
            
            # 3. REMOVER DO STORAGE
            if caminho_storage:
                # ⭐ USAR O SINGLETON
                from supabase_client import SupabaseClient
                supabase = SupabaseClient.get_instance()
                
                try:
                    supabase.storage.from_('matriz_achados_anexos').remove([caminho_storage])
                    print(f"🗑️ Arquivo removido do Storage: {caminho_storage}")
                except Exception as e:
                    print(f"⚠️ Erro ao remover do Storage: {e}")
            
            # 4. REMOVER DO JSON
            anexos.pop(anexo_index)
            anexos_json = json.dumps(anexos)
            
            query_update = text("""
                UPDATE matriz_achados 
                SET anexos = CAST(:anexos AS jsonb),
                    updated_at = NOW()
                WHERE id = :id
            """)
            conn.execute(query_update, {
                'anexos': anexos_json,
                'id': achado_id
            })
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Anexo removido com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao remover anexo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/achado/anexo/<int:achado_id>/<int:anexo_index>/download', methods=['GET'])
def api_download_anexo_achado(achado_id, anexo_index):
    """Baixa um anexo de um achado pelo índice no JSON"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import json
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT anexos
                FROM matriz_achados
                WHERE id = :achado_id
            """)
            result = conn.execute(query, {'achado_id': achado_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Achado não encontrado'}), 404
            
            anexos = []
            if result[0]:
                if isinstance(result[0], str):
                    anexos = json.loads(result[0])
                else:
                    anexos = result[0] or []
            
            if anexo_index >= len(anexos):
                return jsonify({'success': False, 'error': 'Anexo não encontrado'}), 404
            
            anexo = anexos[anexo_index]
            caminho_storage = anexo.get('caminho')
            nome_arquivo = anexo.get('nome')
            
            if not caminho_storage:
                return jsonify({'success': False, 'error': 'Caminho do arquivo não encontrado'}), 404
            
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            url_assinada = supabase.storage.from_('matriz_achados_anexos').create_signed_url(
                path=caminho_storage,
                expires_in=3600  # 1 hora
            )
            
            signed_url = url_assinada['signedURL'] if isinstance(url_assinada, dict) else url_assinada
            
            return jsonify({
                'success': True,
                'url': signed_url,
                'nome_arquivo': nome_arquivo
            })
            
    except Exception as e:
        print(f"❌ Erro ao baixar anexo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# FIM - MATRIZ DE ACHADOS (COMENTÁRIOS COM ANEXOS)
# ============================================================

@app.route('/api/evidencia/<path:caminho>')
def api_baixar_evidencia(caminho):
    """Baixa uma evidência do Supabase Storage"""
    try:
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket_name = 'evidencias_auditorias'
        
        # Gerar URL assinada (1 hora)
        url_assinada = supabase.storage.from_(bucket_name).create_signed_url(
            path=caminho,
            expires_in=3600
        )
        
        # Extrair a URL do dicionário
        if isinstance(url_assinada, dict) and 'signedURL' in url_assinada:
            url = url_assinada['signedURL']
        else:
            url = url_assinada
        
        return jsonify({
            'success': True,
            'url': url
        })
        
    except Exception as e:
        print(f"❌ Erro ao baixar evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================
# API - DIAGNÓSTICO DOS PROCESSOS
# ============================================================
@app.route('/api/processo/verificar')
def api_verificar_processo():
    """Verifica se um processo com o mesmo nome já existe na área E auditoria"""
    nome_processo = request.args.get('nome')
    id_area = request.args.get('id_area')
    auditoria_id = request.args.get('auditoria_id')  # ← NOVO

    if not nome_processo or not id_area or not auditoria_id:
        return jsonify({'existe': False})
    
    from logic import buscar_processo_por_nome_e_area
    processo = buscar_processo_por_nome_e_area(nome_processo, id_area, auditoria_id)  # ← MODIFICAR

    if processo:
        return jsonify({
            'existe': True,
            'processo_id': processo['id'],
            'codigo': processo['codigo_processo']
        })
    return jsonify({'existe': False})

@app.route('/api/processo/gerar-codigo')
def api_gerar_codigo_processo():
    """Gera o próximo código sequencial para uma área em uma auditoria específica"""
    from logic import gerar_codigo_processo
    
    id_area = request.args.get('id_area')
    auditoria_id = request.args.get('auditoria_id')  # ← NOVO
    
    if not id_area or not auditoria_id:
        return jsonify({'error': 'id_area e auditoria_id são obrigatórios'}), 400
    
    try:
        id_area = int(id_area)
        auditoria_id = int(auditoria_id)
    except ValueError:
        return jsonify({'error': 'id_area e auditoria_id devem ser números'}), 400
    
    codigo = gerar_codigo_processo(id_area, auditoria_id)  # ← MODIFICAR
    
    return jsonify({'codigo': codigo})

@app.route('/api/area/<int:area_id>/funcionarios-para-select')
def api_area_funcionarios_para_select(area_id):
    """Retorna funcionários da área formatados para select/multiselect"""
    from database import engine
    from sqlalchemy import text
    
    # Usar funcionarios_area (correto)
    query = text("""
        SELECT id, nome_funcionario, cargo
        FROM funcionarios_area
        WHERE id_area = :area_id AND ativo = true
        ORDER BY nome_funcionario
    """)
    
    with engine.connect() as conn:
        result = conn.execute(query, {'area_id': area_id})
        funcionarios = [{'id': row[0], 'nome': row[1], 'cargo': row[2] or ''} for row in result]
    
    return jsonify(funcionarios)

@app.route('/api/area/<int:area_id>/upload-organograma', methods=['POST'])
def api_upload_organograma(area_id):
    """Faz upload do organograma para o Supabase Storage - qualquer usuário autenticado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import base64
    
    data = request.json
    arquivo_base64 = data.get('arquivo_base64')
    nome_arquivo = data.get('nome_arquivo')
    tipo_arquivo = data.get('tipo_arquivo')
    
    if not arquivo_base64:
        return jsonify({'success': False, 'error': 'Arquivo é obrigatório'}), 400
    
    try:
        # 1. Decodificar Base64
        if ',' in arquivo_base64:
            arquivo_base64 = arquivo_base64.split(',')[1]
        arquivo_bytes = base64.b64decode(arquivo_base64)
        
        # 2. Validar tamanho (5MB)
        if len(arquivo_bytes) > 5 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'Arquivo muito grande. Máximo 5MB'}), 400
        
        # 3. Conectar ao Supabase - USAR SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        # 4. Gerar caminho único
        extensao = nome_arquivo.split('.')[-1].lower()
        caminho = f"area_{area_id}/organograma.{extensao}"
        
        # 5. Fazer upload
        print(f"📎 Fazendo upload do organograma: {caminho}")
        supabase.storage.from_('organogramas').upload(
            path=caminho,
            file=arquivo_bytes,
            file_options={"content-type": tipo_arquivo}
        )
        
        # 6. Obter URL pública
        public_url = supabase.storage.from_('organogramas').get_public_url(caminho)
        
        # 7. Salvar no banco
        with engine.connect() as conn:
            query = text("""
                UPDATE informacoes_area 
                SET organograma_url = :url,
                    organograma_nome = :nome
                WHERE id_area = :area_id
            """)
            conn.execute(query, {
                'url': public_url,
                'nome': nome_arquivo,
                'area_id': area_id
            })
            conn.commit()
        
        print(f"✅ Organograma salvo com sucesso para área {area_id}")
        
        return jsonify({
            'success': True,
            'url': public_url,
            'nome': nome_arquivo,
            'message': 'Organograma salvo com sucesso!'
        })
        
    except Exception as e:
        print(f"❌ Erro no upload do organograma: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/area/<int:area_id>/organograma', methods=['GET'])
def api_buscar_organograma(area_id):
    """Busca o organograma da área"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT organograma_url, organograma_nome
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({
                    'success': True,
                    'tem_organograma': False
                })
            
            return jsonify({
                'success': True,
                'tem_organograma': True,
                'url': result[0],
                'nome': result[1] or 'Organograma'
            })
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/area/<int:area_id>/organograma', methods=['DELETE'])
def api_remover_organograma(area_id):
    """Remove o organograma da área - qualquer usuário autenticado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Buscar URL atual
            query = text("SELECT organograma_url FROM informacoes_area WHERE id_area = :area_id")
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            
            if result and result[0]:
                # ⭐ USAR O SINGLETON
                from supabase_client import SupabaseClient
                supabase = SupabaseClient.get_instance()
                
                # Extrair caminho da URL
                if '/organogramas/' in result[0]:
                    caminho = result[0].split('/organogramas/')[-1]
                    try:
                        supabase.storage.from_('organogramas').remove([caminho])
                        print(f"✅ Arquivo removido do storage: {caminho}")
                    except Exception as e:
                        print(f"⚠️ Erro ao remover do storage: {e}")
            
            # Limpar banco
            query = text("""
                UPDATE informacoes_area 
                SET organograma_url = NULL,
                    organograma_nome = NULL
                WHERE id_area = :area_id
            """)
            conn.execute(query, {'area_id': area_id})
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Organograma removido com sucesso!'})
        
    except Exception as e:
        print(f"❌ Erro ao remover organograma: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ====== API - SALVAR INFORMAÇÕES BÁSICAS DO PROCESSO ======
@app.route('/api/processo/salvar-basico', methods=['POST'])
def api_salvar_processo_basico():
    """Salva ou atualiza as informações básicas do processo"""
    from database import engine
    from sqlalchemy import text
    from logic import gerar_codigo_processo
    
    data = request.json
    print(f"📥 Dados recebidos em salvar-basico: {data}")
    print(f"🔍 processo_id recebido: {data.get('processo_id')}")
    
    # ===== DADOS RECEBIDOS DO FRONTEND =====
    processo_id = data.get('processo_id')
    nome_processo = data.get('nome_processo')
    codigo_processo = data.get('codigo_processo')
    id_area = data.get('id_area')
    nome_area = data.get('nome_area')
    executores_ids = data.get('executores_ids', [])
    auditoria_id = data.get('auditoria_id')
    
    # ===== VALIDAÇÕES BÁSICAS =====
    if not nome_processo or not id_area:
        return jsonify({'success': False, 'error': 'Nome do processo e área são obrigatórios'}), 400
    
    try:
        with engine.connect() as conn:
            # ===== BUSCAR NOME DA ÁREA SE NÃO VEIO =====
            if not nome_area:
                busca_area = text("SELECT nome_area FROM informacoes_area WHERE id_area = :id_area")
                result_area = conn.execute(busca_area, {'id_area': id_area}).fetchone()
                nome_area = result_area[0] if result_area else ''
            
            # ===== DECIDIR ENTRE UPDATE (EDIÇÃO) OU INSERT (NOVO) =====
            if processo_id:
                # ===== CASO 1: EDIÇÃO - Processo já existe, vamos ATUALIZAR =====
                print(f"✏️ Editando processo existente ID: {processo_id}")
                
                update_query = text("""
                    UPDATE processos 
                    SET nome_processo = :nome, 
                        codigo_processo = :codigo,
                        area = :area,
                        auditoria_id = :auditoria_id,
                        updated_at = NOW()
                    WHERE id = :id
                    RETURNING id
                """)
                result = conn.execute(update_query, {
                    'nome': nome_processo,
                    'codigo': codigo_processo,
                    'area': nome_area,
                    'auditoria_id': auditoria_id,
                    'id': processo_id
                })
                processo_id = result.fetchone()[0]
                print(f"✅ Processo {processo_id} atualizado com sucesso!")
                
            else:
                # ===== CASO 2: NOVO PROCESSO - Vamos CRIAR =====
                print(f"➕ Criando novo processo: {nome_processo}")
                
                # Verificar se já existe outro com mesmo nome na área E MESMA AUDITORIA
                check_query = text("""
                    SELECT id FROM processos 
                    WHERE nome_processo = :nome 
                    AND id_area = :id_area 
                    AND auditoria_id = :auditoria_id
                """)
                existing = conn.execute(check_query, {
                    'nome': nome_processo,
                    'id_area': id_area,
                    'auditoria_id': auditoria_id
                }).fetchone()
                
                if existing:
                    # Se já existe, usar o ID existente (edição implícita)
                    processo_id = existing[0]
                    print(f"⚠️ Processo já existe! Reutilizando ID: {processo_id}")
                    
                    # Atualizar mesmo assim
                    update_query = text("""
                        UPDATE processos 
                        SET nome_processo = :nome, 
                            codigo_processo = :codigo,
                            area = :area,
                            auditoria_id = :auditoria_id,
                            updated_at = NOW()
                        WHERE id = :id
                    """)
                    conn.execute(update_query, {
                        'nome': nome_processo,
                        'codigo': codigo_processo,
                        'area': nome_area,
                        'auditoria_id': auditoria_id,
                        'id': processo_id
                    })
                else:
                    # Realmente novo: gerar código e inserir
                    if not codigo_processo:
                        codigo_processo = gerar_codigo_processo(id_area, auditoria_id)  # ← PASSAR AUDITORIA_ID
                    
                    insert_query = text("""
                        INSERT INTO processos (
                            nome_processo, codigo_processo, id_area, area, 
                            auditoria_id, created_at, updated_at
                        )
                        VALUES (
                            :nome, :codigo, :id_area, :area, 
                            :auditoria_id, NOW(), NOW()
                        )
                        RETURNING id
                    """)
                    result = conn.execute(insert_query, {
                        'nome': nome_processo,
                        'codigo': codigo_processo,
                        'id_area': id_area,
                        'area': nome_area,
                        'auditoria_id': auditoria_id
                    })
                    processo_id = result.fetchone()[0]
                    print(f"✅ Novo processo criado com ID: {processo_id}")
            
            # ===== SALVAR EXECUTORES (funcionários que executam o processo) =====
            if executores_ids:
                print(f"👥 Salvando {len(executores_ids)} executores para o processo {processo_id}")
                
                # Remover executores antigos (para não duplicar)
                delete_executors = text("DELETE FROM processo_executores WHERE processo_id = :processo_id")
                conn.execute(delete_executors, {'processo_id': processo_id})
                
                # Inserir os novos executores
                insert_executor = text("""
                    INSERT INTO processo_executores (processo_id, funcionario_id, created_at, updated_at)
                    VALUES (:processo_id, :funcionario_id, NOW(), NOW())
                """)
                for func_id in executores_ids:
                    conn.execute(insert_executor, {
                        'processo_id': processo_id,
                        'funcionario_id': func_id
                    })
                print(f"✅ {len(executores_ids)} executores salvos!")
            else:
                print(f"⚠️ Nenhum executor para salvar no processo {processo_id}")
            
            # ⭐ REMOVIDO: Bloco de vinculação à auditoria (não é mais necessário)
            # O auditoria_id já está na tabela processos!
            
            # ===== CONFIRMAR TRANSAÇÃO =====
            conn.commit()
            
            # ===== RETORNAR SUCESSO =====
            return jsonify({
                'success': True,
                'processo_id': processo_id,
                'codigo_processo': codigo_processo,
                'message': 'Informações básicas salvas com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar processo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/processo/salvar-detalhes', methods=['POST'])
def api_salvar_processo_detalhes():
    """Salva os detalhes do processo (descrição, objetivo, etc)"""
    from database import engine
    from sqlalchemy import text
    
    data = request.json
    processo_id = data.get('processo_id')
    descricao = data.get('descricao', '')
    etapa_ini = data.get('etapa_ini', '')
    etapa_fim = data.get('etapa_fim', '')
    produto = data.get('produto', '')
    objetivo = data.get('objetivo', '')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'ID do processo é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE processos 
                SET descricao = :descricao,
                    etapa_ini = :etapa_ini,
                    etapa_fim = :etapa_fim,
                    produto = :produto,
                    objetivo = :objetivo
                WHERE id = :processo_id
            """)
            
            conn.execute(query, {
                'descricao': descricao,
                'etapa_ini': etapa_ini,
                'etapa_fim': etapa_fim,
                'produto': produto,
                'objetivo': objetivo,
                'processo_id': processo_id
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Detalhes salvos com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar detalhes: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/desativar', methods=['PUT'])
def api_desativar_processo(processo_id):
    """Desativa um processo (soft delete)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE processos 
                SET status = 'Inativo'
                WHERE id = :processo_id
            """)
            conn.execute(query, {'processo_id': processo_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Processo desativado'})
            
    except Exception as e:
        print(f"❌ Erro ao desativar processo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/riscos')
def api_processo_riscos(processo_id):
    """Retorna os riscos de um processo"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    id, nome_risco, fator_risco, melhoria,
                    impacto, probabilidade, motivo_risco,
                    categoria, causas,
                    tratamento_risco, descricao_tratamento, prazo_implantacao,
                    score_risco, apetite_impacto, apetite_probabilidade
                FROM riscos
                WHERE processo_id = :processo_id
            """)
            result = conn.execute(query, {'processo_id': processo_id}).fetchall()
            
            riscos = []
            for row in result:               
                # Converter strings para listas
                categorias_str = row[7] if len(row) > 8 else ''
                causas_str = row[7] if len(row) > 9 else ''
                
                categorias = categorias_str.split(',') if categorias_str else []
                causas_list = causas_str.split(',') if causas_str else []
                
                # Formatar data
                prazo = row[11] if len(row) > 11 and row[11] else ''
                
                risco = {
                    'id': row[0],
                    'nome_risco': row[1] if len(row) > 1 and row[1] else '',
                    'fator_risco': row[2] if len(row) > 2 and row[2] else '',
                    'melhoria': row[3] if len(row) > 3 and row[3] else '',
                    'impacto': row[4] if len(row) > 4 and row[4] else 'Médio',
                    'probabilidade': row[5] if len(row) > 5 and row[5] else 'Médio',
                    'motivo_risco': row[6] if len(row) > 6 and row[6] else '',
                    'categorias': [c.strip() for c in categorias if c.strip()],
                    'categoria_causa': [c.strip() for c in causas_list if c.strip()],
                    'score_risco': row[12] if len(row) > 12 and row[12] else 0,
                    # ⭐ CAMPOS DE TRATAMENTO CORRIGIDOS ⭐
                    'como_tratar': row[9] if len(row) > 9 and row[9] else '',
                    'desc_tratamento': row[10] if len(row) > 10 and row[10] else '',
                    'prazo_implantacao': prazo,
                    'apetite_impacto': row[13] if len(row) > 13 and row[13] else 'Médio',
                    'apetite_probabilidade': row[14] if len(row) > 14 and row[14] else 'Médio'
                }
                
                riscos.append(risco)
            
            # Log para debug no servidor
            print(f"✅ Buscou {len(riscos)} riscos para o processo {processo_id}")
            if riscos:
                print(f"📊 Primeiro risco - como_tratar: '{riscos[0].get('como_tratar', 'N/A')}'")
                print(f"📊 Primeiro risco - desc_tratamento: '{riscos[0].get('desc_tratamento', 'N/A')}'")
            
            return jsonify({'success': True, 'riscos': riscos})
            
    except Exception as e:
        print(f"❌ Erro ao buscar riscos: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/dados')
def api_processo_dados(processo_id):
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            # ===== 1. BUSCAR DADOS BÁSICOS DO PROCESSO =====
            # ⭐ AGORA COM auditoria_id DIRETO NO SELECT
            query = text("""
                SELECT p.id, p.nome_processo, p.codigo_processo, p.id_area, p.auditoria_id,
                       p.descricao, p.etapa_ini, p.etapa_fim, p.produto, p.objetivo,
                       p.fluxo_bpmn_nome, p.fluxo_bpmn_tipo,
                       i.nome_area
                FROM processos p
                JOIN informacoes_area i ON p.id_area = i.id_area
                WHERE p.id = :processo_id
            """)
            processo = conn.execute(query, {'processo_id': processo_id}).fetchone()
            
            if not processo:
                return jsonify({'success': False, 'error': 'Processo não encontrado'}), 404
            
            # ⭐ REMOVIDO: A busca separada da auditoria (já não é mais necessária)
            # O auditoria_id já está no SELECT acima no índice 4
            
            # ===== 2. BUSCAR EXECUTORES =====
            query_exec = text("""
                SELECT f.id, f.nome_funcionario, f.cargo
                FROM processo_executores pe
                JOIN funcionarios_area f ON pe.funcionario_id = f.id
                WHERE pe.processo_id = :processo_id
            """)
            executores = conn.execute(query_exec, {'processo_id': processo_id}).fetchall()
            
            # ===== 3. BUSCAR RISCOS =====
            query_riscos = text("""
                SELECT id, nome_risco, fator_risco, melhoria,
                       impacto, probabilidade, motivo_risco, categoria, causas,
                       tratamento_risco, descricao_tratamento, prazo_implantacao,
                       apetite_impacto, apetite_probabilidade
                FROM riscos
                WHERE processo_id = :processo_id
            """)
            riscos_result = conn.execute(query_riscos, {'processo_id': processo_id}).fetchall()
            
            riscos = []
            for r in riscos_result:                
                categorias = r[7].split(',') if r[7] else []
                categoria_causa = r[8].split(',') if r[8] else []
                
                # Converter data
                prazo = r[11] if r[11] else ''
                
                riscos.append({
                    'id': r[0],
                    'nome_risco': r[1] or '',
                    'fator_risco': r[2] or '',
                    'melhoria': r[3] or '',
                    'impacto': r[4] or 'Médio',
                    'probabilidade': r[5] or 'Médio',
                    'motivo_risco': r[6] or '',
                    'categorias': [c.strip() for c in categorias if c.strip()],
                    'categoria_causa': [c.strip() for c in categoria_causa if c.strip()],
                    'como_tratar': r[9] or '',
                    'desc_tratamento': r[10] or '',
                    'prazo_implantacao': prazo,
                    'apetite_impacto': r[12] or 'Médio',
                    'apetite_probabilidade': r[13] or 'Médio'
                })
            
            # ===== 4. RETORNAR TODOS OS DADOS =====
            # ⭐ NOVO: p.auditoria_id está no índice 4
            return jsonify({
                'success': True,
                'nome_processo': processo[1],
                'codigo_processo': processo[2],
                'id_area': processo[3],
                'auditoria_id': processo[4],  # ← AGORA VEM DIRETO DO SELECT
                'nome_area': processo[12],    # ← Índice ajustado (12 em vez de 11)
                'descricao': processo[5] or '',
                'etapa_ini': processo[6] or '',
                'etapa_fim': processo[7] or '',
                'produto': processo[8] or '',
                'objetivo': processo[9] or '',
                'fluxo_bpmn_nome': processo[10] or '',
                'fluxo_bpmn_tipo': processo[11] or '',
                'executores': [{'id': e[0], 'nome': e[1], 'cargo': e[2] or ''} for e in executores],
                'riscos': riscos
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar dados do processo: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/processo/<int:processo_id>/upload-bpmn', methods=['POST'])
def api_processo_upload_bpmn(processo_id):
    """Faz upload do fluxo BPMN do processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import base64
    
    data = request.json
    arquivo_base64 = data.get('arquivo_base64')
    nome_arquivo = data.get('nome_arquivo')
    tipo_arquivo = data.get('tipo_arquivo')
    
    if not arquivo_base64:
        return jsonify({'success': False, 'error': 'Arquivo é obrigatório'}), 400
    
    try:
        # Decodificar Base64 para bytes
        if ',' in arquivo_base64:
            arquivo_base64 = arquivo_base64.split(',')[1]
        arquivo_bytes = base64.b64decode(arquivo_base64)
        
        with engine.connect() as conn:
            query = text("""
                UPDATE processos 
                SET fluxo_bpmn = :fluxo_bpmn,
                    fluxo_bpmn_nome = :nome,
                    fluxo_bpmn_tipo = :tipo,
                    updated_at = NOW()
                WHERE id = :processo_id
            """)
            
            conn.execute(query, {
                'fluxo_bpmn': arquivo_bytes,
                'nome': nome_arquivo,
                'tipo': tipo_arquivo,
                'processo_id': processo_id
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Fluxo BPMN salvo com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar fluxo BPMN: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/download-bpmn')
def api_processo_download_bpmn(processo_id):
    """Faz download do fluxo BPMN do processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT fluxo_bpmn, fluxo_bpmn_nome, fluxo_bpmn_tipo
                FROM processos
                WHERE id = :processo_id
            """)
            result = conn.execute(query, {'processo_id': processo_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({'error': 'Nenhum fluxo BPMN encontrado'}), 404
            
            return send_file(
                io.BytesIO(result[0]),
                mimetype=result[2] or 'application/octet-stream',
                as_attachment=True,
                download_name=result[1] or f'fluxo_bpmn_processo_{processo_id}'
            )
            
    except Exception as e:
        print(f"❌ Erro ao baixar fluxo BPMN: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/processo/<int:processo_id>/remover-bpmn', methods=['DELETE'])
def api_processo_remover_bpmn(processo_id):
    """Remove o fluxo BPMN do processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE processos 
                SET fluxo_bpmn = NULL,
                    fluxo_bpmn_nome = NULL,
                    fluxo_bpmn_tipo = NULL,
                    updated_at = NOW()
                WHERE id = :processo_id
            """)
            conn.execute(query, {'processo_id': processo_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Fluxo BPMN removido'})
            
    except Exception as e:
        print(f"❌ Erro ao remover fluxo BPMN: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processo/salvar-riscos', methods=['POST'])
def api_salvar_processo_riscos():
    from database import engine
    from sqlalchemy import text
    
    data = request.json
    processo_id = data.get('processo_id')
    riscos = data.get('riscos', [])
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'ID do processo é obrigatório'}), 400
    
    # Mapa de risco para calcular score
    MAPA_RISCO = {
        ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14,
        ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
        ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10,
        ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
        ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6,
        ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
        ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2,
        ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
    }
    
    def calcular_score(impacto, probabilidade):
        return MAPA_RISCO.get((impacto, probabilidade), 0)
    
    try:
        with engine.connect() as conn:
            # Remover riscos existentes
            delete_query = text("DELETE FROM riscos WHERE processo_id = :processo_id")
            conn.execute(delete_query, {'processo_id': processo_id})
            
            # Inserir novos riscos
            insert_query = text("""
                INSERT INTO riscos (
                    processo_id, nome_risco, fator_risco, melhoria, 
                    impacto, probabilidade, motivo_risco, 
                    categoria, causas, score_risco,
                    tratamento_risco, descricao_tratamento, prazo_implantacao,
                    apetite_impacto, apetite_probabilidade
                )
                VALUES (
                    :processo_id, :nome_risco, :fator_risco, :melhoria, 
                    :impacto, :probabilidade, :motivo_risco, 
                    :categoria, :causas, :score_risco,
                    :tratamento_risco, :descricao_tratamento, :prazo_implantacao,
                    :apetite_impacto, :apetite_probabilidade
                )
            """)
            
            for risco in riscos:
                impacto = risco.get('impacto', 'Médio')
                probabilidade = risco.get('probabilidade', 'Médio')
                score = calcular_score(impacto, probabilidade)
                
                # Converter arrays para strings separadas por vírgula
                categorias = risco.get('categorias', [])
                categoria_str = ', '.join(categorias) if categorias else None
                
                # IMPORTANTE: frontend envia "categoria_causa", banco chama "causas"
                causas = risco.get('categoria_causa', [])
                causas_str = ', '.join([c.strip() for c in causas]) if causas else None
                
                conn.execute(insert_query, {
                    'processo_id': processo_id,
                    'nome_risco': risco.get('nome_risco', ''),
                    'fator_risco': risco.get('fator_risco', ''),
                    'melhoria': risco.get('melhoria', ''),
                    'impacto': impacto,
                    'probabilidade': probabilidade,
                    'motivo_risco': risco.get('motivo_risco', ''),
                    'categoria': categoria_str,
                    'causas': causas_str,                              # ← corrigido
                    'score_risco': score,
                    'tratamento_risco': risco.get('como_tratar', ''),   # ← frontend → banco
                    'descricao_tratamento': risco.get('desc_tratamento', ''),
                    'prazo_implantacao': risco.get('prazo_implantacao') or None,
                    'apetite_impacto': risco.get('apetite_impacto', 'Médio'),
                    'apetite_probabilidade': risco.get('apetite_probabilidade', 'Médio')
                })
            
            conn.commit()
            print(f"✅ {len(riscos)} riscos salvos para o processo {processo_id}")
            return jsonify({'success': True, 'message': f'{len(riscos)} riscos salvos'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar riscos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/processos-por-auditoria')
def api_processos_por_auditoria():
    """Retorna todos os processos de uma auditoria"""
    from database import engine
    from sqlalchemy import text

    auditoria_id = request.args.get('auditoria_id')
    if not auditoria_id:
        return jsonify({'success': False, 'error': 'auditoria_id é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            # ⭐ AGORA É DIRETO - SEM JOIN!
            query = text("""
                SELECT p.id, p.codigo_processo, p.nome_processo, p.objetivo, p.fluxo_bpmn_nome
                FROM processos p
                WHERE p.auditoria_id = :auditoria_id
                    AND p.status = 'Ativo'
                ORDER BY 
                    CAST(SUBSTRING(p.codigo_processo FROM '^[0-9]+') AS INTEGER),
                    CAST(SUBSTRING(p.codigo_processo FROM '[0-9]+$') AS INTEGER)
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id})
            processos = [dict(row._mapping) for row in result]

            return jsonify({'success': True, 'processos': processos})
    
    except Exception as e:
        print(f"❌ Erro ao buscar processos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processos-por-area')
def api_processos_por_area():
    """Retorna todos os processos de uma área (com opção de filtrar por auditoria)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    area_id = request.args.get('area_id')
    auditoria_id = request.args.get('auditoria_id')
    
    if not area_id:
        return jsonify({'success': False, 'error': 'area_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            if auditoria_id:
                # Se tem auditoria, filtrar por ela
                query = text("""
                    SELECT 
                        p.id, 
                        p.codigo_processo, 
                        p.nome_processo, 
                        p.objetivo,
                        p.auditoria_id,
                        a.codigo_auditoria
                    FROM processos p
                    LEFT JOIN auditorias a ON p.auditoria_id = a.id
                    WHERE p.id_area = :area_id 
                        AND p.status = 'Ativo'
                        AND p.auditoria_id = :auditoria_id
                    ORDER BY 
                        CAST(SPLIT_PART(p.codigo_processo, '.', 2) AS INTEGER)
                """)
                result = conn.execute(query, {
                    "area_id": area_id,
                    "auditoria_id": auditoria_id
                }).fetchall()
            else:
                # Sem auditoria - todos os processos da área
                query = text("""
                    SELECT 
                        p.id, 
                        p.codigo_processo, 
                        p.nome_processo, 
                        p.objetivo,
                        p.auditoria_id,
                        a.codigo_auditoria
                    FROM processos p
                    LEFT JOIN auditorias a ON p.auditoria_id = a.id
                    WHERE p.id_area = :area_id 
                        AND p.status = 'Ativo'
                    ORDER BY 
                        CAST(SPLIT_PART(p.codigo_processo, '.', 2) AS INTEGER)
                """)
                result = conn.execute(query, {"area_id": area_id}).fetchall()
            
            processos = []
            for row in result:
                processos.append({
                    'id': row[0],
                    'codigo_processo': row[1] or '',
                    'nome_processo': row[2] or '',
                    'objetivo': row[3] or '',
                    'auditoria_id': row[4],
                    'codigo_auditoria': row[5] or f'Auditoria {row[4]}' if row[4] else '-'
                })
            
            return jsonify({'success': True, 'processos': processos})
            
    except Exception as e:
        print(f"❌ Erro em /api/processos-por-area: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
                           

# ============================================================
# API - ÁREAS E FUNCIONÁRIOS
# ============================================================

@app.route('/api/areas')
def api_areas():
    """Retorna todas as áreas (ativas e inativas)"""
    
    
    # Passar apenas_ativas=False para buscar TODAS as áreas
    df = listar_areas(apenas_ativas=False)
    
    if df.empty:
        return jsonify([])
    
    return jsonify(df.to_dict(orient='records'))

@app.route('/api/totais')
def api_totais():
    """Retorna totais de áreas e funcionários"""
    
    df_areas = listar_areas()
    total_areas = len(df_areas) if not df_areas.empty else 0
    
    total_funcionarios = 0
    if not df_areas.empty:
        for _, area in df_areas.iterrows():
            df_func = listar_funcionarios_area(area['id_area'])
            if not df_func.empty:
                total_funcionarios += len(df_func)
    
    return jsonify({
        'areas': total_areas,
        'funcionarios': total_funcionarios,
        'total_geral': total_areas + total_funcionarios
    })

@app.route('/api/area/<int:area_id>')
def api_area_detalhes(area_id):
    """Retorna detalhes de uma área específica (com organograma)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ⭐ BUSCAR DIRETAMENTE COM OS CAMPOS DO ORGANOGRAMA
            query = text("""
                SELECT id_area, nome_area, loc_unidade, email, telefone, gestor,
                       superintendente, diretor, objetivo_area, status,
                       organograma_url, organograma_nome
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            
            if not result:
                return jsonify({}), 404
            
            # Converter para dicionário
            area_dict = {
                'id_area': result[0],
                'nome_area': result[1],
                'loc_unidade': result[2],
                'email': result[3],
                'telefone': result[4],
                'gestor': result[5],
                'superintendente': result[6] or '',
                'diretor': result[7] or '',
                'objetivo_area': result[8] or '',
                'status': result[9],
                'organograma_url': result[10] or '',  # ⭐
                'organograma_nome': result[11] or '', # ⭐
                'unidade': result[2]  # Para compatibilidade
            }
            
            return jsonify(area_dict)
            
    except Exception as e:
        print(f"❌ Erro ao buscar área: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/area/<int:area_id>/funcionarios')
def api_area_funcionarios(area_id):
    """Retorna todos os funcionários de uma área com tempo calculado"""
    
    df = listar_funcionarios_area(area_id)
    
    if df.empty:
        return jsonify([])
    
    funcionarios = df.to_dict(orient='records')
    
    for func in funcionarios:
        func['tempo_funcao'] = calcular_tempo(func.get('data_inicio_funcao'))
        func['tempo_empresa'] = calcular_tempo(func.get('data_inicio_empresa'))
    
    return jsonify(funcionarios)

@app.route('/api/area/<int:area_id>', methods=['DELETE'])
def api_excluir_area(area_id):
    """Desativa uma área (soft delete) - qualquer usuário autenticado"""
    from logic import excluir_area
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    resultado = excluir_area(area_id)
    print(f"🔍 Resultado de excluir_area({area_id}): {resultado}")
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao desativar área'}), 400

@app.route('/api/area/<int:area_id>/organograma-url', methods=['GET'])
def api_organograma_url(area_id):
    """Retorna URL assinada para o organograma (validade 5 minutos)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT organograma_url, organograma_nome
                FROM informacoes_area
                WHERE id_area = :area_id
            """)
            result = conn.execute(query, {'area_id': area_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Organograma não encontrado'}), 404
            
            url_completa = result[0]
            nome = result[1] or 'organograma'
            
            # Extrair o caminho da URL pública
            if '/organogramas/' in url_completa:
                caminho = url_completa.split('/organogramas/')[-1]
            else:
                caminho = url_completa
            
            print(f"📎 Caminho extraído: {caminho}")
            
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            supabase = SupabaseClient.get_instance()
            
            # Gerar URL assinada (expira em 300 segundos = 5 minutos)
            url_assinada = supabase.storage.from_('organogramas').create_signed_url(
                path=caminho,
                expires_in=300
            )
            
            return jsonify({
                'success': True,
                'url': url_assinada['signedURL'],
                'nome': nome
            })
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/salvar-area', methods=['POST'])
def api_salvar_area():
    from logic import salvar_area
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    dados = request.json
    
    if not dados.get('nome'):
        return jsonify({'success': False, 'error': 'Nome da área é obrigatório'}), 400
    
    if not dados.get('gestor'):
        return jsonify({'success': False, 'error': 'Gestor é obrigatório'}), 400
    
    resultado = salvar_area(dados)
    
    if resultado:
        return jsonify({'success': True, 'id': resultado})
    return jsonify({'success': False, 'error': 'Falha ao salvar área'}), 400

@app.route('/api/area/<int:area_id>', methods=['PUT'])
def api_atualizar_area(area_id):
    from logic import atualizar_area
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    dados = request.json
    dados['superintendente'] = dados.get('superintendente', '')
    dados['diretor'] = dados.get('diretor', '')

    resultado = atualizar_area(area_id, dados)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao atualizar área'}), 400

@app.route('/api/area/<int:area_id>/reativar', methods=['PUT'])
def api_reativar_area(area_id):
    """Reativa uma área - qualquer usuário autenticado"""
    from logic import reativar_area
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    resultado = reativar_area(area_id)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao reativar área'}), 400

@app.route('/api/area/<int:area_id>/todos-funcionarios')
def api_area_todos_funcionarios(area_id):
    """Retorna TODOS os funcionários de uma área (ativos e inativos) com tempo calculado"""
    from logic import listar_funcionarios_area_todos
    
    df = listar_funcionarios_area_todos(area_id)
    
    if df.empty:
        return jsonify([])
    
    funcionarios = df.to_dict(orient='records')
    
    # Adicionar tempo calculado para cada funcionário
    for func in funcionarios:
        func['tempo_funcao'] = calcular_tempo(func.get('data_inicio_funcao'))
        func['tempo_empresa'] = calcular_tempo(func.get('data_inicio_empresa'))
    
    return jsonify(funcionarios)

@app.route('/api/funcionario/<int:funcionario_id>', methods=['DELETE'])
def api_excluir_funcionario(funcionario_id):
    """Exclui um funcionário - qualquer usuário autenticado"""
    from logic import excluir_funcionario
    
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    resultado = excluir_funcionario(funcionario_id)
    
    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao excluir funcionário'}), 400

@app.route('/api/funcionario/<int:funcionario_id>', methods=['PUT'])
def api_atualizar_funcionario(funcionario_id):
    """Atualiza um funcionário - qualquer usuário autenticado"""
    from logic import atualizar_funcionario

    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    dados = request.json
    
    # ⭐ VALIDAÇÃO BÁSICA
    if not dados.get('nome'):
        return jsonify({'success': False, 'error': 'Nome do funcionário é obrigatório'}), 400
    
    resultado = atualizar_funcionario(funcionario_id, dados)

    if resultado:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Falha ao atualizar funcionário'}), 400

@app.route('/api/funcionario/<int:funcionario_id>')
def api_funcionario_detalhes(funcionario_id):
    """Retorna os dados de um funcionário específico"""
    from logic import buscar_funcionario_por_id

    funcionario = buscar_funcionario_por_id(funcionario_id)

    if funcionario:
        return jsonify(funcionario)
    return jsonify({}), 404

@app.route('/api/salvar-funcionario', methods=['POST'])
def api_salvar_funcionario():
    """Salva um novo funcionário - qualquer usuário autenticado"""
    from logic import salvar_funcionario

    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    dados = request.json

    if not dados.get('nome'):
        return jsonify({'success': False, 'error': 'Nome do funcionário é obrigatório'}), 400
    
    if not dados.get('id_area'):
        return jsonify({'success': False, 'error': 'Área é obrigatória'}), 400
    
    resultado = salvar_funcionario(dados)
    
    if resultado:
        return jsonify({'success': True, 'id': resultado})
    return jsonify({'success': False, 'error': 'Falha ao salvar funcionário'}), 400

# ============================================================
# DETALHAMENTO DOS PROCESSOS
# ============================================================

@app.route('/api/risco-etapa/salvar', methods=['POST'])
def api_risco_etapa_salvar():
    """Salva um novo risco de etapa ou atualiza existente"""
    from database import engine
    from sqlalchemy import text

    data = request.json
    risco_id = data.get('id')
    etapa_id = data.get('etapa_id')
    auditoria_id = data.get('auditoria_id')

    # 1. Identificação do Risco
    nome_risco = data.get('nome_risco', '')
    categoria = data.get('categoria', '')

    # 2. Causa e Análise
    fator_risco = data.get('fator_risco', '')
    consequencia = data.get('consequencia', '')
    origem = data.get('origem', '')
    impacto_aceitavel = data.get('apetite_impacto', 'Médio')  # ⭐ CORRIGIDO: apetite_impacto
    probabilidade_aceitavel = data.get('apetite_probabilidade', 'Médio')  # ⭐ CORRIGIDO: apetite_probabilidade

    # 3. Avaliação do Risco
    impacto = data.get('impacto', 'Médio')
    probabilidade = data.get('probabilidade', 'Médio')
    motivo_classificacao = data.get('motivo', '')  # ⭐ CORRIGIDO: motivo (não motivo_classificacao)
    info_adicional = data.get('info_adicional', '')
    financeiro = data.get('financeiro', False)
    
    # ⭐ NOVO: Status do risco
    ativo = data.get('ativo', True)  # Default: True (ativo)

    # 4. Tratamento
    tratamento = data.get('tratamento', '')
    desc_tratamento = data.get('desc_tratamento', '')
    prazo_implantacao = data.get('prazo_implantacao') or None
    descricao_prazo = data.get('descricao_prazo', '')

    # 5. Relacionamentos
    causas = data.get('causas', [])
    if isinstance(causas, list):
        causas_str = ', '.join(causas)
    else:
        causas_str = causas

    # Validação básica
    if not etapa_id:
        return jsonify({'success': False, 'error': 'Etapa é obrigatória'}), 400
    
    if not nome_risco:
        return jsonify({'success': False, 'error': 'Nome do risco é obrigatório'}), 400

    # Calcular a magnitude (score) baseado em impacto e probabilidade
    MAPA_RISCO = {
        ("Muito Alto", "Muito Alto"): 15, ("Alto", "Muito Alto"): 14,
        ("Médio", "Muito Alto"): 13, ("Baixo", "Muito Alto"): 12,
        ("Muito Alto", "Alto"): 11, ("Alto", "Alto"): 10,
        ("Médio", "Alto"): 9, ("Baixo", "Alto"): 8,
        ("Muito Alto", "Médio"): 7, ("Alto", "Médio"): 6,
        ("Médio", "Médio"): 5, ("Baixo", "Médio"): 4,
        ("Muito Alto", "Baixo"): 3, ("Alto", "Baixo"): 2,
        ("Médio", "Baixo"): 1, ("Baixo", "Baixo"): 0
    }

    magnitude = MAPA_RISCO.get((impacto, probabilidade), 0)

    try:
        with engine.connect() as conn:
            if risco_id:
                # EDIÇÃO: atualizar risco existente
                query = text("""
                    UPDATE riscos_etapa
                    SET nome_risco = :nome_risco,
                        categoria = :categoria,
                        fator_risco = :fator_risco,
                        consequencia = :consequencia,
                        impacto = :impacto,
                        probabilidade = :probabilidade,
                        magnitude = :magnitude,
                        impacto_aceitavel = :impacto_aceitavel,
                        probabilidade_aceitavel = :probabilidade_aceitavel,
                        tratamento = :tratamento,
                        origem = :origem,
                        desc_tratamento = :desc_tratamento,
                        financeiro = :financeiro,
                        info_adicional = :info_adicional,
                        motivo_classificacao = :motivo_classificacao,
                        prazo_implantacao = :prazo_implantacao,
                        descricao_prazo = :descricao_prazo,
                        causas = :causas,
                        ativo = :ativo,  -- ⭐ NOVO
                        updated_at = NOW()
                    WHERE id = :risco_id
                """)

                conn.execute(query, {
                    'risco_id': risco_id,
                    'nome_risco': nome_risco,
                    'categoria': categoria,
                    'fator_risco': fator_risco,
                    'consequencia': consequencia,
                    'impacto': impacto,
                    'probabilidade': probabilidade,
                    'magnitude': magnitude,
                    'impacto_aceitavel': impacto_aceitavel,
                    'probabilidade_aceitavel': probabilidade_aceitavel,
                    'tratamento': tratamento,
                    'origem': origem,
                    'desc_tratamento': desc_tratamento,
                    'financeiro': financeiro,
                    'info_adicional': info_adicional,
                    'motivo_classificacao': motivo_classificacao,
                    'prazo_implantacao': prazo_implantacao,
                    'descricao_prazo': descricao_prazo,
                    'causas': causas_str,
                    'ativo': ativo  # ⭐ NOVO
                })

                print(f"✏️ Risco de etapa {risco_id} atualizado!")
                novo_id = risco_id
            
            else:
                # NOVO RISCO: inserir risco
                query = text("""
                    INSERT INTO riscos_etapa (
                        etapa_id, auditoria_id, nome_risco, categoria,
                        fator_risco, consequencia, impacto, probabilidade,
                        magnitude, impacto_aceitavel,
                        probabilidade_aceitavel, tratamento, origem, causas,
                        desc_tratamento, financeiro, info_adicional, 
                        motivo_classificacao, prazo_implantacao, descricao_prazo, 
                        ativo, created_at  -- ⭐ NOVO: ativo
                    ) VALUES (
                        :etapa_id, :auditoria_id, :nome_risco, :categoria,
                        :fator_risco, :consequencia, :impacto, :probabilidade,
                        :magnitude, :impacto_aceitavel, :probabilidade_aceitavel, 
                        :tratamento, :origem, :causas,
                        :desc_tratamento, :financeiro, :info_adicional,
                        :motivo_classificacao, :prazo_implantacao, :descricao_prazo,
                        :ativo, NOW()  -- ⭐ NOVO: ativo
                    )
                    RETURNING id
                """)

                result = conn.execute(query, {
                    'etapa_id': etapa_id,
                    'auditoria_id': auditoria_id,
                    'nome_risco': nome_risco,
                    'categoria': categoria,
                    'fator_risco': fator_risco,
                    'consequencia': consequencia,
                    'impacto': impacto,
                    'probabilidade': probabilidade,
                    'magnitude': magnitude,
                    'impacto_aceitavel': impacto_aceitavel,
                    'probabilidade_aceitavel': probabilidade_aceitavel,
                    'tratamento': tratamento,
                    'origem': origem,
                    'desc_tratamento': desc_tratamento,
                    'financeiro': financeiro,
                    'info_adicional': info_adicional,
                    'motivo_classificacao': motivo_classificacao,
                    'prazo_implantacao': prazo_implantacao,
                    'descricao_prazo': descricao_prazo,
                    'causas': causas_str,
                    'ativo': ativo  # ⭐ NOVO
                })

                novo_id = result.fetchone()[0]
                print(f"✅ Novo risco de etapa criado! ID: {novo_id}")

            conn.commit()

            return jsonify({
                'success': True,
                'message': 'Risco salvo com sucesso',
                'risco_id': novo_id
            })
    except Exception as e:
        print(f"❌ Erro ao salvar risco de etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/risco-etapa/<int:risco_id>')
def api_risco_etapa_detalhes(risco_id):
    """Retorna os dados de um risco específico para edição"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, etapa_id, nome_risco, categoria, fator_risco,
                       consequencia, impacto, probabilidade, magnitude,
                       impacto_aceitavel, probabilidade_aceitavel, tratamento, origem, desc_tratamento, motivo_classificacao, financeiro,
                       info_adicional, ativo, causas, prazo_implantacao
                FROM riscos_etapa
                WHERE id = :risco_id
            """)
            result = conn.execute(query, {'risco_id': risco_id}).fetchone()

            if not result:
                return jsonify({'success': False, 'error': 'Risco não encontrado'}), 404

            risco = {
                'id': result[0],
                'etapa_id': result[1],
                'nome_risco': result[2] or '',
                'categoria': result[3] or '',
                'fator_risco': result[4] or '',
                'consequencia': result[5] or '',
                'impacto': result[6] or 'Médio',
                'probabilidade': result[7] or 'Médio',
                'magnitude': result[8] or 0,
                'impacto_aceitavel': result[9] or 'Médio',
                'probabilidade_aceitavel': result[10] or 'Médio',
                'tratamento': result[11] or '',
                'origem': result[12] or '',
                'desc_tratamento': result[13] or '',
                'motivo_classificacao': result[14] or '',
                'financeiro': result[15] or False,
                'info_adicional': result[16] or '',
                'ativo': result[16] if result[17] is not None else True,
                'causas': [c.strip() for c in result[18].split(',')] if result[18] else [],
                'prazo_implantacao': result[19] or ''
            }

            return jsonify({'success': True, 'risco': risco})

    except Exception as e:
        print(f"❌ Erro ao buscar risco: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/risco-etapa/<int:risco_id>/status', methods=['PUT'])
def api_alternar_status_risco(risco_id):
    """Alterna o status (ativo/inativo) de um risco"""
    from database import engine
    from sqlalchemy import text
    
    try:
        data = request.json
        novo_status = data.get('ativo')
        
        if novo_status is None:
            return jsonify({'success': False, 'error': 'Status não informado'}), 400
        
        with engine.connect() as conn:
            query = text("""
                UPDATE riscos_etapa 
                SET ativo = :ativo, updated_at = NOW()
                WHERE id = :risco_id
                RETURNING id
            """)
            
            result = conn.execute(query, {
                'ativo': novo_status,
                'risco_id': risco_id
            })
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Risco não encontrado'}), 404
            
            conn.commit()
            
            status_texto = 'ativado' if novo_status else 'desativado'
            return jsonify({
                'success': True, 
                'message': f'Risco {status_texto} com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao alternar status do risco: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/riscos')
def api_etapa_riscos(etapa_id):
    """Retorna todos os riscos associados a uma etapa"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome_risco, categoria, fator_risco, consequencia,
                       impacto, probabilidade, magnitude, impacto_aceitavel, probabilidade_aceitavel, tratamento,
                       origem, desc_tratamento, motivo_classificacao, financeiro, info_adicional, ativo, causas, prazo_implantacao
                FROM riscos_etapa
                WHERE etapa_id = :etapa_id AND (ativo IS NULL OR ativo = true)
                ORDER BY id
            """)
            
            # ← IMPORTANTE: ESTA LINHA PRECISA ESTAR DENTRO DO WITH!
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchall()

            riscos = []
            for row in result:
                riscos.append({
                    'id': row[0],
                    'nome_risco': row[1] or '',
                    'categoria': row[2] or '',
                    'fator_risco': row[3] or '',
                    'consequencia': row[4] or '',
                    'impacto': row[5] or 'Médio',
                    'probabilidade': row[6] or 'Médio',
                    'magnitude': row[7] or 0,
                    'impacto_aceitavel': row[8] or 'Médio',
                    'probabilidade_aceitavel': row[9] or 'Médio',
                    'tratamento': row[10] or '',
                    'origem': row[11] or '',
                    'desc_tratamento': row[12] or '',
                    'motivo_classificacao': row[13] or '',
                    'financeiro': row[14] or False,
                    'info_adicional': row[15] or '',
                    'ativo': row[16] if row[16] is not None else True,
                    'causas': [c.strip() for c in row[17].split(',')] if row[17] else [],
                    'prazo_implantacao': row[18] or ''
                })

            return jsonify({'success': True, 'riscos': riscos})
    
    except Exception as e:
        print(f"❌ Erro ao buscar riscos da etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/riscos/count')
def api_etapa_riscos_count(etapa_id):
    """Retorna a quantidade de riscos de uma etapa"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) 
                FROM riscos_etapa 
                WHERE etapa_id = :etapa_id 
                AND (ativo IS NULL OR ativo = true)
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()

            # result[0] contém o número de riscos
            total = result[0] if result[0] else 0
            
            return jsonify({
                'success': True, 
                'total': total
            })
            
    except Exception as e:
        print(f"❌ Erro ao contar riscos da etapa {etapa_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/riscos/todos')
def api_etapa_riscos_todos(etapa_id):
    """Retorna TODOS os riscos (ativos e inativos) - usado para edição"""
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # ⭐ SEM o filtro de ativo
            query = text("""
                SELECT id, nome_risco, categoria, fator_risco, consequencia,
                       impacto, probabilidade, magnitude, impacto_aceitavel, 
                       probabilidade_aceitavel, tratamento,
                       origem, desc_tratamento, motivo_classificacao, 
                       financeiro, info_adicional, ativo, causas, prazo_implantacao
                FROM riscos_etapa
                WHERE etapa_id = :etapa_id
                ORDER BY id
            """)
            
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchall()

            riscos = []
            for row in result:
                riscos.append({
                    'id': row[0],
                    'nome_risco': row[1] or '',
                    'categoria': row[2] or '',
                    'fator_risco': row[3] or '',
                    'consequencia': row[4] or '',
                    'impacto': row[5] or 'Médio',
                    'probabilidade': row[6] or 'Médio',
                    'magnitude': row[7] or 0,
                    'impacto_aceitavel': row[8] or 'Médio',
                    'probabilidade_aceitavel': row[9] or 'Médio',
                    'tratamento': row[10] or '',
                    'origem': row[11] or '',
                    'desc_tratamento': row[12] or '',
                    'motivo_classificacao': row[13] or '',
                    'financeiro': row[14] or False,
                    'info_adicional': row[15] or '',
                    'ativo': row[16] if row[16] is not None else True,
                    'causas': [c.strip() for c in row[17].split(',')] if row[17] else [],
                    'prazo_implantacao': row[18] or ''
                })

            return jsonify({'success': True, 'riscos': riscos})
    
    except Exception as e:
        print(f"❌ Erro ao buscar riscos da etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/detalhamento_riscos')
def detalhamento_riscos():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()

    return render_template('detalhamento_riscos.html', areas=areas)

@app.route('/detalhamento_controles')
def detalhamento_controles():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    
    return render_template('detalhamento_controles.html', areas=areas)

@app.route('/matriz_achados')
def matriz_achados():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    from logic import carregar_areas_banco
    areas = carregar_areas_banco()
    
    return render_template('matriz_achados.html', areas=areas)

@app.route('/api/etapa/<int:etapa_id>/download/<tipo>', methods=['GET'])
def api_download_arquivo(etapa_id, tipo):
    """
    Baixa um arquivo da etapa (manual, diagrama, etc)
    """
    from database import engine
    from sqlalchemy import text
    from flask import redirect, send_file
    import io
    
    try:
        with engine.connect() as conn:
            if tipo == 'manual':
                # 🔥 CORRIGIDO: Buscar apenas manual_url e manual_nome
                query = text("""
                    SELECT manual_url, manual_nome 
                    FROM etapas_processo 
                    WHERE id = :etapa_id
                """)
                result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
                
                if not result:
                    return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
                
                # 🔥 Acessar pelos índices corretos (0 e 1)
                manual_url = result[0]
                manual_nome = result[1]
                
                if not manual_url or manual_url.strip() == '':
                    return jsonify({'success': False, 'error': 'Nenhum manual anexado'}), 404
                
                # Redirecionar para a URL do Supabase
                return redirect(manual_url)
            
            elif tipo == 'diagrama':
                query = text("""
                    SELECT diagrama_bpmn, diagrama_nome 
                    FROM etapas_processo 
                    WHERE id = :etapa_id
                """)
                result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
                
                if not result:
                    return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
                
                diagrama_bytes = result[0]
                diagrama_nome = result[1]
                
                if not diagrama_bytes:
                    return jsonify({'success': False, 'error': 'Nenhum diagrama anexado'}), 404
                
                return send_file(
                    io.BytesIO(diagrama_bytes),
                    download_name=diagrama_nome or 'diagrama.bpmn',
                    as_attachment=True
                )
            
            elif tipo == 'mapeamento':
                query = text("""
                    SELECT arquivo_mapeamento, arquivo_mapeamento_nome 
                    FROM etapas_processo 
                    WHERE id = :etapa_id
                """)
                result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
                
                if not result:
                    return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
                
                mapeamento_bytes = result[0]
                mapeamento_nome = result[1]
                
                if not mapeamento_bytes:
                    return jsonify({'success': False, 'error': 'Nenhum mapeamento anexado'}), 404
                
                return send_file(
                    io.BytesIO(mapeamento_bytes),
                    download_name=mapeamento_nome or 'mapeamento.pdf',
                    as_attachment=True
                )
            
            else:
                return jsonify({'success': False, 'error': f'Tipo de arquivo inválido: {tipo}'}), 400
            
    except Exception as e:
        print(f"❌ Erro ao baixar arquivo: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/excluir', methods=['DELETE'])
def api_excluir_etapa(etapa_id):
    """Remove uma etapa do processo"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("DELETE FROM etapas_processo WHERE id = :etapa_id")
            conn.execute(query, {'etapa_id': etapa_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Etapa removida com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>')
def api_etapa_detalhes(etapa_id):
    """Retorna os dados de uma etapa específica para edição"""
    from database import engine
    from sqlalchemy import text
    import base64
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, processo_id, codigo_etapa, nome_etapa, descricao_etapa,
                       como_e_feito, objetivo_etapa, status_etapa, criticidade_etapa,
                       politica_interna, analise_critica, sugestao_melhoria,
                       necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                       executores_etapa,
                       diagrama_bpmn, diagrama_nome, diagrama_tipo,
                       manual_nome, manual_url,
                       arquivo_mapeamento, arquivo_mapeamento_nome, arquivo_mapeamento_tipo,
                       -- ⭐ NOVO CAMPO
                       manual_em_andamento
                FROM etapas_processo
                WHERE id = :etapa_id
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
            
            # ===== CONVERTER DIAGRAMA PARA BASE64 =====
            diagrama_base64 = None
            if result[16]:  # diagrama_bpmn
                diagrama_base64 = base64.b64encode(result[16]).decode('utf-8')
                        
            # ===== CONVERTER ARQUIVO DE MAPEAMENTO PARA BASE64 =====
            arquivo_mapeamento_base64 = None
            if result[21]:  # arquivo_mapeamento
                arquivo_mapeamento_base64 = base64.b64encode(result[21]).decode('utf-8')
            
            etapa = {
                'id': result[0],
                'processo_id': result[1],
                'codigo_etapa': result[2] or '',
                'nome_etapa': result[3] or '',
                'descricao_etapa': result[4] or '',
                'como_e_feito': result[5] or '',
                'objetivo_etapa': result[6] or '',
                'status_etapa': result[7] or 'Ativa',
                'criticidade_etapa': result[8] or 'Em aprovação',
                'politica_interna': result[9] or '',
                'analise_critica': result[10] or '',
                'sugestao_melhoria': result[11] or '',
                'necessidade_implantacao': result[12] or '',
                'ganho_previsto': result[13] or '',
                'obrigacoes_regulatorias': result[14] or '',
                'executores_etapa': result[15] or '',
                
                # Diagrama
                'diagrama_base64': diagrama_base64,
                'diagrama_nome': result[17] or '',
                'diagrama_tipo': result[18] or '',
                
                # Manual
                'manual_nome': result[19] or '',
                'manual_url': result[20] or '',
                
                # Arquivo de Mapeamento
                'arquivo_mapeamento_base64': arquivo_mapeamento_base64,
                'arquivo_mapeamento_nome': result[22] or '',
                'arquivo_mapeamento_tipo': result[23] or '',
                
                # ⭐ NOVO CAMPO
                'manual_em_andamento': result[24] if len(result) > 24 and result[24] else False
            }
            
            return jsonify({'success': True, 'etapa': etapa})
            
    except Exception as e:
        print(f"❌ Erro ao buscar etapa: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/etapa/gerar-codigo')
def api_gerar_codigo_etapa():
    """Gera o próximo código de etapa para um processo"""
    from database import engine
    from sqlalchemy import text
    
    processo_id = request.args.get('processo_id')
    if not processo_id:
        return jsonify({'error': 'processo_id é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            # Buscar o código do processo
            query_processo = text("SELECT codigo_processo FROM processos WHERE id = :processo_id")
            processo = conn.execute(query_processo, {'processo_id': processo_id}).fetchone()
            
            if not processo:
                return jsonify({'error': 'Processo não encontrado'}), 404
            
            codigo_processo = processo[0]
            
            # Buscar o maior número de etapa para este processo
            query_etapas = text("""
                SELECT MAX(CAST(COALESCE(REGEXP_REPLACE(codigo_etapa, '^.*\\.', ''), '0') AS INTEGER))
                FROM etapas_processo
                WHERE processo_id = :processo_id
            """)
            result = conn.execute(query_etapas, {'processo_id': processo_id}).fetchone()
            
            ultimo_numero = result[0] if result[0] else 0
            novo_numero = ultimo_numero + 1
            
            codigo_etapa = f"{codigo_processo}.{novo_numero}"
            
            return jsonify({'success': True, 'codigo_etapa': codigo_etapa})
            
    except Exception as e:
        print(f"❌ Erro ao gerar código da etapa: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/etapa/salvar', methods=['POST'])
def api_salvar_etapa():
    """Salva uma nova etapa ou atualiza existente"""
    from database import engine
    from sqlalchemy import text
    import base64
    import json
    
    data = request.json
    etapa_id = data.get('id')
    processo_id = data.get('processo_id')
    auditoria_id = data.get('auditoria_id')
    codigo_etapa = data.get('codigo_etapa')
    nome_etapa = data.get('nome_etapa')
    descricao_etapa = data.get('descricao_etapa', '')
    como_e_feito = data.get('como_e_feito', '')
    objetivo_etapa = data.get('objetivo_etapa', '')
    status_etapa = data.get('status_etapa', 'Ativa')
    criticidade_etapa = data.get('criticidade_etapa', 'Em aprovação')
    politica_interna = data.get('politica_interna', '')
    analise_critica = data.get('analise_critica', '')
    sugestao_melhoria = data.get('sugestao_melhoria', '')
    necessidade_implantacao = data.get('necessidade_implantacao', '')
    ganho_previsto = data.get('ganho_previsto', '')
    obrigacoes_regulatorias = data.get('obrigacoes_regulatorias', '[]')
    executores_etapa = data.get('executores_etapa', '')
    manual_em_andamento = data.get('manual_em_andamento', False)
    
    # ⭐⭐⭐ CORREÇÃO: Se auditoria_id não veio, buscar do processo
    if not auditoria_id and processo_id:
        try:
            with engine.connect() as conn:
                busca_query = text("SELECT auditoria_id FROM processos WHERE id = :processo_id")
                result = conn.execute(busca_query, {'processo_id': processo_id}).fetchone()
                if result and result[0]:
                    auditoria_id = result[0]
                    print(f"🔍 Auditoria_id {auditoria_id} obtido do processo {processo_id}")
        except Exception as e:
            print(f"⚠️ Erro ao buscar auditoria_id do processo: {e}")
    
    # Processar upload de arquivos (vêm como base64)
    diagrama_bytes = None
    diagrama_nome = data.get('diagrama_nome')
    diagrama_tipo = data.get('diagrama_tipo')
    
    if data.get('diagrama_base64'):
        diagrama_bytes = base64.b64decode(data['diagrama_base64'].split(',')[1] if ',' in data['diagrama_base64'] else data['diagrama_base64'])
    
    # 🔥 CORRIGIDO: Removido processamento de manual_base64
    manual_nome = data.get('manual_nome')
    manual_url = data.get('manual_url')
    
    # Processar upload do arquivo do mapeamento
    arquivo_mapeamento_bytes = None
    arquivo_mapeamento_nome = data.get('arquivo_mapeamento_nome')
    arquivo_mapeamento_tipo = data.get('arquivo_mapeamento_tipo')

    if data.get('arquivo_mapeamento_base64'):
        arquivo_mapeamento_bytes = base64.b64decode(data['arquivo_mapeamento_base64'].split(',')[1] if ',' in data['arquivo_mapeamento_base64'] else data['arquivo_mapeamento_base64'])

    # ⭐⭐⭐ PROCESSAR OBRIGAÇÕES REGULATÓRIAS - VERSÃO CORRIGIDA ⭐⭐⭐
    try:
        if isinstance(obrigacoes_regulatorias, str):
            obrigacoes = json.loads(obrigacoes_regulatorias) if obrigacoes_regulatorias else []
        else:
            obrigacoes = obrigacoes_regulatorias or []
        
        if obrigacoes and isinstance(obrigacoes, list):
            for idx, obrigacao in enumerate(obrigacoes):
                if 'arquivo_base64' in obrigacao:
                    del obrigacao['arquivo_base64']
                    print(f"⚠️ Obrigação {idx}: removido campo arquivo_base64")
                if '_upload_file' in obrigacao:
                    del obrigacao['_upload_file']
                if '_file_data' in obrigacao:
                    del obrigacao['_file_data']
                if '_index' in obrigacao:
                    del obrigacao['_index']
                
                if 'titulo' not in obrigacao or not obrigacao['titulo']:
                    obrigacao['titulo'] = 'INEXISTENTE'
                if 'descricao_completa' not in obrigacao:
                    obrigacao['descricao_completa'] = 'INEXISTENTE'
                if 'arquivo_url' not in obrigacao:
                    obrigacao['arquivo_url'] = ''
                if 'arquivo_nome' not in obrigacao:
                    obrigacao['arquivo_nome'] = ''
                if 'arquivo_tamanho' not in obrigacao:
                    obrigacao['arquivo_tamanho'] = 0
                if 'prazo' not in obrigacao:
                    obrigacao['prazo'] = ''
                if 'obrigatorio' not in obrigacao:
                    obrigacao['obrigatorio'] = False
                if 'orgao_regulador' not in obrigacao:
                    obrigacao['orgao_regulador'] = ''
                if 'documento_necessario' not in obrigacao:
                    obrigacao['documento_necessario'] = ''
                
                print(f"📋 Obrigação {idx}: {obrigacao.get('titulo')} - URL: {obrigacao.get('arquivo_url', 'sem arquivo')}")
        
        obrigacoes_regulatorias = json.dumps(obrigacoes, ensure_ascii=False)
        print(f"✅ Obrigações processadas: {len(obrigacoes)} itens (sem Base64)")
        
    except Exception as e:
        print(f"⚠️ Erro ao processar obrigações regulatórias: {e}")
        import traceback
        traceback.print_exc()
        pass

    if not processo_id:
        return jsonify({'success': False, 'error': 'ID do processo é obrigatório'}), 400
    
    if not nome_etapa:
        return jsonify({'success': False, 'error': 'Nome da etapa é obrigatório'}), 400
    
    try:
        with engine.connect() as conn:
            if etapa_id:
                # ========== EDIÇÃO: atualizar etapa existente ==========
                
                remover_diagrama = data.get('remover_diagrama', False)
                remover_manual = data.get('remover_manual', False)
                
                if remover_diagrama:
                    diagrama_bytes = None
                    diagrama_nome = None
                    diagrama_tipo = None
                    print(f"🗑️ Removendo diagrama da etapa {etapa_id}")
                
                # 🔥 CORRIGIDO: Se remover_manual, limpar URL e nome
                if remover_manual:
                    manual_url = None
                    manual_nome = None
                    print(f"🗑️ Removendo manual da etapa {etapa_id}")
                
                params = {
                    'etapa_id': etapa_id,
                    'nome_etapa': nome_etapa,
                    'descricao_etapa': descricao_etapa,
                    'como_e_feito': como_e_feito,
                    'objetivo_etapa': objetivo_etapa,
                    'status_etapa': status_etapa,
                    'criticidade_etapa': criticidade_etapa,
                    'politica_interna': politica_interna,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto,
                    'obrigacoes_regulatorias': obrigacoes_regulatorias,
                    'executores_etapa': executores_etapa,
                    'manual_em_andamento': manual_em_andamento
                }
                
                if auditoria_id:
                    params['auditoria_id'] = auditoria_id
                
                base_fields = """
                    nome_etapa = :nome_etapa,
                    descricao_etapa = :descricao_etapa,
                    como_e_feito = :como_e_feito,
                    objetivo_etapa = :objetivo_etapa,
                    status_etapa = :status_etapa,
                    criticidade_etapa = :criticidade_etapa,
                    politica_interna = :politica_interna,
                    analise_critica = :analise_critica,
                    sugestao_melhoria = :sugestao_melhoria,
                    necessidade_implantacao = :necessidade_implantacao,
                    ganho_previsto = :ganho_previsto,
                    obrigacoes_regulatorias = :obrigacoes_regulatorias,
                    executores_etapa = :executores_etapa,
                    manual_em_andamento = :manual_em_andamento
                """
                
                if auditoria_id:
                    base_fields += ", auditoria_id = :auditoria_id"
                
                update_fields = []
                
                # Diagrama
                if data.get('diagrama_base64') or remover_diagrama:
                    update_fields.append("diagrama_bpmn = :diagrama_bpmn")
                    update_fields.append("diagrama_nome = :diagrama_nome")
                    update_fields.append("diagrama_tipo = :diagrama_tipo")
                    params['diagrama_bpmn'] = diagrama_bytes
                    params['diagrama_nome'] = diagrama_nome
                    params['diagrama_tipo'] = diagrama_tipo
                
                # 🔥 CORRIGIDO: Manual - usar URL em vez de Base64
                if manual_url is not None or remover_manual:
                    update_fields.append("manual_nome = :manual_nome")
                    update_fields.append("manual_url = :manual_url")
                    params['manual_nome'] = manual_nome
                    params['manual_url'] = manual_url
                
                # Mapeamento
                remover_arquivo_mapeamento = data.get('remover_arquivo_mapeamento', False)
                if data.get('arquivo_mapeamento_base64') or remover_arquivo_mapeamento:
                    update_fields.append("arquivo_mapeamento = :arquivo_mapeamento")
                    update_fields.append("arquivo_mapeamento_nome = :arquivo_mapeamento_nome")
                    update_fields.append("arquivo_mapeamento_tipo = :arquivo_mapeamento_tipo")
                    params['arquivo_mapeamento'] = arquivo_mapeamento_bytes
                    params['arquivo_mapeamento_nome'] = arquivo_mapeamento_nome
                    params['arquivo_mapeamento_tipo'] = arquivo_mapeamento_tipo
                
                if update_fields:
                    query_sql = f"""
                        UPDATE etapas_processo
                        SET {base_fields}, {', '.join(update_fields)}, updated_at = NOW()
                        WHERE id = :etapa_id
                    """
                else:
                    query_sql = f"""
                        UPDATE etapas_processo
                        SET {base_fields}, updated_at = NOW()
                        WHERE id = :etapa_id
                    """
                
                query = text(query_sql)
                conn.execute(query, params)
                
                print(f"✏️ Etapa {etapa_id} atualizada com sucesso! auditoria_id={auditoria_id}")
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Etapa salva com sucesso',
                    'codigo_etapa': codigo_etapa,
                    'etapa_id': etapa_id,
                    'id': etapa_id
                })
                
            else:
                # ========== NOVA ETAPA: inserir ==========
                
                if not auditoria_id and processo_id:
                    busca_query = text("SELECT auditoria_id FROM processos WHERE id = :processo_id")
                    result = conn.execute(busca_query, {'processo_id': processo_id}).fetchone()
                    if result and result[0]:
                        auditoria_id = result[0]
                        print(f"🔍 Nova etapa - auditoria_id {auditoria_id} obtido do processo {processo_id}")
                
                if not codigo_etapa:
                    query_codigo = text("SELECT codigo_processo FROM processos WHERE id = :processo_id")
                    processo_codigo = conn.execute(query_codigo, {'processo_id': processo_id}).fetchone()
                    
                    if processo_codigo:
                        codigo_base = processo_codigo[0]
                        query_max = text("""
                            SELECT MAX(CAST(SUBSTRING(codigo_etapa FROM '[^.]+$') AS INTEGER))
                            FROM etapas_processo
                            WHERE processo_id = :processo_id
                        """)
                        max_result = conn.execute(query_max, {'processo_id': processo_id}).fetchone()
                        proximo_num = (max_result[0] or 0) + 1
                        codigo_etapa = f"{codigo_base}.{proximo_num}"
                    else:
                        codigo_etapa = f"{processo_id}.1"
                
                query = text("""
                    INSERT INTO etapas_processo (
                        processo_id, auditoria_id, codigo_etapa, nome_etapa,
                        descricao_etapa, como_e_feito, objetivo_etapa,
                        status_etapa, criticidade_etapa,
                        politica_interna, analise_critica, sugestao_melhoria,
                        necessidade_implantacao, ganho_previsto, obrigacoes_regulatorias,
                        executores_etapa,
                        diagrama_bpmn, diagrama_nome, diagrama_tipo,
                        manual_nome, manual_url,
                        arquivo_mapeamento, arquivo_mapeamento_nome, arquivo_mapeamento_tipo,
                        manual_em_andamento,
                        created_at
                    ) VALUES (
                        :processo_id, :auditoria_id, :codigo_etapa, :nome_etapa,
                        :descricao_etapa, :como_e_feito, :objetivo_etapa,
                        :status_etapa, :criticidade_etapa,
                        :politica_interna, :analise_critica, :sugestao_melhoria,
                        :necessidade_implantacao, :ganho_previsto, :obrigacoes_regulatorias,
                        :executores_etapa,
                        :diagrama_bpmn, :diagrama_nome, :diagrama_tipo,
                        :manual_nome, :manual_url,
                        :arquivo_mapeamento, :arquivo_mapeamento_nome, :arquivo_mapeamento_tipo,
                        :manual_em_andamento,
                        NOW()
                    )
                    RETURNING id
                """)
                
                result = conn.execute(query, {
                    'processo_id': processo_id,
                    'auditoria_id': auditoria_id,
                    'codigo_etapa': codigo_etapa,
                    'nome_etapa': nome_etapa,
                    'descricao_etapa': descricao_etapa,
                    'como_e_feito': como_e_feito,
                    'objetivo_etapa': objetivo_etapa,
                    'status_etapa': status_etapa,
                    'criticidade_etapa': criticidade_etapa,
                    'politica_interna': politica_interna,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto,
                    'obrigacoes_regulatorias': obrigacoes_regulatorias,
                    'executores_etapa': executores_etapa,
                    'diagrama_bpmn': diagrama_bytes,
                    'diagrama_nome': diagrama_nome,
                    'diagrama_tipo': diagrama_tipo,
                    'manual_nome': manual_nome,
                    'manual_url': manual_url,
                    'arquivo_mapeamento': arquivo_mapeamento_bytes,
                    'arquivo_mapeamento_nome': arquivo_mapeamento_nome,
                    'arquivo_mapeamento_tipo': arquivo_mapeamento_tipo,
                    "manual_em_andamento": manual_em_andamento
                })
                
                novo_id = result.fetchone()[0]
                
                print(f"✅ Nova etapa criada! ID: {novo_id}, Código: {codigo_etapa}, auditoria_id: {auditoria_id}")
                conn.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Etapa salva com sucesso',
                    'codigo_etapa': codigo_etapa,
                    'etapa_id': novo_id,
                    'id': novo_id
                })
            
    except Exception as e:
        print(f"❌ Erro ao salvar etapa: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload/detalhamento', methods=['POST'])
def api_upload_detalhamento():
    """
    Endpoint para upload de arquivos para o bucket detalhamento_etapas
    """
    try:
        # Verificar se o arquivo foi enviado
        if 'arquivo' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'success': False, 'error': 'Nome do arquivo vazio'}), 400
        
        # Obter dados adicionais
        tipo = request.form.get('tipo', 'obrigacao')
        etapa_id = request.form.get('etapa_id', 'temp')
        titulo_obrigacao = request.form.get('titulo_obrigacao', '')
        
        # Validar tipo de arquivo
        tipos_permitidos = ['application/pdf']
        if arquivo.content_type not in tipos_permitidos:
            return jsonify({'success': False, 'error': 'Apenas arquivos PDF são permitidos'}), 400
        
        # Validar tamanho (10MB)
        arquivo.seek(0, 2)
        tamanho = arquivo.tell()
        arquivo.seek(0)
        
        if tamanho > 10 * 1024 * 1024:
            return jsonify({'success': False, 'error': 'Arquivo muito grande (máx. 10MB)'}), 400
        
        
        
        # Gerar nome único
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        nome_unico = f"{timestamp}_{unique_id}"
        
        # Fazer upload para o bucket
        url_arquivo = upload_para_bucket_detalhamento(
            arquivo,
            nome_unico,
            tipo,
            etapa_id
        )
        
        if url_arquivo:
            return jsonify({
                'success': True,
                'url': url_arquivo,
                'nome_arquivo': arquivo.filename,
                'tamanho': tamanho,
                'nome_unico': nome_unico
            })
        else:
            return jsonify({'success': False, 'error': 'Erro ao fazer upload para o bucket'}), 500
        
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/etapa/<int:etapa_id>/download-manual', methods=['GET'])
def api_download_manual(etapa_id):
    """
    Baixa o manual da etapa usando a URL salva
    """
    from database import engine
    from sqlalchemy import text
    from flask import redirect
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT manual_url, manual_nome 
                FROM etapas_processo 
                WHERE id = :etapa_id
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Etapa não encontrada'}), 404
            
            manual_url = result[0]
            manual_nome = result[1]
            
            if not manual_url or manual_url.strip() == '':
                return jsonify({'success': False, 'error': 'Nenhum manual anexado'}), 404
            
            # 🔥 Redirecionar para a URL do Supabase (já é assinada)
            return redirect(manual_url)
            
    except Exception as e:
        print(f"❌ Erro ao baixar manual: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/remover-manual', methods=['DELETE'])
def api_remover_manual(etapa_id):
    """
    Remove o manual da etapa:
    - Exclui do storage
    - Limpa a URL na tabela
    """
    from database import engine
    from sqlalchemy import text
    
    try:
        data = request.json
        arquivo_url = data.get('arquivo_url') if data else None
        
        if not arquivo_url:
            return jsonify({'success': False, 'error': 'URL do manual não fornecida'}), 400
        
        print(f"🗑️ Removendo manual da etapa {etapa_id}")
        print(f"📎 URL do manual: {arquivo_url}")
        
        # 🔥 Excluir do storage
        excluir_arquivo_storage(arquivo_url)
        
        # 🔥 Limpar URL na tabela
        with engine.connect() as conn:
            query = text("""
                UPDATE etapas_processo 
                SET manual_url = NULL, 
                    manual_nome = NULL,
                    manual_em_andamento = FALSE,
                    updated_at = NOW()
                WHERE id = :etapa_id
            """)
            conn.execute(query, {'etapa_id': etapa_id})
            conn.commit()
        
        print(f"✅ Manual removido com sucesso da etapa {etapa_id}")
        
        return jsonify({
            'success': True,
            'message': 'Manual removido com sucesso'
        })
        
    except Exception as e:
        print(f"❌ Erro ao remover manual: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/risco/<int:risco_id>/controles')
def api_risco_controles(risco_id):
    """Retorna todos os controles associados a um risco"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome_controle, como_executado, objetivo_controle,
                       periodicidade_execucao, evidencia_realizacao, forma_execucao,
                       natureza, status_controle, responsaveis_tratamento,
                       risco_avaliacao, causa_motivo, frequencia_evidencia, 
                       local_evidencia, lgpd, created_at, updated_at
                FROM controles_etapa
                WHERE risco_id = :risco_id
                ORDER BY id
            """)
            
            result = conn.execute(query, {'risco_id': risco_id}).fetchall()
            
            controles = []
            for row in result:
                controles.append({
                    'id': row[0],
                    'nome_controle': row[1] or '',
                    'como_executado': row[2] or '',
                    'objetivo_controle': row[3] or '',
                    'periodicidade_execucao': row[4] or '',
                    'evidencia_realizacao': row[5] or '',
                    'forma_execucao': row[6] or '',
                    'natureza': row[7] or '',
                    'status_controle': row[8] or '',
                    'responsaveis_tratamento': row[9] or '',
                    'risco_avaliacao': row[10] or '',
                    'causa_motivo': row[11] or '',
                    'frequencia_evidencia': row[12] or '',
                    'local_evidencia': row[13] or '',
                    'lgpd': row[14] or '',
                    'created_at': row[15].isoformat() if row[15] else '',
                    'updated_at': row[16].strftime('%Y-%m-%d') if row[16] else ''
                })
            
            return jsonify({'success': True, 'controles': controles})
            
    except Exception as e:
        print(f"❌ Erro ao buscar controles do risco: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/etapa/<int:etapa_id>/controles/count')
def api_etapa_controles_count(etapa_id):
    """Retorna a quantidade de controles de uma etapa"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) FROM controles_etapa ce
                JOIN riscos_etapa re ON ce.risco_id = re.id
                WHERE re.etapa_id = :etapa_id AND re.ativo = true
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchone()
            return jsonify({'success': True, 'total': result[0]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/risco/<int:risco_id>/controles/count')
def api_risco_controles_count(risco_id):
    """Retorna a quantidade de controles de um risco específico"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) as total
                FROM controles_etapa
                WHERE risco_id = :risco_id
            """)
            result = conn.execute(query, {'risco_id': risco_id}).fetchone()
            
            return jsonify({
                'success': True,
                'total': result[0] or 0
            })
            
    except Exception as e:
        print(f"❌ Erro ao contar controles do risco {risco_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# COMUNICAÇÃO DOS RESULTADOS
# ============================================================

@app.route('/api/checklist/analises-por-auditoria')
def api_checklist_analises_por_auditoria():
    """Retorna as análises críticas de todas as etapas dos processos de uma auditoria, filtradas por categoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    auditoria_id = request.args.get('auditoria_id')
    categoria = request.args.get('categoria', 'governanca')
    
    if not auditoria_id:
        return jsonify({'success': False, 'error': 'auditoria_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    ac.id, ac.tipo, ac.categoria,
                    ac.analise_critica, ac.sugestao_melhoria,
                    ac.necessidade_implantacao, ac.ganho_previsto,
                    ep.codigo_etapa, ep.nome_etapa,
                    p.codigo_processo, p.nome_processo
                FROM analises_criticas ac
                JOIN etapas_processo ep ON ac.etapa_id = ep.id
                JOIN processos p ON ep.processo_id = p.id
                WHERE p.auditoria_id = :auditoria_id   -- ← AGORA É DIRETO!
                AND ac.categoria = :categoria
                ORDER BY p.codigo_processo, ep.codigo_etapa, ac.tipo
            """)
            
            result = conn.execute(query, {
                'auditoria_id': auditoria_id,
                'categoria': categoria
            }).fetchall()
            
            analises = []
            for row in result:
                analises.append({
                    'id': row[0],
                    'tipo': row[1],
                    'categoria': row[2],
                    'analise_critica': row[3] or '',
                    'sugestao_melhoria': row[4] or '',
                    'necessidade_implantacao': row[5] or '',
                    'ganho_previsto': row[6] or '',
                    'codigo_etapa': row[7] or '',
                    'nome_etapa': row[8] or '',
                    'codigo_processo': row[9] or '',
                    'nome_processo': row[10] or ''
                })
            
            return jsonify({'success': True, 'analises': analises})
            
    except Exception as e:
        print(f"❌ Erro ao buscar análises: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/carregar', methods=['GET'])
def api_checklist_carregar():
    """Carrega as respostas de um checklist para um processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    tipo = request.args.get('tipo')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    if not tipo or tipo not in ['governanca', 'riscos', 'controles']:
        return jsonify({'success': False, 'error': 'tipo inválido'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ⭐ 1. BUSCAR O CHECKLIST
            query_checklist = text("""
                SELECT id, status, observacoes_gerais
                FROM checklists
                WHERE processo_id = :processo_id AND tipo = :tipo
            """)
            
            checklist = conn.execute(query_checklist, {
                'processo_id': processo_id,
                'tipo': tipo
            }).fetchone()
            
            num_perguntas = {
                'governanca': 13,
                'riscos': 12,
                'controles': 12
            }.get(tipo, 12)
            
            if not checklist:
                respostas_vazias = []
                for i in range(1, num_perguntas + 1):
                    respostas_vazias.append({
                        'id': None,  # ← ID DA RESPOSTA (None)
                        'ordem': i,
                        'resposta': '',
                        'comentario': '',
                        'evidencias': []
                    })
                
                return jsonify({
                    'success': True,
                    'id': None,
                    'status': 'Não iniciado',
                    'observacoes_gerais': '',
                    'respostas': respostas_vazias
                })
            
            checklist_id = checklist[0]
            status = checklist[1] or 'Não iniciado'
            observacoes = checklist[2] or ''
            
            # ⭐ 2. BUSCAR AS RESPOSTAS
            query_respostas = text("""
                SELECT id, pergunta_ordem, resposta, comentario
                FROM checklist_respostas
                WHERE checklist_id = :checklist_id
                ORDER BY pergunta_ordem
            """)

            respostas_db = conn.execute(query_respostas, {
                'checklist_id': checklist_id
            }).fetchall()

            # ⭐ 3. CRIAR MAPA DE RESPOSTAS POR ORDEM COM O ID CORRETO
            respostas_map = {}
            for r in respostas_db:
                # ⭐ CONVERTER PARA STRING (já que pergunta_ordem é VARCHAR)
                chave = str(r[1])
                respostas_map[chave] = {
                    'id': r[0],
                    'ordem': r[1],
                    'resposta': r[2] or '',
                    'comentario': r[3] or ''
                }

            # ⭐ LOG PARA DEBUG
            print(f"🔍 Respostas encontradas: {len(respostas_db)}")
            print(f"🔍 Mapa de respostas: {respostas_map}")

            # ⭐ 4. MONTAR RESPOSTAS NA ORDEM CORRETA
            respostas = []

            if tipo == 'governanca':
                # Definição das ordens do frontend
                ordens_frontend = ['1', '1.1', '1.2', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13']
                
                # Mapeamento: frontend_ordem -> banco_pergunta_ordem
                mapeamento_banco = {
                    '1': '1',
                    '1.1': '1.1',
                    '1.2': '1.2',
                    '2': '2',
                    '3': '3',
                    '4': '4',
                    '5': '5',
                    '6': '6',
                    '7': '7',
                    '8': '8',
                    '9': '9',
                    '10': '10',
                    '11': '11',
                    '12': '12',
                    '13': '13'   # ← AGORA CORRETO!
                }
                
                for ordem_frontend in ordens_frontend:
                    ordem_banco = mapeamento_banco.get(ordem_frontend, ordem_frontend)
                    resposta_data = respostas_map.get(ordem_banco, {
                        'id': None,
                        'ordem': ordem_frontend,
                        'resposta': '',
                        'comentario': ''
                    })
                    
                    # Buscar evidências
                    evidencias = []
                    if resposta_data['id']:
                        query_evidencias = text("""
                            SELECT id, nome_arquivo, tamanho_bytes
                            FROM checklist_evidencias
                            WHERE resposta_id = :resposta_id
                        """)
                        ev_result = conn.execute(query_evidencias, {
                            'resposta_id': resposta_data['id']
                        }).fetchall()
                        
                        for ev in ev_result:
                            evidencias.append({
                                'id': ev[0],
                                'nome': ev[1],
                                'tamanho': ev[2]
                            })
                    
                    respostas.append({
                        'id': resposta_data['id'],
                        'ordem': ordem_frontend,
                        'resposta': resposta_data['resposta'],
                        'comentario': resposta_data['comentario'],
                        'evidencias': evidencias
                    })

            else:
                # Para riscos e controles, ordem normal
                for i in range(1, num_perguntas + 1):
                    ordem = str(i)
                    resposta_data = respostas_map.get(ordem, {
                        'id': None,
                        'ordem': ordem,
                        'resposta': '',
                        'comentario': ''
                    })
                    
                    # Buscar evidências
                    evidencias = []
                    if resposta_data['id']:
                        query_evidencias = text("""
                            SELECT id, nome_arquivo, tamanho_bytes
                            FROM checklist_evidencias
                            WHERE resposta_id = :resposta_id
                        """)
                        ev_result = conn.execute(query_evidencias, {
                            'resposta_id': resposta_data['id']
                        }).fetchall()
                        
                        for ev in ev_result:
                            evidencias.append({
                                'id': ev[0],
                                'nome': ev[1],
                                'tamanho': ev[2]
                            })
                    
                    respostas.append({
                        'id': resposta_data['id'],
                        'ordem': ordem,
                        'resposta': resposta_data['resposta'],
                        'comentario': resposta_data['comentario'],
                        'evidencias': evidencias
                    })

            # ⭐ LOG PARA DEBUG
            print(f"📤 Respostas sendo enviadas: {[{'id': r['id'], 'ordem': r['ordem']} for r in respostas]}")
            
            return jsonify({
                'success': True,
                'id': checklist_id,
                'status': status,
                'observacoes_gerais': observacoes,
                'respostas': respostas  # ← CADA UMA COM SEU ID
            })
            
    except Exception as e:
        print(f"❌ Erro ao carregar checklist: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/salvar', methods=['POST'])
def api_checklist_salvar():
    """Salva as respostas de um checklist (UPSERT)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    processo_id = data.get('processo_id')
    tipo = data.get('tipo')
    respostas = data.get('respostas', [])
    concluir = data.get('concluir', False)
    observacoes_gerais = data.get('observacoes_gerais', '')
    
    if not processo_id or not tipo:
        return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # 1. BUSCAR OU CRIAR O CHECKLIST
            query_checklist = text("""
                SELECT id FROM checklists
                WHERE processo_id = :processo_id AND tipo = :tipo
            """)
            checklist = conn.execute(query_checklist, {
                'processo_id': processo_id,
                'tipo': tipo
            }).fetchone()
            
            if not checklist:
                query_insert = text("""
                    INSERT INTO checklists (processo_id, tipo, status, observacoes_gerais)
                    VALUES (:processo_id, :tipo, 'Não iniciado', :observacoes_gerais)
                    RETURNING id
                """)
                result = conn.execute(query_insert, {
                    'processo_id': processo_id,
                    'tipo': tipo,
                    'observacoes_gerais': observacoes_gerais
                })
                conn.commit()
                checklist_id = result.fetchone()[0]
                print(f"📝 Checklist criado: id={checklist_id}")
            else:
                checklist_id = checklist[0]
                print(f"📝 Checklist encontrado: id={checklist_id}")
                # Atualizar observações gerais
                query_update = text("""
                    UPDATE checklists SET observacoes_gerais = :observacoes_gerais
                    WHERE id = :checklist_id
                """)
                conn.execute(query_update, {
                    'observacoes_gerais': observacoes_gerais,
                    'checklist_id': checklist_id
                })
                conn.commit()
            
            # ⭐ 2. UPSERT - INSERIR OU ATUALIZAR RESPOSTAS (SEM DELETAR)
            respostas_ids = {}
            
            for resp in respostas:
                pergunta_ordem = resp.get('ordem')
                resposta_valor = resp.get('resposta', '')
                comentario_valor = resp.get('comentario', '')
                
                print(f"📝 Upsert resposta: pergunta={pergunta_ordem}, resposta='{resposta_valor}'")
                
                # ⭐⭐ USAR ON CONFLICT PARA ATUALIZAR EM VEZ DE DELETAR ⭐⭐
                query_upsert = text("""
                    INSERT INTO checklist_respostas (checklist_id, pergunta_ordem, resposta, comentario)
                    VALUES (:checklist_id, :pergunta_ordem, :resposta, :comentario)
                    ON CONFLICT (checklist_id, pergunta_ordem) 
                    DO UPDATE SET 
                        resposta = EXCLUDED.resposta,
                        comentario = EXCLUDED.comentario,
                        updated_at = NOW()
                    RETURNING id
                """)
                
                result = conn.execute(query_upsert, {
                    'checklist_id': checklist_id,
                    'pergunta_ordem': pergunta_ordem,
                    'resposta': resposta_valor,
                    'comentario': comentario_valor
                })
                conn.commit()
                
                resposta_id = result.fetchone()[0]
                respostas_ids[str(pergunta_ordem)] = resposta_id
                print(f"✅ Resposta salva: pergunta {pergunta_ordem} → id {resposta_id} (mantido)")
            
            # 4. ATUALIZAR STATUS DO CHECKLIST
            novo_status = 'Concluído' if concluir else 'Em andamento'
            query_status = text("""
                UPDATE checklists SET status = :status, updated_at = NOW()
                WHERE id = :checklist_id
            """)
            conn.execute(query_status, {
                'status': novo_status,
                'checklist_id': checklist_id
            })
            conn.commit()
            
            print(f"📤 respostas_ids sendo retornados: {respostas_ids}")
            
            return jsonify({
                'success': True,
                'id': checklist_id,
                'respostas_ids': respostas_ids,
                'message': 'Respostas salvas com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar checklist: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/checklist/progresso')
def api_checklist_progresso():
    """Retorna o progresso dos checklists para um processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    # Configuração dos checklists
    CONFIG = {
        'governanca': {'total': 13},
        'riscos': {'total': 12},
        'controles': {'total': 12}
    }
    
    resultado = {}
    
    try:
        with engine.connect() as conn:
            for tipo, config in CONFIG.items():
                total = config['total']
                
                # Buscar o checklist
                query_checklist = text("""
                    SELECT id, status
                    FROM checklists
                    WHERE processo_id = :processo_id AND tipo = :tipo
                """)
                
                checklist = conn.execute(query_checklist, {
                    'processo_id': processo_id,
                    'tipo': tipo
                }).fetchone()
                
                if not checklist:
                    resultado[tipo] = {
                        'total': total,
                        'respondidas': 0,
                        'status': 'Não iniciado'
                    }
                else:
                    checklist_id = checklist[0]
                    status = checklist[1] or 'Em andamento'
                    
                    # ⭐⭐⭐ CONTAR APENAS PERGUNTAS PRINCIPAIS ⭐⭐⭐
                    # Para governança: contar perguntas 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
                    # Ignorar 1.1 e 1.2
                    
                    if tipo == 'governanca':
                        # ⭐ Lista das perguntas principais (excluindo subitens)
                        query_respondidas = text("""
                            SELECT COUNT(*) 
                            FROM checklist_respostas 
                            WHERE checklist_id = :checklist_id 
                            AND resposta IS NOT NULL 
                            AND resposta != ''
                            AND pergunta_ordem IN ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13')
                        """)
                    else:
                        # Para riscos e controles, todas as perguntas são principais
                        query_respondidas = text("""
                            SELECT COUNT(*) 
                            FROM checklist_respostas 
                            WHERE checklist_id = :checklist_id 
                            AND resposta IS NOT NULL 
                            AND resposta != ''
                        """)
                    
                    result = conn.execute(query_respondidas, {
                        'checklist_id': checklist_id
                    })
                    
                    respondidas = result.fetchone()[0]
                    
                    resultado[tipo] = {
                        'total': total,
                        'respondidas': respondidas,
                        'status': status
                    }
            
            return jsonify({
                'success': True,
                'progresso': resultado
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar progresso: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/checklist/evidencia/<int:evidencia_id>/download', methods=['GET'])
def baixar_evidencia_checklist(evidencia_id):
    """Baixa uma evidência do checklist do Supabase Storage"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    from flask import send_file
    import io
    import re
    from urllib.parse import unquote
    
    try:
        # 1. BUSCAR EVIDÊNCIA NO BANCO
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome_arquivo, caminho_arquivo, tamanho_bytes, content_type
                FROM checklist_evidencias
                WHERE id = :evidencia_id
            """)
            
            result = conn.execute(query, {'evidencia_id': evidencia_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Evidência não encontrada'}), 404
            
            evidencia_id = result[0]
            nome_arquivo = result[1]
            caminho_arquivo = result[2]
            tamanho_bytes = result[3]
            content_type = result[4] or 'application/pdf'
        
        print(f"📥 Baixando evidência: id={evidencia_id}, nome={nome_arquivo}")
        print(f"📥 Caminho: {caminho_arquivo}")
        
        # 2. VERIFICAR SE O CAMINHO É UMA URL OU UM PATH
        if caminho_arquivo.startswith('https://'):
            # Já é uma URL - baixar diretamente
            import requests
            try:
                response = requests.get(caminho_arquivo)
                if response.status_code == 200:
                    return send_file(
                        io.BytesIO(response.content),
                        download_name=nome_arquivo,
                        mimetype=content_type,
                        as_attachment=True
                    )
                else:
                    return jsonify({'success': False, 'error': f'Erro ao baixar: status {response.status_code}'}), 500
            except Exception as e:
                return jsonify({'success': False, 'error': f'Erro ao baixar: {str(e)}'}), 500
        
        # 3. É UM PATH - GERAR URL ASSINADA
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        bucket = "matriz_eficacia"
        
        try:
            # Extrair o caminho do arquivo
            file_path = caminho_arquivo
            
            # Se for URL com /sign/, extrair o caminho
            if '/sign/' in file_path:
                match = re.search(r'/sign/[^/]+/(.+)', file_path)
                if match:
                    file_path = match.group(1).split('?')[0]
                    file_path = unquote(file_path)
            
            print(f"📥 File path extraído: {file_path}")
            
            # Tentar baixar diretamente
            response = supabase.storage.from_(bucket).download(file_path)
            
            if response:
                print(f"✅ Arquivo baixado! Tamanho: {len(response)} bytes")
                return send_file(
                    io.BytesIO(response),
                    download_name=nome_arquivo,
                    mimetype=content_type,
                    as_attachment=True
                )
            else:
                print("❌ Resposta vazia do Storage")
                
                # Tentar gerar URL assinada e redirecionar
                signed_url = supabase.storage.from_(bucket).create_signed_url(
                    file_path, 3600  # 1 hora
                )
                
                if signed_url and signed_url.get('signedURL'):
                    print(f"✅ URL assinada gerada: {signed_url['signedURL'][:100]}...")
                    from flask import redirect
                    return redirect(signed_url['signedURL'])
                else:
                    return jsonify({'success': False, 'error': 'Erro ao gerar URL assinada'}), 500
                
        except Exception as e:
            print(f"❌ Erro no download: {e}")
            import traceback
            traceback.print_exc()
            
            # Tentar URL direta como fallback
            try:
                if caminho_arquivo.startswith('https://'):
                    import requests
                    response = requests.get(caminho_arquivo)
                    if response.status_code == 200:
                        return send_file(
                            io.BytesIO(response.content),
                            download_name=nome_arquivo,
                            mimetype=content_type,
                            as_attachment=True
                        )
            except:
                pass
            
            return jsonify({'success': False, 'error': f'Erro ao baixar: {str(e)}'}), 500
            
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/evidencia/<int:evidencia_id>', methods=['DELETE'])
def remover_evidencia_checklist(evidencia_id):
    """Remove uma evidência do checklist (banco + storage)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    import re
    from urllib.parse import unquote
    
    try:
        # 1. BUSCAR EVIDÊNCIA NO BANCO
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome_arquivo, caminho_arquivo
                FROM checklist_evidencias
                WHERE id = :evidencia_id
            """)
            
            result = conn.execute(query, {'evidencia_id': evidencia_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Evidência não encontrada'}), 404
            
            evidencia_id = result[0]
            nome_arquivo = result[1]
            caminho_arquivo = result[2]
            
            print(f"🗑️ Removendo evidência: id={evidencia_id}, nome={nome_arquivo}")
            print(f"🗑️ Caminho: {caminho_arquivo}")
            
            # 2. REMOVER DO STORAGE
            # ⭐ USAR O SINGLETON
            from supabase_client import SupabaseClient
            
            try:
                supabase = SupabaseClient.get_instance()
                bucket = "matriz_eficacia"
                
                # Extrair o caminho do arquivo do storage
                file_path = caminho_arquivo
                
                # Se for URL com /sign/, extrair o caminho
                if '/sign/' in file_path:
                    match = re.search(r'/sign/[^/]+/(.+)', file_path)
                    if match:
                        file_path = match.group(1).split('?')[0]
                        file_path = unquote(file_path)
                # Se for URL completa do storage, extrair o path
                elif 'supabase.co/storage/v1/object/' in file_path:
                    parts = file_path.split('/object/')
                    if len(parts) > 1:
                        path_parts = parts[1].split('/', 2)
                        if len(path_parts) >= 3:
                            file_path = path_parts[2]
                
                print(f"🗑️ File path para remover: {file_path}")
                
                # Remover do storage
                response = supabase.storage.from_(bucket).remove([file_path])
                print(f"🗑️ Resposta do storage: {response}")
                
            except Exception as e:
                print(f"⚠️ Erro ao remover do storage: {e}")
            
            # 3. REMOVER DO BANCO
            query_delete = text("""
                DELETE FROM checklist_evidencias
                WHERE id = :evidencia_id
            """)
            
            conn.execute(query_delete, {'evidencia_id': evidencia_id})
            conn.commit()
            
            print(f"✅ Evidência removida com sucesso! ID: {evidencia_id}")
            
            return jsonify({
                'success': True,
                'message': 'Evidência removida com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao remover evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/checklist/evidencia/salvar', methods=['POST'])
def salvar_evidencia_checklist():
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        data = request.json
        resposta_id = data.get('resposta_id')
        evidencia_base64 = data.get('evidencia_base64')
        evidencia_nome = data.get('evidencia_nome')
        
        print(f"📎 Recebendo evidência: resposta_id={resposta_id}, nome={evidencia_nome}")
        
        if not resposta_id or not evidencia_base64 or not evidencia_nome:
            return jsonify({'success': False, 'error': 'Dados incompletos'}), 400
        
        # Validar tipo do arquivo
        if not evidencia_nome.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Apenas arquivos PDF são permitidos'}), 400
        
        with engine.connect() as conn:
            # 1. VERIFICAR SE A RESPOSTA EXISTE
            query_resposta = text("""
                SELECT id, checklist_id, pergunta_ordem
                FROM checklist_respostas
                WHERE id = :resposta_id
            """)
            resposta = conn.execute(query_resposta, {'resposta_id': resposta_id}).fetchone()
            
            if not resposta:
                return jsonify({'success': False, 'error': 'Resposta não encontrada'}), 404
            
            checklist_id = resposta[1]
            pergunta_ordem = resposta[2]
            
            print(f"📎 Checklist ID: {checklist_id}, Pergunta: {pergunta_ordem}")
            
            # 2. UPLOAD PARA O STORAGE
            
            caminho = upload_evidencia_checklist(
                checklist_id=checklist_id,
                pergunta_ordem=pergunta_ordem,
                evidencia_base64=evidencia_base64,
                evidencia_nome=evidencia_nome,
                bucket_name="matriz_eficacia"
            )
            
            if not caminho:
                return jsonify({'success': False, 'error': 'Erro ao fazer upload da evidência'}), 500
            
            print(f"📎 Upload realizado: {caminho}")
            
            # 3. SALVAR NO BANCO
            print("🔍 Inserindo no banco...")
            
            query_insert = text("""
                INSERT INTO checklist_evidencias (resposta_id, nome_arquivo, caminho_arquivo, tamanho_bytes, content_type)
                VALUES (:resposta_id, :nome_arquivo, :caminho_arquivo, :tamanho_bytes, :content_type)
                RETURNING id
            """)
            
            # Calcular tamanho aproximado
            import base64
            tamanho_aproximado = 0
            if evidencia_base64:
                # Remover prefixo se existir
                base64_data = evidencia_base64
                if ',' in base64_data:
                    base64_data = base64_data.split(',')[1]
                tamanho_aproximado = int(len(base64_data) * 0.75)
            
            print(f"📎 Tamanho aproximado: {tamanho_aproximado} bytes")
            
            result = conn.execute(query_insert, {
                'resposta_id': resposta_id,
                'nome_arquivo': evidencia_nome,
                'caminho_arquivo': caminho,
                'tamanho_bytes': tamanho_aproximado,
                'content_type': 'application/pdf'
            })
            conn.commit()
            
            evidencia_id = result.fetchone()[0]
            
            print(f"✅ Evidência salva com sucesso! ID: {evidencia_id}")
            
            return jsonify({
                'success': True,
                'evidencia': {
                    'id': evidencia_id,
                    'nome': evidencia_nome,
                    'caminho': caminho,
                    'tamanho': tamanho_aproximado
                }
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar evidência: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/checklist/evidencias/<int:resposta_id>', methods=['GET'])
def listar_evidencias_checklist(resposta_id):
    """Lista as evidências de uma resposta específica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ⭐ VERIFICAR SE A RESPOSTA EXISTE
            query_resposta = text("""
                SELECT id FROM checklist_respostas WHERE id = :resposta_id
            """)
            resposta = conn.execute(query_resposta, {'resposta_id': resposta_id}).fetchone()
            
            if not resposta:
                return jsonify({
                    'success': True,
                    'evidencias': [],
                    'message': f'Resposta {resposta_id} não encontrada'
                })
            
            # ⭐ BUSCAR EVIDÊNCIAS
            query_evidencias = text("""
                SELECT id, nome_arquivo, caminho_arquivo, tamanho_bytes, uploaded_at
                FROM checklist_evidencias
                WHERE resposta_id = :resposta_id
                ORDER BY uploaded_at DESC
            """)
            
            result = conn.execute(query_evidencias, {'resposta_id': resposta_id}).fetchall()
            
            evidencias = []
            for row in result:
                evidencias.append({
                    'id': row[0],
                    'nome': row[1],
                    'caminho': row[2],
                    'tamanho': row[3],
                    'data': row[4].isoformat() if row[4] else None
                })
            
            return jsonify({
                'success': True,
                'evidencias': evidencias
            })
            
    except Exception as e:
        print(f"❌ Erro ao listar evidências: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================
# GERAÇÃO DE RELATÓRIOS
# ============================================================

@app.route('/api/relatorios/areas')
def api_relatorios_areas():
    """Retorna todas as áreas ativas para os relatórios"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            # ⭐ ADICIONAR loc_unidade NO SELECT
            query = text("""
                SELECT id_area, nome_area, gestor, loc_unidade
                FROM informacoes_area
                WHERE status = 'Ativo'
                ORDER BY nome_area
            """)

            result = conn.execute(query).fetchall()

            areas = []

            for row in result:
                id_area = row[0]
                nome_area = row[1]
                gestor = row[2] or 'Não informado'
                unidade = row[3] if len(row) > 3 and row[3] else ''  # ⭐ PEGAR UNIDADE
                
                # ⭐ FORMATAR NOME COM UNIDADE
                if unidade and unidade.strip():
                    nome_exibicao = f"{nome_area} - {unidade}"
                else:
                    nome_exibicao = nome_area

                areas.append({
                    'id': id_area,
                    'nome': nome_exibicao,  # ← NOME FORMATADO
                    'nome_original': nome_area,  # ← OPCIONAL (para referência)
                    'gestor': gestor,
                    'unidade': unidade  # ← UNIDADE SEPARADA (opcional)
                })

            return jsonify({'success': True, 'areas': areas})

    except Exception as e:
        print(f"❌ Erro ao buscar áreas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relatorios/auditorias-por-area')
def api_relatorios_auditorias_por_area():
    """Retorna as auditorias de uma área específica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    area_id = request.args.get('area_id')
    if not area_id:
        return jsonify({'success': False, 'error': 'area_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text

    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, codigo_auditoria, titulo, ano, trimestre, unidade
                FROM auditorias
                WHERE id_area = :area_id
                ORDER BY ano DESC, trimestre DESC
            """)

            result = conn.execute(query, {'area_id': area_id}).fetchall()

            auditorias = []
            for row in result:
                auditorias.append({
                    'id': row[0],
                    'codigo_auditoria': row[1],
                    'titulo': row[2],
                    'ano': row[3],
                    'trimestre': row[4],
                    'unidade': row[5] or ''
                })

            return jsonify({'success': True, 'auditorias': auditorias})
    
    except Exception as e:
        print(f"❌ Erro ao buscar auditorias: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/relatorios/gerar-panorama', methods=['POST'])

def api_gerar_relatorio_panorama():
    """Gera relatório de validação - Matriz Panorama"""
    from logic import gerar_validacao_relatorio_panorama
    from flask import send_file, request, jsonify
    import io
    from database import engine
    from sqlalchemy import text
    
    try:
        data = request.get_json()
        area_id = data.get('area_id')
        auditoria_id = data.get('auditoria_id')
        processo_id = data.get('processo_id')  # Pode ser None
        orientacao = data.get('orientacao', 'RETRATO')
        
        if not area_id or not auditoria_id:
            return jsonify({'error': 'Área e auditoria são obrigatórios'}), 400
        
        # Buscar informações da área
        with engine.connect() as conn:
            query_area = text("""
                SELECT nome_area, gestor, cargo 
                FROM informacoes_area 
                WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {"area_id": area_id}).fetchone()
            
            if not area_info:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0]
            gestor = area_info[1] or 'Não informado'
            cargo = area_info[2] or 'Não informado'
        
        # Gerar o relatório
        pdf_bytes = gerar_validacao_relatorio_panorama(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            cargo=cargo,
            orientacao=orientacao,
            auditoria_id=auditoria_id,
            processo_id=processo_id
        )
        
        # Nome do arquivo
        if processo_id:
            nome_arquivo = f"relatorio_panorama_processo_{processo_id}.pdf"
        else:
            nome_arquivo = f"relatorio_panorama_auditoria_{auditoria_id}.pdf"
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/relatorios/gerar-detalhamento', methods=['POST'])

def api_gerar_relatorio_detalhamento():
    """Gera relatório de validação - Matriz Detalhamento"""
    from logic import gerar_validacao_relatorio_detalhamento
    from flask import send_file, request, jsonify
    import io
    from database import engine
    from sqlalchemy import text
    
    try:
        data = request.get_json()
        area_id = data.get('area_id')
        auditoria_id = data.get('auditoria_id')
        processo_id = data.get('processo_id')  # Pode ser None
        orientacao = data.get('orientacao', 'RETRATO')
        
        if not area_id or not auditoria_id:
            return jsonify({'error': 'Área e auditoria são obrigatórios'}), 400
        
        # Buscar informações da área
        with engine.connect() as conn:
            query_area = text("""
                SELECT nome_area, gestor, cargo 
                FROM informacoes_area 
                WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {"area_id": area_id}).fetchone()
            
            if not area_info:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0]
            gestor = area_info[1] or 'Não informado'
            cargo = area_info[2] or 'Não informado'
        
        # Gerar o relatório
        pdf_bytes = gerar_validacao_relatorio_detalhamento(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            cargo=cargo,
            orientacao=orientacao,
            auditoria_id=auditoria_id,
            processo_id=processo_id
        )
        
        # Nome do arquivo
        if processo_id:
            nome_arquivo = f"relatorio_detalhamento_processo_{processo_id}.pdf"
        else:
            nome_arquivo = f"relatorio_detalhamento_auditoria_{auditoria_id}.pdf"
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/relatorios/gerar-gerencial', methods=['POST'])
def api_relatorios_gerar_gerencial():
    """Gera o relatório gerencial em PDF e retorna diretamente"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    area_id = data.get('area_id')
    auditoria_id = data.get('auditoria_id')
    orientacao = data.get('orientacao', 'RETRATO')
    processo_id = data.get('processo_id')  # ⭐ NOVO: PODE SER NONE
    
    if not area_id or not auditoria_id:
        return jsonify({'success': False, 'error': 'area_id e auditoria_id são obrigatórios'}), 400
    
    from database import engine
    from sqlalchemy import text
    from logic import gerar_relatorio_gerencial_area
    
    try:
        # Buscar nome da área e gestor
        with engine.connect() as conn:
            query_area = text("""
                SELECT nome_area, gestor, cargo FROM informacoes_area WHERE id_area = :area_id
            """)
            area_info = conn.execute(query_area, {'area_id': area_id}).fetchone()
            
            if not area_info:
                return jsonify({'success': False, 'error': 'Área não encontrada'}), 404
            
            area_nome = area_info[0] or 'Área sem nome'
            gestor = area_info[1] or 'Gestor não informado'
            cargo = area_info[2] or 'Cargo não informado'
        
        # ⭐ GERAR O PDF - PASSANDO O processo_id
        pdf_bytes = gerar_relatorio_gerencial_area(
            area_id=area_id,
            area_nome=area_nome,
            gestor=gestor,
            cargo=cargo,
            orientacao=orientacao,
            auditoria_id=auditoria_id,
            processo_id=processo_id  # ⭐ ADICIONADO
        )
        
        # Criar nome do arquivo (incluir processo se selecionado)
        if processo_id:
            nome_arquivo = f"relatorio_gerencial_processo_{processo_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        else:
            nome_arquivo = f"relatorio_gerencial_{area_nome}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Retornar o PDF diretamente
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=nome_arquivo
        )
        
    except Exception as e:
        print(f"❌ Erro ao gerar relatório: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/relatorios/gerar-parecer', methods=['POST'])
def gerar_parecer():

    from flask import Flask, jsonify, request, session, make_response
    """Endpoint para gerar o parecer da auditoria"""
    try:
        # Verificar autenticação
        if 'usuario_id' not in session:
            return jsonify({'error': 'Não autenticado'}), 401
        
        data = request.get_json()
        area_id = data.get('area_id')
        auditoria_id = data.get('auditoria_id')
        processo_id = data.get('processo_id')
        orientacao = data.get('orientacao', 'RETRATO')
        incluir_abr = data.get('incluir_abr', False)  # ⭐ NOVO PARÂMETRO
        
        # Verificar permissão para ABR
        perfil = session.get('usuario_perfil', 'usuario')
        if incluir_abr and perfil not in ['administrador', 'admin']:
            return jsonify({'error': 'Apenas administradores podem incluir a seção ABR'}), 403
        
        # Buscar dados necessários
        with engine.connect() as conn:
            # Buscar informações da área
            query_area = text("SELECT id_area, nome_area FROM informacoes_area WHERE id_area = :area_id")
            area = conn.execute(query_area, {'area_id': area_id}).fetchone()
            
            if not area:
                return jsonify({'error': 'Área não encontrada'}), 404
            
            # Buscar gestor
            query_gestor = text("""
                SELECT gestor, cargo
                FROM informacoes_area 
                WHERE id_area = :area_id
            """)
            gestor_info = conn.execute(query_gestor, {'area_id': area_id}).fetchone()
            
            gestor = gestor_info[0] if gestor_info else 'Não informado'
            cargo = gestor_info[1] if gestor_info and len(gestor_info) > 1 else 'Não informado'
            
            usuario_nome = session.get('usuario_nome', 'Auditor')
        
        # ⭐ PASSAR O PARÂMETRO incluir_abr PARA A FUNÇÃO
        pdf_bytes = gerar_relatorio_parecer_auditoria(
            area_id=area_id,
            area_nome=area[1],
            gestor=gestor,
            cargo=cargo,
            auditoria_id=auditoria_id,
            processo_id=processo_id,
            usuario_nome=usuario_nome,
            orientacao=orientacao,
            incluir_abr=incluir_abr  # ⭐ NOVO PARÂMETRO
        )
        
        # Criar resposta com o PDF
        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="parecer_auditoria_processo_{processo_id}.pdf"'
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/relatorios/download')
def api_relatorios_download():
    """Faz o download do relatório PDF gerado"""

    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    
    pdf_bytes = session.get('relatorio_pdf')
    nome_arquivo = session.get('relatorio_nome', 'relatorio.pdf')

    if not pdf_bytes:
        return jsonify({'error': 'Nenhum relatório gerado'}), 404
    
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=nome_arquivo
    )

@app.route('/api/relatorios/processos-por-auditoria')
def api_relatorios_processos_por_auditoria():
    """Retorna os processos de uma auditoria específica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    auditoria_id = request.args.get('auditoria_id')
    if not auditoria_id:
        return jsonify({'success': False, 'error': 'auditoria_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, codigo_processo, nome_processo
                FROM processos
                WHERE auditoria_id = :auditoria_id AND status = 'Ativo'
                ORDER BY string_to_array(codigo_processo, '.')::int[]
            """)
            result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            processos = [{'id': row[0], 'codigo_processo': row[1], 'nome_processo': row[2]} for row in result]
            
            return jsonify({'success': True, 'processos': processos})
            
    except Exception as e:
        print(f"❌ Erro ao buscar processos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# ROTA DE TESTE PARA AUDITORIA (remover depois)
# ============================================================

@app.route('/debug-auditoria')
def debug_auditoria():
    """🔍 Rota de teste para verificar se a auditoria está configurada"""
    if not session.get('autenticado'):
        return jsonify({'erro': 'Faça login primeiro'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Tenta ler as variáveis que configuramos
            resultado = conn.execute(text("""
                SELECT 
                    current_setting('app.usuario_id', true) as usuario_id,
                    current_setting('app.usuario_nome', true) as usuario_nome,
                    current_setting('app.ip_origem', true) as ip_origem
            """))
            row = resultado.fetchone()
            
            return jsonify({
                'sucesso': True,
                'usuario_id': row[0],
                'usuario_nome': row[1],
                'ip_origem': row[2],
                'explicacao': '✅ Se você vê seus dados, a auditoria está pronta!'
            })
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': str(e),
            'explicacao': '⚠️ As variáveis ainda não foram configuradas para esta conexão'
        }), 500
    

@app.route('/debug-sessao')
def debug_sessao():
    """🔍 Verifica o que tem na sessão do Flask"""
    if not session.get('autenticado'):
        return jsonify({'erro': 'Não logado'}), 401
    
    return jsonify({
        'autenticado': session.get('autenticado'),
        'usuario_id': session.get('usuario_id'),
        'usuario_nome': session.get('usuario_nome'),
        'usuario_logado': session.get('usuario_logado'),
        'usuario_perfil': session.get('usuario_perfil'),
        'login_timestamp': session.get('login_timestamp')
    })

# ============================================================
# LOG DE ALTERACOES
# ============================================================

@app.route('/api/logs')
def api_logs():
    """
    API que retorna os logs da tabela log_auditoria com paginação
    Apenas administradores podem acessar
    """
    
    # 1. Verificar autenticação
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # 2. Verificar se é administrador
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    # 3. Importar dependências
    from database import engine
    from sqlalchemy import text
    
    # 4. Pegar parâmetros da URL
    pagina = request.args.get('pagina', 1, type=int)
    limite = request.args.get('limite', 20, type=int)
    tabela = request.args.get('tabela', '')
    operacao = request.args.get('operacao', '')
    usuario = request.args.get('usuario', '')
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    
    # Calcular offset (deslocamento) para paginação
    # Exemplo: página 1, limite 20 → offset 0 (registros 1-20)
    #          página 2, limite 20 → offset 20 (registros 21-40)
    offset = (pagina - 1) * limite
    
    # 5. Construir a query BASE (para contar total)
    base_query = """
        FROM log_auditoria
        WHERE 1=1
    """
    
    # 6. Construir a query de SELECT (para buscar os dados)
    select_query = """
        SELECT 
            id,
            tabela_afetada,
            registro_id,
            operacao,
            usuario_nome,
            ip_origem,
            data_hora,
            dados_anteriores,
            dados_novos
    """
    
    # 7. Parâmetros compartilhados entre as queries
    params = {}
    
    # 8. Adicionar filtros (mesmo para COUNT e SELECT)
    if tabela:
        base_query += " AND tabela_afetada = :tabela"
        select_query += base_query  # Adiciona o WHERE à SELECT também
        params['tabela'] = tabela
    else:
        select_query += base_query
    
    # Recriar base_query para o COUNT (porque já foi usada)
    count_query = "SELECT COUNT(*) " + base_query
    
    # Ajustar select_query para incluir o ORDER BY e LIMIT
    select_query += " ORDER BY id DESC LIMIT :limite OFFSET :offset"
    params['limite'] = limite
    params['offset'] = offset
    
    # Adicionar filtros individualmente (para não duplicar)
    if operacao:
        select_query = select_query.replace("WHERE 1=1", "WHERE 1=1 AND operacao = :operacao")
        count_query = count_query.replace("WHERE 1=1", "WHERE 1=1 AND operacao = :operacao")
        params['operacao'] = operacao
    
    if usuario:
        select_query = select_query.replace("WHERE 1=1", "WHERE 1=1 AND usuario_nome ILIKE :usuario")
        count_query = count_query.replace("WHERE 1=1", "WHERE 1=1 AND usuario_nome ILIKE :usuario")
        params['usuario'] = f'%{usuario}%'
    
    if data_inicio:
        select_query = select_query.replace("WHERE 1=1", "WHERE 1=1 AND data_hora >= :data_inicio")
        count_query = count_query.replace("WHERE 1=1", "WHERE 1=1 AND data_hora >= :data_inicio")
        params['data_inicio'] = data_inicio
    
    if data_fim:
        select_query = select_query.replace("WHERE 1=1", "WHERE 1=1 AND data_hora <= :data_fim")
        count_query = count_query.replace("WHERE 1=1", "WHERE 1=1 AND data_hora <= :data_fim")
        params['data_fim'] = data_fim + ' 23:59:59'  # Inclui todo o dia
    
    try:
        with engine.connect() as conn:
            # 9. Primeiro, buscar o TOTAL de registros (para paginação)
            total_result = conn.execute(text(count_query), params)
            total_registros = total_result.fetchone()[0]
            
            # 10. Calcular total de páginas
            total_paginas = (total_registros + limite - 1) // limite if total_registros > 0 else 1
            
            # 11. Buscar os registros da página atual
            result = conn.execute(text(select_query), params)
            
            # 12. Converter os resultados para lista de dicionários
            import re

            logs = []
            for row in result:
                logs.append({
                    'id': row[0],
                    'tabela_afetada': row[1],
                    'registro_id': row[2],
                    'operacao': row[3],
                    'usuario_nome': row[4] or 'Sistema',
                    'ip_origem': row[5] or '-',
                    'data_hora': row[6].strftime('%d/%m/%Y %H:%M:%S') if row[6] else '',
                    'dados_anteriores': row[7],
                    'dados_novos': row[8]
                })
            
            return jsonify({
                'success': True,
                'logs': logs,
                'total_registros': total_registros,
                'total_paginas': total_paginas,
                'pagina_atual': pagina,
                'limite': limite
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar logs: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tabelas')
def api_tabelas():
    """
    Retorna a lista de todas as tabelas do banco (exceto log_auditoria)
    Apenas administradores podem acessar
    """
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Buscar todas as tabelas do schema public
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    AND table_name != 'log_auditoria'
                ORDER BY table_name
            """)
            result = conn.execute(query)
            tabelas = [row[0] for row in result]
            
            return jsonify({'success': True, 'tabelas': tabelas})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/usuarios')
def api_usuarios():
    """
    Retorna a lista de usuários para o filtro de logs
    Apenas administradores podem acessar
    """
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Acesso negado'}), 403
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome, login
                FROM usuarios
                                WHERE ativo = true
                ORDER BY nome
            """)
            result = conn.execute(query)
            usuarios = [{'id': row[0], 'nome': row[1], 'login': row[2]} for row in result]
            
            return jsonify({'success': True, 'usuarios': usuarios})
    except Exception as e:
        print(f"❌ Erro ao buscar usuários: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - ANÁLISES CRÍTICAS
# ============================================================

@app.route('/api/etapa/<int:etapa_id>/analises', methods=['GET'])
def api_etapa_analises(etapa_id):
    """Retorna todas as análises críticas de uma etapa com evidências"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, etapa_id, tipo, categoria,
                       analise_critica, sugestao_melhoria,
                       necessidade_implantacao, ganho_previsto,
                       evidencia_url, evidencia_nome,  -- ⭐ NOVO
                       created_at, updated_at
                FROM analises_criticas
                WHERE etapa_id = :etapa_id
                ORDER BY tipo, categoria
            """)
            result = conn.execute(query, {'etapa_id': etapa_id}).fetchall()
            
            analises = []
            for row in result:
                analise = {
                    'id': row[0],
                    'etapa_id': row[1],
                    'tipo': row[2],
                    'categoria': row[3],
                    'analise_critica': row[4] or '',
                    'sugestao_melhoria': row[5] or '',
                    'necessidade_implantacao': row[6] or '',
                    'ganho_previsto': row[7] or '',
                    'evidencia_url': row[8],      # ⭐ NOVO
                    'evidencia_nome': row[9],     # ⭐ NOVO
                    'created_at': row[10].isoformat() if row[10] else '',
                    'updated_at': row[11].strftime('%Y-%m-%d %H:%M') if row[11] else ''
                }
                analises.append(analise)
            
            return jsonify({'success': True, 'analises': analises})
            
    except Exception as e:
        print(f"❌ Erro ao buscar análises: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analises-criticas-por-processo', methods=['GET'])
def api_analises_criticas_por_processo():
    """Retorna as análises críticas do auditado para um processo específico"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    ac.id,
                    ac.analise_critica,
                    ac.sugestao_melhoria,
                    ac.necessidade_implantacao,
                    ac.ganho_previsto,
                    ac.observacoes,
                    ac.categoria,
                    ac.tipo,
                    ac.sugestao_sera_implantada,
                    ac.plano_acao,
                    ac.responsavel_implantacao,
                    ac.data_inicio_prevista,
                    ac.data_conclusao_prevista,
                    ac.anexo_nome,
                    ac.efetivamente_implantada,
                    ac.data_implantacao_efetiva,
                    ac.created_at,
                    ac.updated_at,
                    ep.id as etapa_id,    
                    ep.codigo_etapa,
                    ep.nome_etapa,
                    ep.processo_id,
                    ac.evidencia_url,      -- ⭐ NOVO
                    ac.evidencia_nome      -- ⭐ NOVO
                FROM analises_criticas ac
                JOIN etapas_processo ep ON ac.etapa_id = ep.id
                WHERE ep.processo_id = :processo_id
                AND ac.tipo = 'auditado'
                ORDER BY ep.codigo_etapa, ac.categoria
            """)
            result = conn.execute(query, {'processo_id': processo_id}).fetchall()
            
            analises = []
            for row in result:
                analises.append({
                    'id': row[0],
                    'analise_critica': row[1] or '',
                    'sugestao_melhoria': row[2] or '',
                    'necessidade_implantacao': row[3] or '',
                    'ganho_previsto': row[4] or '',
                    'observacoes': row[5] or '',
                    'categoria': row[6] or 'governanca',
                    'tipo': row[7],
                    'sugestao_sera_implantada': row[8],
                    'plano_acao': row[9] or '',
                    'responsavel_implantacao': row[10] or '',
                    'data_inicio_prevista': row[11].strftime('%Y-%m-%d') if row[11] else None,
                    'data_conclusao_prevista': row[12].strftime('%Y-%m-%d') if row[12] else None,
                    'anexo_nome': row[13] or '',
                    'efetivamente_implantada': row[14] if row[14] is not None else None,
                    'data_implantacao_efetiva': row[15].strftime('%Y-%m-%d') if row[15] else None,
                    'created_at': row[16].isoformat() if row[16] else '',
                    'updated_at': row[17].isoformat() if row[17] else '',
                    'etapa_id': row[18],
                    'codigo_etapa': row[19] or '',
                    'nome_etapa': row[20] or '',
                    'processo_id': row[21],
                    'evidencia_url': row[22] or None,      # ⭐ NOVO
                    'evidencia_nome': row[23] or None      # ⭐ NOVO
                })
            
            print(f"✅ Buscadas {len(analises)} análises do auditado para o processo {processo_id}")
            
            return jsonify({'success': True, 'analises': analises})
            
    except Exception as e:
        print(f"❌ Erro ao buscar análises críticas: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise-auditor/evidencia/<int:evidencia_id>/download')
def baixar_evidencia_analise_auditor(evidencia_id):
    """Baixa a evidência do Storage"""
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    import io
    from flask import send_file
    import re
    from urllib.parse import unquote
    
    try:
        print(f"🔍 DEBUG: Iniciando download da evidência ID: {evidencia_id}")
        
        # Buscar a evidência no banco
        from database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            query = text("""
                SELECT id, evidencia_url, evidencia_nome 
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditor'
            """)
            result = conn.execute(query, {'id': evidencia_id})
            row = result.fetchone()
            
            if not row:
                return jsonify({'error': 'Evidência não encontrada'}), 404
            
            evidencia_url = row[1]
            evidencia_nome = row[2]
            
            if not evidencia_url:
                return jsonify({'error': 'Evidência não possui URL'}), 404
        
        # ⭐ EXTRAIR O CAMINHO
        match = re.search(r'/sign/[^/]+/(.+)', evidencia_url)
        if not match:
            return jsonify({'error': 'Não foi possível extrair o caminho do arquivo'}), 400
        
        file_path = match.group(1).split('?')[0]
        file_path = unquote(file_path)
        
        # ⭐ BUCKET CORRETO
        bucket = "evidencia_analises_auditor"
        
        print(f"📄 DEBUG: Bucket: {bucket}")
        print(f"📄 DEBUG: File path: {file_path}")
        
        # ⭐ USAR O SINGLETON
        from supabase_client import SupabaseClient
        supabase = SupabaseClient.get_instance()
        
        # ⭐ BAIXAR O ARQUIVO
        try:
            print(f"📥 DEBUG: Tentando download do Storage...")
            response = supabase.storage.from_(bucket).download(file_path)
            
            if response:
                print(f"✅ DEBUG: Arquivo baixado! Tamanho: {len(response)} bytes")
                
                return send_file(
                    io.BytesIO(response),
                    download_name=evidencia_nome or 'evidencia.pdf',
                    mimetype='application/pdf',
                    as_attachment=True
                )
            else:
                print(f"❌ DEBUG: Resposta vazia do Storage")
                
                # TENTAR URL DIRETA COMO FALLBACK
                import requests
                print(f"🔄 DEBUG: Tentando URL direta...")
                response = requests.get(evidencia_url)
                if response.status_code == 200:
                    print(f"✅ DEBUG: Download via URL direta! Tamanho: {len(response.content)} bytes")
                    return send_file(
                        io.BytesIO(response.content),
                        download_name=evidencia_nome or 'evidencia.pdf',
                        mimetype='application/pdf',
                        as_attachment=True
                    )
                else:
                    return jsonify({'error': f'Erro ao baixar: status {response.status_code}'}), 500
                
        except Exception as e:
            print(f"❌ DEBUG: Erro no download: {e}")
            import traceback
            traceback.print_exc()
            
            # TENTAR URL DIRETA COMO FALLBACK
            try:
                import requests
                print(f"🔄 DEBUG: Tentando URL direta (fallback)...")
                response = requests.get(evidencia_url)
                if response.status_code == 200:
                    return send_file(
                        io.BytesIO(response.content),
                        download_name=evidencia_nome or 'evidencia.pdf',
                        mimetype='application/pdf',
                        as_attachment=True
                    )
                else:
                    return jsonify({'error': f'Erro ao baixar: status {response.status_code}'}), 500
            except Exception as e2:
                return jsonify({'error': f'Erro ao baixar: {str(e)}'}), 500
            
    except Exception as e:
        print(f"❌ DEBUG: Erro geral: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/analise-auditor/<int:analise_id>', methods=['PUT'])
def api_analise_auditor_atualizar(analise_id):
    """Atualiza uma análise existente do auditor"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # ⭐ DECLARAR TODAS AS VARIÁVEIS NO INÍCIO
    processo_id = None
    analise_critica = ''
    sugestao_melhoria = ''
    necessidade_implantacao = ''
    ganho_previsto = ''
    observacoes = ''
    sugestao_sera_implantada = None
    plano_acao = ''
    responsavel_implantacao = ''
    data_inicio_prevista = None
    data_conclusao_prevista = None
    anexo_nome = None
    evidencia_nome = None
    remover_anexo = False
    remover_evidencia = False
    anexo_file = None
    evidencia_file = None
    
    # ⭐ Verificar se é FormData
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Receber dados do FormData
        data = request.form
        processo_id = data.get('processo_id')
        analise_critica = data.get('analise_critica', '')
        sugestao_melhoria = data.get('sugestao_melhoria', '')
        necessidade_implantacao = data.get('necessidade_implantacao', '')
        ganho_previsto = data.get('ganho_previsto', '')
        observacoes = data.get('observacoes', '')
        plano_acao = data.get('plano_acao', '')
        responsavel_implantacao = data.get('responsavel_implantacao', '')
        data_inicio_prevista = data.get('data_inicio_prevista')
        data_conclusao_prevista = data.get('data_conclusao_prevista')
        anexo_nome = data.get('anexo_nome')
        evidencia_nome = data.get('evidencia_nome')
        remover_anexo = data.get('remover_anexo') == 'true'
        remover_evidencia = data.get('remover_evidencia') == 'true'
        
        # Converter sugestao_sera_implantada
        sugestao_sera_implantada_str = data.get('sugestao_sera_implantada', '')
        if sugestao_sera_implantada_str == 'true':
            sugestao_sera_implantada = True
        elif sugestao_sera_implantada_str == 'false':
            sugestao_sera_implantada = False
        else:
            sugestao_sera_implantada = None
        
        # ⭐ RECEBER OS ARQUIVOS
        anexo_file = request.files.get('anexo')
        evidencia_file = request.files.get('evidencia')
        
    else:
        # Fallback: receber como JSON
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
        
        processo_id = data.get('processo_id')
        analise_critica = data.get('analise_critica', '')
        sugestao_melhoria = data.get('sugestao_melhoria', '')
        necessidade_implantacao = data.get('necessidade_implantacao', '')
        ganho_previsto = data.get('ganho_previsto', '')
        observacoes = data.get('observacoes', '')
        sugestao_sera_implantada = data.get('sugestao_sera_implantada')
        plano_acao = data.get('plano_acao', '')
        responsavel_implantacao = data.get('responsavel_implantacao', '')
        data_inicio_prevista = data.get('data_inicio_prevista')
        data_conclusao_prevista = data.get('data_conclusao_prevista')
        anexo_nome = data.get('anexo_nome')
        evidencia_nome = data.get('evidencia_nome')
        remover_anexo = data.get('remover_anexo', False)
        remover_evidencia = data.get('remover_evidencia', False)
        
        # Processar base64 se vier do JSON
        anexo_base64 = data.get('anexo_base64')
        evidencia_base64 = data.get('evidencia_base64')
        
        # Converter base64 para arquivo se necessário
        if anexo_base64:
            import base64
            import io
            if ',' in anexo_base64:
                anexo_base64 = anexo_base64.split(',')[1]
            anexo_bytes = base64.b64decode(anexo_base64)
            anexo_file = io.BytesIO(anexo_bytes)
            anexo_file.filename = anexo_nome
        
        if evidencia_base64:
            import base64
            import io
            if ',' in evidencia_base64:
                evidencia_base64 = evidencia_base64.split(',')[1]
            evidencia_bytes = base64.b64decode(evidencia_base64)
            evidencia_file = io.BytesIO(evidencia_bytes)
            evidencia_file.filename = evidencia_nome
    
    if not analise_critica:
        return jsonify({'success': False, 'error': 'Análise Crítica é obrigatória'}), 400
    
    from database import engine
    from sqlalchemy import text
    import base64
    from psycopg2 import Binary
    
    try:
        with engine.connect() as conn:
            # Verificar se a análise existe
            check = conn.execute(
                text("SELECT id FROM analises_criticas WHERE id = :id AND tipo = 'auditor'"),
                {'id': analise_id}
            ).fetchone()
            
            if not check:
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            # ⭐ Processar anexo
            anexo_bytes = None
            if anexo_file:
                try:
                    if hasattr(anexo_file, 'read'):
                        anexo_file.seek(0)
                        anexo_bytes = anexo_file.read()
                    else:
                        anexo_file.seek(0)
                        anexo_bytes = anexo_file.read()
                    print(f"📎 Anexo recebido: {anexo_nome} ({len(anexo_bytes)} bytes)")
                except Exception as e:
                    print(f"⚠️ Erro ao ler anexo: {e}")
                    anexo_bytes = None
            
            anexo_param = Binary(anexo_bytes) if anexo_bytes else None
            
            # ⭐ Construir a query de UPDATE dinamicamente
            update_fields = []
            update_params = {
                'analise_critica': analise_critica,
                'sugestao_melhoria': sugestao_melhoria,
                'necessidade_implantacao': necessidade_implantacao,
                'ganho_previsto': ganho_previsto,
                'observacoes': observacoes,
                'sugestao_sera_implantada': sugestao_sera_implantada,
                'plano_acao': plano_acao,
                'responsavel_implantacao': responsavel_implantacao,
                'data_inicio_prevista': data_inicio_prevista,
                'data_conclusao_prevista': data_conclusao_prevista,
                'id': analise_id
            }
            
            # Adicionar campos que podem ser atualizados
            update_fields.append("analise_critica = :analise_critica")
            update_fields.append("sugestao_melhoria = :sugestao_melhoria")
            update_fields.append("necessidade_implantacao = :necessidade_implantacao")
            update_fields.append("ganho_previsto = :ganho_previsto")
            update_fields.append("observacoes = :observacoes")
            update_fields.append("sugestao_sera_implantada = :sugestao_sera_implantada")
            update_fields.append("plano_acao = :plano_acao")
            update_fields.append("responsavel_implantacao = :responsavel_implantacao")
            update_fields.append("data_inicio_prevista = :data_inicio_prevista")
            update_fields.append("data_conclusao_prevista = :data_conclusao_prevista")
            
            # Anexo
            if anexo_param is not None:
                update_fields.append("anexo_base64 = :anexo_base64")
                update_fields.append("anexo_nome = :anexo_nome")
                update_params['anexo_base64'] = anexo_param
                update_params['anexo_nome'] = anexo_nome
            elif remover_anexo:
                update_fields.append("anexo_base64 = NULL")
                update_fields.append("anexo_nome = NULL")
            
            update_fields.append("updated_at = NOW()")
            
            # Montar a query
            query_sql = f"""
                UPDATE analises_criticas 
                SET {', '.join(update_fields)}
                WHERE id = :id
            """
            
            conn.execute(text(query_sql), update_params)
            
            # ⭐ Processar evidência
            if evidencia_file:
                try:
                    # Ler o arquivo
                    if hasattr(evidencia_file, 'read'):
                        evidencia_file.seek(0)
                        evidencia_bytes = evidencia_file.read()
                    else:
                        evidencia_file.seek(0)
                        evidencia_bytes = evidencia_file.read()
                    
                    # Converter para base64
                    evidencia_base64 = base64.b64encode(evidencia_bytes).decode('utf-8')
                    
                    # Upload da nova evidência
                    evidencia_url = upload_evidencia_storage(
                        analise_id, 
                        evidencia_base64, 
                        evidencia_nome
                    )
                    
                    if evidencia_url:
                        update_evidencia = text("""
                            UPDATE analises_criticas 
                            SET evidencia_url = :evidencia_url,
                                evidencia_nome = :evidencia_nome
                            WHERE id = :id
                        """)
                        conn.execute(update_evidencia, {
                            'evidencia_url': evidencia_url,
                            'evidencia_nome': evidencia_nome,
                            'id': analise_id
                        })
                        print(f"📎 Evidência atualizada: {evidencia_nome}")
                    else:
                        print(f"⚠️ Falha ao salvar evidência no Storage")
                        
                except Exception as e:
                    print(f"⚠️ Erro ao processar evidência: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Remover evidência se solicitado
            if remover_evidencia and not evidencia_file:
                update_evidencia = text("""
                    UPDATE analises_criticas 
                    SET evidencia_url = NULL,
                        evidencia_nome = NULL
                    WHERE id = :id
                """)
                conn.execute(update_evidencia, {'id': analise_id})
                print(f"🗑️ Evidência removida da análise {analise_id}")
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'message': 'Análise atualizada com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao atualizar análise: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-auditor/<int:analise_id>', methods=['DELETE'])
def api_analise_auditor_excluir(analise_id):
    """Exclui uma análise do auditor"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ✅ CORRETO: usar a tabela analises_criticas
            query = text("""
                DELETE FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditor'
            """)
            result = conn.execute(query, {'id': analise_id})
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            return jsonify({'success': True, 'message': 'Análise excluída com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir análise do auditor: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-auditor/salvar', methods=['POST'])
def api_analise_auditor_salvar():
    """Salva uma nova análise do auditor com evidência no Storage (bucket privado)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # ⭐ IMPORTANTE: Verificar se é FormData ou JSON
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Receber dados do FormData
        data = request.form
        processo_id = data.get('processo_id')
        analise_critica = data.get('analise_critica', '')
        sugestao_melhoria = data.get('sugestao_melhoria', '')
        necessidade_implantacao = data.get('necessidade_implantacao', '')
        ganho_previsto = data.get('ganho_previsto', '')
        observacoes = data.get('observacoes', '')
        sugestao_sera_implantada_str = data.get('sugestao_sera_implantada', '')
        
        # Converter string para boolean/None
        if sugestao_sera_implantada_str == 'true':
            sugestao_sera_implantada = True
        elif sugestao_sera_implantada_str == 'false':
            sugestao_sera_implantada = False
        else:
            sugestao_sera_implantada = None
        
        plano_acao = data.get('plano_acao', '')
        responsavel_implantacao = data.get('responsavel_implantacao', '')
        data_inicio_prevista = data.get('data_inicio_prevista')
        data_conclusao_prevista = data.get('data_conclusao_prevista')
        anexo_nome = data.get('anexo_nome')
        evidencia_nome = data.get('evidencia_nome')
        
        # ⭐ RECEBER OS ARQUIVOS DO FormData
        anexo_file = request.files.get('anexo')
        evidencia_file = request.files.get('evidencia')
        
        remover_anexo = data.get('remover_anexo') == 'true'
        remover_evidencia = data.get('remover_evidencia') == 'true'
        
    else:
        # Fallback: receber como JSON (para compatibilidade)
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'Dados não fornecidos'}), 400
        
        processo_id = data.get('processo_id')
        analise_critica = data.get('analise_critica', '')
        sugestao_melhoria = data.get('sugestao_melhoria', '')
        necessidade_implantacao = data.get('necessidade_implantacao', '')
        ganho_previsto = data.get('ganho_previsto', '')
        observacoes = data.get('observacoes', '')
        sugestao_sera_implantada = data.get('sugestao_sera_implantada')
        plano_acao = data.get('plano_acao', '')
        responsavel_implantacao = data.get('responsavel_implantacao', '')
        data_inicio_prevista = data.get('data_inicio_prevista')
        data_conclusao_prevista = data.get('data_conclusao_prevista')
        anexo_nome = data.get('anexo_nome')
        evidencia_nome = data.get('evidencia_nome')
        remover_anexo = data.get('remover_anexo', False)
        remover_evidencia = data.get('remover_evidencia', False)
        
        # Processar base64 se vier do JSON
        anexo_base64 = data.get('anexo_base64')
        evidencia_base64 = data.get('evidencia_base64')
        anexo_file = None
        evidencia_file = None
        
        # Converter base64 para arquivo se necessário
        if anexo_base64:
            import base64
            import io
            if ',' in anexo_base64:
                anexo_base64 = anexo_base64.split(',')[1]
            anexo_bytes = base64.b64decode(anexo_base64)
            anexo_file = io.BytesIO(anexo_bytes)
            anexo_file.filename = anexo_nome
        
        if evidencia_base64:
            import base64
            import io
            if ',' in evidencia_base64:
                evidencia_base64 = evidencia_base64.split(',')[1]
            evidencia_bytes = base64.b64decode(evidencia_base64)
            evidencia_file = io.BytesIO(evidencia_bytes)
            evidencia_file.filename = evidencia_nome
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    if not analise_critica:
        return jsonify({'success': False, 'error': 'Análise Crítica é obrigatória'}), 400
    
    from database import engine
    from sqlalchemy import text
    import base64
    from psycopg2 import Binary
    import io
    
    try:
        with engine.connect() as conn:
            # Processar anexo
            anexo_bytes = None
            if anexo_file:
                try:
                    if hasattr(anexo_file, 'read'):
                        anexo_bytes = anexo_file.read()
                    else:
                        # É um BytesIO
                        anexo_file.seek(0)
                        anexo_bytes = anexo_file.read()
                    print(f"📎 Anexo recebido: {anexo_nome} ({len(anexo_bytes)} bytes)")
                except Exception as e:
                    print(f"⚠️ Erro ao ler anexo: {e}")
                    anexo_bytes = None
            
            anexo_param = Binary(anexo_bytes) if anexo_bytes else None
            
            # Inserir a análise
            query = text("""
                INSERT INTO analises_criticas (
                    processo_id, etapa_id, tipo, categoria,
                    analise_critica, sugestao_melhoria,
                    necessidade_implantacao, ganho_previsto, observacoes,
                    sugestao_sera_implantada, plano_acao, responsavel_implantacao,
                    data_inicio_prevista, data_conclusao_prevista,
                    anexo_base64, anexo_nome,
                    created_at, updated_at
                ) VALUES (
                    :processo_id, NULL, 'auditor', 'geral',
                    :analise_critica, :sugestao_melhoria,
                    :necessidade_implantacao, :ganho_previsto, :observacoes,
                    :sugestao_sera_implantada, :plano_acao, :responsavel_implantacao,
                    :data_inicio_prevista, :data_conclusao_prevista,
                    :anexo_base64, :anexo_nome,
                    NOW(), NOW()
                )
                RETURNING id
            """)
            
            result = conn.execute(query, {
                'processo_id': processo_id,
                'analise_critica': analise_critica,
                'sugestao_melhoria': sugestao_melhoria,
                'necessidade_implantacao': necessidade_implantacao,
                'ganho_previsto': ganho_previsto,
                'observacoes': observacoes,
                'sugestao_sera_implantada': sugestao_sera_implantada,
                'plano_acao': plano_acao,
                'responsavel_implantacao': responsavel_implantacao,
                'data_inicio_prevista': data_inicio_prevista,
                'data_conclusao_prevista': data_conclusao_prevista,
                'anexo_base64': anexo_param,
                'anexo_nome': anexo_nome
            })
            novo_id = result.fetchone()[0]
            
            # ⭐ Salvar evidência no Storage
            evidencia_url = None
            if evidencia_file:
                try:
                    # Ler o arquivo
                    if hasattr(evidencia_file, 'read'):
                        evidencia_file.seek(0)
                        evidencia_bytes = evidencia_file.read()
                    else:
                        evidencia_bytes = evidencia_file.read()
                    
                    # Converter para base64 para a função de upload
                    evidencia_base64 = base64.b64encode(evidencia_bytes).decode('utf-8')
                    
                    # Chamar a função de upload
                    evidencia_url = upload_evidencia_storage(
                        novo_id, 
                        evidencia_base64, 
                        evidencia_nome
                    )
                    
                    if evidencia_url:
                        # Atualizar a análise com a URL
                        update_query = text("""
                            UPDATE analises_criticas 
                            SET evidencia_url = :evidencia_url,
                                evidencia_nome = :evidencia_nome
                            WHERE id = :id
                        """)
                        conn.execute(update_query, {
                            'evidencia_url': evidencia_url,
                            'evidencia_nome': evidencia_nome,
                            'id': novo_id
                        })
                        print(f"📎 Evidência salva com sucesso: {evidencia_nome}")
                    else:
                        print(f"⚠️ Falha ao salvar evidência no Storage")
                    
                except Exception as e:
                    print(f"⚠️ Erro ao salvar evidência no Storage: {e}")
                    import traceback
                    traceback.print_exc()
            
            conn.commit()
            
            return jsonify({
                'success': True, 
                'id': novo_id, 
                'message': 'Análise salva com sucesso',
                'evidencia_url': evidencia_url
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar análise do auditor: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analises-auditor/por-processo', methods=['GET'])
def api_analises_auditor_por_processo():
    """Retorna todas as análises do auditor para um processo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    processo_id = request.args.get('processo_id')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    id, processo_id, etapa_id, tipo, categoria,
                    analise_critica, sugestao_melhoria,
                    necessidade_implantacao, ganho_previsto, observacoes,
                    sugestao_sera_implantada, plano_acao, responsavel_implantacao,
                    data_inicio_prevista, data_conclusao_prevista,
                    anexo_nome,
                    efetivamente_implantada, data_implantacao_efetiva, comentario_implantacao,
                    status, created_by, created_at, updated_at,
                    evidencia_url, evidencia_nome  -- ⭐ NOVO: campos da evidência
                FROM analises_criticas
                WHERE processo_id = :processo_id 
                    AND tipo = 'auditor'
                    AND status = 'ativo'
                ORDER BY created_at DESC
            """)
            
            result = conn.execute(query, {'processo_id': processo_id})
            
            analises = []
            for row in result:
                analise = {
                    'id': row[0],
                    'processo_id': row[1],
                    'etapa_id': row[2],
                    'tipo': row[3],
                    'categoria': row[4],
                    'analise_critica': row[5],
                    'sugestao_melhoria': row[6],
                    'necessidade_implantacao': row[7],
                    'ganho_previsto': row[8],
                    'observacoes': row[9],
                    'sugestao_sera_implantada': row[10],
                    'plano_acao': row[11],
                    'responsavel_implantacao': row[12],
                    'data_inicio_prevista': row[13].isoformat() if row[13] else None,
                    'data_conclusao_prevista': row[14].isoformat() if row[14] else None,
                    'anexo_nome': row[15],
                    'efetivamente_implantada': row[16],
                    'data_implantacao_efetiva': row[17].isoformat() if row[17] else None,
                    'comentario_implantacao': row[18],
                    'status': row[19],
                    'created_by': row[20],
                    'created_at': row[21].isoformat() if row[21] else None,
                    'updated_at': row[22].isoformat() if row[22] else None,
                    # ⭐ NOVO: Evidências
                    'evidencia_url': row[23],
                    'evidencia_nome': row[24],
                    'evidencias': []
                }
                
                # Se tiver evidência, adicionar na lista
                if row[24]:  # evidencia_nome
                    analise['evidencias'].append({
                        'id': row[0],
                        'nome_arquivo': row[24],
                        'url': row[23]
                    })
                
                analises.append(analise)
            
            return jsonify({
                'success': True,
                'analises': analises
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar análises do auditor: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/analise-auditor/<int:analise_id>/anexo')
def api_analise_auditor_anexo(analise_id):
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    from flask import send_file
    import io
    import base64
    import binascii
    
    try:
        with engine.connect() as conn:
            # ⭐ USAR CONEXÃO BRUTA PARA PEGAR OS BYTES CORRETAMENTE
            raw_conn = conn.connection
            cursor = raw_conn.cursor()
            
            cursor.execute("""
                SELECT anexo_base64, anexo_nome 
                FROM analises_criticas 
                WHERE id = %s AND tipo = 'auditor'
            """, (analise_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row or not row[0]:
                return jsonify({'error': 'Arquivo não encontrado'}), 404
            
            # ⭐ O DADO JÁ VEM COMO BYTES DO psycopg2
            anexo_bytes = row[0]
            anexo_nome = row[1] or f'anexo_analise_{analise_id}.pdf'
            
            # Verificar se é bytes
            if not isinstance(anexo_bytes, bytes):
                # Se veio como string hexadecimal, converter
                if isinstance(anexo_bytes, str):
                    # Remover '\x' se existir
                    hex_str = anexo_bytes.replace('\\x', '')
                    anexo_bytes = bytes.fromhex(hex_str)
                else:
                    try:
                        anexo_bytes = bytes(anexo_bytes)
                    except:
                        return jsonify({'error': 'Formato de arquivo inválido'}), 400
            
            # Verificar se é um PDF válido
            if len(anexo_bytes) > 4:
                if anexo_bytes[:4] != b'%PDF':
                    print(f"⚠️ Primeiros bytes: {anexo_bytes[:10]}")
                    # Não é PDF, pode ser que os dados ainda estejam em Base64
                    try:
                        # Tentar decodificar como Base64
                        anexo_bytes = base64.b64decode(anexo_bytes)
                        print(f"✅ Decodificado Base64, tamanho: {len(anexo_bytes)}")
                    except:
                        pass
            
            if len(anexo_bytes) < 100:
                return jsonify({'error': 'Arquivo muito pequeno (corrompido)'}), 400
            
            print(f"📎 Arquivo: {anexo_nome}, tamanho: {len(anexo_bytes)} bytes")
            
            return send_file(
                io.BytesIO(anexo_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=anexo_nome
            )
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/analise-auditor/<int:analise_id>/confirmar-implantacao', methods=['PUT'])
def api_analise_auditor_confirmar_implantacao(analise_id):
    """Confirma se a melhoria foi efetivamente implantada e CRIA FOLLOW-UPS automáticos"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    efetivamente_implantada = data.get('efetivamente_implantada')
    data_implantacao_efetiva = data.get('data_implantacao_efetiva')
    comentario_implantacao = data.get('comentario_implantacao', '')
    
    if efetivamente_implantada and not data_implantacao_efetiva:
        return jsonify({'success': False, 'error': 'Data de implantação é obrigatória'}), 400
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime, timedelta
    
    try:
        with engine.connect() as conn:
            # Buscar dados atuais da análise (usando 'tipo', não 'tipo')
            result = conn.execute(text("""
                SELECT sugestao_sera_implantada, processo_id
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditor'
            """), {'id': analise_id})
            analise = result.fetchone()
            
            if not analise:
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            # Atualizar a análise
            conn.execute(text("""
                UPDATE analises_criticas 
                SET efetivamente_implantada = :efetivamente_implantada,
                    data_implantacao_efetiva = :data_implantacao_efetiva,
                    comentario_implantacao = :comentario,
                    updated_at = NOW()
                WHERE id = :id
            """), {
                'id': analise_id,
                'efetivamente_implantada': efetivamente_implantada,
                'data_implantacao_efetiva': data_implantacao_efetiva,
                'comentario': comentario_implantacao
            })
            
            # Se foi implantada, criar follow-ups automáticos
            if efetivamente_implantada:
                data_base = datetime.strptime(data_implantacao_efetiva, '%Y-%m-%d')
                
                follow_ups = [
                    {'etapa': 'FOLLOW_UP_30', 'dias': 30},
                    {'etapa': 'FOLLOW_UP_60', 'dias': 60},
                    {'etapa': 'FOLLOW_UP_90', 'dias': 90}
                ]
                
                for fu in follow_ups:
                    data_prevista = data_base + timedelta(days=fu['dias'])
                    
                    # Verificar se já existe follow-up
                    check = conn.execute(text("""
                        SELECT id FROM analises_follow_up 
                        WHERE analise_id = :analise_id AND etapa = :etapa
                    """), {'analise_id': analise_id, 'etapa': fu['etapa']}).fetchone()
                    
                    if not check:
                        conn.execute(text("""
                            INSERT INTO analises_follow_up (
                                analise_id, etapa, data_prevista, status, created_by, created_at
                            ) VALUES (
                                :analise_id, :etapa, :data_prevista, 'Pendente', :created_by, NOW()
                            )
                        """), {
                            'analise_id': analise_id,
                            'etapa': fu['etapa'],
                            'data_prevista': data_prevista.date(),
                            'created_by': session.get('usuario_nome', 'Sistema')
                        })
                        print(f"✅ Follow-up {fu['etapa']} criado para {data_prevista.date()}")
                
                # Registrar no histórico de andamento (se a tabela existir)
                try:
                    conn.execute(text("""
                        INSERT INTO analises_historico_andamento (
                            analise_id, status, comentario, created_by, created_at
                        ) VALUES (
                            :analise_id, 'Concluido', :comentario, :created_by, NOW()
                        )
                    """), {
                        'analise_id': analise_id,
                        'comentario': f'✅ Melhoria implantada em {data_implantacao_efetiva}. Follow-ups criados para 30, 60 e 90 dias.',
                        'created_by': session.get('usuario_nome', 'Sistema')
                    })
                except Exception as e:
                    print(f"⚠️ Histórico: {e}")
            
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Implantação confirmada e follow-ups criados'})
            
    except Exception as e:
        print(f"❌ Erro ao confirmar implantação: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-auditor/<int:analise_id>/evidencias')
def listar_evidencias_analise(analise_id):
    """Lista as evidências de uma análise (para debug)"""
    if not session.get('autenticado'):
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        from database import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            query = text("""
                SELECT id, evidencia_url, evidencia_nome, created_at
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditor'
            """)
            result = conn.execute(query, {'id': analise_id})
            row = result.fetchone()
            
            if not row:
                return jsonify({'error': 'Análise não encontrada'}), 404
            
            return jsonify({
                'success': True,
                'analise_id': row[0],
                'evidencia_url': row[1],
                'evidencia_nome': row[2],
                'created_at': row[3]
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/melhorias/ativas', methods=['GET'])
def api_melhorias_ativas():
    """Lista melhorias que estão em acompanhamento (mesmo após auditoria finalizada)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    auditoria_id = request.args.get('auditoria_id')
    apenas_pendentes = request.args.get('apenas_pendentes', 'true').lower() == 'true'
    
    from database import engine
    from sqlalchemy import text
    from datetime import date
    
    try:
        with engine.connect() as conn:
            hoje = date.today()
            
            # Query corrigida: usa 'tipo' em vez de 'tipo'
            query = """
                SELECT 
                    a.id,
                    a.tipo,
                    a.sugestao_melhoria,
                    a.responsavel_implantacao,
                    a.data_conclusao_prevista,
                    a.data_implantacao_efetiva,
                    a.efetivamente_implantada,
                    p.codigo_processo,
                    p.nome_processo
                FROM analises_criticas a
                JOIN processos p ON a.processo_id = p.id
                WHERE a.sugestao_sera_implantada = true
                  AND (a.efetivamente_implantada = false OR a.efetivamente_implantada IS NULL)
            """
            
            params = {}
            
            if auditoria_id:
                query += " AND p.auditoria_id = :auditoria_id"
                params['auditoria_id'] = auditoria_id
            
            if apenas_pendentes:
                query += " AND (a.data_conclusao_prevista < :hoje OR a.data_conclusao_prevista IS NULL)"
                params['hoje'] = hoje
            
            query += " ORDER BY a.data_conclusao_prevista ASC NULLS LAST"
            
            result = conn.execute(text(query), params).fetchall()
            
            melhorias = []
            for row in result:
                prazo_vencido = False
                if row[4] and not row[6]:  # data_conclusao_prevista existe e não está implantada
                    prazo_vencido = row[4] < hoje
                
                melhorias.append({
                    'id': row[0],
                    'tipo': row[1],
                    'sugestao_melhoria': row[2] or '',
                    'responsavel': row[3] or '',
                    'data_conclusao_prevista': row[4].isoformat() if row[4] else None,
                    'data_implantacao': row[5].isoformat() if row[5] else None,
                    'efetivamente_implantada': row[6] or False,
                    'prazo_vencido': prazo_vencido,
                    'processo': f"{row[7]} - {row[8]}" if row[7] else row[8] or ''
                })
            
            return jsonify({'success': True, 'melhorias': melhorias})
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise/salvar', methods=['POST'])
def api_analise_salvar():
    """Salva ou atualiza uma análise crítica (auditado) com evidência"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('id')
    etapa_id = data.get('etapa_id')
    tipo = data.get('tipo', 'auditado')
    categoria = data.get('categoria', 'governanca')
    analise_critica = data.get('analise_critica', '')
    sugestao_melhoria = data.get('sugestao_melhoria', '')
    necessidade_implantacao = data.get('necessidade_implantacao', '')
    ganho_previsto = data.get('ganho_previsto', '')
    
    # Campos de evidência
    evidencia_base64 = data.get('evidencia_base64')
    evidencia_nome = data.get('evidencia_nome')
    remover_evidencia = data.get('remover_evidencia', False)
    
    if not etapa_id:
        return jsonify({'success': False, 'error': 'etapa_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    import base64
    import os
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            # Buscar o processo_id da etapa
            query_processo = text("""
                SELECT processo_id FROM etapas_processo WHERE id = :etapa_id
            """)
            result_processo = conn.execute(query_processo, {'etapa_id': etapa_id}).fetchone()
            processo_id = result_processo[0] if result_processo else None
            
            print(f"🔍 Etapa {etapa_id} pertence ao processo {processo_id}")
            
            # Processar evidência (se houver)
            evidencia_url_final = None
            evidencia_nome_final = None
            
            if remover_evidencia:
                print(f"🗑️ Removendo evidência da análise {analise_id or 'nova'}")
                evidencia_url_final = None
                evidencia_nome_final = None
            elif evidencia_base64 and evidencia_nome:
                try:
                    # Decodificar Base64
                    if ',' in evidencia_base64:
                        evidencia_base64 = evidencia_base64.split(',')[1]
                    evidencia_bytes = base64.b64decode(evidencia_base64)
                    
                    # Validar tamanho (10MB)
                    if len(evidencia_bytes) > 10 * 1024 * 1024:
                        return jsonify({'success': False, 'error': 'Arquivo muito grande. Máximo 10MB'}), 400
                    
                    # ⭐ USAR O SINGLETON - NÃO MAIS create_client!
                    from supabase_client import SupabaseClient
                    supabase = SupabaseClient.get_instance()
                    
                    # Se for edição, buscar ID da análise para criar o caminho
                    if analise_id:
                        query_analise = text("""
                            SELECT id FROM analises_criticas WHERE id = :id
                        """)
                        result_analise = conn.execute(query_analise, {'id': analise_id}).fetchone()
                        if result_analise:
                            analise_id_para_path = analise_id
                        else:
                            analise_id_para_path = int(datetime.now().timestamp())
                    else:
                        analise_id_para_path = int(datetime.now().timestamp())
                    
                    # Gerar caminho único
                    extensao = evidencia_nome.split('.')[-1].lower() if '.' in evidencia_nome else 'pdf'
                    timestamp = int(datetime.now().timestamp())
                    caminho = f"analises_auditado/{analise_id_para_path}/evidencia_{analise_id_para_path}_{timestamp}.{extensao}"
                    
                    # Fazer upload
                    supabase.storage.from_('evidencia_analises_auditado').upload(
                        path=caminho,
                        file=evidencia_bytes,
                        file_options={"content-type": "application/pdf"}
                    )
                    
                    # Gerar URL assinada
                    url_assinada = supabase.storage.from_('evidencia_analises_auditado').create_signed_url(
                        path=caminho,
                        expires_in=604800  # 7 dias
                    )
                    
                    evidencia_url_final = url_assinada['signedURL']
                    evidencia_nome_final = evidencia_nome
                    
                    print(f"📎 Evidência salva no Storage: {evidencia_url_final}")
                    
                except Exception as e:
                    print(f"⚠️ Erro ao salvar evidência no Storage: {e}")
            
            # Buscar evidência existente se não houver nova e não for remoção
            if not evidencia_base64 and not remover_evidencia and analise_id:
                query_existente = text("""
                    SELECT evidencia_url, evidencia_nome 
                    FROM analises_criticas 
                    WHERE id = :id
                """)
                result_existente = conn.execute(query_existente, {'id': analise_id}).fetchone()
                if result_existente and result_existente[0]:
                    evidencia_url_final = result_existente[0]
                    evidencia_nome_final = result_existente[1]
            
            if analise_id:
                # Atualizar
                query = text("""
                    UPDATE analises_criticas
                    SET tipo = :tipo,
                        categoria = :categoria,
                        analise_critica = :analise_critica,
                        sugestao_melhoria = :sugestao_melhoria,
                        necessidade_implantacao = :necessidade_implantacao,
                        ganho_previsto = :ganho_previsto,
                        evidencia_url = :evidencia_url,
                        evidencia_nome = :evidencia_nome,
                        updated_at = NOW()
                    WHERE id = :id
                """)
                conn.execute(query, {
                    'id': analise_id,
                    'tipo': tipo,
                    'categoria': categoria,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto,
                    'evidencia_url': evidencia_url_final,
                    'evidencia_nome': evidencia_nome_final
                })
                print(f"✏️ Análise {analise_id} atualizada")
            else:
                # Inserir nova
                query = text("""
                    INSERT INTO analises_criticas
                    (etapa_id, processo_id, tipo, categoria, 
                     analise_critica, sugestao_melhoria, 
                     necessidade_implantacao, ganho_previsto,
                     evidencia_url, evidencia_nome)
                    VALUES (:etapa_id, :processo_id, :tipo, :categoria,
                            :analise_critica, :sugestao_melhoria,
                            :necessidade_implantacao, :ganho_previsto,
                            :evidencia_url, :evidencia_nome)
                    RETURNING id
                """)
                result = conn.execute(query, {
                    'etapa_id': etapa_id,
                    'processo_id': processo_id,
                    'tipo': tipo,
                    'categoria': categoria,
                    'analise_critica': analise_critica,
                    'sugestao_melhoria': sugestao_melhoria,
                    'necessidade_implantacao': necessidade_implantacao,
                    'ganho_previsto': ganho_previsto,
                    'evidencia_url': evidencia_url_final,
                    'evidencia_nome': evidencia_nome_final
                })
                analise_id = result.fetchone()[0]
                print(f"✅ Nova análise criada! ID: {analise_id}, processo_id: {processo_id}")
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'id': analise_id,
                'message': 'Análise salva com sucesso'
            })
            
    except Exception as e:
        print(f"❌ Erro ao salvar análise: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise/<int:analise_id>', methods=['DELETE'])
def api_analise_excluir(analise_id):
    """Exclui uma análise crítica"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("DELETE FROM analises_criticas WHERE id = :id")
            conn.execute(query, {'id': analise_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Análise excluída'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir análise: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-follow-ups/criar', methods=['POST'])
def api_analise_follow_ups_criar():
    """Cria follow-ups automáticos para uma análise"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('analise_id')
    follow_ups = data.get('follow_ups', [])
    
    if not analise_id:
        return jsonify({'success': False, 'error': 'analise_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            for fu in follow_ups:
                query = text("""
                    INSERT INTO analises_follow_up (
                        analise_id, etapa, data_prevista, status, 
                        comentario, created_at, updated_at
                    ) VALUES (
                        :analise_id, :etapa, :data_prevista, 'Pendente',
                        'Aguardando registro', NOW(), NOW()
                    )
                """)
                conn.execute(query, {
                    'analise_id': analise_id,
                    'etapa': fu.get('etapa'),
                    'data_prevista': fu.get('data_prevista')
                })
            conn.commit()
            
            return jsonify({'success': True, 'message': f'{len(follow_ups)} follow-ups criados'})
            
    except Exception as e:
        print(f"❌ Erro ao criar follow-ups: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/analise-auditado/salvar', methods=['POST'])
def api_analise_auditado_salvar():
    """Salva uma nova análise do auditado com plano de ação e anexo"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    processo_id = data.get('processo_id')
    etapa_id = data.get('etapa_id')
    categoria = data.get('categoria')
    
    # Campos principais
    analise_critica = data.get('analise_critica', '')
    sugestao_melhoria = data.get('sugestao_melhoria', '')
    necessidade_implantacao = data.get('necessidade_implantacao', '')
    ganho_previsto = data.get('ganho_previsto', '')
    observacoes = data.get('observacoes', '')
    
    # Campos do plano de ação
    sugestao_sera_implantada = data.get('sugestao_sera_implantada')
    plano_acao = data.get('plano_acao', '')
    responsavel_implantacao = data.get('responsavel_implantacao', '')
    data_inicio_prevista = data.get('data_inicio_prevista')
    data_conclusao_prevista = data.get('data_conclusao_prevista')
    
    # Anexo
    anexo_base64 = data.get('anexo_base64')
    anexo_nome = data.get('anexo_nome')
    
    if not processo_id:
        return jsonify({'success': False, 'error': 'processo_id é obrigatório'}), 400
    
    if not etapa_id:
        return jsonify({'success': False, 'error': 'etapa_id é obrigatório'}), 400
    
    if not categoria:
        return jsonify({'success': False, 'error': 'categoria é obrigatória'}), 400
    
    if not analise_critica:
        return jsonify({'success': False, 'error': 'Análise Crítica é obrigatória'}), 400
    
    from database import engine
    from sqlalchemy import text
    import base64
    from psycopg2 import Binary
    
    try:
        with engine.connect() as conn:
            # Processar anexo
            anexo_bytes = None
            if anexo_base64:
                if ',' in anexo_base64:
                    anexo_base64 = anexo_base64.split(',')[1]
                anexo_bytes = base64.b64decode(anexo_base64)
                print(f"📎 Anexo recebido: {anexo_nome}, tamanho: {len(anexo_bytes)} bytes")
            
            anexo_param = Binary(anexo_bytes) if anexo_bytes else None
            
            query = text("""
                INSERT INTO analises_criticas (
                    processo_id, etapa_id, tipo, categoria,
                    analise_critica, sugestao_melhoria,
                    necessidade_implantacao, ganho_previsto, observacoes,
                    sugestao_sera_implantada, plano_acao, responsavel_implantacao,
                    data_inicio_prevista, data_conclusao_prevista,
                    anexo_base64, anexo_nome,
                    created_at, updated_at
                ) VALUES (
                    :processo_id, :etapa_id, 'auditado', :categoria,
                    :analise_critica, :sugestao_melhoria,
                    :necessidade_implantacao, :ganho_previsto, :observacoes,
                    :sugestao_sera_implantada, :plano_acao, :responsavel_implantacao,
                    :data_inicio_prevista, :data_conclusao_prevista,
                    :anexo_base64, :anexo_nome,
                    NOW(), NOW()
                )
                RETURNING id
            """)
            
            result = conn.execute(query, {
                'processo_id': processo_id,
                'etapa_id': etapa_id,
                'categoria': categoria,
                'analise_critica': analise_critica,
                'sugestao_melhoria': sugestao_melhoria,
                'necessidade_implantacao': necessidade_implantacao,
                'ganho_previsto': ganho_previsto,
                'observacoes': observacoes,
                'sugestao_sera_implantada': sugestao_sera_implantada,
                'plano_acao': plano_acao,
                'responsavel_implantacao': responsavel_implantacao,
                'data_inicio_prevista': data_inicio_prevista,
                'data_conclusao_prevista': data_conclusao_prevista,
                'anexo_base64': anexo_param,
                'anexo_nome': anexo_nome
            })
            novo_id = result.fetchone()[0]
            conn.commit()
            
            print(f"✅ Análise do auditado salva com ID: {novo_id}")
            
            return jsonify({'success': True, 'id': novo_id, 'message': 'Análise salva com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar análise do auditado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-auditado/<int:analise_id>/evidencia', methods=['GET'])
def api_analise_auditado_evidencia(analise_id):
    """Baixa a evidência de uma análise do auditado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    from flask import redirect
    from urllib.parse import urlparse
    
    try:
        with engine.connect() as conn:
            # Buscar a URL da evidência
            query = text("""
                SELECT evidencia_url, evidencia_nome
                FROM analises_criticas
                WHERE id = :id AND tipo = 'auditado'
            """)
            result = conn.execute(query, {'id': analise_id}).fetchone()
            
            if not result or not result[0]:
                return jsonify({'success': False, 'error': 'Evidência não encontrada'}), 404
            
            evidencia_url = result[0]
            evidencia_nome = result[1] or 'evidencia.pdf'
            
            # Extrair o caminho da URL para regenerar assinatura
            parsed = urlparse(evidencia_url)
            path_parts = parsed.path.split('/')
            
            caminho = None
            for i, part in enumerate(path_parts):
                if part == 'evidencia_analises_auditado' and i + 1 < len(path_parts):
                    caminho = '/'.join(path_parts[i+1:])
                    if '?' in caminho:
                        caminho = caminho.split('?')[0]
                    break
            
            if caminho:
                # ⭐ USAR O SINGLETON
                from supabase_client import SupabaseClient
                supabase = SupabaseClient.get_instance()
                
                url_assinada = supabase.storage.from_('evidencia_analises_auditado').create_signed_url(
                    path=caminho,
                    expires_in=604800  # 7 dias
                )
                
                # Atualizar a URL no banco
                update_query = text("""
                    UPDATE analises_criticas 
                    SET evidencia_url = :evidencia_url,
                        updated_at = NOW()
                    WHERE id = :id
                """)
                conn.execute(update_query, {
                    'evidencia_url': url_assinada['signedURL'],
                    'id': analise_id
                })
                conn.commit()
                
                return redirect(url_assinada['signedURL'])
            
            # Fallback: redirecionar para a URL atual
            return redirect(evidencia_url)
            
    except Exception as e:
        print(f"❌ Erro ao baixar evidência do auditado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-auditado/<int:analise_id>', methods=['PUT'])
def api_analise_auditado_atualizar(analise_id):
    """Atualiza uma análise do auditado existente (incluindo anexo e evidência)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    
    from database import engine
    from sqlalchemy import text
    import base64
    from psycopg2 import Binary
    from datetime import datetime
    
    # Anexo do plano de ação (se veio)
    remover_anexo = data.get('remover_anexo', False)
    anexo_base64 = data.get('anexo_base64')
    anexo_nome = data.get('anexo_nome')
    
    # Evidência da análise
    evidencia_base64 = data.get('evidencia_base64')
    evidencia_nome = data.get('evidencia_nome')
    remover_evidencia = data.get('remover_evidencia', False)
    
    try:
        with engine.connect() as conn:
            # Buscar dados atuais
            result_current = conn.execute(text("""
                SELECT anexo_base64, anexo_nome, evidencia_url, evidencia_nome
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditado'
            """), {'id': analise_id})
            current = result_current.fetchone()
            
            # Processar anexo do plano de ação
            anexo_bytes = None
            anexo_nome_final = None
            
            if remover_anexo:
                print(f"🗑️ Removendo anexo da análise {analise_id}")
            elif anexo_base64:
                if ',' in anexo_base64:
                    anexo_base64 = anexo_base64.split(',')[1]
                anexo_bytes = base64.b64decode(anexo_base64)
                anexo_nome_final = anexo_nome
                print(f"📎 Atualizando anexo: {anexo_nome_final}")
            else:
                if current and current[0]:
                    anexo_bytes = current[0]
                    anexo_nome_final = current[1]
            
            anexo_param = Binary(anexo_bytes) if anexo_bytes else None
            
            # ⭐ PROCESSAR EVIDÊNCIA COM SINGLETON
            evidencia_url_final = current[2] if current else None
            evidencia_nome_final = current[3] if current else None
            
            if remover_evidencia:
                print(f"🗑️ Removendo evidência da análise {analise_id}")
                evidencia_url_final = None
                evidencia_nome_final = None
            elif evidencia_base64 and evidencia_nome:
                try:
                    # Decodificar Base64
                    if ',' in evidencia_base64:
                        evidencia_base64 = evidencia_base64.split(',')[1]
                    evidencia_bytes = base64.b64decode(evidencia_base64)
                    
                    # Validar tamanho (10MB)
                    if len(evidencia_bytes) > 10 * 1024 * 1024:
                        return jsonify({'success': False, 'error': 'Arquivo muito grande. Máximo 10MB'}), 400
                    
                    # ⭐ USAR O SINGLETON
                    from supabase_client import SupabaseClient
                    supabase = SupabaseClient.get_instance()
                    
                    # Gerar caminho único
                    extensao = evidencia_nome.split('.')[-1].lower() if '.' in evidencia_nome else 'pdf'
                    timestamp = int(datetime.now().timestamp())
                    caminho = f"analises_auditado/{analise_id}/evidencia_{analise_id}_{timestamp}.{extensao}"
                    
                    # Fazer upload
                    supabase.storage.from_('evidencia_analises_auditado').upload(
                        path=caminho,
                        file=evidencia_bytes,
                        file_options={"content-type": "application/pdf"}
                    )
                    
                    # Gerar URL assinada
                    url_assinada = supabase.storage.from_('evidencia_analises_auditado').create_signed_url(
                        path=caminho,
                        expires_in=604800  # 7 dias
                    )
                    
                    evidencia_url_final = url_assinada['signedURL']
                    evidencia_nome_final = evidencia_nome
                    
                    print(f"📎 Evidência salva no Storage: {evidencia_url_final}")
                    
                except Exception as e:
                    print(f"⚠️ Erro ao salvar evidência no Storage: {e}")
                    # Mantém a evidência existente em caso de erro
                    evidencia_url_final = current[2] if current else None
                    evidencia_nome_final = current[3] if current else None
            
            # Atualizar a análise
            query = text("""
                UPDATE analises_criticas 
                SET analise_critica = :analise_critica,
                    sugestao_melhoria = :sugestao_melhoria,
                    necessidade_implantacao = :necessidade_implantacao,
                    ganho_previsto = :ganho_previsto,
                    observacoes = :observacoes,
                    sugestao_sera_implantada = :sugestao_sera_implantada,
                    plano_acao = :plano_acao,
                    responsavel_implantacao = :responsavel_implantacao,
                    data_inicio_prevista = :data_inicio_prevista,
                    data_conclusao_prevista = :data_conclusao_prevista,
                    anexo_base64 = :anexo_base64,
                    anexo_nome = :anexo_nome,
                    evidencia_url = :evidencia_url,
                    evidencia_nome = :evidencia_nome,
                    updated_at = NOW()
                WHERE id = :id AND tipo = 'auditado'
            """)
            
            result = conn.execute(query, {
                'id': analise_id,
                'analise_critica': data.get('analise_critica', ''),
                'sugestao_melhoria': data.get('sugestao_melhoria', ''),
                'necessidade_implantacao': data.get('necessidade_implantacao', ''),
                'ganho_previsto': data.get('ganho_previsto', ''),
                'observacoes': data.get('observacoes', ''),
                'sugestao_sera_implantada': data.get('sugestao_sera_implantada'),
                'plano_acao': data.get('plano_acao', ''),
                'responsavel_implantacao': data.get('responsavel_implantacao', ''),
                'data_inicio_prevista': data.get('data_inicio_prevista'),
                'data_conclusao_prevista': data.get('data_conclusao_prevista'),
                'anexo_base64': anexo_param,
                'anexo_nome': anexo_nome_final,
                'evidencia_url': evidencia_url_final,
                'evidencia_nome': evidencia_nome_final
            })
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            print(f"✅ Análise {analise_id} atualizada com sucesso")
            
            return jsonify({'success': True, 'message': 'Análise atualizada com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao atualizar análise do auditado: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analise-auditado/<int:analise_id>/anexo')
def api_analise_auditado_anexo(analise_id):
    """Baixa o anexo PDF de uma análise do auditado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    from flask import send_file
    import io
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT anexo_base64, anexo_nome 
                FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditado'
            """), {'id': analise_id})
            row = result.fetchone()
            
            if not row or not row[0]:
                return jsonify({'error': 'Arquivo não encontrado'}), 404
            
            anexo_bytes = bytes(row[0]) if hasattr(row[0], '__iter__') else row[0]
            anexo_nome = row[1] or f'anexo_auditado_{analise_id}.pdf'
            
            return send_file(
                io.BytesIO(anexo_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=anexo_nome
            )
            
    except Exception as e:
        print(f"❌ Erro ao baixar anexo: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analise-auditado/<int:analise_id>/confirmar-implantacao', methods=['PUT'])
def api_analise_auditado_confirmar_implantacao(analise_id):
    """Confirma implantação de uma análise do auditado e cria follow-ups"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    efetivamente_implantada = data.get('efetivamente_implantada')
    data_implantacao_efetiva = data.get('data_implantacao_efetiva')
    comentario_implantacao = data.get('comentario_implantacao', '')
    
    if efetivamente_implantada and not data_implantacao_efetiva:
        return jsonify({'success': False, 'error': 'Data de implantação é obrigatória'}), 400
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime, timedelta
    
    try:
        with engine.connect() as conn:
            # Verificar se existe e é do tipo 'auditado'
            result = conn.execute(text("""
                SELECT id FROM analises_criticas 
                WHERE id = :id AND tipo = 'auditado'
            """), {'id': analise_id})
            if not result.fetchone():
                return jsonify({'success': False, 'error': 'Análise não encontrada'}), 404
            
            # Atualizar
            conn.execute(text("""
                UPDATE analises_criticas 
                SET efetivamente_implantada = :efetivamente_implantada,
                    data_implantacao_efetiva = :data_implantacao_efetiva,
                    comentario_implantacao = :comentario,
                    updated_at = NOW()
                WHERE id = :id
            """), {
                'id': analise_id,
                'efetivamente_implantada': efetivamente_implantada,
                'data_implantacao_efetiva': data_implantacao_efetiva,
                'comentario': comentario_implantacao
            })
            
            # Criar follow-ups se implantada
            if efetivamente_implantada:
                data_base = datetime.strptime(data_implantacao_efetiva, '%Y-%m-%d')
                
                follow_ups = [
                    {'etapa': 'FOLLOW_UP_30', 'dias': 30},
                    {'etapa': 'FOLLOW_UP_60', 'dias': 60},
                    {'etapa': 'FOLLOW_UP_90', 'dias': 90}
                ]
                
                for fu in follow_ups:
                    data_prevista = data_base + timedelta(days=fu['dias'])
                    
                    check = conn.execute(text("""
                        SELECT id FROM analises_follow_up 
                        WHERE analise_id = :analise_id AND etapa = :etapa
                    """), {'analise_id': analise_id, 'etapa': fu['etapa']}).fetchone()
                    
                    if not check:
                        conn.execute(text("""
                            INSERT INTO analises_follow_up (
                                analise_id, etapa, data_prevista, status, created_by, created_at
                            ) VALUES (
                                :analise_id, :etapa, :data_prevista, 'Pendente', :created_by, NOW()
                            )
                        """), {
                            'analise_id': analise_id,
                            'etapa': fu['etapa'],
                            'data_prevista': data_prevista.date(),
                            'created_by': session.get('usuario_nome', 'Sistema')
                        })
            
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Implantação confirmada e follow-ups criados'})
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - HISTÓRICO DE ANDAMENTO
# ============================================================

@app.route('/api/analise-historico/<int:analise_id>', methods=['GET'])
def api_analise_historico_buscar(analise_id):
    """Busca o histórico de andamento de uma análise"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, status, comentario, created_by, created_at
                FROM analises_historico_andamento
                WHERE analise_id = :analise_id
                ORDER BY created_at DESC
            """)
            result = conn.execute(query, {'analise_id': analise_id}).fetchall()
            
            historico = []
            for row in result:
                historico.append({
                    'id': row[0],
                    'status': row[1],
                    'comentario': row[2] or '',
                    'created_by': row[3] or '',
                    'data_registro': row[4].isoformat() if row[4] else None
                })
            
            return jsonify({'success': True, 'historico': historico})
            
    except Exception as e:
        print(f"❌ Erro ao buscar histórico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise-historico/salvar', methods=['POST'])
def api_analise_historico_salvar():
    """Salva um registro de andamento"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    analise_id = data.get('analise_id')
    status = data.get('status')
    comentario = data.get('comentario')
    usuario_nome = session.get('usuario_nome', 'Sistema')
    
    if not analise_id:
        return jsonify({'success': False, 'error': 'analise_id é obrigatório'}), 400
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            query = text("""
                INSERT INTO analises_historico_andamento (
                    analise_id, status, comentario, created_by, created_at
                ) VALUES (
                    :analise_id, :status, :comentario, :created_by, NOW()
                )
            """)
            conn.execute(query, {
                'analise_id': analise_id,
                'status': status,
                'comentario': comentario,
                'created_by': usuario_nome
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Andamento registrado'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar histórico: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise-follow-ups/<int:analise_id>', methods=['GET'])
def api_analise_follow_ups_buscar(analise_id):
    """Busca os follow-ups de uma análise"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, etapa, data_prevista, data_realizada, status, comentario, responsavel
                FROM analises_follow_up
                WHERE analise_id = :analise_id
                ORDER BY data_prevista ASC
            """)
            result = conn.execute(query, {'analise_id': analise_id}).fetchall()
            
            follow_ups = []
            for row in result:
                follow_ups.append({
                    'id': row[0],
                    'etapa': row[1],
                    'data_prevista': row[2].isoformat() if row[2] else None,
                    'data_realizada': row[3].isoformat() if row[3] else None,
                    'status': row[4] or 'Pendente',
                    'comentario': row[5] or '',
                    'responsavel': row[6] or ''
                })
            
            return jsonify({'success': True, 'follow_ups': follow_ups})
            
    except Exception as e:
        print(f"❌ Erro ao buscar follow-ups: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analise-follow-up/<int:follow_up_id>', methods=['PUT'])
def api_analise_follow_up_atualizar(follow_up_id):
    """Atualiza um follow-up (registra resultado)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    status = data.get('status')
    comentario = data.get('comentario')
    usuario_nome = session.get('usuario_nome', 'Sistema')
    
    from database import engine
    from sqlalchemy import text
    from datetime import datetime
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE analises_follow_up 
                SET status = :status,
                    comentario = :comentario,
                    data_realizada = NOW(),
                    responsavel = :responsavel,
                    updated_at = NOW()
                WHERE id = :id
            """)
            result = conn.execute(query, {
                'id': follow_up_id,
                'status': status,
                'comentario': comentario,
                'responsavel': usuario_nome
            })
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Follow-up não encontrado'}), 404
            
            return jsonify({'success': True, 'message': 'Follow-up registrado'})
            
    except Exception as e:
        print(f"❌ Erro ao atualizar follow-up: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - ANOTAÇÕES DO AUDITOR
# ============================================================

@app.route('/api/anotacoes', methods=['GET'])
def api_anotacoes_listar():
    """Retorna todas as anotações do usuário logado"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    usuario_id = session.get('usuario_id')
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, titulo, conteudo, created_at, updated_at
                FROM anotacoes_auditor
                WHERE usuario_id = :usuario_id
                ORDER BY updated_at DESC
            """)
            result = conn.execute(query, {'usuario_id': usuario_id}).fetchall()
            
            anotacoes = []
            for row in result:
                anotacoes.append({
                    'id': row[0],
                    'titulo': row[1] or 'Sem título',
                    'conteudo': row[2] or '',
                    'created_at': row[3].strftime('%d/%m/%Y %H:%M') if row[3] else '',
                    'updated_at': row[4].strftime('%d/%m/%Y %H:%M') if row[4] else ''
                })
            
            return jsonify({'success': True, 'anotacoes': anotacoes})
            
    except Exception as e:
        print(f"❌ Erro ao buscar anotações: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/anotacoes/salvar', methods=['POST'])
def api_anotacoes_salvar():
    """Salva ou atualiza uma anotação"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    usuario_id = session.get('usuario_id')
    data = request.json
    
    anotacao_id = data.get('id')
    titulo = data.get('titulo', 'Sem título')
    conteudo = data.get('conteudo', '')
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            if anotacao_id:
                # Atualizar
                query = text("""
                    UPDATE anotacoes_auditor
                    SET titulo = :titulo, conteudo = :conteudo, updated_at = NOW()
                    WHERE id = :id AND usuario_id = :usuario_id
                """)
                conn.execute(query, {
                    'id': anotacao_id,
                    'titulo': titulo,
                    'conteudo': conteudo,
                    'usuario_id': usuario_id
                })
            else:
                # Nova
                query = text("""
                    INSERT INTO anotacoes_auditor (usuario_id, titulo, conteudo)
                    VALUES (:usuario_id, :titulo, :conteudo)
                    RETURNING id
                """)
                result = conn.execute(query, {
                    'usuario_id': usuario_id,
                    'titulo': titulo,
                    'conteudo': conteudo
                })
                anotacao_id = result.fetchone()[0]
            
            conn.commit()
            
            return jsonify({'success': True, 'id': anotacao_id, 'message': 'Anotação salva!'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar anotação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/anotacoes/<int:anotacao_id>', methods=['DELETE'])
def api_anotacoes_excluir(anotacao_id):
    """Exclui uma anotação"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    usuario_id = session.get('usuario_id')
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                DELETE FROM anotacoes_auditor
                WHERE id = :id AND usuario_id = :usuario_id
            """)
            conn.execute(query, {'id': anotacao_id, 'usuario_id': usuario_id})
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Anotação excluída'})
            
    except Exception as e:
        print(f"❌ Erro ao excluir anotação: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================================================
# API - DASHBOARD
# ============================================================

@app.route('/api/dashboard/riscos-etapa-magnitude')
def api_dashboard_riscos_etapa_magnitude():
    """Retorna quantidade de riscos de ETAPA por faixa de magnitude
    Suporta filtros por auditoria_id (única) ou auditoria_ids (múltiplas)
    """
    from database import engine
    from sqlalchemy import text
    
    try:
        auditoria_ids = request.args.get('auditoria_ids', '')
        auditoria_id = request.args.get('auditoria_id', '')
        
        with engine.connect() as conn:
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT 
                        SUM(CASE WHEN magnitude <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN magnitude >= 4 AND magnitude <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN magnitude >= 8 AND magnitude <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN magnitude >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos_etapa
                    WHERE ativo = true
                    AND auditoria_id IN ({placeholders})
                """)
                result = conn.execute(query, params).fetchone()
            
            # CASO 2: Uma auditoria específica
            elif auditoria_id:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN magnitude <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN magnitude >= 4 AND magnitude <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN magnitude >= 8 AND magnitude <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN magnitude >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos_etapa
                    WHERE ativo = true
                    AND auditoria_id = :auditoria_id
                """)
                result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            # CASO 3: Nenhum filtro - todos os riscos de etapa ativos
            else:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN magnitude <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN magnitude >= 4 AND magnitude <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN magnitude >= 8 AND magnitude <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN magnitude >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos_etapa
                    WHERE ativo = true
                """)
                result = conn.execute(query).fetchone()
            
            return jsonify({
                'success': True,
                'baixo': result[0] or 0,
                'medio': result[1] or 0,
                'alto': result[2] or 0,
                'critico': result[3] or 0
            })
            
    except Exception as e:
        print(f"❌ Erro em /api/dashboard/riscos-etapa-magnitude: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# ============================
# ===== API - AUDITORIAS =====
# ============================

@app.route('/api/usuarios-para-select')
def api_usuarios_para_select():
    """Retorna lista de usuários ativos para seleção"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id, nome, login, perfil
                FROM usuarios
                WHERE ativo = true
                ORDER BY nome
            """)
            result = conn.execute(query).fetchall()
            
            usuarios = [{'id': row[0], 'nome': row[1], 'login': row[2], 'perfil': row[3]} for row in result]
            
            return jsonify(usuarios)
            
    except Exception as e:
        print(f"❌ Erro ao buscar usuários: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auditorias')
def api_auditorias_listar():
    """Retorna todas as auditorias cadastradas"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    a.id,
                    a.codigo_auditoria,
                    a.id_area,
                    a.titulo,
                    a.ano,
                    a.trimestre,
                    a.data_inicio,
                    a.data_fim,
                    a.status,
                    a.responsavel_equipe,
                    a.unidade,
                    a.emergencial,
                    i.nome_area
                FROM auditorias a
                LEFT JOIN informacoes_area i ON a.id_area = i.id_area
                ORDER BY a.ano DESC, a.trimestre DESC
            """)
            result = conn.execute(query).fetchall()
            
            auditorias = []
            for row in result:
                # ⭐ RESPONSAVEL_EQUIPE está no índice 9 (décimo campo do SELECT)
                responsaveis_raw = row[9]
                
                # Converter ARRAY do PostgreSQL para lista Python
                if responsaveis_raw is None:
                    responsaveis_lista = []
                elif isinstance(responsaveis_raw, list):
                    responsaveis_lista = responsaveis_raw
                else:
                    responsaveis_lista = []
                
                auditorias.append({
                    'id': row[0],
                    'codigo_auditoria': row[1],
                    'id_area': row[2],
                    'titulo': row[3],
                    'ano': row[4],
                    'trimestre': row[5],
                    'data_inicio': row[6].strftime('%Y-%m-%d') if row[6] else None,
                    'data_fim': row[7].strftime('%Y-%m-%d') if row[7] else None,
                    'status': row[8],
                    'responsavel_equipe': responsaveis_lista,
                    'unidade': row[10] if len(row) > 10 else None,
                    'emergecial': row[11] if len(row) > 11 else None,
                    'nome_area': row[12] if len(row) > 12 else None
                })
            
            return jsonify(auditorias)
            
    except Exception as e:
        print(f"❌ Erro ao listar auditorias: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auditorias/salvar', methods=['POST'])
def api_auditorias_salvar():
    """Salva uma nova auditoria ou atualiza existente"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                INSERT INTO auditorias (
                    codigo_auditoria, id_area, titulo, ano, trimestre, 
                    data_inicio, data_fim, status, unidade, responsavel_equipe
                ) VALUES (
                    :codigo, :id_area, :titulo, :ano, :trimestre,
                    :data_inicio, :data_fim, :status, :unidade, :responsaveis
                )
            """)
            
            conn.execute(query, {
                'codigo': data.get('codigo_auditoria'),
                'id_area': data.get('id_area'),
                'titulo': data.get('titulo'),
                'ano': data.get('ano'),
                'trimestre': data.get('trimestre'),
                'data_inicio': data.get('data_inicio'),
                'data_fim': data.get('data_fim'),
                'status': data.get('status', 'Planejamento'),
                'unidade': data.get('unidade'),
                'responsaveis': data.get('responsavel_equipe', [])
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Auditoria salva com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao salvar auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auditorias/<int:auditoria_id>', methods=['DELETE'])
def api_auditorias_excluir(auditoria_id):
    """Exclui uma auditoria"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("DELETE FROM auditorias WHERE id = :id")
            conn.execute(query, {'id': auditoria_id})
            conn.commit()
            
            return jsonify({'success': True})
            
    except Exception as e:
        print(f"❌ Erro ao excluir auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/auditorias/<int:auditoria_id>', methods=['PUT'])
def api_auditorias_atualizar(auditoria_id):
    """Atualiza uma auditoria existente (com validação de permissão)"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    data = request.json
    usuario_nome = session.get('usuario_nome')
    usuario_perfil = session.get('usuario_perfil')
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Buscar a auditoria para verificar permissão
            query_check = text("SELECT responsavel_equipe FROM auditorias WHERE id = :id")
            result_check = conn.execute(query_check, {'id': auditoria_id}).fetchone()
            
            if not result_check:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            responsaveis = result_check[0] or []
            
            # Verificar permissão: administrador OU responsável
            if usuario_perfil not in ['administrador', 'admin'] and usuario_nome not in responsaveis:
                return jsonify({'success': False, 'error': 'Você não tem permissão para editar esta auditoria'}), 403
            
            # Se a auditoria está cancelada, não permite editar
            query_status = text("SELECT status FROM auditorias WHERE id = :id")
            status_result = conn.execute(query_status, {'id': auditoria_id}).fetchone()
            
            if status_result and status_result[0] == 'Cancelada':
                return jsonify({'success': False, 'error': 'Auditorias canceladas não podem ser editadas'}), 403
            
            # Atualizar
            query = text("""
                UPDATE auditorias 
                SET codigo_auditoria = :codigo,
                    id_area = :id_area,
                    titulo = :titulo,
                    ano = :ano,
                    trimestre = :trimestre,
                    data_inicio = :data_inicio,
                    data_fim = :data_fim,
                    status = :status,
                    unidade = :unidade,
                    responsavel_equipe = :responsaveis,
                    updated_at = NOW()
                WHERE id = :id
            """)
            
            conn.execute(query, {
                'id': auditoria_id,
                'codigo': data.get('codigo_auditoria'),
                'id_area': data.get('id_area'),
                'titulo': data.get('titulo'),
                'ano': data.get('ano'),
                'trimestre': data.get('trimestre'),
                'data_inicio': data.get('data_inicio'),
                'data_fim': data.get('data_fim'),
                'status': data.get('status', 'Planejamento'),
                'unidade': data.get('unidade'),
                'responsaveis': data.get('responsavel_equipe', [])
            })
            conn.commit()
            
            return jsonify({'success': True, 'message': 'Auditoria atualizada com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao atualizar auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auditorias/<int:auditoria_id>')
def api_auditorias_buscar(auditoria_id):
    """Retorna uma auditoria específica para edição"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    id, 
                    codigo_auditoria, 
                    id_area, 
                    titulo, 
                    ano, 
                    trimestre, 
                    data_inicio, 
                    data_fim, 
                    status, 
                    responsavel_equipe, 
                    unidade,
                    emergencial
                FROM auditorias 
                WHERE id = :id
            """)
            result = conn.execute(query, {'id': auditoria_id}).fetchone()
            
            if not result:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada'}), 404
            
            # ⭐ DEBUG: Imprimir todos os campos
            print(f"🔍 RESULT COMPLETO: {result}")
            print(f"🔍 QUANTIDADE DE CAMPOS: {len(result)}")
            print(f"🔍 ÍNDICE 0 (id): {result[0]}")
            print(f"🔍 ÍNDICE 11 (emergencial): {result[11] if len(result) > 11 else 'NÃO EXISTE'}")
            
            # responsavel_equipe está no índice 9
            responsaveis = result[9] if result[9] else []
            if not isinstance(responsaveis, list):
                responsaveis = []
            
            auditoria = {
                'id': result[0],
                'codigo_auditoria': result[1],
                'id_area': result[2],
                'titulo': result[3],
                'ano': result[4],
                'trimestre': result[5],
                'data_inicio': result[6].strftime('%Y-%m-%d') if result[6] else None,
                'data_fim': result[7].strftime('%Y-%m-%d') if result[7] else None,
                'status': result[8],
                'responsavel_equipe': responsaveis,
                'unidade': result[10] if len(result) > 10 else None,
                'emergencial': result[11] if len(result) > 11 and result[11] is not None else False
            }
            
            print(f"🔍 AUDITORIA DICT: {auditoria}")
            
            return jsonify({'success': True, 'auditoria': auditoria})
            
    except Exception as e:
        print(f"❌ Erro ao buscar auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/auditorias/<int:auditoria_id>/cancelar', methods=['PUT'])
def api_auditorias_cancelar(auditoria_id):
    """Cancela uma auditoria (soft delete) - apenas administrador"""
    if not session.get('autenticado'):
        return jsonify({'success': False, 'error': 'Não autenticado'}), 401
    
    # Verificar se é administrador
    if session.get('usuario_perfil') not in ['administrador', 'admin']:
        return jsonify({'success': False, 'error': 'Apenas administradores podem cancelar auditorias'}), 403
    
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            query = text("""
                UPDATE auditorias 
                SET status = 'Cancelada', updated_at = NOW()
                WHERE id = :id AND status != 'Cancelada'
            """)
            result = conn.execute(query, {'id': auditoria_id})
            conn.commit()
            
            if result.rowcount == 0:
                return jsonify({'success': False, 'error': 'Auditoria não encontrada ou já cancelada'}), 404
            
            return jsonify({'success': True, 'message': 'Auditoria cancelada com sucesso'})
            
    except Exception as e:
        print(f"❌ Erro ao cancelar auditoria: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ============================
# ===== FIM API - AUDITORIAS =====
# ============================

@app.route('/api/auditorias/situacao')
def api_auditorias_situacao():
    """Retorna situação das auditorias com todos os status existentes"""
    from database import engine
    from sqlalchemy import text
    
    try:
        area_id = request.args.get('area_id')
        
        with engine.connect() as conn:
            if area_id:
                query = text("""
                    SELECT status, COUNT(*) as total
                    FROM auditorias
                    WHERE id_area = :area_id
                    GROUP BY status
                    ORDER BY 
                        CASE status
                            WHEN 'Planejamento' THEN 1
                            WHEN 'Em Execução' THEN 2
                            WHEN 'Concluída' THEN 3
                            WHEN 'Concluída Avaliação' THEN 4
                            WHEN 'Concluída com Follow-Up' THEN 5
                            WHEN 'Em Atraso' THEN 6
                            WHEN 'Inconclusiva' THEN 7
                            ELSE 8
                        END
                """)
                result = conn.execute(query, {'area_id': area_id}).fetchall()
            else:
                query = text("""
                    SELECT status, COUNT(*) as total
                    FROM auditorias
                    GROUP BY status
                    ORDER BY 
                        CASE status
                            WHEN 'Planejamento' THEN 1
                            WHEN 'Em Execução' THEN 2
                            WHEN 'Concluída' THEN 3
                            WHEN 'Concluída Avaliação' THEN 4
                            WHEN 'Concluída com Follow-Up' THEN 5
                            WHEN 'Em Atraso' THEN 6
                            WHEN 'Inconclusiva' THEN 7
                            ELSE 8
                        END
                """)
                result = conn.execute(query).fetchall()
            
            # Mapeamento de cores e ícones para cada status
            cores_status = {
                'Planejamento': '#ffc107',           # Amarelo
                'Em Execução': '#17a2b8',             # Azul
                'Concluída': '#28a745',               # Verde
                'Concluída Avaliação': '#20c997',     # Verde menta
                'Concluída com Follow-Up': '#34ce57', # Verde claro
                'Em Atraso': '#dc3545',               # Vermelho
                'Inconclusiva': '#6c757d'             # Cinza
            }
            
            # Nomes amigáveis para exibição
            nomes_status = {
                'Planejamento': 'Planejamento',
                'Em Execução': 'Em Execução',
                'Concluída': 'Concluída',
                'Concluída Avaliação': 'Concluída (Avaliação)',
                'Concluída com Follow-Up': 'Concluída (Follow-Up)',
                'Em Atraso': 'Em Atraso',
                'Inconclusiva': 'Inconclusiva'
            }
            
            labels = []
            dados = []
            cores = []
            
            for row in result:
                status = row[0]
                total = row[1]
                labels.append(nomes_status.get(status, status))
                dados.append(total)
                cores.append(cores_status.get(status, '#6c757d'))
            
            # Se não houver dados, retorna vazio
            if not dados:
                return jsonify({
                    'success': True,
                    'labels': ['Nenhuma auditoria'],
                    'dados': [1],
                    'cores': ['#e0e0e0']
                })
            
            return jsonify({
                'success': True,
                'labels': labels,
                'dados': dados,
                'cores': cores
            })
            
    except Exception as e:
        print(f"❌ Erro ao buscar situação das auditorias: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processos/detalhados')
def api_processos_detalhados():
    """Retorna a quantidade de processos que possuem etapas cadastradas (com filtros)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT COUNT(DISTINCT p.id)
                    FROM processos p
                    JOIN etapas_processo ep ON p.id = ep.processo_id
                    WHERE p.status = 'Ativo'
                    AND p.auditoria_id IN ({placeholders})
                """)
                total = conn.execute(query, params).fetchone()[0] or 0
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT COUNT(DISTINCT p.id)
                    FROM processos p
                    JOIN etapas_processo ep ON p.id = ep.processo_id
                    WHERE p.status = 'Ativo'
                    AND p.auditoria_id = :auditoria_id
                """)
                total = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()[0] or 0
            
            # CASO 3: Nenhum filtro
            else:
                query = text("""
                    SELECT COUNT(DISTINCT p.id)
                    FROM processos p
                    JOIN etapas_processo ep ON p.id = ep.processo_id
                    WHERE p.status = 'Ativo'
                """)
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
            
    except Exception as e:
        print(f"❌ Erro em /api/processos/detalhados: {e}")
        return jsonify({'total': 0, 'error': str(e)})

@app.route('/api/processos/total')
def api_processos_total():
    """Retorna o total de processos ativos (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # Pega os parâmetros
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT COUNT(*) FROM processos 
                    WHERE status = 'Ativo' 
                    AND auditoria_id IN ({placeholders})
                """)
                total = conn.execute(query, params).fetchone()[0] or 0
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT COUNT(*) FROM processos 
                    WHERE status = 'Ativo' AND auditoria_id = :auditoria_id
                """)
                total = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()[0] or 0
            
            # CASO 3: Nenhum filtro
            else:
                query = text("SELECT COUNT(*) FROM processos WHERE status = 'Ativo'")
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
            
    except Exception as e:
        print(f"❌ Erro em /api/processos/total: {e}")
        return jsonify({'total': 0, 'error': str(e)})

@app.route('/api/auditorias/total')
def api_auditorias_total():
    """Retorna o total de auditorias (com filtro por área)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        area_id = request.args.get('area_id')
        
        with engine.connect() as conn:
            if area_id:
                query = text("SELECT COUNT(*) FROM auditorias WHERE id_area = :area_id")
                total = conn.execute(query, {'area_id': area_id}).fetchone()[0] or 0
            else:
                query = text("SELECT COUNT(*) FROM auditorias")
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
    except Exception as e:
        return jsonify({'total': 0, 'error': str(e)})

@app.route('/api/riscos/total')
def api_riscos_total():
    """Retorna o total de riscos (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT COUNT(r.id) 
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE p.auditoria_id IN ({placeholders})
                """)
                total = conn.execute(query, params).fetchone()[0] or 0
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT COUNT(r.id) 
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE p.auditoria_id = :auditoria_id
                """)
                total = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()[0] or 0
            
            # CASO 3: Nenhum filtro
            else:
                query = text("SELECT COUNT(*) FROM riscos")
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
            
    except Exception as e:
        print(f"❌ Erro em /api/riscos/total: {e}")
        return jsonify({'total': 0, 'error': str(e)})

@app.route('/api/dashboard/riscos-magnitude')
def api_dashboard_riscos_magnitude():
    """Retorna quantidade de riscos por faixa de magnitude (com suporte a filtros)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        auditoria_ids = request.args.get('auditoria_ids', '')
        auditoria_id = request.args.get('auditoria_id', '')
        
        with engine.connect() as conn:
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT 
                        SUM(CASE WHEN r.score_risco <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN r.score_risco >= 4 AND r.score_risco <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN r.score_risco >= 8 AND r.score_risco <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN r.score_risco >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE p.auditoria_id IN ({placeholders})
                """)
                result = conn.execute(query, params).fetchone()
            
            # CASO 2: Auditoria única ⭐ NOVO!
            elif auditoria_id:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN r.score_risco <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN r.score_risco >= 4 AND r.score_risco <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN r.score_risco >= 8 AND r.score_risco <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN r.score_risco >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos r
                    JOIN processos p ON r.processo_id = p.id
                    WHERE p.auditoria_id = :auditoria_id
                """)
                result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()
            
            # CASO 3: Nenhum filtro - todos os riscos
            else:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN score_risco <= 3 THEN 1 ELSE 0 END) as baixo,
                        SUM(CASE WHEN score_risco >= 4 AND score_risco <= 7 THEN 1 ELSE 0 END) as medio,
                        SUM(CASE WHEN score_risco >= 8 AND score_risco <= 11 THEN 1 ELSE 0 END) as alto,
                        SUM(CASE WHEN score_risco >= 12 THEN 1 ELSE 0 END) as critico
                    FROM riscos
                """)
                result = conn.execute(query).fetchone()
            
            return jsonify({
                'success': True,
                'baixo': result[0] or 0,
                'medio': result[1] or 0,
                'alto': result[2] or 0,
                'critico': result[3] or 0
            })
            
    except Exception as e:
        print(f"❌ Erro em /api/dashboard/riscos-magnitude: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/auditorias-status')
def api_dashboard_auditorias_status():
    """Retorna quantidade de auditorias por status (com filtro por área)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        area_id = request.args.get('area_id')
        
        with engine.connect() as conn:
            if area_id:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) as concluida,
                        SUM(CASE WHEN status = 'Em Execução' THEN 1 ELSE 0 END) as execucao,
                        SUM(CASE WHEN status = 'Planejamento' THEN 1 ELSE 0 END) as planejamento
                    FROM auditorias
                    WHERE id_area = :area_id
                """)
                result = conn.execute(query, {'area_id': area_id}).fetchone()
            else:
                query = text("""
                    SELECT 
                        SUM(CASE WHEN status = 'Concluída' THEN 1 ELSE 0 END) as concluida,
                        SUM(CASE WHEN status = 'Em Execução' THEN 1 ELSE 0 END) as execucao,
                        SUM(CASE WHEN status = 'Planejamento' THEN 1 ELSE 0 END) as planejamento
                    FROM auditorias
                """)
                result = conn.execute(query).fetchone()
            
            return jsonify({
                'success': True,
                'concluida': result[0] or 0,
                'execucao': result[1] or 0,
                'planejamento': result[2] or 0
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/top-areas')
def api_dashboard_top_areas():
    """Retorna as áreas com mais processos (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT i.nome_area, COUNT(p.id) as total
                    FROM informacoes_area i
                    LEFT JOIN processos p ON i.id_area = p.id_area 
                        AND p.status = 'Ativo' 
                        AND p.auditoria_id IN ({placeholders})
                    GROUP BY i.id_area, i.nome_area
                    ORDER BY total DESC
                    LIMIT 5
                """)
                result = conn.execute(query, params).fetchall()
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT i.nome_area, COUNT(p.id) as total
                    FROM informacoes_area i
                    LEFT JOIN processos p ON i.id_area = p.id_area 
                        AND p.status = 'Ativo' 
                        AND p.auditoria_id = :auditoria_id
                    GROUP BY i.id_area, i.nome_area
                    ORDER BY total DESC
                    LIMIT 5
                """)
                result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            # CASO 3: Nenhum filtro
            else:
                query = text("""
                    SELECT i.nome_area, COUNT(p.id) as total
                    FROM informacoes_area i
                    LEFT JOIN processos p ON i.id_area = p.id_area AND p.status = 'Ativo'
                    GROUP BY i.id_area, i.nome_area
                    ORDER BY total DESC
                    LIMIT 5
                """)
                result = conn.execute(query).fetchall()
            
            areas = [{'nome_area': row[0], 'total': row[1]} for row in result]
            
            return jsonify({'success': True, 'areas': areas})
            
    except Exception as e:
        print(f"❌ Erro em /api/dashboard/top-areas: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/resumo-riscos')
def api_dashboard_resumo_riscos():
    """Retorna resumo de riscos por processo (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            auditoria_ids = request.args.get('auditoria_ids', '')
            auditoria_id = request.args.get('auditoria_id', '')
            
            # CASO 1: Múltiplas auditorias
            if auditoria_ids:
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                query = text(f"""
                    SELECT 
                        p.id,
                        p.codigo_processo,
                        p.nome_processo,
                        COUNT(r.id) as total_riscos,
                        MAX(r.score_risco) as score_maximo
                    FROM processos p
                    LEFT JOIN riscos r ON p.id = r.processo_id
                    WHERE p.status = 'Ativo' 
                        AND p.auditoria_id IN ({placeholders})
                    GROUP BY p.id, p.codigo_processo, p.nome_processo
                    HAVING COUNT(r.id) > 0
                    ORDER BY score_maximo DESC NULLS LAST
                    LIMIT 10
                """)
                result = conn.execute(query, params).fetchall()
            
            # CASO 2: Única auditoria
            elif auditoria_id:
                query = text("""
                    SELECT 
                        p.id,
                        p.codigo_processo,
                        p.nome_processo,
                        COUNT(r.id) as total_riscos,
                        MAX(r.score_risco) as score_maximo
                    FROM processos p
                    LEFT JOIN riscos r ON p.id = r.processo_id
                    WHERE p.status = 'Ativo' AND p.auditoria_id = :auditoria_id
                    GROUP BY p.id, p.codigo_processo, p.nome_processo
                    HAVING COUNT(r.id) > 0
                    ORDER BY score_maximo DESC NULLS LAST
                    LIMIT 10
                """)
                result = conn.execute(query, {'auditoria_id': auditoria_id}).fetchall()
            
            # CASO 3: Nenhum filtro
            else:
                query = text("""
                    SELECT 
                        p.id,
                        p.codigo_processo,
                        p.nome_processo,
                        COUNT(r.id) as total_riscos,
                        MAX(r.score_risco) as score_maximo
                    FROM processos p
                    LEFT JOIN riscos r ON p.id = r.processo_id
                    WHERE p.status = 'Ativo'
                    GROUP BY p.id, p.codigo_processo, p.nome_processo
                    HAVING COUNT(r.id) > 0
                    ORDER BY score_maximo DESC NULLS LAST
                    LIMIT 10
                """)
                result = conn.execute(query).fetchall()
            
            processos = []
            for row in result:
                processos.append({
                    'id': row[0],
                    'codigo_processo': row[1] or '',
                    'nome_processo': row[2] or '',
                    'total_riscos': row[3] or 0,
                    'score_maximo': row[4] or 0
                })
            
            return jsonify({'success': True, 'processos': processos})
            
    except Exception as e:
        print(f"❌ Erro em /api/dashboard/resumo-riscos: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/controles/total')
def api_controles_total():
    """Retorna o total de controles cadastrados (com suporte a múltiplas auditorias)"""
    from database import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            # ⭐ NOVO: Pega o parâmetro de múltiplas auditorias
            auditoria_ids = request.args.get('auditoria_ids', '')
            # Mantém o antigo para compatibilidade
            auditoria_id = request.args.get('auditoria_id', '')
            
            # ⭐ CASO 1: Múltiplas auditorias (ex: "1,9")
            if auditoria_ids:
                # Converter "1,9" para lista [1, 9]
                ids_list = [int(x) for x in auditoria_ids.split(',') if x]
                
                # Criar placeholders para SQL (ex: ':id0, :id1')
                placeholders = ','.join([':id' + str(i) for i in range(len(ids_list))])
                
                # Criar dicionário de parâmetros (ex: {'id0': 1, 'id1': 9})
                params = {f'id{i}': id_val for i, id_val in enumerate(ids_list)}
                
                # Query com IN (ex: WHERE p.auditoria_id IN (:id0, :id1))
                query = text(f"""
                    SELECT COUNT(*) FROM controles_etapa ce
                    JOIN riscos_etapa re ON ce.risco_id = re.id
                    JOIN etapas_processo ep ON re.etapa_id = ep.id
                    JOIN processos p ON ep.processo_id = p.id
                    WHERE p.auditoria_id IN ({placeholders})
                """)
                total = conn.execute(query, params).fetchone()[0] or 0
            
            # ⭐ CASO 2: Uma única auditoria (compatibilidade)
            elif auditoria_id:
                query = text("""
                    SELECT COUNT(*) FROM controles_etapa ce
                    JOIN riscos_etapa re ON ce.risco_id = re.id
                    JOIN etapas_processo ep ON re.etapa_id = ep.id
                    JOIN processos p ON ep.processo_id = p.id
                    WHERE p.auditoria_id = :auditoria_id
                """)
                total = conn.execute(query, {'auditoria_id': auditoria_id}).fetchone()[0] or 0
            
            # ⭐ CASO 3: Nenhum filtro - todos os controles
            else:
                query = text("SELECT COUNT(*) FROM controles_etapa")
                total = conn.execute(query).fetchone()[0] or 0
            
            return jsonify({'total': total})
            
    except Exception as e:
        print(f"❌ Erro em /api/controles/total: {e}")
        return jsonify({'total': 0, 'error': str(e)})

# ============================================================
# FIM API - DASHBOARD
# ============================================================

@app.route('/diagnostico-rapido')
def diagnostico_rapido():
    import time
    import psutil
    from flask import render_template_string
    
    resultados = {
        'memoria': psutil.virtual_memory().percent,
        'cpu': psutil.cpu_percent(interval=1),
    }
    
    # Teste de banco de dados
    start = time.time()
    from database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT 1")).fetchone()
    resultados['db_tempo'] = f"{(time.time() - start)*1000:.0f}ms"
    
    # Teste de renderização
    start = time.time()
    render_template_string('<h1>Teste</h1>')
    resultados['template_tempo'] = f"{(time.time() - start)*1000:.0f}ms"
    
    return jsonify(resultados)

# ============================================================
# PONTO DE ENTRADA
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Servidor Flask iniciando...")
    print(f"📁 SECRET_KEY configurada: {'✅ OK' if app.secret_key else '❌ FALHOU'}")
    print(f"⏱️ Timeout da sessão: {app.config['PERMANENT_SESSION_LIFETIME']}")
    print("=" * 50)
    print("\n📍 Acesse: http://127.0.0.1:5000/login")
    print("🔒 Use suas credenciais cadastradas no Supabase")
    print("\n⚠️ Aperte CTRL+C para parar o servidor\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)