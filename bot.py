import os
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands
from mcstatus import JavaServer
from python_aternos import Client as AternosClient

# 1. Servidor Flask para mantener vivo el servicio en Render
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

# --- COMANDO 1: ESTADO E IP (Usando mcstatus - Inmune a Cloudflare) ---
@bot.command(name="estado")
async def estado(ctx):
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
        await ctx.send(embed=embed)
        
    except Exception:
        embed = discord.Embed(
            title="🔴 Servidor Apagado / Iniciando",
            description=f"El servidor en `{SERVER_IP}` no está respondiendo en este momento.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# --- COMANDO 2: ENCENDER (Usando Cookie de Aternos) ---
@bot.command(name="encender")
async def encender(ctx):
    if not ATERNOS_SESSION:
        await ctx.send("❌ No se ha configurado la variable `ATERNOS_SESSION` en Render.")
        return

    await ctx.send("⏳ Intentando enviar la orden de encendido a Aternos...")
    
    def start_aternos():
        # Inicializa cliente usando únicamente la cookie de sesión
        aternos = AternosClient.from_cookies(ATERNOS_SESSION)
        servers = aternos.list_servers()
        if servers:
            servidor = servers[0]
            servidor.start()
            return True, servidor.status
        return False, "No se encontraron servidores."

    try:
        # Ejecutar llamada bloqueante de aternos en un hilo secundario
        success, status_msg = await asyncio.to_thread(start_aternos)
        if success:
            await ctx.send(f"🚀 ¡Petición enviada! Estado actual del servidor: **{status_msg}**")
        else:
            await ctx.send(f"⚠️ No se pudo iniciar: {status_msg}")
    except Exception as e:
        await ctx.send(f"❌ Error al conectar con Aternos (posible cookie expirada): `{e}`")

# Iniciar bot
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
