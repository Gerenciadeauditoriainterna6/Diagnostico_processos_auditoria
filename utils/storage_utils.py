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