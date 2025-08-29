import re

from sqlalchemy import and_, exists

from dao.models import Story, User, WhoReadWhat

GOOGLE_DOC_URL = "https://docs.google.com"
CREDIT_REACT = "✅"


# Super basic - we should switch to 'contains' instead in case anybody posts something before the link
def is_google_link(message_content):
    if message_content.startswith(GOOGLE_DOC_URL):
        return True
    else:
        return False


# Quite fragile with many assumptions, but a decent start for the refactor
def extract_embed_details(message):
    print("Attempting to extract title and wordcount from story message...")
    story_details = {
        "title": "an awesome story",
        "wordcount": 0,
    }

    if len(message.embeds) > 0:
        story_details["title"] = message.embeds[0].title

        wordcount = re.findall(r"\[(.*?)\]", story_details["title"])
        if len(wordcount) > 0:
            story_details["wordcount"] = int(wordcount[0])

    return story_details


# DB stuff, mostly for testing
# Probably not great to pass around DB session like this, but eh
def init_user_info(guild_members, db_session):
    print("Initialising user info...")

    for member in guild_members:
        member_username = str(member.name)
        print(f"Init for: {member_username}")

        result = db_session.query(User).filter_by(username=member_username).first()
        if not result:
            print("User doesn't exist in DB, creating...")

            user = User(
                username=member_username,
                feedback_credits=0,
                read_stories_total=0,
                wordcount_read_total=0,
            )
            db_session.add(user)
            db_session.commit()

        else:
            print("User exists in DB, skipping")


async def init_story_info(channel_messages, db_session):
    print("Initialising submitted story info...")

    async for message in channel_messages:
        # Populate DB with posted stories

        if is_google_link(message.content):
            story_result = db_session.query(Story).filter_by(story_message=str(message.content)).first()

            # Only add if story doesn't exist in DB already
            if not story_result:
                print("Story link/message doesn't exist in DB, adding...")
                story_details = extract_embed_details(message)

                story = Story(
                    author_username=str(message.author),
                    story_message=str(message.content),
                    title=str(story_details["title"]),
                    date_posted=str(message.created_at),
                )
                db_session.add(story)
                db_session.commit()
            else:
                print("Story exists in DB, skipping")

            # Populate DB with who read what stories
            print("Checking who read what...")
            reactions = message.reactions

            # Super jank, I'm sure there's a nicer way - need more reading about async stuff.
            # Doing it twice for now but I don't think we need to query again. Ceases to be an issue once we move this DB population out of on_ready logic
            story_result = db_session.query(Story).filter_by(story_message=str(message.content)).first()

            for reaction in reactions:
                if reaction.emoji == CREDIT_REACT:
                    async for user in reaction.users():
                        # Reconstructing who read what based on messages - will move this OUT of on_ready logic once I'm happy with table/querying
                        who_read_what_result = db_session.query(
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

                            db_session.add(who_read_story)
                            db_session.commit()
                        else:
                            print("Who read what already in DB, skipping")
