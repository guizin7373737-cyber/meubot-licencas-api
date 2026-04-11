from flask import Flask, request, jsonify
from functools import wraps
import os
from datetime import datetime
import hashlib
import random
import string
import logging
from db_backup import init_backup, get_backup
from db_manager import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

API_SECRET = os.environ.get('API_SECRET', 'seu_token_secreto_aqui')
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
        db = get_db()
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
        
        # Busca a licença
        usuario = db.select('usuarios', where_col='license_key', where_val=license_key, fetch='one')
        
        if not usuario:
            logger.warning(f"❌ Licença não encontrada: {license_key}")
            return jsonify({'erro': 'Licença inválida'}), 400
        
        # Verifica se já foi registrada
        if usuario['registered'] == 1:
            logger.warning(f"⚠️ Licença já registrada: {license_key}")
            return jsonify({'erro': 'Licença já foi ativada'}), 400
        
        # Atualiza o registro
        db.update('usuarios',
            where_col='license_key',
            where_val=license_key,
            username=username,
            password_hash=password_hash,
            hwid=hwid,
            ip_registro=ip_cliente,
            registered=1,
            ativo=1
        )
        
        # Verifica se funcionou
        usuario_atualizado = db.select('usuarios', where_col='license_key', where_val=license_key, fetch='one')
        
        if usuario_atualizado and usuario_atualizado['registered'] == 1:
            logger.info(f"✅ Licença registrada com sucesso: {license_key} | User: {username}")
            # Sincroniza backup
            backup = get_backup()
            if backup:
                backup.sync_backup()
                logger.info("💾 Backup sincronizado")
            return jsonify({
                'mensagem': 'Licença ativada com sucesso!',
                'license_key': license_key,
                'username': username
            }), 201
        else:
            logger.error(f"❌ Falha ao registrar: {license_key}")
            return jsonify({'erro': 'Erro ao registrar licença'}), 500
    
    except Exception as e:
        logger.error(f"❌ Erro em /registrar: {str(e)}")
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

@app.route('/validar', methods=['POST'])
def validar():
    """Valida uma licença já registrada"""
    try:
        db = get_db()
        dados = request.json or {}
        license_key = dados.get('license_key', '').strip()
        hwid = dados.get('hwid', '').strip()
        
        if not license_key or not hwid:
            return jsonify({'erro': 'Licença ou HWID não fornecidos'}), 400
        
        usuario = db.select_custom(
            "SELECT * FROM usuarios WHERE license_key = ? AND hwid = ? AND ativo = 1 AND registered = 1",
            params=(license_key, hwid),
            fetch='one'
        )
        
        if usuario:
            return jsonify({
                'mensagem': 'Licença válida',
                'status': 'ativo'
            }), 200
        else:
            return jsonify({'erro': 'Licença inválida ou não corresponde ao HWID'}), 401
    
    except Exception as e:
        logger.error(f"Erro em /validar: {str(e)}")
        return jsonify({'erro': f'Erro no servidor: {str(e)}'}), 500

@app.route('/login', methods=['POST'])
def login():
    """Faz login com username e password"""
    try:
        db = get_db()
        dados = request.json or {}
        username = dados.get('username', '').strip()
        password = dados.get('password', '').strip()
        
        logger.info(f"🔐 Tentativa de login: {username}")
        
        if not username or not password:
            logger.warning(f"❌ Login vazio: user={username}")
            return jsonify({'erro': 'Username ou password vazios'}), 400
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Busca o usuário
        usuario = db.select_custom(
            "SELECT * FROM usuarios WHERE username = ?",
            params=(username,),
            fetch='one'
        )
        
        if not usuario:
            logger.warning(f"❌ Usuário não encontrado: {username}")
            return jsonify({'erro': 'Credenciais inválidas'}), 401
        
        logger.info(f"✓ Usuário encontrado: {username} | Registered: {usuario['registered']} | Ativo: {usuario['ativo']}")
        
        # Verifica password
        if usuario['password_hash'] != password_hash:
            logger.warning(f"❌ Senha incorreta para: {username}")
            return jsonify({'erro': 'Credenciais inválidas'}), 401
        
        # Verifica se está ativo e registrado
        if usuario['ativo'] == 0 or usuario['registered'] == 0:
            logger.warning(f"❌ Licença inativa/não registrada: {username} | Ativo: {usuario['ativo']} | Registrada: {usuario['registered']}")
            return jsonify({'erro': 'Licença banida ou não registrada'}), 401
        
        logger.info(f"✅ Login bem-sucedido: {username}")
        return jsonify({
            'mensagem': 'Login bem-sucedido',
            'license_key': usuario['license_key'],
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
        db = get_db()
        
        while True:
            license_key = gerar_licenca()
            usuario = db.select('usuarios', where_col='license_key', where_val=license_key, fetch='one')
            
            if not usuario:
                db.insert('usuarios', license_key=license_key)
                
                # Sincroniza backup
                backup = get_backup()
                if backup:
                    backup.sync_backup()
                
                logger.info(f"✅ Nova licença gerada: {license_key}")
                return jsonify({'license_key': license_key}), 201

    except Exception as e:
        logger.error(f"❌ Erro em /gerar: {str(e)}")
        return jsonify({'erro': f'Erro ao gerar licença: {str(e)}'}), 500

@app.route('/listar', methods=['GET'])
@verificar_token
def listar_route():
    """Lista licenças com filtro (Bot only)"""
    try:
        db = get_db()
        
        # Verifica integridade do BD antes de listar
        backup = get_backup()
        if backup:
            backup.verify_db_integrity()
        
        filtro = request.args.get('filtro', 'todas').lower()
        
        query = "SELECT id, license_key, username, hwid, data_registro, ativo, registered FROM usuarios WHERE 1=1"
        
        if filtro == 'ativas':
            query += " AND ativo = 1 AND registered = 1"
        elif filtro == 'naoregistradas':
            query += " AND registered = 0 AND ativo = 1"
        elif filtro == 'banidas':
            query += " AND ativo = 0"
        
        query += " ORDER BY data_registro DESC LIMIT 20"
        rows = db.select_custom(query, fetch='all')

        return jsonify({'rows': [
            {
                'id': r['id'],
                'license_key': r['license_key'],
                'username': r['username'],
                'hwid': r['hwid'],
                'data_registro': r['data_registro'],
                'ativo': r['ativo'],
                'registered': r['registered']
            }
            for r in rows
        ]}), 200
    except Exception as e:
        logger.error(f"❌ Erro em /listar: {str(e)}")
        return jsonify({'erro': f'Erro ao listar: {str(e)}'}), 500

@app.route('/info/<license_key>', methods=['GET'])
@verificar_token
def info(license_key):
    """Retorna informações de uma licença (Bot only)"""
    try:
        db = get_db()
        usuario = db.select('usuarios', where_col='license_key', where_val=license_key, fetch='one')
        
        if not usuario:
            return jsonify({'erro': 'Licença não encontrada'}), 404
        
        return jsonify({
            'id': usuario['id'],
            'license_key': usuario['license_key'],
            'username': usuario['username'],
            'password_hash': usuario['password_hash'],
            'hwid': usuario['hwid'],
            'ip_registro': usuario['ip_registro'],
            'data_registro': usuario['data_registro'],
            'ativo': usuario['ativo'],
            'registered': usuario['registered']
        }), 200
    except Exception as e:
        logger.error(f"❌ Erro em /info: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

@app.route('/banir/<license_key>', methods=['POST'])
@verificar_token
def banir(license_key):
    """Banir uma licença (Bot only)"""
    try:
        db = get_db()
        db.update('usuarios', where_col='license_key', where_val=license_key, ativo=0)
        logger.info(f"🚫 Licença banida: {license_key}")
        return jsonify({'mensagem': f'Licença {license_key} banida'}), 200
    except Exception as e:
        logger.error(f"❌ Erro em /banir: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

@app.route('/reativar/<license_key>', methods=['POST'])
@verificar_token
def reativar(license_key):
    """Reativar uma licença banida (Bot only)"""
    try:
        db = get_db()
        db.update('usuarios', where_col='license_key', where_val=license_key, ativo=1)
        logger.info(f"✅ Licença reativada: {license_key}")
        return jsonify({'mensagem': f'Licença {license_key} reativada'}), 200
    except Exception as e:
        logger.error(f"❌ Erro em /reativar: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

@app.route('/resetar/<license_key>', methods=['POST'])
@verificar_token
def resetar(license_key):
    """Resetar HWID de uma licença (Bot only)"""
    try:
        db = get_db()
        db.update('usuarios', where_col='license_key', where_val=license_key, hwid=None, registered=0)
        logger.info(f"🔄 Licença resetada: {license_key}")
        return jsonify({'mensagem': f'HWID de {license_key} resetado'}), 200
    except Exception as e:
        logger.error(f"❌ Erro em /resetar: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

@app.route('/remover/<license_key>', methods=['DELETE'])
@verificar_token
def remover(license_key):
    """Remover uma licença permanentemente (Bot only)"""
    try:
        db = get_db()
        # Aqui vamos marcar como deletado em vez de remover (para auditoria)
        db.update('usuarios', where_col='license_key', where_val=license_key, ativo=0)
        logger.info(f"🗑️ Licença removida: {license_key}")
        return jsonify({'mensagem': f'Licença {license_key} removida'}), 200
    except Exception as e:
        logger.error(f"❌ Erro em /remover: {str(e)}")
        return jsonify({'erro': f'Erro: {str(e)}'}), 500

if __name__ == '__main__':
    logger.info("🚀 Iniciando NEOREPLAY Licencas API...")
    logger.info("🔄 Inicializando Database Manager (PostgreSQL + SQLite fallback)...")
    db = get_db()
    logger.info("✅ Database Manager ativo!")
    
    logger.info("🔄 Inicializando sistema de backup...")
    init_backup(None)  # db_manager não precisa de DB_FILE
    logger.info("✅ Sistema de backup ativo!")
    
    logger.info(f"🌍 Servidor rodando em porta {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=(ENV == 'development'))
