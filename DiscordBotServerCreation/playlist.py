import discord
from discord import ui

class QueueButtons(discord.ui.View):
    def __init__(self, *, ctx, cog, page):
        super().__init__(timeout=None)
        self.page = page
        self.ctx = ctx
        self.cog = cog

    async def updateEmbed(self, interaction:discord.Interaction):
        embed = await self.ctx.invoke(self.cog.getQueueEmbed, page=self.page)
        await interaction.response.edit_message(embed=embed, view=self)

    async def updateEmbed2(self):
        embed = await self.ctx.invoke(self.cog.getQueueEmbed, page=self.page)
        await self.message.edit(embed=embed, view=self)


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='⏪', custom_id='mostLeft')
    async def mostLeft(self, interaction:discord.Interaction, button:discord.ui.Button):
        self.page = 1
        await self.updateEmbed(interaction)


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='◀', custom_id='left')
    async def left(self, interaction:discord.Interaction, button:discord.ui.Button):
        pages = self.ctx.voice_state.pages()
        if pages <= 0:
            self.page = 1
        elif self.page > pages:
            self.page = pages
        elif self.page > 1:
            self.page -= 1

        await self.updateEmbed(interaction)


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='▶', custom_id='right')
    async def right(self, interaction:discord.Interaction, button:discord.ui.Button):
        pages = self.ctx.voice_state.pages()
        if pages <= 0:
            self.page = 1
        elif self.page > pages:
            self.page = pages
        elif self.page < pages:
            self.page += 1
            
        await self.updateEmbed(interaction)


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='⏩', custom_id='mostRight')
    async def mostRight(self, interaction:discord.Interaction, button:discord.ui.Button):
        pages = self.ctx.voice_state.pages()
        if pages <= 0:
            self.page = 1
        else:
            self.page = self.ctx.voice_state.pages()

        await self.updateEmbed(interaction)


############################################################################


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='🔀', custom_id='shuffle', row=2)
    async def shuffle(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.ctx.invoke(self.cog.shuffle)
        await self.updateEmbed(interaction)


    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji='🔁', custom_id='loop', row=2)
    async def loop(self, interaction:discord.Interaction, button:discord.ui.Button):
        if await self.ctx.invoke(self.cog.loop):
            button.style = discord.ButtonStyle.success
        else:
            button.style = discord.ButtonStyle.secondary
        await self.updateEmbed(interaction)


    @discord.ui.button(style=discord.ButtonStyle.success, emoji='🔄', custom_id='reload', row=2)
    async def reload(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.updateEmbed(interaction)


    @discord.ui.button(style=discord.ButtonStyle.danger, emoji='🗑', custom_id='clear2', row=2)
    async def clear2(self, interaction:discord.Interaction, button:discord.ui.Button):
        view = ConfirmButtons(parent=self, interaction=interaction)
        await interaction.response.send_message(f'Are you sure you want to clear {self.ctx.voice_state.tracks()} songs?', ephemeral=True, view=view)


class ConfirmButtons(discord.ui.View):
    def __init__(self, *, timeout=180, parent, interaction):
        super().__init__(timeout=timeout)
        self.parent = parent
        self.ctx = parent.ctx
        self.cog = parent.cog
        self.interaction = interaction

    @discord.ui.button(style=discord.ButtonStyle.danger, label='Yes', custom_id='yes')
    async def yes(self, interaction:discord.Interaction, button:discord.ui.Button):
        await self.ctx.invoke(self.cog.clear)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content='Queue cleaned. You can close this message.', view=self)
        # Edit the embeds
        await self.ctx.voice_state.radio.updateEmbed2()
        await self.ctx.voice_state.queue.updateEmbed2()

    @discord.ui.button(style=discord.ButtonStyle.secondary, label='No', custom_id='no')
    async def no(self, interaction:discord.Interaction, button:discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content='Queue was not cleaned. You can close this message.', view=self)