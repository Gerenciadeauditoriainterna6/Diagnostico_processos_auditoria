# database.py - Versão para Flask + Render
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env (apenas em desenvolvimento)
load_dotenv()

# ============================================
# CONFIGURAÇÃO DA BASE
# ============================================

Base = declarative_base()

def get_db_engine():
    # Tenta pegar a DATABASE_URL das variáveis de ambiente
    db_url = os.environ.get('DATABASE_URL')
    
    if not db_url:
        raise Exception("❌ DATABASE_URL não encontrada! Verifique seu arquivo .env")
    
    # Configuração SSL para o Supabase
    if 'supabase' in db_url:
        if '?' not in db_url:
            db_url = db_url + '?sslmode=require'
        else:
            db_url = db_url + '&sslmode=require'
    
    # Cria a engine de conexão
    engine = create_engine(
        db_url,
        pool_pre_ping=True,  # Mantém conexão ativa
        pool_recycle=3600     # Reconecta a cada hora
    )
    
    return engine

# Cria a engine global
engine = get_db_engine()

# Cria a sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================
# MODELOS
# ============================================

class Checklist(Base):
    __tablename__ = 'checklists'
    
    id = Column(Integer, primary_key=True)
    processo_id = Column(Integer, ForeignKey('processos.id'), nullable=False)
    tipo = Column(String(20), nullable=False)  # 'governanca', 'riscos', 'controles'
    status = Column(String(20), default='Não iniciado')
    observacoes_gerais = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamentos
    respostas = relationship('ChecklistResposta', back_populates='checklist', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'processo_id': self.processo_id,
            'tipo': self.tipo,
            'status': self.status,
            'observacoes_gerais': self.observacoes_gerais,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ChecklistResposta(Base):
    __tablename__ = 'checklist_respostas'
    
    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, ForeignKey('checklists.id'), nullable=False)
    pergunta_ordem = Column(Integer, nullable=False)
    resposta = Column(String(20))  # 'Sim', 'Não', 'Não se aplica'
    comentario = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relacionamentos
    checklist = relationship('Checklist', back_populates='respostas')
    evidencias = relationship('ChecklistEvidencia', back_populates='resposta', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'checklist_id': self.checklist_id,
            'pergunta_ordem': self.pergunta_ordem,
            'resposta': self.resposta,
            'comentario': self.comentario,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'evidencias': [e.to_dict() for e in self.evidencias]
        }


class ChecklistEvidencia(Base):
    __tablename__ = 'checklist_evidencias'
    
    id = Column(Integer, primary_key=True)
    resposta_id = Column(Integer, ForeignKey('checklist_respostas.id'), nullable=False)
    nome_arquivo = Column(String(255), nullable=False)
    caminho_arquivo = Column(String(500), nullable=False)
    tamanho_bytes = Column(Integer)
    content_type = Column(String(100))
    uploaded_at = Column(DateTime, default=datetime.now)
    
    # Relacionamentos
    resposta = relationship('ChecklistResposta', back_populates='evidencias')
    
    def to_dict(self):
        return {
            'id': self.id,
            'resposta_id': self.resposta_id,
            'nome_arquivo': self.nome_arquivo,
            'caminho_arquivo': self.caminho_arquivo,
            'tamanho_bytes': self.tamanho_bytes,
            'content_type': self.content_type,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }


# ============================================
# FUNÇÕES DE CRIAÇÃO DE TABELAS
# ============================================

def criar_tabelas():
    """Cria todas as tabelas no banco de dados"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Retorna uma sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# EXPORTAÇÕES
# ============================================

# Para facilitar a importação
__all__ = [
    'engine',
    'SessionLocal',
    'Base',
    'Checklist',
    'ChecklistResposta',
    'ChecklistEvidencia',
    'criar_tabelas',
    'get_db'
]