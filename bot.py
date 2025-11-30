import aiohttp
import io
import discord
import asyncio
from discord.ext import commands
from discord.ui import Modal, TextInput
import os


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
ID_SERVIDOR = 1380696158174974062  # Guarujá RP

CARGOS_AUTORIZADOS = [
    1444744042700079316,   # dono
    1444744188829761737,  # socio
]

ID_CARGO_ADV1 = 1444792937685848295
ID_CARGO_ADV2 = 1444793001342668830
ID_CARGO_ADV3 = 1444793057076580372
ID_CARGO_BANIDO = 1444793189193093275
ID_CARGO_TURISTA = 1444743687824474162  # cargo para novos membros

# Modal de mensagem
class MensagemModal(Modal, title="📢 Enviar Mensagem"):
    conteudo = TextInput(
        label="Conteúdo da mensagem",
        placeholder="Escreva o conteúdo aqui...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏳ Mensagem sendo enviada...", ephemeral=True)
        msg_inicial = await interaction.channel.send(self.conteudo.value)

        await interaction.followup.send(
            "📎 Responda à mensagem acima com *anexos* (imagens/vídeos) em até 5 minutos.",
            ephemeral=True
        )

        def check(m):
            return (
                m.reference and
                m.reference.message_id == msg_inicial.id and
                m.author == interaction.user and
                m.channel == interaction.channel
            )

        try:
            reply = await bot.wait_for("message", timeout=300.0, check=check)
            arquivos = []
            async with aiohttp.ClientSession() as session:
                for a in reply.attachments:
                    async with session.get(a.url) as resp:
                        if resp.status == 200:
                            dados = await resp.read()
                            arquivos.append(discord.File(io.BytesIO(dados), filename=a.filename))
            try:
                await msg_inicial.delete()
                await reply.delete()
            except discord.Forbidden:
                pass
            await interaction.channel.send(content=self.conteudo.value, files=arquivos)
        except asyncio.TimeoutError:
            pass

# /mensagem
@bot.tree.command(name="mensagem", description="Envie uma mensagem como o bot", guild=discord.Object(id=ID_SERVIDOR))
async def mensagem(interaction: discord.Interaction):
    if not any(discord.utils.get(interaction.user.roles, id=role_id) for role_id in CARGOS_AUTORIZADOS):
        await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True)
        return
    await interaction.response.send_modal(MensagemModal())

# /adv
@bot.tree.command(name="adv", description="Aplica uma advertência a um membro", guild=discord.Object(id=ID_SERVIDOR))
@discord.app_commands.describe(membro="Membro a advertir", motivo="Motivo da advertência")
async def adv(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ Sem permissão para aplicar advertências.", ephemeral=True)
        return

    adv1 = interaction.guild.get_role(ID_CARGO_ADV1)
    adv2 = interaction.guild.get_role(ID_CARGO_ADV2)
    adv3 = interaction.guild.get_role(ID_CARGO_ADV3)
    banido = interaction.guild.get_role(ID_CARGO_BANIDO)

    if banido in membro.roles:
        await interaction.response.send_message("⚠ Membro já com cargo de banido.", ephemeral=True)
        return

    if adv3 in membro.roles:
        await membro.remove_roles(adv3)
        await membro.add_roles(banido)
        await interaction.response.send_message(f"🚫 {membro.mention} recebeu a *4ª advertência* e foi marcado como *banido*.", ephemeral=True)
    elif adv2 in membro.roles:
        await membro.remove_roles(adv2)
        await membro.add_roles(adv3)
        await interaction.response.send_message(f"⚠ {membro.mention} recebeu a *3ª advertência*.", ephemeral=True)
    elif adv1 in membro.roles:
        await membro.remove_roles(adv1)
        await membro.add_roles(adv2)
        await interaction.response.send_message(f"⚠ {membro.mention} recebeu a *2ª advertência*.", ephemeral=True)
    else:
        await membro.add_roles(adv1)
        await interaction.response.send_message(f"⚠ {membro.mention} recebeu a *1ª advertência*.", ephemeral=True)

    try:
        embed_dm = discord.Embed(
            title="⚠ Advertência Recebida",
            description=f"Você recebeu uma advertência no servidor *{interaction.guild.name}*.",
            color=discord.Color.orange()
        )
        embed_dm.add_field(name="Motivo", value=motivo, inline=False)
        embed_dm.set_footer(text=f"Por: {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await membro.send(embed=embed_dm)
    except discord.Forbidden:
        pass

# /ban
@bot.tree.command(name="ban", description="Bane um membro", guild=discord.Object(id=ID_SERVIDOR))
@discord.app_commands.describe(membro="Membro que será banido", motivo="Motivo do banimento")
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ Sem permissão para banir.", ephemeral=True)
        return
    try:
        await membro.ban(reason=motivo)
        await interaction.response.send_message(f"✅ {membro.mention} foi banido com sucesso.", ephemeral=True)
        embed = discord.Embed(
            title="🚫 Membro Banido",
            description=f"{membro.mention} foi banido.",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Motivo", value=motivo, inline=False)
        embed.set_footer(text=f"Banido por: {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await interaction.channel.send(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ O bot não pode banir esse membro.", ephemeral=True)

# Evento ao entrar no servidor
@bot.event
async def on_member_join(member):
    cargo = member.guild.get_role(ID_CARGO_TURISTA)
    if cargo:
        await member.add_roles(cargo, reason="Novo membro entrou no servidor")

# Bot pronto
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=ID_SERVIDOR))
        print(f"✅ {len(synced)} comando(s) sincronizado(s).")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")

bot.run(TOKEN)