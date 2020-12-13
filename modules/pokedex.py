import logging

import poketwo
from poketwo import Worker
from poketwo.commands import CommandHandler, Context
from poketwo.commands.converters import Converter
from poketwo.commands.events import CommandError
from poketwo.shared.data import DataManager
from poketwo.shared.data.models import Species

logging.basicConfig(level=logging.INFO)

worker = Worker(
    host="amqp://guest:guest@127.0.0.1",
    exchange="poketwo.gateway",
    queue="pokedex",
)
api = worker.api
cache = worker.cache
commands = CommandHandler(worker, command_prefix="p!")
data = DataManager()


class SpeciesConverter(Converter):
    async def convert(self, ctx: Context, arg: str):
        if arg.startswith(("N", "n", "#")):
            try:
                species = data.species_by_number(int(arg[1:]))
            except ValueError:
                species = data.species_by_name(arg)
        else:
            species = data.species_by_name(arg)
        return species


def species_to_embed(species: Species):
    embed = poketwo.Embed(title=species.name)

    if species.description:
        embed.description = species.description.replace("\n", " ")

    if species.evolution_text:
        embed.add_field(name="Evolution", value=species.evolution_text, inline=False)

    base_stats = (
        f"**HP:** {species.base_stats.hp}",
        f"**Attack:** {species.base_stats.atk}",
        f"**Defense:** {species.base_stats.defn}",
        f"**Sp. Atk:** {species.base_stats.satk}",
        f"**Sp. Def:** {species.base_stats.sdef}",
        f"**Speed:** {species.base_stats.spd}",
    )
    embed.add_field(
        name="Names",
        value="\n".join(f"{lang} {name}" for lang, name in species.names),
        inline=False,
    )
    embed.add_field(name="Base Stats", value="\n".join(base_stats))
    embed.add_field(
        name="Appearance",
        value=f"Height: {species.height} m\nWeight: {species.weight} kg",
    )
    embed.add_field(name="Types", value="\n".join(species.types))
    embed.set_image(url=species.image_url)

    return embed


@worker.listen(CommandError)
async def on_command_error(event: CommandError):
    await event.ctx.reply(str(event.error))


@commands.command(aliases=("dex",))
async def pokedex(ctx: Context, *, species: SpeciesConverter):
    """Look up a pokémon species in the Pokédex."""

    await ctx.reply(embed=species_to_embed(species))


@commands.command()
async def ping(ctx: Context):
    message = await ctx.reply("Pong!")
    delta = message.timestamp - ctx.message.timestamp
    ms = int(delta.total_seconds() * 1000)
    await api.edit_message(message.channel_id, message.id, f"Pong! **{ms} ms**")


worker.run()
