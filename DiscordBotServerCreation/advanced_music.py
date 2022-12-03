import asyncio
import functools
import itertools
import math
import random
import copy
import discord
import youtube_dl
from playlist import *
from radio import *
from async_timeout import timeout
from discord.ext import commands

# Silence useless bug reports messages
youtube_dl.utils.bug_reports_message = lambda: ''


class VoiceError(Exception):
    pass


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
    }

    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn',
    }

    ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 0.1):
        super().__init__(source, volume)

        self.requester = ctx.author
        self.channel = ctx.channel
        self.data = data

        self.uploader = data.get('uploader')
        self.uploader_url = data.get('uploader_url')
        date = data.get('upload_date')
        self.upload_date = date[6:8] + '.' + date[4:6] + '.' + date[0:4]
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.description = data.get('description')
        self.duration = self.parse_duration(int(data.get('duration')))
        self.tags = data.get('tags')
        self.url = data.get('webpage_url')
        self.views = data.get('view_count')
        self.likes = data.get('like_count')
        self.dislikes = data.get('dislike_count')
        self.stream_url = data.get('url')

    def __str__(self):
        return '**{0.title}** by **{0.uploader}**'.format(self)

    @classmethod
    async def createSource(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))
        return cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS, executable='external/ffmpeg.exe'), data=info)


    @classmethod
    async def createMultipleSource(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        sources = []
        if 'entries' in data:
            for entry in data['entries']:
                process_info = entry

                webpage_url = process_info['url']
                partial = functools.partial(cls.ytdl.extract_info, webpage_url, download=False)
                processed_info = await loop.run_in_executor(None, partial)

                if processed_info is None:
                    raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

                if 'entries' not in processed_info:
                    info = processed_info
                else:
                    info = None
                    while info is None:
                        try:
                            info = processed_info['entries'].pop(0)
                        except IndexError:
                            raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))
                sources.append(cls(ctx, discord.FFmpegPCMAudio(info['url'], **cls.FFMPEG_OPTIONS, executable='external/ffmpeg.exe'), data=info))
        return sources
        

    @classmethod
    async def copy_source(cls, ctx: commands.Context, data: dict):
        return cls(ctx, discord.FFmpegPCMAudio(data['url'], **cls.FFMPEG_OPTIONS, executable='external/ffmpeg.exe'), data=data)


    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{}'.format(days))
            duration.append('{:02}'.format(hours))
            duration.append('{:02}'.format(minutes))
        elif hours > 0:
            duration.append('{}'.format(hours))
            duration.append('{:02}'.format(minutes))
        else:
            duration.append('{}'.format(minutes))
        duration.append('{:02}'.format(seconds))

        return ':'.join(duration)


class Song:
    __slots__ = ('source', 'requester')

    def __init__(self, source: YTDLSource):
        self.source = source
        self.requester = source.requester

    def create_embed(self):
        embed = discord.Embed(title='Now playing',
                              description='``{0.source.title}``'.format(self),
                              color=discord.Color.random())
        #embed.add_field(name='Duration', value=self.source.duration)
        embed.add_field(name='Requested by', value=self.requester.mention)
        embed.add_field(name='Uploaded by', value='[{0.source.uploader}]({0.source.uploader_url})'.format(self))
        embed.add_field(name='URL', value='[Click]({0.source.url})'.format(self))
        embed.set_thumbnail(url=self.source.thumbnail)
        return embed


class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]


class VoiceState:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current = None
        self.voice = None
        self.next = asyncio.Event()
        self.songs = SongQueue()
        self.itemsPerPage = 10

        self.isLooping = False
        self._volume = 0.1
        self.skip_votes = set()

        self.audio_player = bot.loop.create_task(self.audio_player_task())

    def __del__(self):
        self.audio_player.cancel()

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value: float):
        self._volume = value
        if self.current:
            self.current.source.volume = self._volume

    async def audio_player_task(self):
        while True:
            self.next.clear()

            if not self.isLooping or not self.current:
                try:
                    async with timeout(60*3):  # wait 3 minutes
                        self.current = await self.songs.get()
                        self.current.source.volume = self._volume
                        await self.queue.updateEmbed2()
                        await self.radio.updateEmbed2()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return
            else: # Loop the same song
                source = await YTDLSource.copy_source(self._ctx, self.current.source.data)
                self.current = Song(source)
                self.current.source.volume = self._volume

            self.voice.play(self.current.source, after=self.playNextSong)
            #await self.current.source.channel.send(embed=self.current.create_embed())

            await self.next.wait()

    def tracks(self):
        return len(self.songs)

    def pages(self):
        return math.ceil(self.tracks() / self.itemsPerPage)

    def hasSong(self):
        return self.voice and self.current

    def playNextSong(self, error=None):
        if error:
            raise VoiceError(str(error))
        self.next.set()

    def changeVolume(self, up: bool):
        if up:
            self.volume += 0.1
        else:
            self.volume -= 0.1
        self.volume = max(0, min(self.volume, 1))

    def getVolumeField(self):
        string = ''
        if self.volume <= 0:
            string += '🔇 '
        elif self.volume <= 0.2:
            string += '🔈 '
        elif self.volume <= 0.4:
            string += '🔉 '
        else:
            string += '🔊 '
        chunk = 10
        for x in range(1,10+1):
            if x / 10 >= self.volume:
                chunk = x
                break
        for x in range(1,10+1):
            if x != chunk:
                string += '─'
            else:
                string += '○'
        return string

    def createEmbed(self):
        embed = None
        if self.current:
            embed = self.current.create_embed()
        else:
            embed = discord.Embed(title='Nothing is playing', description='', color=discord.Color.random())
        field = self.getVolumeField()
        embed.description += f'\n\n⚪════════════════════════════════════\n\n⠀⠀'
        if self.current:
            embed.description += f'0:00 / {self.current.source.duration}'
        else:
            embed.description += '0:00 / 0:00'
        embed.description += f'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀{field}'
        return embed

    def pause(self):
        if self.voice.is_paused():
            self.voice.resume()
        else:
            self.voice.pause()
        return not self.voice.is_paused()

    def skip(self):
        self.skip_votes.clear()
        if self.hasSong():
            self.voice.stop()
            self.current = None

    def clear(self):
        self.songs.clear()
        if self.hasSong():
            self.voice.stop()
            self.current = None
            return True
        return False

    async def stop(self):
        self.songs.clear()
        if self.voice:
            await self.voice.disconnect()
            self.voice = None


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(self.bot, ctx)
            self.voice_states[ctx.guild.id] = state

        return state

    def cog_unload(self):
        for state in self.voice_states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send('An error occurred: {}'.format(str(error)))

    @commands.command(name='join')
    async def _join(self, ctx: commands.Context):
        """Joins a voice channel."""
        destination = ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()


    @commands.command(name='leave', aliases=['disconnect','exit'])
    async def _leave(self, ctx: commands.Context):
        """Clears the queue and leaves the voice channel."""
        await ctx.message.delete()
        if not ctx.voice_state.voice:
            await ctx.send('Not connected to any voice channel.', delete_after=5)
            return

        await ctx.voice_state.stop()
        del self.voice_states[ctx.guild.id]


    @commands.command(name='volume', aliases=['vol'])
    async def _volume(self, ctx: commands.Context, *, volume: int):
        """Sets the volume of the player."""
        await ctx.message.delete()
        if not ctx.voice_state.hasSong():
            return await ctx.send('Nothing being played at the moment.', delete_after=5)

        if 0 > volume > 100:
            return await ctx.send('Volume must be between 0 and 100', delete_after=5)

        ctx.voice_state.volume = volume / 100
        await ctx.send('Changed volume to {}%'.format(volume), delete_after=5)


    async def pause(self, ctx: commands.Context):
        return ctx.voice_state.pause()


    async def volumeDown(self, ctx: commands.Context):
        return ctx.voice_state.changeVolume(False)


    async def volumeUp(self, ctx: commands.Context):
        return ctx.voice_state.changeVolume(True)


    async def shuffle(self, ctx: commands.Context):
        ctx.voice_state.songs.shuffle()


    async def loop(self, ctx: commands.Context):
        ctx.voice_state.isLooping = not ctx.voice_state.isLooping
        return ctx.voice_state.isLooping


    async def clear(self, ctx: commands.Context):
        ctx.voice_state.clear()


    @commands.command(name='skip')
    async def _skip(self, ctx: commands.Context):
        """Vote to skip a song. The requester can automatically skip."""
        await ctx.message.delete()
        if not ctx.voice_state.hasSong():
            return await ctx.send('Nothing is being played.', delete_after=5)

        voter = ctx.message.author
        if voter == ctx.voice_state.current.requester:
            ctx.voice_state.skip()
        elif voter.id not in ctx.voice_state.skip_votes:
            ctx.voice_state.skip_votes.add(voter.id)
            votes = len(ctx.voice_state.skip_votes)
            if votes >= 3:
                ctx.voice_state.skip()
            else:
                await ctx.send(f'Skip vote added, currently at **{votes}/3**', delete_after=5)
        else:
            await ctx.send('You have already voted to skip this song.')


    async def getQueueEmbed(self, ctx: commands.Context, *, page: int):
        start = (page - 1) * ctx.voice_state.itemsPerPage
        end = start + ctx.voice_state.itemsPerPage

        queue = ''
        for i, song in enumerate(ctx.voice_state.songs[start:end], start=start):
            queue += f'`{i+1}.` [**{song.source.title}**]({song.source.url})\n'

        embed = discord.Embed(description=f'**{ctx.voice_state.tracks()} songs:**\n\n{queue}')
        embed.set_footer(text=f'Page {page}/{max(ctx.voice_state.pages(),1)}')

        return embed


    async def getRadioEmbed(self, ctx: commands.Context):
        return ctx.voice_state.createEmbed()


    @commands.command(name='remove')
    async def _remove(self, ctx: commands.Context, index: int):
        """Removes a song from the queue at a given index."""
        await ctx.message.delete()
        if len(ctx.voice_state.songs) == 0:
            await ctx.send('Queue is empty.', delete_after=5)
            return

        if not len(ctx.voice_state.songs) >= index > 0:
            await ctx.send('That index does not exist.', delete_after=5)
            return

        ctx.voice_state.songs.remove(index - 1)
        await ctx.send('Item removed.', delete_after=5)


    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx: commands.Context, *, search: str):
        """Plays a song.

        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """
        await ctx.message.delete()
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                source = await YTDLSource.createSource(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.send(f'An error occurred while processing this request: {str(e)}', delete_after=5)
            else:
                await ctx.voice_state.songs.put(Song(source))
                await ctx.voice_state.queue.updateEmbed2()

    @commands.command(name='playlist')
    async def _playlist(self, ctx: commands.Context, *, search: str):
        """Plays a playlist.

        This command automatically searches from various sites if no URL is provided.
        A list of these sites can be found here: https://rg3.github.io/youtube-dl/supportedsites.html
        """
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        async with ctx.typing():
            try:
                sources = await YTDLSource.createMultipleSource(ctx, search, loop=self.bot.loop)
            except YTDLError as e:
                await ctx.message.delete()
                await ctx.send(f'An error occurred while processing this request: {str(e)}', delete_after=5)
            else:
                await ctx.message.delete()
                for source in sources:
                    await ctx.voice_state.songs.put(Song(source))
                    await ctx.voice_state.queue.updateEmbed2()


    @commands.command(name='radio')
    async def _radio(self, ctx: commands.Context):
        """Starts a radio."""
        await ctx.message.delete()
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)

        # Radio
        embed = await ctx.invoke(self.getRadioEmbed)
        ctx.voice_state.radio = RadioButtons(ctx=ctx, cog=self)
        ctx.voice_state.radio.message = await ctx.send(embed=embed, view=ctx.voice_state.radio)
        # Queue
        embed = await ctx.invoke(self.getQueueEmbed, page=1)
        ctx.voice_state.queue = QueueButtons(ctx=ctx, cog=self, page=1)
        ctx.voice_state.queue.message = await ctx.send(embed=embed, view=ctx.voice_state.queue)


    @_join.before_invoke
    @_play.before_invoke
    @_playlist.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError('You are not connected to any voice channel.')

        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError('Bot is already in a voice channel.')