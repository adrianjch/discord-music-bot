import discord
from discord import ui

class RadioButtons(discord.ui.View):
    def __init__(self, *, ctx, cog):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.cog = cog

    async def updateEmbed(self, interaction:discord.Interaction):
        embed = await self.ctx.invoke(self.cog.getRadioEmbed)
        await interaction.response.edit_message(embed=embed, view=self)

    async def updateEmbed2(self):
        embed = await self.ctx.invoke(self.cog.getRadioEmbed)
        await self.message.edit(embed=embed, view=self)


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='⏸', custom_id='pause')
    async def pause(self, interaction:discord.Interaction, button:discord.ui.Button):
        if await self.ctx.invoke(self.cog.pause):
            button.emoji = '⏸'
        else:
            button.emoji = '▶'
        await self.updateEmbed(interaction)


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='🔈', custom_id='volumeDown')
    async def volumeDown(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.ctx.invoke(self.cog.volumeDown)
        await self.updateEmbed(interaction)


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='🔊', custom_id='volumeUp')
    async def volumeUp(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.ctx.invoke(self.cog.volumeUp)
        await self.updateEmbed(interaction)