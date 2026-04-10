import requests
import os
from dotenv import load_dotenv

load_dotenv()

SERVIDOR_URL = os.getenv('SERVIDOR_URL', 'https://meubot-licencas-api-1.onrender.com').rstrip('/')
API_SECRET = os.getenv('API_SECRET', 'seu_token_secreto_aqui')

print(f"🔍 Testando API em: {SERVIDOR_URL}")
print(f"📝 API Secret: {API_SECRET}")
print("-" * 50)

# Teste 1: Status do servidor
print("\n✅ Teste 1: Verificando status do servidor...")
try:
    resp = requests.get(f"{SERVIDOR_URL}/status", timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Resposta: {resp.text}")
    if resp.status_code == 200:
        print("✅ Servidor online!\n")
    else:
        print("❌ Servidor respondeu com erro\n")
except Exception as e:
    print(f"❌ Erro: {e}\n")

# Teste 2: Gerar licença
print("✅ Teste 2: Tentando gerar licença...")
headers = {
    'Authorization': f'Bearer {API_SECRET}',
    'Content-Type': 'application/json'
}

try:
    resp = requests.post(f"{SERVIDOR_URL}/gerar", headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Headers Response: {dict(resp.headers)}")
    print(f"Conteúdo bruto: {repr(resp.text)}")
    print(f"Tamanho: {len(resp.text)} bytes")
    
    if resp.status_code in [200, 201]:
        try:
            dados = resp.json()
            print(f"✅ JSON parse OK: {dados}")
        except Exception as e:
            print(f"❌ Erro ao parsear JSON: {e}")
    else:
        print(f"❌ Erro HTTP {resp.status_code}")
except Exception as e:
    print(f"❌ Erro na requisição: {e}")

print("\n" + "-" * 50)
print("✅ Testes concluídos!")
