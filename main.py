import discord
from discord.ext import commands, tasks
import requests
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import sqlite3
import asyncio
from pathlib import Path

# Carregar .env de múltiplos locais possíveis
env_paths = [
    Path(__file__).parent.parent / '.env',  # Raiz do projeto
    Path(__file__).parent / '.env',          # Pasta Meubot/
    Path.cwd() / '.env'                      # Diretório atual
]

for env_file in env_paths:
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Arquivo .env carregado de: {env_file}")
        break
else:
    print("⚠️ Nenhum arquivo .env encontrado, usando variáveis de ambiente")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Banco de dados centralizado na raiz
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'licencas.db')

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DONO_ID = int(os.getenv('DONO_ID', '0'))
SERVIDOR_URL = os.getenv('SERVIDOR_URL', 'http://localhost:8080').rstrip('/')
API_SECRET = os.getenv('API_SECRET', 'cb9a5aff10e31724e02c51728be35711')

if not DISCORD_TOKEN:
    logger.error("❌ DISCORD_TOKEN não definido!")
    exit(1)
if DONO_ID == 0:
    logger.error("❌ DONO_ID não definido!")
    exit(1)

logger.info(f"🤖 Bot iniciando...")
logger.info(f"📡 Servidor: {SERVIDOR_URL}")
logger.info(f"👤 Dono ID: {DONO_ID}")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.dm_messages = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=commands.DefaultHelpCommand(),
    description="🎫 Bot de Gerenciamento de Licenças NEOREPLAY"
)

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
    logger.info("✅ Banco de dados inicializado")

def fazer_requisicao(metodo, endpoint, dados=None, params=None, tentativa=0):
    """Faz requisição com retry automático e timeout aumentado"""
    url = f"{SERVIDOR_URL}{endpoint}"
    headers = {
        'Authorization': f'Bearer {API_SECRET}',
        'Content-Type': 'application/json'
    }
    
    max_tentativas = 3
    timeout = 30  # Aumentado para 30 segundos
    
    try:
        if metodo == 'GET':
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        elif metodo == 'POST':
            resp = requests.post(url, json=dados, headers=headers, timeout=timeout)
        elif metodo == 'DELETE':
            resp = requests.delete(url, headers=headers, timeout=timeout)
        else:
            return (False, None, f"Método desconhecido: {metodo}")
        
        if resp.status_code in [200, 201]:
            try:
                return (True, resp.json(), None)
            except Exception as json_err:
                logger.error(f"❌ Erro ao parsear JSON: {json_err}")
                logger.error(f"Resposta recebida: {repr(resp.text)}")
                return (False, None, f"❌ Resposta inválida do servidor")
        else:
            erro = resp.json().get('erro', 'Erro desconhecido') if resp.text else 'Erro desconhecido'
            return (False, None, erro)
    except requests.exceptions.Timeout:
        if tentativa < max_tentativas - 1:
            logger.warning(f"⏱️ Timeout na tentativa {tentativa + 1}/{max_tentativas}, retentando...")
            return fazer_requisicao(metodo, endpoint, dados, params, tentativa + 1)
        else:
            logger.error(f"❌ Servidor não respondeu após {max_tentativas} tentativas")
            return (False, None, "⏱️ Servidor não respondendo (timeout)")
    except requests.exceptions.ConnectionError:
        if tentativa < max_tentativas - 1:
            logger.warning(f"❌ Erro de conexão, tentativa {tentativa + 1}/{max_tentativas}...")
            return fazer_requisicao(metodo, endpoint, dados, params, tentativa + 1)
        else:
            return (False, None, "❌ Conexão recusada pelo servidor")
    except Exception as e:
        logger.error(f"Erro na requisição: {str(e)}")
        return (False, None, f"❌ Erro: {str(e)}")

def eh_dono(ctx):
    return ctx.author.id == DONO_ID

@bot.event
async def on_ready():
    init_db()
    logger.info(f"✅ Bot conectado como {bot.user}")
    logger.info(f"👥 Guilds: {len(bot.guilds)}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="!ajuda para usar"
        )
    )
    
    # Inicia o heartbeat para manter o servidor acordado
    if not keep_alive.is_running():
        keep_alive.start()
        logger.info("💓 Heartbeat iniciado")

@tasks.loop(minutes=5)
async def keep_alive():
    """Task que faz ping no servidor a cada 5 minutos para manter acordado"""
    try:
        logger.info("💓 Sending heartbeat to server...")
        sucesso, _, _ = fazer_requisicao('GET', '/status')
        if sucesso:
            logger.info("✅ Servidor respondendo normalmente")
        else:
            logger.warning("⚠️ Servidor lento, próxima tentativa em 5 minutos")
    except Exception as e:
        logger.error(f"❌ Erro no heartbeat: {e}")

@bot.event
async def on_command_error(ctx, erro):
    if isinstance(erro, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para usar esse comando.")
    elif isinstance(erro, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argumento faltando: {erro.param}")
    else:
        logger.error(f"Erro em comando: {erro}")
        await ctx.send(f"❌ Erro ao executar comando: {str(erro)}")

@bot.command(name="gerar", help="Gera uma nova licença", brief="Gera nova licença")
async def gerar(ctx):
    if not eh_dono(ctx):
        await ctx.send("❌ Apenas o dono pode usar este comando.")
        return
    
    async with ctx.typing():
        sucesso, dados, erro = fazer_requisicao('POST', '/gerar')
    
    if sucesso:
        license_key = dados['license_key']
        embed = discord.Embed(
            title="✅ Nova Licença Gerada",
            description=f"```\n{license_key}\n```",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Status", value="🟡 Não registrada", inline=False)
        await ctx.send(embed=embed)
        logger.info(f"License generated: {license_key}")
    else:
        await ctx.send(f"❌ Erro ao gerar licença: {erro}")

@bot.command(name="listar", help="Lista licenças com filtro", brief="Lista licenças")
async def listar(ctx, filtro: str = "ativas"):
    if not eh_dono(ctx):
        await ctx.send("❌ Apenas o dono pode usar este comando.")
        return
    
    async with ctx.typing():
        sucesso, dados, erro = fazer_requisicao('GET', '/listar', params={'filtro': filtro})
    
    if sucesso:
        rows = dados.get('rows', [])
        if not rows:
            await ctx.send(f"📋 Nenhuma licença com filtro '{filtro}'")
            return
        
        msg = f"📋 **Licenças ({filtro})**\n```"
        for row in rows[:10]:
            status_icon = "🔵" if row['registered'] else ("🔴" if row['ativo'] == 0 else "🟡")
            license_key = row['license_key'][:20] + "..." if len(row['license_key']) > 20 else row['license_key']
            username = row['username'] or 'N/A'
            msg += f"{status_icon} {license_key} | {username}\n"
        msg += "```"
        await ctx.send(msg)
    else:
        await ctx.send(f"❌ Erro ao listar: {erro}")

@bot.command(name="info", help="Mostra informações detalhadas de uma licença", brief="Info de licença")
async def info(ctx, license_key: str):
    if not eh_dono(ctx):
        await ctx.send("❌ Apenas o dono pode usar este comando.")
        return
    
    async with ctx.typing():
        sucesso, dados, erro = fazer_requisicao('GET', f'/info/{license_key}')
    
    if sucesso:
        embed = discord.Embed(
            title="📋 Informações da Licença",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="License Key", value=f"```\n{dados['license_key']}\n```", inline=False)
        embed.add_field(name="Username", value=dados['username'] or 'Não registrado', inline=True)
        embed.add_field(name="HWID", value=dados['hwid'][:16] + "..." if dados['hwid'] else 'N/A', inline=True)
        embed.add_field(name="Status", value="🟢 Ativo" if dados['ativo'] else "🔴 Banido", inline=True)
        embed.add_field(name="Registrada", value="✅ Sim" if dados['registered'] else "❌ Não", inline=True)
        embed.add_field(name="Data de Criação", value=dados['data_registro'], inline=False)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {erro}")

@bot.command(name="banir", help="Banir uma licença", brief="Banir licença")
async def banir(ctx, license_key: str):
    if not eh_dono(ctx):
        await ctx.send("❌ Apenas o dono pode usar este comando.")
        return
    
    async with ctx.typing():
        sucesso, dados, erro = fazer_requisicao('POST', f'/banir/{license_key}')
    
    if sucesso:
        await ctx.send(f"🚫 Licença `{license_key}` foi banida.")
        logger.info(f"License banned: {license_key}")
    else:
        await ctx.send(f"❌ {erro}")

@bot.command(name="reativar", help="Reativar uma licença banida", brief="Reativar licença")
async def reativar(ctx, license_key: str):
    if not eh_dono(ctx):
        await ctx.send("❌ Apenas o dono pode usar este comando.")
        return
    
    async with ctx.typing():
        sucesso, dados, erro = fazer_requisicao('POST', f'/reativar/{license_key}')
    
    if sucesso:
        await ctx.send(f"✅ Licença `{license_key}` foi reativada.")
        logger.info(f"License reactivated: {license_key}")
    else:
        await ctx.send(f"❌ {erro}")

@bot.command(name="resetar", help="Resetar HWID e marcar como não registrada", brief="Resetar licença")
async def resetar(ctx, license_key: str):
    if not eh_dono(ctx):
        await ctx.send("❌ Apenas o dono pode usar este comando.")
        return
    
    async with ctx.typing():
        sucesso, dados, erro = fazer_requisicao('POST', f'/resetar/{license_key}')
    
    if sucesso:
        await ctx.send(f"🔄 HWID de `{license_key}` foi resetado.")
        logger.info(f"License reset: {license_key}")
    else:
        await ctx.send(f"❌ {erro}")

@bot.command(name="remover", help="Remover uma licença permanentemente", brief="Remover licença")
async def remover(ctx, license_key: str):
    if not eh_dono(ctx):
        await ctx.send("❌ Apenas o dono pode usar este comando.")
        return
    
    confirm_msg = await ctx.send(f"⚠️ Tem certeza que quer remover `{license_key}` permanentemente? (sim/não)")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['sim', 'não']
    
    try:
        resposta = await bot.wait_for('message', check=check, timeout=30.0)
        if resposta.content.lower() == 'não':
            await ctx.send("❌ Operação cancelada.")
            return
    except:
        await ctx.send("⏱️ Tempo esgotado.")
        return
    
    async with ctx.typing():
        sucesso, dados, erro = fazer_requisicao('DELETE', f'/remover/{license_key}')
    
    if sucesso:
        await ctx.send(f"🗑️ Licença `{license_key}` foi removida permanentemente.")
        logger.info(f"License deleted: {license_key}")
    else:
        await ctx.send(f"❌ {erro}")

@bot.command(name="ajuda", help="Mostra os comandos disponíveis", brief="Mostra ajuda")
async def ajuda(ctx):
    if not eh_dono(ctx):
        await ctx.send("❌ Apenas o dono pode usar este comando.")
        return
    
    embed = discord.Embed(
        title="🎫 Comandos do Bot de Licenças",
        description="Aqui estão todos os comandos disponíveis",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    
    comandos = [
        ("!gerar", "Gera uma nova licença NEOREPLAY", "🎫"),
        ("!listar [filtro]", "Lista licenças (ativas/naoregistradas/banidas/todas)", "📋"),
        ("!info <key>", "Mostra detalhes de uma licença", "ℹ️"),
        ("!banir <key>", "Banir uma licença", "🚫"),
        ("!reativar <key>", "Reativar uma licença banida", "✅"),
        ("!resetar <key>", "Resetar HWID e registração", "🔄"),
        ("!remover <key>", "Remover uma licença (IRREVERSÍVEL)", "🗑️"),
        ("!ajuda", "Mostra esta mensagem", "📖"),
        ("!status", "Status do servidor", "📡"),
    ]
    
    for cmd, desc, icon in comandos:
        embed.add_field(name=f"{icon} {cmd}", value=desc, inline=False)
    
    embed.set_footer(text=f"Bot v2.0 | Servidor: {SERVIDOR_URL}")
    await ctx.send(embed=embed)

@bot.command(name="status", help="Mostra o status do servidor", brief="Status do servidor")
async def status(ctx):
    try:
        resp = requests.get(f"{SERVIDOR_URL}/status", timeout=5)
        if resp.status_code == 200:
            await ctx.send("✅ Servidor online e funcionando")
        else:
            await ctx.send("❌ Servidor respondeu com erro")
    except:
        await ctx.send("❌ Servidor offline ou não respondendo")

if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot Discord...")
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"❌ Erro ao rodar bot: {e}")
        exit(1)
