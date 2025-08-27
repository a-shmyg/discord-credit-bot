import os

import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD = int(os.getenv("DISCORD_GUILD_ID"))
CHANNEL = int(os.getenv("DISCORD_TEST_CHANNEL_ID"))
CREDIT_REACT = "✅"

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    guild = client.get_guild(GUILD)
    channel = client.get_channel(CHANNEL)

    print(f'We have logged in as {client.user} to {guild}')

@client.event
async def on_raw_reaction_add(payload):
    channel = client.get_channel(CHANNEL)
    channel_of_react = payload.channel_id

    # Limiting this event to only single channel - ignore reactions from elsewhere for now
    if channel_of_react != CHANNEL:
        print("Wrong channel, ignoring")
        return
    
    print(f'Reaction event triggered in archive channel')

    user_who_reacted = payload.user_id
    user_reacted_with = payload.emoji.name
    message_id = payload.message_id

    # Fetch the actual message that got reacted to - naive solution for now, just looping over last 500 messages in channel
    channel_messages = channel.history(limit=500)

    async for message in channel_messages:
        # We only want to allow credit for google docs links (for now).
        # This is a SUPER basic check, probably better ways exist but good enough for now
        google_doc_url = "https://docs.google.com"

        if message.id == message_id and user_reacted_with == CREDIT_REACT and message.content.startswith(google_doc_url):
            print(f"User reacted to message. Content: {message.content}. React emoji: {user_reacted_with}")
            
            await channel.send("Someone just reacted to a GOOGLE DOC link with a GREEN TICK emoji!")
            return

client.run(TOKEN)
