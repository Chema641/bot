import os
import threading
import discord
from discord import app_commands
from discord.ext import commands, tasks
from mcstatus import JavaServer
from python_aternos import Client as AternosClient
from flask import Flask

# =========================================================
# CONFIGURACIÓN DEL BOT Y SERVIDORES
# =========================================================
# Token de tu bot de Discord
TOKEN = os.getenv("DISCORD_TOKEN", "TU_TOKEN_DE_DISCORD_AQUI")

# Credenciales de tu cuenta de Aternos
ATERNOS_USER = os.getenv("ATERNOS_USER", "TU_USUARIO_ATERNOS")
ATERNOS_PASS = os.getenv("ATERNOS_PASS", "TU_CONTRASEÑA_ATERNOS")

# IP/Dominio del servidor (Ejemplo: "miservidor.aternos.me")
SERVER_IP_TEXT = "background-ears.gl.joinmc.link"  # Cambia por tu IP de Aternos
SERVER_ADDRESS = "background-ears.gl.joinmc.link:25565"

REGLAS_TEXT = """
1. **Respeto mutuo:** Tratar bien a todos los miembros en el chat y voz.
2. **Cero Griefing:** Prohibido destruir o alterar construcciones ajenas sin permiso.
3. **Pertenencias:** Respetar los cofres y ítems de los demás jugadores.
4. **Fair Play:** Prohibido el uso de hacks, X-Ray o clientes modificados con ventajas.
5. **Diviértete:** ¡Cualquier duda o sugerencia avísale a los admins!
"""

# =========================================================
# SERVIDOR WEB PARA HEALTH CHECKS DE RENDER
# =========================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Discord funcionando correctamente 24/7."

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# =========================================================
# FUNCIONES AUXILIARES DE ATERNOS
# =========================================================
def get_aternos_server():
    """Conecta a la API de Aternos y recupera la instancia del servidor."""
    try:
        aternos = AternosClient.from_credentials(ATERNOS_USER, ATERNOS_PASS)
        servers = aternos.list_servers()
        if servers:
            return servers[0]
    except Exception as e:
        print(f"Error al conectar con Aternos: {e}")
    return None

# =========================================================
# INICIALIZACIÓN DE DISCORD
# =========================================================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================================================
# TAREA EN SEGUNDO PLANO (ESTADO EN DISCORD)
# =========================================================
@tasks.loop(seconds=30)
async def actualizar_estado_presencia():
    """Actualiza la actividad del bot dependiendo del estado en Aternos / Minecraft."""
    try:
        server = JavaServer.lookup(SERVER_ADDRESS)
        status = server.status()
        count = status.players.online
        
        await bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name=f"Minecraft ({count} jug)")
        )
    except Exception:
        await bot.change_presence(
            status=discord.Status.dnd,
            activity=discord.Game(name="Servidor Mimido / Iniciando")
        )

@bot.event
async def on_ready():
    print(f"Bot conectado con éxito como {bot.user}")
    
    if not actualizar_estado_presencia.is_running():
        actualizar_estado_presencia.start()

    try:
        synced = await bot.tree.sync()
        print(f"Sincronizados {len(synced)} comandos.")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

# =========================================================
# COMANDOS DE DISCORD
# =========================================================

# 1. EMPEZAR (ATERNOS)
@bot.tree.command(name="empezar", description="Enciende el servidor de Minecraft en Aternos")
async def empezar(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        srv = get_aternos_server()
        if not srv:
            await interaction.followup.send("❌ No se pudo conectar a la cuenta de Aternos. Revisa las credenciales.")
            return

        if srv.status == "online":
            await interaction.followup.send("🟢 **El servidor ya se encuentra encendido.** ¡Pueden entrar a jugar!")
            return

        if srv.status == "starting" or srv.status == "loading":
            await interaction.followup.send("⏳ **El servidor ya se está encendiendo.** Dale un par de minutos.")
            return

        # Envía la orden de inicio a Aternos
        srv.start()

        embed = discord.Embed(
            title="Solicitud enviada a Aternos 🚀",
            description="El servidor de Minecraft ha recibido la orden de arranque.\nSi hay cola de espera en Aternos, tardará unos minutos en abrirse.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Revisa la presencia del bot para saber cuándo esté en línea.")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Error al encender Aternos",
            description=f"Ocurrió un problema con la API:\n`{str(e)}`",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

# 2. DETENER (ATERNOS)
@bot.tree.command(name="detener", description="Apaga el servidor de Minecraft en Aternos")
async def detener(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        srv = get_aternos_server()
        if not srv:
            await interaction.followup.send("❌ No se pudo conectar a la cuenta de Aternos.")
            return

        if srv.status == "offline":
            await interaction.followup.send("🔴 **El servidor ya se encuentra apagado.**")
            return

        srv.stop()

        embed = discord.Embed(
            title="Servidor Apagado 🛑",
            description="Se ha enviado la orden de apagar a Aternos. Guardando mapa y cerrando sesión...",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(
            title="Error al apagar",
            description=f"Ocurrió un error:\n`{str(e)}`",
            color=discord.Color.gold()
        )
        await interaction.followup.send(embed=embed)

# 3. IP
@bot.tree.command(name="ip", description="Muestra la dirección IP para conectarse")
async def ip(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Dirección IP del Servidor",
        description=f"```\n{SERVER_IP_TEXT}\n```",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Copia esta IP e ingrésala en tu cliente de Minecraft.")
    await interaction.response.send_message(embed=embed)

# 4. ESTADO
@bot.tree.command(name="estado", description="Consulta el estado del servidor en línea")
async def estado(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        server = JavaServer.lookup(SERVER_ADDRESS)
        status = server.status()

        players_online = status.players.online
        players_max = status.players.max
        
        if status.players.sample:
            player_list = "\n".join([f"• {player.name}" for player in status.players.sample])
        elif players_online > 0:
            player_list = "Jugadores conectados."
        else:
            player_list = "*No hay nadie conectado en este momento.*"

        embed = discord.Embed(title="Servidor En Línea 🟢", color=discord.Color.green())
        embed.add_field(name="Jugadores", value=f"**{players_online} / {players_max}**", inline=True)
        embed.add_field(name="Ping", value=f"**{round(status.latency)} ms**", inline=True)
        embed.add_field(name="Versión", value=f"**{status.version.name}**", inline=False)
        embed.add_field(name="Lista de Jugadores", value=player_list, inline=False)

        await interaction.followup.send(embed=embed)

    except Exception:
        embed = discord.Embed(
            title="Servidor Offline / Cargando 🔴",
            description="El servidor está apagado o iniciando. Puedes encenderlo con `/empezar`.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)

# 5. JUGADORES
@bot.tree.command(name="jugadores", description="Muestra la lista de jugadores conectados actualmente")
async def jugadores(interaction: discord.Interaction):
    await interaction.response.defer()

    try:
        server = JavaServer.lookup(SERVER_ADDRESS)
        status = server.status()
        
        if status.players.online == 0:
            embed = discord.Embed(
                title="Jugadores Conectados (0)",
                description="*No hay nadie jugando en este momento.*",
                color=discord.Color.orange()
            )
        else:
            if status.players.sample:
                nombres = "\n".join([f"**{p.name}**" for p in status.players.sample])
            else:
                nombres = "Hay jugadores activos, pero sus nombres están ocultos."

            embed = discord.Embed(
                title=f"Jugadores Conectados ({status.players.online}/{status.players.max})",
                description=nombres,
                color=discord.Color.green()
            )

        await interaction.followup.send(embed=embed)

    except Exception:
        await interaction.followup.send("El servidor está apagado.")

# 6. REGLAS
@bot.tree.command(name="reglas", description="Muestra las reglas comunitarias del servidor")
async def reglas(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Reglas del Servidor",
        description=REGLAS_TEXT,
        color=discord.Color.purple()
    )
    embed.set_footer(text="El desconocimiento de las reglas no exime de su cumplimiento.")
    await interaction.response.send_message(embed=embed)

# 7. AYUDA
@bot.tree.command(name="ayuda", description="Muestra la lista de comandos disponibles")
async def ayuda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Comandos del Bot",
        description="Aquí tienes la lista de todos los comandos disponibles:",
        color=discord.Color.teal()
    )
    embed.add_field(name="/empezar", value="Enciende el servidor en Aternos.", inline=False)
    embed.add_field(name="/detener", value="Apaga el servidor en Aternos.", inline=False)
    embed.add_field(name="/estado", value="Revisa si el servidor está listo, ping y versión.", inline=False)
    embed.add_field(name="/jugadores", value="Lista detallada de quiénes están dentro jugando.", inline=False)
    embed.add_field(name="/ip", value="Obtén la dirección IP para conectarte.", inline=False)
    embed.add_field(name="/reglas", value="Lee las normas de convivencia del servidor.", inline=False)
    embed.add_field(name="/ayuda", value="Muestra este panel de ayuda.", inline=False)
    
    await interaction.response.send_message(embed=embed)

# =========================================================
# EJECUCIÓN CONJUNTA
# =========================================================
if __name__ == "__main__":
    # Inicia el servidor web Flask en un hilo separado
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

    # Arranca el bot de Discord
    bot.run(TOKEN)
