import sqlite3
import os

DB_FILE = 'licencas.db'

def init_database():
    """Inicializa o banco de dados com a tabela usuarios"""
    conn = sqlite3.connect(DB_FILE)
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
    
    # Verifica se tabela foi criada
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")
    if c.fetchone():
        print('✅ Tabela usuarios criada com sucesso!')
    else:
        print('❌ Erro ao criar tabela usuarios')
    
    conn.close()

if __name__ == '__main__':
    init_database()
