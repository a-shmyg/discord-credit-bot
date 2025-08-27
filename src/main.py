import os
import re

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
CHANNEL = int(os.getenv("DISCORD_TEST_CHANNEL_ID"))
CREDIT_REACT = "✅"

# Following the slash command example here - https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py
GUILD = discord.Object(GUILD_ID)

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

client = discord.Client(intents=intents)

# Slash commands
tree = app_commands.CommandTree(client)
tree.copy_global_to(guild=GUILD)


# We'll need to add some kind of DB for state at some point, but for now:
user_credit_state = {}


# Discord.py stuff
@client.event
async def on_ready():
    guild = client.get_guild(GUILD_ID)
    channel = client.get_channel(CHANNEL)

    await tree.sync(guild=GUILD)

    # To do this properly we should think about how to model our data, and what relationships each piece of data has with each other
    # For a quick test though, this is good enough
    print("Initialising how much credit everybody's got")
    for member in guild.members:
        print(f"Init for: {member.name}")

        member_credit_state = {
            "feedback_credits": 0,
            "total_stories_read": 0,
            "total_words_read": 0,
        }

        # Not recommended usually, but until we get proper state set up it's fine
        global user_credit_state
        user_credit_state.update({member.name: member_credit_state})

    print(f"We have logged in as {client.user} to {guild}")


@client.event
async def on_raw_reaction_add(payload):
    guild = client.get_guild(GUILD_ID)
    channel = client.get_channel(CHANNEL)
    channel_of_react = payload.channel_id

    # Limiting this event to only single channel - ignore reactions from elsewhere for now
    if channel_of_react != CHANNEL:
        return

    user_who_reacted = guild.get_member(payload.user_id)
    user_reacted_with = payload.emoji.name
    message_id = payload.message_id

    # Fetch the actual message that got reacted to - naive solution for now, just looping over last 500 messages in channel
    channel_messages = channel.history(limit=500)

    async for message in channel_messages:
        # We only want to allow credit for google docs links (for now).
        # This is a SUPER basic check, probably better ways exist but good enough for now
        google_doc_url = "https://docs.google.com"
        story_title = "an awesome story"

        if (
            message.id == message_id
            and user_reacted_with == CREDIT_REACT
            and message.content.startswith(google_doc_url)
        ):
            print(
                f"{user_who_reacted} reacted to message. Content: {message.content}. React emoji: {user_reacted_with}"
            )

            # Relying on the embed is a hack - I want to avoid needing to touch Google API if at all possible
            # It's risky if someone decides to remove the embed off their story discord message, as we won't get the info we need
            # But it keeps the bot mega simple, so let's just add a simple fallback in case someone does remove the embed, and be happy

            if len(message.embeds) > 0:
                # Hell of an assumption, but fine for now - MVP etc etc
                google_doc_embed = message.embeds[0]
                story_title = google_doc_embed.title

                # This relies on someone putting wordcount into very specific format in the title, but whatevs
                story_words = re.findall(r'\[(.*?)\]', google_doc_embed.title)

            else:
                print("No embed for Google Doc so using fallback for title")

            # Temporary until we get DB/state set up
            print(f"Updating credits for {user_who_reacted}...")

            global user_credit_state
            current_user_credits = user_credit_state[user_who_reacted.name][
                "feedback_credits"
            ]
            user_credit_state[user_who_reacted.name]["feedback_credits"] = (
                current_user_credits + 1
            )

            current_user_stories_read = user_credit_state[user_who_reacted.name][
                "total_stories_read"
            ]
            user_credit_state[user_who_reacted.name]["total_stories_read"] = (
                current_user_stories_read + 1
            )

            # Fragile as hell, if someone puts a non-number between the brackets like [Lol] in the title, this will break
            if len(story_words) > 0:
                print("Estimating wordcount from title...")

                current_user_words_read = user_credit_state[user_who_reacted.name][
                    "total_words_read"
                ]
                user_credit_state[user_who_reacted.name]["total_words_read"] = (
                    current_user_words_read + int(story_words[0])
                )

            await channel.send(
                f"{user_who_reacted} has read {story_title} and gets a feedback credit!"
            )
            return


# Would be nicer as a hidden message or a DM to not clog up channel
@tree.command(name="credits", description="Get number of feedback credits", guild=GUILD)
async def credits(interaction):
    print(f"Getting credit info for the {interaction.user} who invoked me...")
    user_credits = user_credit_state[str(interaction.user)]["feedback_credits"]

    await interaction.response.send_message(
        f"{interaction.user.mention} has {user_credits} feedback credits to use"
    )


@tree.command(
    name="stats", description="Get user stats for posted stories", guild=GUILD
)
async def stats(interaction):
    print(f"Getting stats for the {interaction.user} who invoked me...")

    channel = client.get_channel(CHANNEL)
    channel_messages = channel.history()
    user_name = str(interaction.user)

    # More efficient to just update values from a DB than trawling through entire channel history, but keeping it simple for now
    submitted_stories = 0
    async for message in channel_messages:
        google_doc_url = "https://docs.google.com"

        if str(message.author) == user_name and message.content.startswith(
            google_doc_url
        ):
            submitted_stories = submitted_stories + 1

    stories_read = user_credit_state[user_name]["total_stories_read"]
    words_read = user_credit_state[user_name]["total_words_read"]

    format_message = f""" {interaction.user.mention} server stats:
        Total stories read: {stories_read}
        Total stories submitted: {submitted_stories} 
        Total words read (that we know of!): {words_read}
    """

    await interaction.response.send_message(format_message)


client.run(TOKEN)
