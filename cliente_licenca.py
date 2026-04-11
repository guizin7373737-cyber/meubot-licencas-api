import requests
import hashlib
import platform
import json
import os
import base64

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ URL DO SERVIDOR
# Use a variável de ambiente SERVIDOR_URL ou MEUBOT_SERVER_URL para apontar para
# o servidor/API que está rodando. Exemplo:
#  - local: "http://localhost:8080"
#  - remoto: "https://seusubdominio.discloud.app"
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SERVIDOR_URL = os.environ.get("SERVIDOR_URL") or os.environ.get("MEUBOT_SERVER_URL") or "https://meubot-licencas-api-1.onrender.com"

# ✅ TOKEN DE AUTENTICAÇÃO (DEVE CORRESPONDER AO API_SECRET DO SERVIDOR)
API_SECRET = os.environ.get("API_SECRET", "cb9a5aff10e31724e02c51728be35711")

ARQUIVO_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licenca.dat")


def gerar_hwid():
    """Gera um HWID baseado em características do sistema."""
    dados = platform.node() + platform.machine() + platform.processor()
    hwid = hashlib.md5(dados.encode()).hexdigest()
    return hwid


def salvar_licenca_local(license_key, username, password, hwid):
    """Salva as credenciais codificadas em base64."""
    dados = {
        "license_key": license_key,
        "username": username,
        "password": password,
        "hwid": hwid
    }
    with open(ARQUIVO_CONFIG, "w") as f:
        f.write(base64.b64encode(json.dumps(dados).encode()).decode())


def carregar_licenca_local():
    """Carrega credenciais salvas localmente."""
    if not os.path.exists(ARQUIVO_CONFIG):
        return None
    try:
        with open(ARQUIVO_CONFIG, "r") as f:
            dados = json.loads(base64.b64decode(f.read()).decode())
        return dados
    except:
        return None


def ativar_licenca(license_key, username, password):
    """Faz o primeiro registro da licença no servidor."""
    hwid = gerar_hwid()
    try:
        resposta = requests.post(
            f"{SERVIDOR_URL}/registrar",
            json={
                "license_key": license_key,
                "username": username,
                "password": password,
                "hwid": hwid
            },
            headers={
                "Authorization": f"Bearer {API_SECRET}"
            },
            timeout=10
        )
        if resposta.status_code == 201:
            salvar_licenca_local(license_key, username, password, hwid)
            return (True, "Licença ativada com sucesso!")
        else:
            erro = resposta.json().get("erro", "Erro desconhecido")
            return (False, erro)
    except requests.exceptions.ConnectionError:
        return (False, "Não foi possível conectar ao servidor. Verifique sua conexão.")
    except requests.exceptions.Timeout:
        return (False, "Servidor não respondeu a tempo.")
    except Exception as e:
        return (False, f"Erro inesperado: {str(e)}")


def validar_licenca():
    """Verifica se a licença atual é válida no servidor."""
    config = carregar_licenca_local()
    if not config:
        return (False, "Nenhuma licença encontrada. Ative primeiro.")
    
    try:
        resposta = requests.post(
            f"{SERVIDOR_URL}/validar",
            json={
                "license_key": config["license_key"],
                "hwid": config["hwid"]
            },
            timeout=10
        )
        if resposta.status_code == 200:
            return (True, "Licença válida")
        else:
            erro = resposta.json().get("erro", "Licença inválida")
            return (False, erro)
    except requests.exceptions.ConnectionError:
        return (False, "Não foi possível conectar ao servidor.")
    except requests.exceptions.Timeout:
        return (False, "Servidor não respondeu a tempo.")
    except Exception as e:
        return (False, f"Erro inesperado: {str(e)}")


def validar_licenca_login(username, password):
    """Valida login: verifica credenciais locais e valida licença no servidor."""
    config = carregar_licenca_local()
    if not config:
        return (False, "Nenhuma licença ativada neste dispositivo.")
    
    if config["username"] != username or config["password"] != password:
        return (False, "Usuário ou senha incorretos!")
    
    # Validar licença no servidor
    valido, msg = validar_licenca()
    if not valido:
        return (False, msg)
    
    return (True, config["license_key"])
