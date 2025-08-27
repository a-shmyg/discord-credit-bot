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
intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    guild = client.get_guild(GUILD)
    channel = client.get_channel(CHANNEL)

    print(f'We have logged in as {client.user} to {guild}')

@client.event
async def on_raw_reaction_add(payload):
    guild = client.get_guild(GUILD)
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


        if message.id == message_id and user_reacted_with == CREDIT_REACT and message.content.startswith(google_doc_url):
            print(f"{user_who_reacted} reacted to message. Content: {message.content}. React emoji: {user_reacted_with}")
            
            # Relying on the embed is a hack - I want to avoid needing to touch Google API if at all possible
            # It's risky if someone decides to remove the embed off their story discord message, as we won't get the info we need
            # But it keeps the bot mega simple, so let's just add a simple fallback in case someone does remove the embed, and be happy
            
            if len(message.embeds) > 0:
                # Hell of an assumption, but fine for now - MVP etc etc
                google_doc_embed = message.embeds[0]
                story_title = google_doc_embed.title
                
            else:
                print("No embed for google doc so using fallback for title")


            await channel.send(f"{user_who_reacted} has read {story_title} and gets a feedback credit!")
            return

client.run(TOKEN)
