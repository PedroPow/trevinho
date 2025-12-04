import discord
import aiohttp
import asyncio
import io
import os
from discord.ext import commands
from discord.ui import Modal, TextInput

# ============================
#   CONFIGURAÇÕES DO SERVIDOR
# ============================

GUILD_ID = 1380696158174974062

VERIFY_CHANNEL_ID = 1444743568202928411
LOG_CHANNEL_ID = 1445534747001360597

ROLE_VERIFY_ID = 1444743630584545522
ROLE_AUTOROLE_ID = 1444743687824474162
ADMIN_ROLE_ID = 1444744188829761737

PAINEL_CHANNEL_ID = 1445562667094769856

# Advertências
ID_CARGO_ADV1 = 1444792937685848295
ID_CARGO_ADV2 = 1444793001342668830
ID_CARGO_ADV3 = 1444793057076580372
ID_CARGO_BANIDO = 1444793189193093275

# Autorizados para /mensagem
CARGOS_AUTORIZADOS = [
    1444744042700079316,
    1444744188829761737,
]

# ============================
#         BOT + INTENTS
# ============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")

# ============================
#        SISTEMA DE LOGS
# ============================

async def enviar_log(guild, titulo, descricao, cor=discord.Color.green()):
    canal = guild.get_channel(LOG_CHANNEL_ID)
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor)
        embed.set_footer(text="Sistema de Logs - Tropa do Trevo")
        await canal.send(embed=embed)

# ============================
#   BOTÃO DE VERIFICAÇÃO
# ============================

class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verificar", style=discord.ButtonStyle.success, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):

        role = interaction.guild.get_role(ROLE_VERIFY_ID)
        if role is None:
            return await interaction.response.send_message("❌ Cargo de verificação não encontrado!", ephemeral=True)

        if role in interaction.user.roles:
            return await interaction.response.send_message("Você já está verificado!", ephemeral=True)

        await interaction.user.add_roles(role)

        await interaction.response.send_message("🎉 Você foi verificado com sucesso!", ephemeral=True)

        await enviar_log(
            interaction.guild,
            "🔔 Novo usuário verificado",
            f"**Usuário:** {interaction.user.mention}\n**Cargo:** `{role.name}`"
        )

# ============================
#     PAINEL ADMINISTRATIVO
# ============================

class PainelAdminView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 Ver Logs", style=discord.ButtonStyle.secondary, custom_id="view_logs")
    async def view_logs(self, interaction: discord.Interaction, button: discord.ui.Button):

        admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
        if admin_role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

        log = interaction.guild.get_channel(LOG_CHANNEL_ID)
        await interaction.response.send_message(f"📌 Os logs estão em: {log.mention}", ephemeral=True)

async def enviar_painel(guild):
    canal = guild.get_channel(PAINEL_CHANNEL_ID)
    if canal:
        embed = discord.Embed(
            title="🛠 Painel Administrativo",
            description="Gerencie o sistema abaixo:",
            color=discord.Color.green()
        )

        await canal.purge(limit=10)
        await canal.send(embed=embed, view=PainelAdminView())

# ============================
#         AUTOROLE
# ============================

@bot.event
async def on_member_join(member):
    role = member.guild.get_role(ROLE_AUTOROLE_ID)

    if role:
        await member.add_roles(role)

    await enviar_log(
        member.guild,
        "👤 Novo membro entrou",
        f"**Usuário:** {member.mention}\n**Cargo automático:** `{role.name}`"
    )

# ============================
#        COMANDO /clearall
# ============================

@bot.tree.command(name="clearall", description="Limpa todas as mensagens do canal.")
async def clearall(interaction: discord.Interaction):

    admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if admin_role not in interaction.user.roles:
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    canal = interaction.channel
    await interaction.response.send_message(f"🧹 Limpando {canal.name}...", ephemeral=True)

    try:
        await canal.purge(limit=None)
    except:
        await canal.purge()

    embed = discord.Embed(
        title="🧹 Canal Limpo",
        description=f"Todas as mensagens foram apagadas!",
        color=discord.Color.green()
    )

    await canal.send(embed=embed)

# ============================
#         MODAL /mensagem
# ============================

class MensagemModal(Modal, title="📢 Enviar Mensagem"):
    conteudo = TextInput(
        label="Conteúdo da mensagem",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction):
        await interaction.response.send_message("⏳ Enviando...", ephemeral=True)

        msg_inicial = await interaction.channel.send(self.conteudo.value)

        await interaction.followup.send(
            "📎 Responda aquela mensagem com anexos em até 5 minutos.",
            ephemeral=True
        )

        def check(m):
            return (
                m.reference and
                m.reference.message_id == msg_inicial.id and
                m.author == interaction.user
            )

        try:
            reply = await bot.wait_for("message", timeout=300.0, check=check)
            files = []

            async with aiohttp.ClientSession() as session:
                for a in reply.attachments:
                    async with session.get(a.url) as resp:
                        dados = await resp.read()
                        files.append(discord.File(io.BytesIO(dados), filename=a.filename))

            await msg_inicial.delete()
            await reply.delete()

            await interaction.channel.send(content=self.conteudo.value, files=files)

        except asyncio.TimeoutError:
            pass

@bot.tree.command(name="mensagem", description="Enviar mensagem como o bot.")
async def mensagem(interaction):
    if not any(role.id in CARGOS_AUTORIZADOS for role in interaction.user.roles):
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    await interaction.response.send_modal(MensagemModal())

# ============================
#      SISTEMA DE ADVs
# ============================

@bot.tree.command(name="adv", description="Aplica advertência.")
async def adv(interaction, membro: discord.Member, motivo: str):

    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    adv1 = interaction.guild.get_role(ID_CARGO_ADV1)
    adv2 = interaction.guild.get_role(ID_CARGO_ADV2)
    adv3 = interaction.guild.get_role(ID_CARGO_ADV3)
    banido = interaction.guild.get_role(ID_CARGO_BANIDO)

    if banido in membro.roles:
        return await interaction.response.send_message("⚠ Esse membro já está banido.", ephemeral=True)

    if adv3 in membro.roles:
        await membro.remove_roles(adv3)
        await membro.add_roles(banido)
        msg = "🚫 4ª advertência → BANIDO"
    elif adv2 in membro.roles:
        await membro.remove_roles(adv2)
        await membro.add_roles(adv3)
        msg = "⚠ 3ª advertência aplicada!"
    elif adv1 in membro.roles:
        await membro.remove_roles(adv1)
        await membro.add_roles(adv2)
        msg = "⚠ 2ª advertência aplicada!"
    else:
        await membro.add_roles(adv1)
        msg = "⚠ 1ª advertência aplicada!"

    await interaction.response.send_message(msg, ephemeral=True)

# ============================
#            BAN
# ============================

@bot.tree.command(name="ban", description="Bane um membro.")
async def ban(interaction, membro: discord.Member, motivo: str):

    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)

    try:
        await membro.ban(reason=motivo)
        await interaction.response.send_message(f"🔨 {membro.mention} banido!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ O bot não pode banir esse usuário.", ephemeral=True)

# ============================
#           ON_READY
# ============================

@bot.event
async def on_ready():

    # Evita duplicar logs, painéis e sincronizações
    if getattr(bot, "ready_once", False):
        return

    bot.ready_once = True

    print(f"🔥 Bot conectado como {bot.user}")

    guild = bot.get_guild(GUILD_ID)

    # Enviar painel administrativo
    await enviar_painel(guild)

    # Enviar painel de verificação
    verify_channel = guild.get_channel(VERIFY_CHANNEL_ID)

    embed = discord.Embed(
        title="🔰 Sistema de Verificação",
        description="Clique no botão abaixo para se verificar.",
        color=discord.Color.green()
    )

    await verify_channel.purge(limit=10)
    await verify_channel.send(embed=embed, view=VerifyButton())

    # Sincronizar comandos
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Comandos sincronizados: {len(synced)}")
    except Exception as e:
        print(f"Erro ao sincronizar: {e}")

    # Log inicial
    await enviar_log(guild, "🚀 Bot iniciado", "Todos os sistemas ativos!")


bot.run(TOKEN)
