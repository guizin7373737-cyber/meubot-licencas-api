"""
Sistema de Banco de Dados Persistente
Suporta PostgreSQL (produção) e SQLite (fallback)
Garante que dados NUNCA sejam perdidos
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

ENV = os.environ.get('FLASK_ENV', 'production')
USE_POSTGRES = os.environ.get('DATABASE_URL') is not None

class DatabaseManager:
    def __init__(self):
        self.use_postgres = USE_POSTGRES
        self.postgres_url = os.environ.get('DATABASE_URL')
        self.sqlite_file = os.path.join(os.path.dirname(__file__), 'licencas.db')
        
        if self.use_postgres:
            logger.info("🐘 Usando PostgreSQL (Produção)")
        else:
            logger.info("🗄️ Usando SQLite (Fallback)")
        
        self.init_db()
    
    def init_db(self):
        """Inicializa o banco de dados"""
        if self.use_postgres:
            self._init_postgres()
        else:
            self._init_sqlite()
    
    def _init_postgres(self):
        """Inicializa PostgreSQL"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    license_key VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(255) DEFAULT '',
                    password_hash VARCHAR(64) DEFAULT '',
                    hwid TEXT,
                    ip_registro VARCHAR(45),
                    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ativo INTEGER DEFAULT 1,
                    registered INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("✅ PostgreSQL inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar PostgreSQL: {e}")
            logger.warning("🔄 Caindo para SQLite...")
            self.use_postgres = False
            self._init_sqlite()
    
    def _init_sqlite(self):
        """Inicializa SQLite"""
        try:
            conn = sqlite3.connect(self.sqlite_file)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT UNIQUE NOT NULL,
                    username TEXT DEFAULT '',
                    password_hash TEXT DEFAULT '',
                    hwid TEXT,
                    ip_registro TEXT,
                    data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ativo INTEGER DEFAULT 1,
                    registered INTEGER DEFAULT 0
                )
            ''')
            conn.commit()
            conn.close()
            logger.info("✅ SQLite inicializado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar SQLite: {e}")
    
    def execute_query(self, query, params=(), fetch='one'):
        """Executa query de forma agnóstica (Postgres ou SQLite)"""
        try:
            if self.use_postgres:
                return self._execute_postgres(query, params, fetch)
            else:
                return self._execute_sqlite(query, params, fetch)
        except Exception as e:
            logger.error(f"❌ Erro na query: {e} | Query: {query}")
            raise
    
    def _execute_postgres(self, query, params, fetch):
        """Executa em PostgreSQL"""
        try:
            conn = psycopg2.connect(self.postgres_url)
            c = conn.cursor(cursor_factory=RealDictCursor)
            
            # Converte sintaxe SQLite para PostgreSQL
            query_pg = query.replace('?', '%s')
            
            c.execute(query_pg, params)
            
            if fetch == 'all':
                result = c.fetchall()
            elif fetch == 'one':
                result = c.fetchone()
            else:
                result = c.rowcount
            
            conn.commit()
            conn.close()
            
            return result
        except Exception as e:
            logger.error(f"❌ Erro PostgreSQL: {e}")
            raise
    
    def _execute_sqlite(self, query, params, fetch):
        """Executa em SQLite"""
        try:
            conn = sqlite3.connect(self.sqlite_file)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            c.execute(query, params)
            
            if fetch == 'all':
                result = c.fetchall()
            elif fetch == 'one':
                result = c.fetchone()
            else:
                result = c.rowcount
            
            conn.commit()
            conn.close()
            
            return result
        except Exception as e:
            logger.error(f"❌ Erro SQLite: {e}")
            raise
    
    def insert(self, table, **kwargs):
        """Insere um registro"""
        cols = ', '.join(kwargs.keys())
        placeholders = ', '.join(['?' for _ in kwargs])
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        vals = tuple(kwargs.values())
        return self.execute_query(query, vals, fetch='rowcount')
    
    def update(self, table, where_col, where_val, **kwargs):
        """Atualiza registros"""
        updates = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        query = f"UPDATE {table} SET {updates} WHERE {where_col} = ?"
        vals = tuple(list(kwargs.values()) + [where_val])
        return self.execute_query(query, vals, fetch='rowcount')
    
    def select(self, table, where_col=None, where_val=None, fetch='all'):
        """Seleciona registros"""
        if where_col:
            query = f"SELECT * FROM {table} WHERE {where_col} = ?"
            params = (where_val,)
        else:
            query = f"SELECT * FROM {table}"
            params = ()
        return self.execute_query(query, params, fetch=fetch)
    
    def select_custom(self, query, params=(), fetch='all'):
        """Executa SELECT customizado"""
        return self.execute_query(query, params, fetch=fetch)
    
    def health_check(self):
        """Verifica saúde do BD"""
        try:
            self.execute_query("SELECT COUNT(*) FROM usuarios", fetch='one')
            return True
        except:
            return False

# Instância global
_db = None

def get_db():
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db
