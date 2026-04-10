#!/usr/bin/env python3
"""
Script de teste local da API
Execute antes de fazer deploy no Render
"""

import requests
import json
import time

# Altere aqui para testar
BASE_URL = "http://localhost:8080"

def test_status():
    print("🔍 Testando /status...")
    try:
        r = requests.get(f"{BASE_URL}/status", timeout=5)
        print(f"✅ Status: {r.status_code}")
        print(f"   Resposta: {r.json()}\n")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}\n")
        return False

def test_registrar():
    print("🔍 Testando POST /registrar...")
    try:
        # Você precisa ter uma licença gerada pelo bot primeiro!
        payload = {
            "license_key": "NEOREPLAY-aaaaaa-bbbbbb-cccccc-dddddd-eeeeee",
            "username": "testuser",
            "password": "testpass123",
            "hwid": "test-hwid-123456"
        }
        r = requests.post(f"{BASE_URL}/registrar", json=payload, timeout=5)
        print(f"✅ Status: {r.status_code}")
        print(f"   Resposta: {r.json()}\n")
    except Exception as e:
        print(f"❌ Erro: {e}\n")

def test_validar():
    print("🔍 Testando POST /validar...")
    try:
        payload = {
            "license_key": "NEOREPLAY-aaaaaa-bbbbbb-cccccc-dddddd-eeeeee",
            "hwid": "test-hwid-123456"
        }
        r = requests.post(f"{BASE_URL}/validar", json=payload, timeout=5)
        print(f"✅ Status: {r.status_code}")
        print(f"   Resposta: {r.json()}\n")
    except Exception as e:
        print(f"❌ Erro: {e}\n")

def test_login():
    print("🔍 Testando POST /login...")
    try:
        payload = {
            "username": "testuser",
            "password": "testpass123"
        }
        r = requests.post(f"{BASE_URL}/login", json=payload, timeout=5)
        print(f"✅ Status: {r.status_code}")
        print(f"   Resposta: {r.json()}\n")
    except Exception as e:
        print(f"❌ Erro: {e}\n")

if __name__ == "__main__":
    print("=" * 50)
    print("TESTE DA API - Render")
    print("=" * 50)
    print(f"URL Base: {BASE_URL}\n")
    
    if not test_status():
        print("❌ Servidor não está respondendo!")
        print("   Execute: python app.py")
        exit(1)
    
    print("Rodando testes...\n")
    test_registrar()
    test_validar()
    test_login()
    
    print("=" * 50)
    print("✅ Testes concluídos!")
    print("=" * 50)
