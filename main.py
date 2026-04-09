import discord
from discord.ext import commands
import sqlite3
import random
import string
import os

# ⚠️ COLOQUE SEU TOKEN AQUI (variável de ambiente)
TOKEN = os.environ.get("DISCORD_TOKEN", "seu_token_aqui")

# ⚠️ COLOQUE SEU ID DO DISCORD AQUI (número de 18 dígitos)
DONO_ID = int(os.environ.get("DISCORD_OWNER_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
DB_FILE = "licencas.db"

def init_db():
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

def gerar_licenca():
    prefixo = "NEOREPLAY"
    caracteres = string.ascii_letters + string.digits
    blocos = [''.join(random.choices(caracteres, k=6)) for _ in range(6)]
    return prefixo + "-" + "-".join(blocos)

@bot.command(name="gerar")
async def gerar(ctx):
    if ctx.author.id != DONO_ID:
        await ctx.send("❌ Sem permissão.")
        return
    while True:
        licenca = gerar_licenca()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id FROM usuarios WHERE license_key = ?", (licenca,))
        if not c.fetchone():
            c.execute("INSERT INTO usuarios (license_key) VALUES (?)", (licenca,))
            conn.commit()
            conn.close()
            await ctx.send(f"✅ **Nova licença:**\n```{licenca}```")
            break
        conn.close()

@bot.command(name="listar")
async def listar(ctx, filtro: str = "todas"):
    if ctx.author.id != DONO_ID:
        await ctx.send("❌ Sem permissão.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = "SELECT license_key, username, hwid, data_registro, ativo, registered FROM usuarios WHERE 1=1"
    if filtro.lower() == "ativas":
        query += " AND ativo = 1"
    elif filtro.lower() == "naoregistradas":
        query += " AND registered = 0 AND ativo = 1"
    elif filtro.lower() == "banidas":
        query += " AND ativo = 0"
    query += " ORDER BY data_registro DESC LIMIT 10"
    c.execute(query)
    rows = c.fetchall()
    conn.close()
    if not rows:
        await ctx.send("Nenhuma licença encontrada.")
        return
    msg = "**📋 Licenças:**\n```"
    for r in rows:
        status = "🔵" if r[5] else ("🔴" if r[4]==0 else "🟡")
        msg += f"{status} {r[0]} | {r[1] or 'N/A'} | {r[2] or 'N/A'}\n"
    msg += "```"
    await ctx.send(msg)

@bot.command(name="resetar")
async def resetar(ctx, licenca: str):
    if ctx.author.id != DONO_ID:
        await ctx.send("❌ Sem permissão.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET hwid = NULL, registered = 0 WHERE license_key = ?", (licenca,))
    if c.rowcount > 0:
        conn.commit()
        await ctx.send(f"✅ HWID de `{licenca}` resetado.")
    else:
        await ctx.send(f"❌ Licença não encontrada.")
    conn.close()

@bot.command(name="banir")
async def banir(ctx, licenca: str):
    if ctx.author.id != DONO_ID:
        await ctx.send("❌ Sem permissão.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET ativo = 0 WHERE license_key = ?", (licenca,))
    if c.rowcount > 0:
        conn.commit()
        await ctx.send(f"🚫 Licença `{licenca}` banida.")
    else:
        await ctx.send(f"❌ Licença não encontrada.")
    conn.close()

@bot.command(name="reativar")
async def reativar(ctx, licenca: str):
    if ctx.author.id != DONO_ID:
        await ctx.send("❌ Sem permissão.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE usuarios SET ativo = 1 WHERE license_key = ?", (licenca,))
    if c.rowcount > 0:
        conn.commit()
        await ctx.send(f"✅ Licença `{licenca}` reativada.")
    else:
        await ctx.send(f"❌ Licença não encontrada.")
    conn.close()

@bot.command(name="remover")
async def remover(ctx, licenca: str):
    if ctx.author.id != DONO_ID:
        await ctx.send("❌ Sem permissão.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM usuarios WHERE license_key = ?", (licenca,))
    if c.rowcount > 0:
        conn.commit()
        await ctx.send(f"🗑️ Licença `{licenca}` removida.")
    else:
        await ctx.send(f"❌ Licença não encontrada.")
    conn.close()

@bot.command(name="info")
async def info(ctx, licenca: str):
    if ctx.author.id != DONO_ID:
        await ctx.send("❌ Sem permissão.")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT license_key, username, hwid, ip_registro, data_registro, ativo, registered FROM usuarios WHERE license_key = ?", (licenca,))
    row = c.fetchone()
    conn.close()
    if not row:
        await ctx.send("Licença não encontrada.")
        return
    status = "🔵 Registrada" if row[6] else ("🔴 Banida" if not row[5] else "🟡 Disponível")
    embed = discord.Embed(title="Info da Licença", color=0x00ff00)
    embed.add_field(name="Chave", value=f"`{row[0]}`", inline=False)
    embed.add_field(name="Usuário", value=row[1] or "N/A", inline=True)
    embed.add_field(name="HWID", value=row[2] or "N/A", inline=True)
    embed.add_field(name="IP", value=row[3] or "N/A", inline=True)
    embed.add_field(name="Data", value=row[4] or "N/A", inline=True)
    embed.add_field(name="Status", value=status, inline=True)
    await ctx.send(embed=embed)

@bot.command(name="ajuda")
async def ajuda_cmd(ctx):
    if ctx.author.id != DONO_ID:
        await ctx.send("❌ Sem permissão.")
        return
    comandos = """
**📋 Comandos:**
`!gerar` – Nova licença NEOREPLAY
`!listar [ativas/naoregistradas/banidas]` – Lista licenças
`!info <licença>` – Detalhes da licença
`!resetar <licença>` – Reseta HWID
`!banir <licença>` – Desativa licença
`!reativar <licença>` – Reativa licença
`!remover <licença>` – Remove do banco
`!ajuda` – Esta mensagem
"""
    await ctx.send(comandos)

@bot.event
async def on_ready():
    init_db()
    print(f"Bot {bot.user} está online!")

bot.run(TOKEN)