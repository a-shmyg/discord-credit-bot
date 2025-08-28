import os
import re

import discord
from discord import app_commands
from dotenv import load_dotenv
from sqlalchemy import (Column, Date, Integer, String, and_, create_engine,
                        exists)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from dao.models import Base, Story, User, WhoReadWhat

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
CHANNEL = int(os.getenv("DISCORD_TEST_CHANNEL_ID"))
CREDIT_REACT = "✅"
GOOGLE_DOC_URL = "https://docs.google.com"

# TODO - organise the code so it's not all in one massive file
DB_USER = os.getenv("POSTGRES_USER")
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")


# Following the slash command example here - https://github.com/Rapptz/discord.py/blob/master/examples/app_commands/basic.py
GUILD = discord.Object(GUILD_ID)

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True
intents.messages = True

client = discord.Client(intents=intents)

# Slash commands
tree = app_commands.CommandTree(client)
tree.copy_global_to(guild=GUILD)


# DB stuff - TODO to also move this out of here later
def get_connection():
    return create_engine(
        url=f"postgresql://{DB_USER}:{DB_PASS}@localhost:5432/{DB_NAME}"
    )


try:
    print("Connecting to DB via SQLAlchemy")
    engine = get_connection()

    print("Creating tables")
    Base.metadata.create_all(engine)
except Exception as e:
    print("Something went wrong: ", e)

Session = sessionmaker(bind=engine)


# Discord.py stuff
@client.event
async def on_ready():
    guild = client.get_guild(GUILD_ID)
    channel = client.get_channel(CHANNEL)

    # TODO - take the DB parts out of the main logic
    s = Session()

    # Basically, on startup if a user doesn't exist, we need to create them. Otherwise, we already have their info stored in DB
    print("Initialising user info...")
    for member in guild.members:
        member_username = str(member.name)
        print(f"Init for: {member_username}")

        result = s.query(User).filter_by(username=member_username).first()

        if not result:
            print("User doesn't exist in DB, creating...")

            user = User(
                username=member_username,
                feedback_credits=0,
                read_stories_total=0,
                wordcount_read_total=0,
            )
            s.add(user)
            s.commit()

        else:
            print("User exists in DB, skipping")

    # Do the same for posted stories. TODO - move this out of main logic. Also, if channel is large the startup will take a lot of time. Better make seperate function for this
    print("Initialising submitted story info...")
    google_doc_url = "https://docs.google.com"  # REALLY need to move this check out into a function or something
    channel_messages = channel.history()

    async for message in channel_messages:
        if message.content.startswith(google_doc_url):
            # Add unique stories to the DB if they're not in there already. Like said above, we need to move this out of the startup logic

            # TODO - on conflict do nothing. Try to insert anyway, if it exists then whatevs. otherwise we're doing SELECT twice.
            story_result = (
                s.query(Story).filter_by(story_message=str(message.content)).first()
            )

            # Only add if story doesn't exist in DB already
            if not story_result:
                print("Story link/message doesn't exist in DB, adding...")

                story = Story(
                    author_username=str(message.author),
                    story_message=str(message.content),
                    date_posted=str(message.created_at),
                )
                s.add(story)
                s.commit()
            else:
                print("Story exists in DB, skipping")

            # This bit is the junction table - for now it's at startup (so checks previous reacts) but TODO to move it out of here after testing
            print("Checking who read what...")
            reactions = message.reactions

            # Super jank, I'm sure there's a nicer way - need more reading about async stuff.
            # Doing it twice for now but I don't think we need to query again. Ceases to be an issue once we move this DB population out of on_ready logic
            story_result = (
                s.query(Story).filter_by(story_message=str(message.content)).first()
            )

            for reaction in reactions:
                if reaction.emoji == CREDIT_REACT:
                    async for user in reaction.users():
                        # Reconstructing who read what based on messages - will move this OUT of on_ready logic once I'm happy with table/querying
                        who_read_what_result = s.query(
                            exists().where(
                                and_(
                                    WhoReadWhat.username == str(user.name),
                                    WhoReadWhat.story_id == story_result.id,
                                )
                            )
                        ).scalar()

                        if not who_read_what_result:
                            # What we're doing here - we need user id of who READ the story AKA author of the REACTION (not the message)
                            print("Who read what entry doesn't exist in DB, adding...")
                            who_read_story = WhoReadWhat(
                                username=str(user.name),
                                story_id=story_result.id,
                            )

                            s.add(who_read_story)
                            s.commit()
                        else:
                            print("Who read what already in DB, skipping")

    s.close()

    # Sync up the slash commands
    await tree.sync(guild=GUILD)

    print(f"We have logged in as {client.user} to {guild}")


@client.event
async def on_message(message):
    guild = client.get_guild(GUILD_ID)
    channel = client.get_channel(CHANNEL)
    channel_of_message = message.channel

    # Limiting this event to only single channel - ignore messages from elsewhere for now. Probs nicer way to do this, one to look into
    if channel_of_message != channel:
        return

    # Super basic check, for now assuming if person posts a doc link in the channel, they're posting a story
    google_doc_url = "https://docs.google.com"
    if message.content.startswith(
        google_doc_url
    ):  # TODO - change to contains... if someone posts message AND adds a link, this won't work
        print(f"{message.author} posted a new story")

        s = Session()

        # Only add if story doesn't exist in DB already
        result = s.query(Story).filter_by(story_message=str(message.content)).first()
        if not result:
            print("Story link/message doesn't exist in DB, adding...")
            story = Story(
                author_username=str(message.author),
                story_message=str(message.content),
                date_posted=str(message.created_at),
            )
            s.add(story)
            s.commit()

        s.close()

# TODO - check for if someone's already read same story
# ALSO - check for if someone's trying to get feedback credits from their own story, lol
@client.event
async def on_raw_reaction_add(payload):
    guild = client.get_guild(GUILD_ID)
    channel = client.get_channel(CHANNEL)
    channel_of_react = payload.channel_id

    # Session for our DB interactions
    s = Session()

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
        story_wordcount = 0

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
                story_words = re.findall(r"\[(.*?)\]", google_doc_embed.title)

                # Horrible, don't do this IRL lol
                if len(story_words) == 1:
                    story_wordcount = int(story_words[0])

            else:
                print("No embed for Google Doc so using fallback for title")

            # This bit tracks who read what - we're just updating in DB whenever somebody does :tick: emoji
            # TODO move this out of here lol it's a mess RN
            print("Updating junction table to track who read what...")

            story_result = (
                s.query(Story).filter_by(story_message=str(message.content)).first()
            )

            who_read_what_result = s.query(
                exists().where(
                    and_(
                        WhoReadWhat.username == str(user_who_reacted.name),
                        WhoReadWhat.story_id == story_result.id,
                    )
                )
            ).scalar()

            if not who_read_what_result:
                # What we're doing here - we need user id of who READ the story AKA author of the REACTION (not the message)
                print("Who read what entry doesn't exist in DB, adding...")
                who_read_story = WhoReadWhat(
                    username=str(user_who_reacted.name),
                    story_id=story_result.id,
                )

                s.add(who_read_story)
                s.commit()
            else:
                print("Who read what already in DB, skipping")

            # TODO - move this out into functions in dao folder
            print(f"Updating credits for {user_who_reacted}...")
            s.query(User).filter_by(username=str(user_who_reacted.name)).update(
                {
                    "feedback_credits": User.feedback_credits + 1,
                    "read_stories_total": User.read_stories_total + 1,
                    "wordcount_read_total": User.wordcount_read_total + story_wordcount,
                }
            )
            s.commit()
            user_result = (
                s.query(User).filter_by(username=str(user_who_reacted.name)).first()
            )
            s.close()
            print(user_result)

            await channel.send(
                f"{user_who_reacted.mention} has read **{story_title}** by {message.author.nick} and gets a feedback credit :coin:!"
            )

            return


# Would be nicer as a hidden message or a DM to not clog up channel
@tree.command(name="credits", description="Get number of feedback credits", guild=GUILD)
async def credits(interaction):
    print(f"Getting credit info for the {interaction.user} who invoked me...")

    s = Session()
    user_result = s.query(User).filter_by(username=str(interaction.user)).first()
    user_credits = user_result.feedback_credits
    s.close()

    await interaction.response.send_message(
        f"{interaction.user.mention} has {user_credits} feedback credits to use :fire:"
    )


@tree.command(
    name="stats", description="Get user stats for posted stories", guild=GUILD
)
async def stats(interaction):
    print(f"Getting stats for the {interaction.user} who invoked me...")

    channel = client.get_channel(CHANNEL)
    username = str(interaction.user)

    s = Session()
    user_submitted_stories = s.query(Story).filter_by(author_username=username).count()
    user_stats = s.query(User).filter_by(username=str(interaction.user)).first()
    s.close()

    format_message = f""" {interaction.user.mention} server stats:
        Total credits: {user_stats.feedback_credits}
        Total stories read: {user_stats.read_stories_total}
        Total stories submitted: {str(user_submitted_stories)} 
        Total words read (that we know of!): {user_stats.wordcount_read_total}
    """

    await interaction.response.send_message(format_message)


# # TODO still because making polls is such a PITA every time
# @tree.command(
#     name="session", description="Create poll for new writing session", guild=GUILD
# )
# async def credits(interaction):
#     print(f"Creating poll for the {interaction.user} who invoked me...")

#     await interaction.response.send_message(f"New poll here (WIP)")


client.run(TOKEN)
