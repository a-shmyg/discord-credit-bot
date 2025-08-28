import os
import re

import discord
from discord import app_commands
from dotenv import load_dotenv
from sqlalchemy import Column, Date, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# from models import User

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

client = discord.Client(intents=intents)

# Slash commands
tree = app_commands.CommandTree(client)
tree.copy_global_to(guild=GUILD)


# DB stuff - move out of this file when refactoring
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)  # TODO - change to UUID
    username = Column(String)
    feedback_credits = Column(Integer)
    submitted_stories_total = Column(Integer)
    read_stories_total = Column(Integer)
    wordcount_read_total = Column(Integer)

    def __repr__(self):
        return "<User(username='{}', feedback_credits='{}', submitted_stories_total='{}', read_stories_total={}, wordcount_read_total={}>".format(
            self.username,
            self.feedback_credits,
            self.submitted_stories_total,
            self.read_stories_total,
            self.wordcount_read_total
        )


def get_connection():
    return create_engine(
        url=f"postgresql://{DB_USER}:{DB_PASS}@localhost:5432/{DB_NAME}"
    )


def create_tables():
    print("Creating tables if they don't exist...")


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
    print("Initialising user info...")
    s = Session()

    # Basically, on startup if a user doesn't exist, we need to create them. Otherwise, we already have their info stored in DB
    for member in guild.members:
        member_username = str(member.name)
        print(f"Init for: {member_username}")

        print("Checking if user exists already...")
        result = s.query(User).filter_by(username=member_username).first()

        if not result:
            print("User doesn't exist in DB, creating...")

            # we're missing total wordcount but eh leave it for now
            user = User(
                username=member_username,
                feedback_credits=0,
                submitted_stories_total=0,
                read_stories_total=0,
                wordcount_read_total=0,
            )
            s.add(user)
            s.commit()

        else:
            print("User exists in DB, skipping")

    result = s.query(User).all()
    print(str(result))
    s.close()

    await tree.sync(guild=GUILD)

    print(f"We have logged in as {client.user} to {guild}")


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

            # This might be better in an actual function IMO
            print(f"Updating credits for {user_who_reacted}...")
            s.query(User).filter_by(username=str(user_who_reacted.name)).update(
                {
                    "feedback_credits": User.feedback_credits + 1,
                    "read_stories_total": User.read_stories_total + 1,
                    "wordcount_read_total": User.wordcount_read_total + story_wordcount
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

    s = Session()
    user_result = s.query(User).filter_by(username=str(interaction.user)).first()
    s.close()

    format_message = f""" {interaction.user.mention} server stats:
        Total credits: {user_result.feedback_credits}
        Total stories read: {user_result.read_stories_total}
        Total stories submitted: {submitted_stories} 
        Total words read (that we know of!): {user_result.wordcount_read_total}
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
