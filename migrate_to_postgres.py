"""
Script para Migrar Dados de SQLite para PostgreSQL
Copia todos os usuários/licenses do SQLite para PostgreSQL
Executa automaticamente com o novo db_manager.py
"""

import sqlite3
import psycopg2
import os
import logging

logger = logging.getLogger(__name__)

def migrate_sqlite_to_postgres(sqlite_file, postgres_url):
    """
    Migra dados do SQLite para PostgreSQL
    Usa INSERT OR IGNORE para não duplicar dados
    """
    try:
        # Conecta ao SQLite
        sqlite_conn = sqlite3.connect(sqlite_file)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        # Pega todos os usuários
        sqlite_cursor.execute("SELECT * FROM usuarios")
        usuarios = sqlite_cursor.fetchall()
        
        if not usuarios:
            logger.info("ℹ️ Nenhum usuário para migrar no SQLite")
            sqlite_conn.close()
            return
        
        # Conecta ao PostgreSQL
        postgres_conn = psycopg2.connect(postgres_url)
        postgres_cursor = postgres_conn.cursor()
        
        migrados = 0
        duplicados = 0
        erros = 0
        
        for usuario in usuarios:
            try:
                # Converte Row para dict
                usr_dict = dict(usuario)
                
                # Tenta inserir
                postgres_cursor.execute('''
                    INSERT INTO usuarios 
                    (license_key, username, password_hash, hwid, ip_registro, data_registro, ativo, registered)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (license_key) DO NOTHING
                ''', (
                    usr_dict.get('license_key'),
                    usr_dict.get('username', ''),
                    usr_dict.get('password_hash', ''),
                    usr_dict.get('hwid'),
                    usr_dict.get('ip_registro'),
                    usr_dict.get('data_registro'),
                    usr_dict.get('ativo', 1),
                    usr_dict.get('registered', 0)
                ))
                
                if postgres_cursor.rowcount > 0:
                    migrados += 1
                    logger.info(f"✅ Migrado: {usr_dict.get('license_key')} ({usr_dict.get('username')})")
                else:
                    duplicados += 1
            except Exception as e:
                erros += 1
                logger.error(f"❌ Erro ao migrar {usuario['license_key']}: {e}")
        
        postgres_conn.commit()
        postgres_conn.close()
        sqlite_conn.close()
        
        logger.info(f"""
📊 Migração Completa:
   ✅ Migrados: {migrados}
   ⚠️ Duplicados (já existiam): {duplicados}
   ❌ Erros: {erros}
   Total: {migrados + duplicados + erros}
        """)
        
        return migrados, duplicados, erros
        
    except Exception as e:
        logger.error(f"❌ Erro geral na migração: {e}")
        return None

if __name__ == "__main__":
    postgres_url = os.environ.get('DATABASE_URL')
    sqlite_file = os.path.join(os.path.dirname(__file__), 'Meubot', 'licencas.db')
    
    if not postgres_url:
        print("❌ DATABASE_URL não configurada!")
        print("Adicione a variável de ambiente DATABASE_URL com a URL do PostgreSQL")
        exit(1)
    
    if not os.path.exists(sqlite_file):
        print(f"⚠️ Arquivo SQLite não encontrado: {sqlite_file}")
        print("Pulando migração")
        exit(0)
    
    print("🔄 Iniciando migração SQLite → PostgreSQL...")
    migrate_sqlite_to_postgres(sqlite_file, postgres_url)
