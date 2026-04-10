from flask import Flask, request, jsonify
from functools import wraps
import sqlite3
import os
from datetime import datetime
import hashlib
import random
import string
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

API_SECRET = os.environ.get('API_SECRET', 'seu_token_secreto_aqui')

# Banco de dados - usar sempre a pasta local (Meubot/)
# Em Render, use /tmp/ que é temporário, mas salvamos periodicamente
if os.environ.get('FLASK_ENV') == 'production':
    # Em Render: usar /tmp/ como fallback
    DB_FILE = os.environ.get('DB_PATH', '/tmp/licencas.db')
    logger.info(f"🔒 Modo PRODUCTION: BD em {DB_FILE}")
else:
    # Localmente: usa a pasta Zphantom2
    DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'licencas.db')
    logger.info(f"🔓 Modo DESENVOLVIMENTO: BD em {DB_FILE}")

logger.info(f"📁 Banco de dados: {DB_FILE}")

ENV = os.environ.get('FLASK_ENV', 'production')
PORT = int(os.environ.get('PORT', 8080))

def verificar_token(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token or token != API_SECRET:
            return jsonify({'erro': 'Token inválido ou ausente'}), 401
        return f(*args, **kwargs)
    return decorador

def init_db():
    """Inicializa o banco de dados e a tabela se necessário"""
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
    logger.info("Database initialized")

def gerar_licenca():
    prefixo = "NEOREPLAY"
    caracteres = string.ascii_letters + string.digits
    blocos = [''.join(random.choices(caracteres, k=6)) for _ in range(6)]
    return prefixo + "-" + "-".join(blocos)

@app.route('/', methods=['GET'])
def home():
    """Health check do servidor"""
    return jsonify({
        'status': 'online',
        'servico': 'NEOREPLAY Licencas',
        'timestamp': datetime.now().isoformat(),
        'versao': '2.0'
    }), 200

@app.route('/status', methods=['GET'])
def status():
    """Status do servidor"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/registrar', methods=['POST'])
@verificar_token
def registrar():
    """Registra uma nova licença com username e password"""
    try:
        dados = request.json or {}
        license_key = dados.get('license_key', '').strip()
        username = dados.get('username', '').strip()
        password = dados.get('password', '').strip()
        hwid = dados.get('hwid', '').strip()
        ip_cliente = request.remote_addr
        
        logger.info(f"📝 Registrando: {license_key} | User: {username}")
        
        if not all([license_key, username, password, hwid]):
            return jsonify({'erro': 'Dados incompletos'}), 400
        
        # Hash da senha
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Verifica se a licença existe
        c.execute('SELECT * FROM usuarios WHERE license_key = ?', (license_key,))
        usuario = c.fetchone()
        
        if not usuario:
            conn.close()
            logger.warning(f"❌ Licença não encontrada: {license_key}")
            return jsonify({'erro': 'Licença inválida'}), 400
        
        # usuario[8] = registered
        if usuario[8] == 1:
            conn.close()
            logger.warning(f"⚠️ Licença já registrada: {license_key}")
            return jsonify({'erro': 'Licença já foi ativada'}), 400
        
        # Atualiza o registro
        c.execute('''
            UPDATE usuarios 
            SET username = ?, password_hash = ?, hwid = ?, ip_registro = ?, registered = 1, ativo = 1
            WHERE license_key = ?
        ''', (username, password_hash, hwid, ip_cliente, license_key))
        
        conn.commit()
        
        # Verifica se o UPDATE funcionou
        c.execute('SELECT registered FROM usuarios WHERE license_key = ?', (license_key,))
        verificar = c.fetchone()
        
        conn.close()
        
        if verificar and verificar[0] == 1:
            logger.info(f"✅ Licença registrada com sucesso: {license_key} | User: {username}")
            return jsonify({
                'mensagem': 'Licença ativada com sucesso!',
                'license_key': license_key,
                'username': username
            }), 201
        else:
            logger.error(f"❌ Falha ao registrar: {license_key}")
            return jsonify({'erro': 'Erro ao registrar licença'}), 500
    
    except sqlite3.IntegrityError as e:
        logger.error(f"❌ Erro de integridade BD: {e}")
        return jsonify({'erro': 'Licença ou username duplicado'}), 400
    except Exception as e:
        logger.error(f"❌ Erro em /registrar: {str(e)}")
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

@app.route('/validar', methods=['POST'])
def validar():
    """Valida uma licença já registrada"""
    try:
        dados = request.json or {}
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
            return jsonify({
                'mensagem': 'Licença válida',
                'status': 'ativo'
            }), 200
        else:
            return jsonify({'erro': 'Licença inválida ou não corresponde ao HWID'}), 401
    
    except Exception as e:
        logger.error(f"Error in /validar: {str(e)}")
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def login():
    """Faz login com username e password"""
    try:
        dados = request.json or {}
        username = dados.get('username', '').strip()
        password = dados.get('password', '').strip()
        
        logger.info(f"🔐 Tentativa de login: {username}")
        
        if not username or not password:
            logger.warning(f"❌ Login vazio: user={username}")
            return jsonify({'erro': 'Username ou password vazios'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        # Primeiro verifica se o usuário existe
        c.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
        usuario = c.fetchone()
        
        if not usuario:
            conn.close()
            logger.warning(f"❌ Usuário não encontrado: {username}")
            return jsonify({'erro': 'Credenciais inválidas'}), 401
        
        logger.info(f"✓ Usuário encontrado: {username} | Registered: {usuario[8]} | Ativo: {usuario[7]}")
        
        # Verifica password
        if usuario[3] != password_hash:
            conn.close()
            logger.warning(f"❌ Senha incorreta para: {username}")
            return jsonify({'erro': 'Credenciais inválidas'}), 401
        
        # Verifica se está ativo e registrado
        if usuario[7] == 0 or usuario[8] == 0:
            conn.close()
            logger.warning(f"❌ Licença inativa/não registrada: {username} | Ativo: {usuario[7]} | Registrada: {usuario[8]}")
            return jsonify({'erro': 'Licença banida ou não registrada'}), 401
        
        conn.close()
        
        logger.info(f"✅ Login bem-sucedido: {username}")
        return jsonify({
            'mensagem': 'Login bem-sucedido',
            'license_key': usuario[1],
            'username': username,
            'status': 'ativo'
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Erro em /login: {str(e)}")
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

@app.route('/gerar', methods=['POST'])
@verificar_token
def gerar_route():
    """Gera uma nova licença (Bot only)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        while True:
            license_key = gerar_licenca()
            c.execute('SELECT id FROM usuarios WHERE license_key = ?', (license_key,))
            if not c.fetchone():
                c.execute('INSERT INTO usuarios (license_key) VALUES (?)', (license_key,))
                conn.commit()
                conn.close()
                logger.info(f"New license generated: {license_key}")
                return jsonify({'license_key': license_key}), 201

    except Exception as e:
        logger.error(f"Error in /gerar: {str(e)}")
        return jsonify({'erro': f'Erro ao gerar licença: {str(e)}'}), 500

@app.route('/listar', methods=['GET'])
@verificar_token
def listar_route():
    """Lista licenças com filtro (Bot only)"""
    try:
        filtro = request.args.get('filtro', 'todas').lower()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        query = "SELECT id, license_key, username, hwid, data_registro, ativo, registered FROM usuarios WHERE 1=1"
        
        if filtro == 'ativas':
            query += " AND ativo = 1 AND registered = 1"
        elif filtro == 'naoregistradas':
            query += " AND registered = 0 AND ativo = 1"
        elif filtro == 'banidas':
            query += " AND ativo = 0"
        
        query += " ORDER BY data_registro DESC LIMIT 20"
        c.execute(query)
        rows = c.fetchall()
        conn.close()

        return jsonify({'rows': [
            {
                'id': r[0],
                'license_key': r[1],
                'username': r[2],
                'hwid': r[3],
                'data_registro': r[4],
                'ativo': r[5],
                'registered': r[6]
            }
            for r in rows
        ]}), 200
    except Exception as e:
        logger.error(f"Error in /listar: {str(e)}")
        return jsonify({'erro': f'Erro ao listar: {str(e)}'}), 500

@app.route('/info/<license_key>', methods=['GET'])
@verificar_token
def info(license_key):
    """Retorna informações de uma licença (Bot only)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT * FROM usuarios WHERE license_key = ?', (license_key,))
        usuario = c.fetchone()
        conn.close()
        
        if not usuario:
            return jsonify({'erro': 'Licença não encontrada'}), 404
        
        return jsonify({
            'id': usuario[0],
            'license_key': usuario[1],
            'username': usuario[2],
            'password_hash': usuario[3],
            'hwid': usuario[4],
            'ip_registro': usuario[5],
            'data_registro': usuario[6],
            'ativo': usuario[7],
            'registered': usuario[8]
        }), 200
    except Exception as e:
        logger.error(f"Error in /info: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

@app.route('/banir/<license_key>', methods=['POST'])
@verificar_token
def banir(license_key):
    """Banir uma licença (Bot only)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE usuarios SET ativo = 0 WHERE license_key = ?', (license_key,))
        
        if c.rowcount > 0:
            conn.commit()
            conn.close()
            logger.info(f"License banned: {license_key}")
            return jsonify({'mensagem': f'Licença {license_key} banida'}), 200
        else:
            conn.close()
            return jsonify({'erro': 'Licença não encontrada'}), 404
    except Exception as e:
        logger.error(f"Error in /banir: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

@app.route('/reativar/<license_key>', methods=['POST'])
@verificar_token
def reativar(license_key):
    """Reativar uma licença banida (Bot only)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE usuarios SET ativo = 1 WHERE license_key = ?', (license_key,))
        
        if c.rowcount > 0:
            conn.commit()
            conn.close()
            logger.info(f"License reactivated: {license_key}")
            return jsonify({'mensagem': f'Licença {license_key} reativada'}), 200
        else:
            conn.close()
            return jsonify({'erro': 'Licença não encontrada'}), 404
    except Exception as e:
        logger.error(f"Error in /reativar: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

@app.route('/resetar/<license_key>', methods=['POST'])
@verificar_token
def resetar(license_key):
    """Resetar HWID de uma licença (Bot only)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('UPDATE usuarios SET hwid = NULL, registered = 0 WHERE license_key = ?', (license_key,))
        
        if c.rowcount > 0:
            conn.commit()
            conn.close()
            logger.info(f"License reset: {license_key}")
            return jsonify({'mensagem': f'HWID de {license_key} resetado'}), 200
        else:
            conn.close()
            return jsonify({'erro': 'Licença não encontrada'}), 404
    except Exception as e:
        logger.error(f"Error in /resetar: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

@app.route('/remover/<license_key>', methods=['DELETE'])
@verificar_token
def remover(license_key):
    """Remover uma licença permanentemente (Bot only)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('DELETE FROM usuarios WHERE license_key = ?', (license_key,))
        
        if c.rowcount > 0:
            conn.commit()
            conn.close()
            logger.info(f"License deleted: {license_key}")
            return jsonify({'mensagem': f'Licença {license_key} removida'}), 200
        else:
            conn.close()
            return jsonify({'erro': 'Licença não encontrada'}), 404
    except Exception as e:
        logger.error(f"Error in /remover: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=PORT, debug=(ENV == 'development'))
