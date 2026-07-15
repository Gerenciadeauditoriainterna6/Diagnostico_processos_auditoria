# services/analise_service.py
from database import engine
from sqlalchemy import text
from typing import Dict, List, Optional, Any

class AnaliseService:
    """Serviço centralizado para gerenciar análises críticas"""
    
    # ⭐ CAMPOS PERMITIDOS PARA UPDATE
    CAMPOS_PERMITIDOS = [
        'analise_critica', 'sugestao_melhoria', 'necessidade_implantacao',
        'ganho_previsto', 'observacoes', 'sugestao_sera_implantada',
        'efetivamente_implantada', 'data_implantacao_efetiva', 'status'
    ]
    
    @staticmethod
    def _get_campos_tabela():
        """Retorna todos os campos da tabela"""
        return AnaliseService.CAMPOS_PERMITIDOS + [
            'processo_id', 'etapa_id', 'tipo', 'categoria',
            'created_by', 'created_at', 'updated_at',
            'evidencia_url', 'evidencia_nome'  # ⭐ ADICIONAR EVIDÊNCIA
        ]
    
    @classmethod
    def listar_por_processo(cls, processo_id: int, tipo: str = 'auditado') -> List[Dict]:
        """Lista análises de um processo"""
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    ac.id,
                    ac.processo_id,
                    ac.etapa_id,
                    ac.tipo,
                    ac.categoria,
                    ac.analise_critica,
                    ac.sugestao_melhoria,
                    ac.necessidade_implantacao,
                    ac.ganho_previsto,
                    ac.observacoes,
                    ac.sugestao_sera_implantada,
                    ac.efetivamente_implantada,
                    ac.data_implantacao_efetiva,
                    ac.status,
                    ac.created_by,
                    ac.created_at,
                    ac.updated_at,
                    ep.codigo_etapa,
                    ep.nome_etapa,
                    ac.evidencia_url,
                    ac.evidencia_nome
                FROM analises_criticas ac
                LEFT JOIN etapas_processo ep ON ac.etapa_id = ep.id
                WHERE ac.processo_id = :processo_id
                AND ac.tipo = :tipo
                AND ac.status = 'ativo'
                ORDER BY ep.codigo_etapa, ac.categoria
            """)
            
            result = conn.execute(query, {'processo_id': processo_id, 'tipo': tipo})
            
            analises = []
            for row in result:
                analises.append({
                    'id': row[0],
                    'processo_id': row[1],
                    'etapa_id': row[2],
                    'tipo': row[3],
                    'categoria': row[4],
                    'analise_critica': row[5] or '',
                    'sugestao_melhoria': row[6] or '',
                    'necessidade_implantacao': row[7] or '',
                    'ganho_previsto': row[8] or '',
                    'observacoes': row[9] or '',
                    'sugestao_sera_implantada': row[10],
                    'efetivamente_implantada': row[11],
                    'data_implantacao_efetiva': row[12].isoformat() if row[12] else None,
                    'status': row[13],
                    'created_by': row[14],
                    'created_at': row[15].isoformat() if row[15] else None,
                    'updated_at': row[16].isoformat() if row[16] else None,
                    'codigo_etapa': row[17] or '',
                    'nome_etapa': row[18] or '',
                    'evidencia_url': row[19],
                    'evidencia_nome': row[20]
                })
            
            return analises
    
    @classmethod
    def criar(cls, dados: Dict) -> int:
        """Cria uma nova análise"""
        campos_validos = {k: v for k, v in dados.items() 
                         if k in cls._get_campos_tabela() and v is not None}
        
        campos = ', '.join(campos_validos.keys())
        valores = ', '.join([f':{k}' for k in campos_validos.keys()])
        
        query = text(f"""
            INSERT INTO analises_criticas ({campos}, created_at, updated_at)
            VALUES ({valores}, NOW(), NOW())
            RETURNING id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, campos_validos)
            novo_id = result.fetchone()[0]
            conn.commit()
            return novo_id
    
    @classmethod
    def atualizar(cls, id: int, dados: Dict) -> bool:
        # ⭐ LOG
        print("=" * 50)
        print("🔧 AnaliseService.atualizar()")
        print(f"  Dados recebidos: {dados}")
        print("=" * 50)
        
        # ⭐ NÃO FILTRAR VALORES None - Permitir atualizar para NULL
        campos_update = {}
        for campo in cls.CAMPOS_PERMITIDOS:
            if campo in dados:
                # ⭐ Incluir mesmo se for None (para setar NULL no banco)
                campos_update[campo] = dados.get(campo)
        
        print(f"  Campos após filtro: {campos_update}")
        
        if not campos_update:
            return False
        
        set_clause = ', '.join([f"{k} = :{k}" for k in campos_update.keys()])
        campos_update['id'] = id
        
        query = text(f"""
            UPDATE analises_criticas 
            SET {set_clause}, updated_at = NOW()
            WHERE id = :id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, campos_update)
            conn.commit()
            return result.rowcount > 0
    
    @classmethod
    def atualizar_evidencia(cls, id: int, evidencia_url: str, evidencia_nome: str) -> bool:
        """Atualiza apenas os campos de evidência de uma análise"""
        query = text("""
            UPDATE analises_criticas 
            SET evidencia_url = :evidencia_url,
                evidencia_nome = :evidencia_nome,
                updated_at = NOW()
            WHERE id = :id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {
                'id': id,
                'evidencia_url': evidencia_url,
                'evidencia_nome': evidencia_nome
            })
            conn.commit()
            return result.rowcount > 0
    
    @classmethod
    def buscar_por_id(cls, id: int) -> Optional[Dict]:
        """Busca uma análise pelo ID"""
        with engine.connect() as conn:
            query = text("""
                SELECT 
                    id, processo_id, etapa_id, tipo, categoria,
                    analise_critica, sugestao_melhoria,
                    necessidade_implantacao, ganho_previsto, observacoes,
                    sugestao_sera_implantada, efetivamente_implantada,
                    data_implantacao_efetiva, status,
                    created_by, created_at, updated_at,
                    evidencia_url, evidencia_nome
                FROM analises_criticas
                WHERE id = :id
            """)
            
            result = conn.execute(query, {'id': id}).fetchone()
            
            if not result:
                return None
            
            return {
                'id': result[0],
                'processo_id': result[1],
                'etapa_id': result[2],
                'tipo': result[3],
                'categoria': result[4],
                'analise_critica': result[5] or '',
                'sugestao_melhoria': result[6] or '',
                'necessidade_implantacao': result[7] or '',
                'ganho_previsto': result[8] or '',
                'observacoes': result[9] or '',
                'sugestao_sera_implantada': result[10],
                'efetivamente_implantada': result[11],
                'data_implantacao_efetiva': result[12].isoformat() if result[12] else None,
                'status': result[13],
                'created_by': result[14],
                'created_at': result[15].isoformat() if result[15] else None,
                'updated_at': result[16].isoformat() if result[16] else None,
                'evidencia_url': result[17],
                'evidencia_nome': result[18]
            }
    
    @classmethod
    def confirmar_implantacao(cls, id: int, efetivamente_implantada: bool, 
                              data_implantacao_efetiva: str, comentario: str = None) -> bool:
        """Confirma a implantação de uma análise"""
        query = text("""
            UPDATE analises_criticas 
            SET efetivamente_implantada = :efetivamente_implantada,
                data_implantacao_efetiva = :data_implantacao_efetiva,
                comentario_implantacao = :comentario,
                updated_at = NOW()
            WHERE id = :id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {
                'id': id,
                'efetivamente_implantada': efetivamente_implantada,
                'data_implantacao_efetiva': data_implantacao_efetiva,
                'comentario': comentario
            })
            conn.commit()
            return result.rowcount > 0
    
    @classmethod
    def deletar(cls, id: int) -> bool:
        """Deleta (soft delete) uma análise"""
        query = text("""
            UPDATE analises_criticas 
            SET status = 'arquivado', updated_at = NOW()
            WHERE id = :id
        """)
        
        with engine.connect() as conn:
            result = conn.execute(query, {'id': id})
            conn.commit()
            return result.rowcount > 0