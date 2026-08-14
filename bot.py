import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from discord import app_commands
from mcstatus import JavaServer

# 1. Servidor Flask para el Health Check de Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Minecraft activo y funcionando."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Configuración del Bot de Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variables de Entorno
SERVER_IP = os.getenv("SERVER_IP", "tu_servidor.aternos.me")

# --- EVENTO DE INICIO Y SINCRONIZACIÓN ---
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Se sincronizaron {len(synced)} comandos Slash.")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

# --- COMANDO 1: /estado ---
@bot.tree.command(name="estado", description="Consulta si el servidor está encendido y la versión")
async def estado(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        server = await JavaServer.async_lookup(SERVER_IP)
        status = await server.async_status()
        
        embed = discord.Embed(
            title="🟢 Servidor Encendido",
            description=f"El servidor está en línea y listo para jugar.",
            color=discord.Color.green()
        )
        embed.add_field(name="IP", value=f"`{SERVER_IP}`", inline=False)
        embed.add_field(name="Jugadores", value=f"{status.players.online}/{status.players.max}", inline=True)
        embed.add_field(name="Versión", value=f"{status.version.name}", inline=True)
        await interaction.followup.send(embed=embed)
    except Exception:
        embed = discord.Embed(
            title="🔴 Servidor Apagado",
            description="El servidor actualmente está fuera de línea o iniciándose.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

# --- COMANDO 2: /jugadores ---
@bot.tree.command(name="jugadores", description="Muestra la lista de jugadores conectados")
async def jugadores(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        server = await JavaServer.async_lookup(SERVER_IP)
        status = await server.async_status()
        
        if status.players.online == 0:
            embed = discord.Embed(
                title="👥 Jugadores Conectados (0)",
                description="No hay nadie conectado en este momento.",
                color=discord.Color.orange()
            )
        else:
            # Extraer nombres si están disponibles
            lista_jugadores = [p.name for p in status.players.sample] if status.players.sample else []
            nombres = "\n".join([f"• {nombre}" for nombre in lista_jugadores]) if lista_jugadores else "No se pueden listar los nombres (servidor en modo privado/protegido)."
            
            embed = discord.Embed(
                title=f"👥 Jugadores Conectados ({status.players.online}/{status.players.max})",
                description=nombres,
                color=discord.Color.blue()
            )
        await interaction.followup.send(embed=embed)
    except Exception:
        await interaction.followup.send("❌ No se puede consultar la lista porque el servidor está apagado.")

# --- COMANDO 3: /ip ---
@bot.tree.command(name="ip", description="Muestra la dirección IP e instrucciones de conexión")
async def ip(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌐 Información de Conexión",
        color=discord.Color.gold()
    )
    embed.add_field(name="Dirección IP (Java):", value=f"`{SERVER_IP}`", inline=False)
    embed.add_field(name="Puerto (Si usas Bedrock/Geyser):", value="`19132` (Puerto por defecto)", inline=False)
    embed.set_footer(text="¡Copia la IP y agrégala a tus directos en Minecraft!")
    await interaction.response.send_message(embed=embed)

# --- COMANDO 4: /reglas ---
@bot.tree.command(name="reglas", description="Reglas fundamentales de convivencia del servidor")
async def reglas(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Reglas del Servidor",
        description="Por favor, sigue estas normas para mantener una comunidad sana y divertida:",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="1. Respeto Mutuo", value="Prohibido el acoso, insultos o discriminación en el chat global.", inline=False)
    embed.add_field(name="2. No Griefing", value="No destruyas, modifiques o robes construcciones de otros jugadores sin su consentimiento.", inline=False)
    embed.add_field(name="3. Juego Limpio", value="Queda estrictamente prohibido el uso de hacks, clientes modificados (X-Ray, Fly, KillAura) o exploits.", inline=False)
    embed.add_field(name="4. Lag y Redstone", value="Evita construir granjas masivas o relojes de redstone infinitos que afecten el rendimiento del servidor.", inline=False)
    embed.add_field(name="5. PvP Consensual", value="No pvp / matar a otros jugadores a menos que ambas partes estén de acuerdo.", inline=False)
    
    embed.set_footer(text="El incumplimiento de las reglas puede resultar en un mute o ban permanente.")
    await interaction.response.send_message(embed=embed)

# Iniciar bot
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
