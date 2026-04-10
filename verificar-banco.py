#!/usr/bin/env python3
"""
Script para debugar o banco de dados de licenças
"""

import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'licencas.db')

os.chdir(os.path.dirname(__file__))
DB_FILE = 'licencas.db'

print("\n" + "="*60)
print("  🔍 VERIFICAÇÃO DO BANCO DE DADOS")
print("="*60)

if not os.path.exists(DB_FILE):
    print(f"\n❌ Banco de dados não encontrado: {DB_FILE}\n")
    exit(1)

print(f"\n📁 Banco: {DB_FILE}")
print(f"📊 Tamanho: {os.path.getsize(DB_FILE) / 1024:.2f} KB")
print(f"📅 Modificado: {datetime.fromtimestamp(os.path.getmtime(DB_FILE))}")

try:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Conta licenças
    c.execute('SELECT COUNT(*) FROM usuarios')
    total = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM usuarios WHERE registered = 1')
    registradas = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM usuarios WHERE ativo = 1')
    ativas = c.fetchone()[0]
    
    print(f"\n📋 ESTATÍSTICAS:")
    print(f"  • Total de licenças: {total}")
    print(f"  • Registradas: {registradas}")
    print(f"  • Ativas: {ativas}")
    
    print(f"\n📝 DETALHES DAS LICENÇAS:\n")
    print(f"{'License Key':<35} | {'Username':<20} | {'Reg'} | {'Ativo'} | {'Data'}")
    print("-" * 95)
    
    c.execute('SELECT license_key, username, registered, ativo, data_registro FROM usuarios ORDER BY data_registro DESC')
    
    linhas = c.fetchall()
    for row in linhas:
        license_key = row[0][:30] + "..." if len(row[0]) > 30 else row[0]
        username = row[1] if row[1] else "N/A"
        username = username[:18] if len(username) > 18 else username
        registrada = "✅" if row[2] == 1 else "❌"
        ativa = "✅" if row[3] == 1 else "❌"
        data = row[4].split()[0] if row[4] else "N/A"
        
        print(f"{license_key:<35} | {username:<20} | {registrada}   | {ativa}    | {data}")
    
    # Testa login
    print(f"\n🔐 TESTE DE LOGIN:\n")
    
    c.execute('SELECT username, password_hash, registered, ativo FROM usuarios WHERE registered = 1 LIMIT 1')
    teste = c.fetchone()
    
    if teste:
        username_teste = teste[0]
        print(f"Usuário: {username_teste}")
        print(f"Hash da senha armazenado: {teste[1][:20]}...")
        print(f"Registrado: {'✅ SIM' if teste[2] == 1 else '❌ NÃO'}")
        print(f"Ativo: {'✅ SIM' if teste[3] == 1 else '❌ NÃO'}")
    else:
        print("Nenhum usuário registrado para testar")
    
    conn.close()
    
    print("\n" + "="*60)
    print("✅ VERIFICAÇÃO CONCLUÍDA")
    print("="*60 + "\n")
    
except Exception as e:
    print(f"\n❌ ERRO: {e}\n")
    exit(1)
