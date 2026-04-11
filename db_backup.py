"""
Sistema de backup automático do banco de dados
Garante que dados não sejam perdidos em Render/Discloud
"""

import sqlite3
import json
import os
import shutil
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DBBackup:
    def __init__(self, db_file=None):
        # Se db_file for None, usa caminho padrão
        if db_file is None:
            db_file = os.path.join(os.path.dirname(__file__), 'licencas.db')
        
        self.db_file = db_file
        self.backup_file = db_file.replace('.db', '_backup.json') if db_file else 'licencas_backup.json'
        self.memory_cache = {}
        self.load_backup()
    
    def load_backup(self):
        """Carrega backup em memória"""
        if os.path.exists(self.backup_file):
            try:
                with open(self.backup_file, 'r') as f:
                    self.memory_cache = json.load(f)
                logger.info(f"✅ Backup carregado em memória: {len(self.memory_cache)} licenças")
                return True
            except Exception as e:
                logger.error(f"❌ Erro ao carregar backup: {e}")
        return False
    
    def save_backup(self):
        """Salva backup em JSON para Render/Discloud"""
        try:
            # Se não tem cache em memória, tira do SQLite (se existir)
            if not self.memory_cache and os.path.exists(self.db_file):
                try:
                    conn = sqlite3.connect(self.db_file)
                    conn.row_factory = sqlite3.Row
                    c = conn.cursor()
                    c.execute('SELECT * FROM usuarios')
                    usuarios = c.fetchall()
                    
                    backup_data = {}
                    for user in usuarios:
                        backup_data[user['license_key']] = {
                            'license_key': user['license_key'],
                            'username': user['username'],
                            'password_hash': user['password_hash'],
                            'hwid': user['hwid'],
                            'ip_registro': user['ip_registro'],
                            'data_registro': user['data_registro'],
                            'ativo': user['ativo'],
                            'registered': user['registered']
                        }
                    conn.close()
                    self.memory_cache = backup_data
                except:
                    pass
            
            # Salva cache em JSON
            if self.memory_cache:
                with open(self.backup_file, 'w') as f:
                    json.dump(self.memory_cache, f, indent=2)
                logger.info(f"💾 Backup salvo: {len(self.memory_cache)} licenças")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao salvar backup: {e}")
            return False
    
    def restore_from_backup(self):
        """Restaura BD do backup em JSON"""
        if not self.memory_cache:
            logger.warning("⚠️ Nenhum backup disponível para restaurar")
            return False
        
        try:
            # Remove BD danificado
            if os.path.exists(self.db_file):
                os.remove(self.db_file)
            
            # Cria novo BD do zero
            from app import init_db
            init_db()
            
            # Restaura dados
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            
            for key, data in self.memory_cache.items():
                c.execute('''
                    INSERT INTO usuarios 
                    (license_key, username, password_hash, hwid, ip_registro, data_registro, ativo, registered)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['license_key'],
                    data['username'],
                    data['password_hash'],
                    data['hwid'],
                    data['ip_registro'],
                    data['data_registro'],
                    data['ativo'],
                    data['registered']
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Banco restaurado do backup: {len(self.memory_cache)} licenças recuperadas")
            return True
        except Exception as e:
            logger.error(f"❌ Erro ao restaurar backup: {e}")
            return False
    
    def verify_db_integrity(self):
        """Verifica integridade do BD e restaura se necessário"""
        try:
            # Se está usando PostgreSQL, não precisa validar SQLite
            if 'DATABASE_URL' in os.environ:
                logger.info("🐘 PostgreSQL ativo, backup em segundo plano")
                return True
            
            if not os.path.exists(self.db_file):
                logger.warning("⚠️ BD não encontrado, restaurando do backup...")
                return self.restore_from_backup()
            
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            
            # Tenta contar registros
            c.execute('SELECT COUNT(*) FROM usuarios')
            count = c.fetchone()[0]
            
            # Testa acesso
            c.execute('SELECT * FROM usuarios LIMIT 1')
            conn.close()
            
            logger.info(f"✅ BD íntegro: {count} licenças")
            return True
        except Exception as e:
            logger.error(f"❌ BD corrompido ou inacessível: {e}")
            logger.warning("🔄 Tentando restaurar do backup...")
            return self.restore_from_backup()
    
    def sync_backup(self):
        """Sincroniza BD com backup (bi-direcional)"""
        self.verify_db_integrity()
        self.save_backup()

# Instância global
_db_backup = None

def init_backup(db_file):
    global _db_backup
    _db_backup = DBBackup(db_file)
    _db_backup.verify_db_integrity()
    return _db_backup

def get_backup():
    global _db_backup
    return _db_backup
