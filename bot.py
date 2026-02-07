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
LOG_ADV = 1444799943825948773
LOG_BAN = 1444799943825948773
ROLE_VERIFY_ID = 1444743630584545522
ROLE_AUTOROLE_ID = 1444743687824474162
ADMIN_ROLE_ID = 1444744188829761737

PAINEL_CHANNEL_ID = 1445562667094769856

# Advertências
ID_CARGO_ADV1 = 1444792937685848295
ID_CARGO_ADV2 = 1444793001342668830
ID_CARGO_ADV3 = 1444793057076580372
ID_CARGO_BANIDO = 1444793189193093275

# Autorizados para comandos (todos os slash commands usarão estes cargos)
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
TOKEN = os.getenv("TOKEN")  # coloque TOKEN no .env

# guard para não reenviar painel/verify em reconexões
bot._ready_sent = False

# ============================
#        SISTEMA DE LOGS
# ============================
async def enviar_log_embed(guild: discord.Guild, embed: discord.Embed):
    """Envia embed para o canal de logs se existir."""
    if not guild:
        return
    canal = guild.get_channel(LOG_CHANNEL_ID)
    if canal:
        try:
            await canal.send(embed=embed)
        except Exception:
            # evita crash por falta de permissões
            return

async def enviar_log(guild, titulo, descricao, cor=discord.Color.green()):
    canal = guild.get_channel(LOG_CHANNEL_ID) if guild else None
    if canal:
        embed = discord.Embed(title=titulo, description=descricao, color=cor)
        embed.set_footer(text="Sistema de Logs - Tropa do Trevo")
        try:
            await canal.send(embed=embed)
        except Exception:
            pass

# ============================
#  HELPERS DE PERMISSÃO
# ============================
def has_authorized_role(member: discord.Member) -> bool:
    """Checa se o membro possui pelo menos um dos cargos autorizados."""
    if not member or not hasattr(member, "roles"):
        return False
    return any(role.id in CARGOS_AUTORIZADOS for role in member.roles)

async def require_authorized(interaction: discord.Interaction) -> bool:
    """Verificação async (uso em comandos) — retorna True se autorizado."""
    if not has_authorized_role(interaction.user):
        await interaction.response.send_message("❌ Você não tem permissão (cargo inválido).", ephemeral=True)
        return False
    return True

# ============================
#   BOTÃO DE VERIFICAÇÃO
# ============================
class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verificar", style=discord.ButtonStyle.success, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(ROLE_VERIFY_ID) if interaction.guild else None
        if role is None:
            return await interaction.response.send_message("❌ Cargo de verificação não encontrado!", ephemeral=True)

        if role in interaction.user.roles:
            return await interaction.response.send_message("Você já está verificado!", ephemeral=True)

        try:
            await interaction.user.add_roles(role)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Não consegui adicionar o cargo (permissão).", ephemeral=True)

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
        if log:
            await interaction.response.send_message(f"📌 Os logs estão em: {log.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Canal de logs não encontrado.", ephemeral=True)

async def enviar_painel(guild: discord.Guild):
    if not guild:
        return
    canal = guild.get_channel(PAINEL_CHANNEL_ID)
    if canal:
        try:
            await canal.purge(limit=10)
        except Exception:
            # se não tiver permissão para purge, tenta enviar mesmo assim
            pass
        embed = discord.Embed(
            title="🛠 Painel Administrativo",
            description="Gerencie o sistema abaixo:",
            color=discord.Color.green()
        )
        try:
            await canal.send(embed=embed, view=PainelAdminView())
        except Exception:
            pass

# ============================
#         AUTOROLE
# ============================
@bot.event
async def on_member_join(member: discord.Member):
    role = member.guild.get_role(ROLE_AUTOROLE_ID) if member.guild else None
    if role:
        try:
            await member.add_roles(role)
        except Exception:
            pass

    # envia log (se existir canal)
    await enviar_log(
        member.guild,
        "👤 Novo membro entrou",
        f"**Usuário:** {member.mention}\n**Cargo automático:** `{role.name if role else 'N/A'}`"
    )

# ============================
#        COMANDO /clearall
# ============================
@bot.tree.command(name="clearall", description="Apaga todas as mensagens do canal atual.", guild=discord.Object(id=GUILD_ID))
async def clearall(interaction: discord.Interaction):
    # validar cargo autorizado
    if not await require_authorized(interaction):
        return

    canal = interaction.channel
    guild = interaction.guild
    if canal is None or guild is None:
        return await interaction.response.send_message("❌ Contexto inválido.", ephemeral=True)

    # responder rápido
    await interaction.response.send_message(f"🧹 Limpando todas as mensagens do canal **{canal.name}**...", ephemeral=True)

    # limpa mensagens
    try:
        # limite=None as vezes falha em alguns builds, tenta em bloco
        await canal.purge(limit=None)
    except Exception:
        try:
            await canal.purge()
        except Exception:
            # se tudo falhar, informa o usuário
            pass

    # enviar confirmação no canal limpo (se permitido)
    try:
        embed_confirm = discord.Embed(
            title="🧹 Canal Limpo",
            description=f"As mensagens do canal `{canal.name}` foram apagadas com sucesso!",
            color=discord.Color.green()
        )
        await canal.send(embed=embed_confirm)
    except Exception:
        # sem permissão para enviar no canal limpo — ignora
        pass

    # preparar log detalhado e enviar para o canal de logs (LOG_CHANNEL_ID)
    embed_log = discord.Embed(
        title="🧹 Log - Canal Limpo",
        description=(
            f"**Usuário:** {interaction.user.mention}\n"
            f"**ID do usuário:** `{interaction.user.id}`\n"
            f"**Canal limpo:** {canal.mention}\n"
            f"**Servidor:** `{guild.name}`"
        ),
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    embed_log.set_footer(text=f"Ação: clearall")

    await enviar_log_embed(guild, embed_log)

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

    async def on_submit(self, interaction: discord.Interaction):
        # checar autorização rapidamente
        if not has_authorized_role(interaction.user):
            # interação ainda pode ser respondida
            await interaction.response.send_message("❌ Você não tem permissão para usar este modal.", ephemeral=True)
            return

        await interaction.response.send_message("⏳ Enviando...", ephemeral=True)

        try:
            msg_inicial = await interaction.channel.send(self.conteudo.value)
        except Exception:
            await interaction.followup.send("❌ Não consegui enviar a mensagem inicial (permissão).", ephemeral=True)
            return

        await interaction.followup.send(
            "📎 Responda aquela mensagem com anexos em até 5 minutos.",
            ephemeral=True
        )

        def check(m: discord.Message):
            return (
                m.reference and
                m.reference.message_id == msg_inicial.id and
                m.author == interaction.user and
                m.channel == interaction.channel
            )

        try:
            reply = await bot.wait_for("message", timeout=300.0, check=check)
            files = []
            async with aiohttp.ClientSession() as session:
                for a in reply.attachments:
                    try:
                        async with session.get(a.url) as resp:
                            dados = await resp.read()
                            files.append(discord.File(io.BytesIO(dados), filename=a.filename))
                    except Exception:
                        continue

            # tenta deletar mensagens do usuário e a de confirmação
            try:
                await msg_inicial.delete()
                await reply.delete()
            except Exception:
                pass

            try:
                await interaction.channel.send(content=self.conteudo.value, files=files)
            except Exception:
                await interaction.followup.send("❌ Não consegui reenviar a mensagem (permissão).", ephemeral=True)

        except asyncio.TimeoutError:
            # tempo esgotado — só ignora
            try:
                await interaction.followup.send("⏰ Tempo esgotado. Nenhum anexo recebido.", ephemeral=True)
            except Exception:
                pass

@bot.tree.command(name="mensagem", description="Enviar mensagem como o bot.", guild=discord.Object(id=GUILD_ID))
async def mensagem(interaction: discord.Interaction):
    if not await require_authorized(interaction):
        return
    # abrir modal
    await interaction.response.send_modal(MensagemModal())

# ============================
#      SISTEMA DE ADVs
# ============================
@bot.tree.command(name="adv", description="Aplica advertência.", guild=discord.Object(id=GUILD_ID))
async def adv(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not await require_authorized(interaction):
        return

    # mantém checagem extra: só membros com permissão de kick podem aplicar adv (opcional)
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ Você precisa de permissão para expulsar (kick) para aplicar advertências.", ephemeral=True)

    adv1 = interaction.guild.get_role(ID_CARGO_ADV1)
    adv2 = interaction.guild.get_role(ID_CARGO_ADV2)
    adv3 = interaction.guild.get_role(ID_CARGO_ADV3)
    banido = interaction.guild.get_role(ID_CARGO_BANIDO)

    if banido in membro.roles:
        return await interaction.response.send_message("⚠ Esse membro já está banido.", ephemeral=True)

    if adv3 in membro.roles:
        try:
            await membro.remove_roles(adv3)
            await membro.add_roles(banido)
            msg = "🚫 4ª advertência → BANIDO"
        except Exception:
            return await interaction.response.send_message("❌ Erro ao atualizar cargos.", ephemeral=True)
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

    # log
    embed = discord.Embed(
        title="⚠ Advertência aplicada",
        description=f"**Membro:** {membro.mention}\n**Por:** {interaction.user.mention}\n**Motivo:** {motivo}",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    await enviar_log_embed(interaction.guild, embed)

# ============================
#            BAN
# ============================
@bot.tree.command(name="ban", description="Bane um membro.", guild=discord.Object(id=GUILD_ID))
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    if not await require_authorized(interaction):
        return

    # checar permissão de ban
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Você precisa da permissão de banir.", ephemeral=True)

    try:
        await membro.ban(reason=motivo)
        await interaction.response.send_message(f"🔨 {membro.mention} banido!", ephemeral=True)
    except discord.Forbidden:
        return await interaction.response.send_message("❌ O bot não pode banir esse usuário.", ephemeral=True)

    embed = discord.Embed(
        title="🚫 Membro Banido",
        description=f"**Membro:** {membro.mention}\n**Por:** {interaction.user.mention}\n**Motivo:** {motivo}",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow()
    )
    await enviar_log_embed(interaction.guild, embed)

# ============================
#           ON_READY
# ============================
@bot.event
async def on_ready():
    # garante executar o bloco de inicialização apenas uma vez por sessão do processo
    if bot._ready_sent:
        return
    bot._ready_sent = True

    print(f"🔥 Bot conectado como {bot.user}")

    guild = bot.get_guild(GUILD_ID)
    # envia painel e verify se guild existir
    if guild:
        try:
            await enviar_painel(guild)
        except Exception:
            pass

        # envia verify embed/button no canal de verificação (se existir)
        try:
            verify_channel = guild.get_channel(VERIFY_CHANNEL_ID)
            if verify_channel:
                try:
                    await verify_channel.purge(limit=10)
                except Exception:
                    pass
                embed = discord.Embed(
                    title="Sistema de Verificação",
                    description="Clique no botão abaixo para se verificar.\n\n"
                    "• Após a verificação altere seu Nick Name no canal:\n"
                    "<#1453448841344061544>.\n"
                    "• É **OBRIGATÓRIO** a Alteração do Nick após a verificação.\n"
                    "• Leia as regras no canal <#1444742456968085635>.\n"
                    "• Qualquer dúvida, contate a equipe de moderação.",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1444735189765849320/1453944484944416928/logo.gif?ex=694f4ad2&is=694df952&hm=516443441d635d2dc56ca959734ca9d4be860406db88ade594d065ff37339b62&")  

                try:
                    await verify_channel.send(embed=embed, view=VerifyButton())
                except Exception:
                    pass
        except Exception:
            pass

    # sincroniza comandos somente pro GUILD (garante que apareçam no servidor)
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"🔧 Slash Commands sincronizados: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    # log de inicialização
    if guild:
        await enviar_log(guild, "🚀 Bot iniciado", "Todos os sistemas ativos!")

# ============================
#           RUN
# ============================
if not TOKEN:
    print("ERRO: TOKEN não definido. Coloque TOKEN no .env ou variáveis de ambiente.")
else:
    bot.run(TOKEN)
