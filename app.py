from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime
import hashlib

app = Flask(__name__)

DB_FILE = "licencas.db"

def init_db():
    """Inicializa o banco de dados se não existir"""
    if not os.path.exists(DB_FILE):
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
        conn.close()

init_db()

@app.route('/registrar', methods=['POST'])
def registrar():
    """Registra uma nova licença com username e password"""
    try:
        dados = request.json
        license_key = dados.get('license_key', '').strip()
        username = dados.get('username', '').strip()
        password = dados.get('password', '').strip()
        hwid = dados.get('hwid', '').strip()
        ip_cliente = request.remote_addr
        
        if not all([license_key, username, password, hwid]):
            return jsonify({'erro': 'Dados incompletos'}), 400
        
        # Hash da senha
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Verifica se a licença existe no banco
        c.execute('SELECT * FROM usuarios WHERE license_key = ?', (license_key,))
        usuario = c.fetchone()
        
        if not usuario:
            return jsonify({'erro': 'Licença inválida ou já foi ativada'}), 400
        
        # Atualiza o registro com username, password e marca como registrado
        c.execute('''
            UPDATE usuarios 
            SET username = ?, password_hash = ?, hwid = ?, ip_registro = ?, registered = 1, ativo = 1
            WHERE license_key = ?
        ''', (username, password_hash, hwid, ip_cliente, license_key))
        
        conn.commit()
        conn.close()
        
        return jsonify({'mensagem': 'Licença ativada com sucesso!', 'license_key': license_key}), 201
    
    except sqlite3.IntegrityError:
        return jsonify({'erro': 'Licença já foi registrada'}), 400
    except Exception as e:
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

@app.route('/validar', methods=['POST'])
def validar():
    """Valida uma licença já registrada"""
    try:
        dados = request.json
        license_key = dados.get('license_key', '').strip()
        hwid = dados.get('hwid', '').strip()
        
        if not license_key or not hwid:
            return jsonify({'erro': 'Licença ou HWID não fornecidos'}), 400
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM usuarios 
            WHERE license_key = ? AND hwid = ? AND ativo = 1 AND registered = 1
        ''', (license_key, hwid))
        
        usuario = c.fetchone()
        conn.close()
        
        if usuario:
            return jsonify({'mensagem': 'Licença válida', 'status': 'ativo'}), 200
        else:
            return jsonify({'erro': 'Licença inválida, HWID não corresponde ou inativa'}), 401
    
    except Exception as e:
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def login():
    """Faz login com username e password"""
    try:
        dados = request.json
        username = dados.get('username', '').strip()
        password = dados.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'erro': 'Username ou password vazios'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute('''
            SELECT * FROM usuarios 
            WHERE username = ? AND password_hash = ? AND ativo = 1 AND registered = 1
        ''', (username, password_hash))
        
        usuario = c.fetchone()
        conn.close()
        
        if usuario:
            return jsonify({
                'mensagem': 'Login bem-sucedido',
                'license_key': usuario[2],
                'status': 'ativo'
            }), 200
        else:
            return jsonify({'erro': 'Credenciais inválidas'}), 401
    
    except Exception as e:
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

@app.route('/status', methods=['GET'])
def status():
    """Verifica o status do servidor"""
    return jsonify({'status': 'online', 'timestamp': datetime.now().isoformat()}), 200

if __name__ == '__main__':
    # Use PORT da variável de ambiente (Discloud usa isso)
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
