import os
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands
from discord import app_commands
from mcstatus import JavaServer
from python_aternos import Client as AternosClient

# 1. Servidor Flask para mantener vivo el servicio en Render (Health Check)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot en línea y funcionando!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# 2. Configuración del Bot de Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Datos del servidor Minecraft
SERVER_IP = os.getenv("SERVER_IP", "tu_servidor.aternos.me")
ATERNOS_SESSION = os.getenv("ATERNOS_SESSION")

# --- EVENTO DE INICIO Y SINCRONIZACIÓN DE COMANDOS SLASH ---
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado exitosamente como: {bot.user}")
    try:
        # Sincroniza los comandos Slash con Discord
        synced = await bot.tree.sync()
        print(f"✅ Se han sincronizado {len(synced)} comando(s) Slash correctamente.")
    except Exception as e:
        print(f"❌ Error al sincronizar comandos: {e}")

# --- COMANDO SLASH 1: /estado ---
@bot.tree.command(name="estado", description="Muestra el estado actual e IP del servidor de Minecraft")
async def estado(interaction: discord.Interaction):
    # Indicar a Discord que procesaremos la solicitud (evita timeout de 3 seg)
    await interaction.response.defer()
    
    try:
        server = await JavaServer.async_lookup(SERVER_IP)
        status = await server.async_status()
        
        embed = discord.Embed(
            title="🟢 Servidor Encendido",
            description=f"**IP:** `{SERVER_IP}`",
            color=discord.Color.green()
        )
        embed.add_field(name="Jugadores", value=f"{status.players.online}/{status.players.max}")
        embed.add_field(name="Versión", value=f"{status.version.name}")
        await interaction.followup.send(embed=embed)
        
    except Exception:
        embed = discord.Embed(
            title="🔴 Servidor Apagado / Iniciando",
            description=f"El servidor en `{SERVER_IP}` no está respondiendo en este momento.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

# --- COMANDO SLASH 2: /encender ---
@bot.tree.command(name="encender", description="Envia la orden para encender el servidor de Aternos")
async def encender(interaction: discord.Interaction):
    if not ATERNOS_SESSION:
        await interaction.response.send_message("❌ No se ha configurado la variable `ATERNOS_SESSION` en Render.", ephemeral=True)
        return

    await interaction.response.send_message("⏳ Intentando enviar la orden de encendido a Aternos...")
    
    def start_aternos():
        # ¡Atención aquí! Estas líneas deben llevar 8 espacios de sangría
        aternos = AternosClient()
        aternos.at_session.cookies.set("ATERNOS_SESSION", ATERNOS_SESSION)
        
        servers = aternos.list_servers()
        if servers:
            servidor = servers[0]
            servidor.start()
            return True, servidor.status
        return False, "No se encontraron servidores asociados a la cuenta."

    try:
        # Ejecutar llamada de aternos en un hilo secundario
        success, status_msg = await asyncio.to_thread(start_aternos)
        if success:
            await interaction.followup.send(f"🚀 ¡Petición enviada! Estado actual del servidor: **{status_msg}**")
        else:
            await interaction.followup.send(f"⚠️ No se pudo iniciar: {status_msg}")
    except Exception as e:
        await interaction.followup.send(f"❌ Error al conectar con Aternos (posible cookie expirada): `{e}`")

# Iniciar bot
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
