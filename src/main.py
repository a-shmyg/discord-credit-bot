import os

import discord
from discord import app_commands
from dotenv import load_dotenv
from sqlalchemy import (Column, Date, Integer, String, and_, create_engine,
                        exists)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from dao.models import Base, Story, User, WhoReadWhat
from util import (extract_embed_details, init_story_info, init_user_info,
                  is_google_link)

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
CHANNEL = int(os.getenv("DISCORD_TEST_CHANNEL_ID"))
CREDIT_REACT = "✅"


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
    return create_engine(url=f"postgresql://{DB_USER}:{DB_PASS}@localhost:5432/{DB_NAME}")


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
    channel_messages = channel.history()

    s = Session()

    # Mostly for testing - not super efficient to run on every startup
    init_user_info(guild.members, s)
    await init_story_info(channel_messages, s)

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
    if is_google_link(message.content):
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

    # Fetch the actual message content which was reacted to, because the payload contains only the ID
    message = await channel.fetch_message(payload.message_id)

    if is_google_link(message.content) and user_reacted_with == CREDIT_REACT:
        db_session = Session()
        story_details = extract_embed_details(message)

        # Super simple check to make sure people don't get credits for reading their own story lol
        if str(user_who_reacted.name) == str(message.author):
            print(f"{user_who_reacted} is author of {story_details["title"]}, skipping")
            return

        # Update the junction table - first check it doesn't exist (TODO - check ON_CONFLICT behaviour for sqlalchemy)
        print(f"Updating who read what table...")
        story_result = db_session.query(Story).filter_by(story_message=str(message.content)).first()

        who_read_what_result = db_session.query(
            exists().where(
                and_(
                    WhoReadWhat.username == str(user_who_reacted.name),
                    WhoReadWhat.story_id == story_result.id,
                )
            )
        ).scalar()

        if not who_read_what_result:
            print("Who read what entry doesn't exist in DB, adding...")
            who_read_story = WhoReadWhat(
                username=str(user_who_reacted.name),
                story_id=story_result.id,
            )

            db_session.add(who_read_story)
            db_session.commit()
        else:
            # This is simple way to make sure someone doesn't spam react :tick: -> remove -> react :tick: for infinite credit
            print(f"{user_who_reacted.name} already read {story_details["title"]}, skipping")
            db_session.close()
            return

        # Update credit info for the user who read the story
        print(f"Updating credits for {user_who_reacted}...")
        db_session.query(User).filter_by(username=str(user_who_reacted.name)).update(
            {
                "feedback_credits": User.feedback_credits + 1,
                "read_stories_total": User.read_stories_total + 1,
                "wordcount_read_total": User.wordcount_read_total + story_details["wordcount"],
            }
        )
        db_session.commit()
        db_session.close()

        await channel.send(
            f"{user_who_reacted.mention} has read **{story_details["title"]}** by {message.author.nick} and gets a feedback credit :coin:!"
        )


# Would be nicer as a hidden message or a DM to not clog up channel
@tree.command(
    name="credits",
    description="Get number of feedback credits",
    guild=GUILD,
)
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
    name="stats",
    description="Get user stats for posted stories",
    guild=GUILD,
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

# FOR TESTING ONLY -> to be removed
@tree.command(
    name="test_document",
    description="Make post a test story link in channel",
    guild=GUILD,
)
async def test_document(interaction):
    print(f"Sending test document on behalf of {interaction.user} who invoked me...")

    channel = client.get_channel(CHANNEL)

    await interaction.response.send_message("https://docs.google.com/document/d/1ZZ81lo1rQf8NX9xnlhCH3ihTONJdRASn00s1a5mdvp4/edit?usp=sharing")

# # TODO still because making polls is such a PITA every time
# @tree.command(
#     name="session", description="Create poll for new writing session", guild=GUILD
# )
# async def credits(interaction):
#     print(f"Creating poll for the {interaction.user} who invoked me...")

#     await interaction.response.send_message(f"New poll here (WIP)")


client.run(TOKEN)
