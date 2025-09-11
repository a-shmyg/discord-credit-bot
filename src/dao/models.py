from sqlalchemy import Column, Date, ForeignKey, Integer, String, Time
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    # id = Column(Integer, primary_key=True)  # TODO - remove, discord guarantees unique usernames
    username = Column(String, primary_key=True)
    feedback_credits = Column(Integer)
    read_stories_total = Column(Integer)
    wordcount_read_total = Column(Integer)

    def __repr__(self):
        return "<User(username='{}', feedback_credits='{}', read_stories_total={}, wordcount_read_total={}>".format(
            self.username,
            self.feedback_credits,
            self.read_stories_total,
            self.wordcount_read_total,
        )


# TODO - add a title column
class Story(Base):
    __tablename__ = "stories"

    # TODO - look into making message ID the primary key, maybe (so long as it will never change on discord end)
    id = Column(Integer, primary_key=True)  # TODO - change to UUID
    author_username = Column(String)
    story_message = Column(String)
    story_message_id = Column(String)
    title = Column(String)
    date_posted = Column(Time)

    def __repr__(self):
        return "<Story(author_username='{}', story_message='{}', story_message_id='{}' title='{}', date_posted='{}'>".format(
            self.author_username,
            self.story_message, #or just use filename for message content for now lol, KISS
            self.story_message_id,
            self.title,
            self.date_posted,
        )

# Terrible table name but whatever, this is for fun
class WhoReadWhat(Base):
    __tablename__ = "who_read_what"

    # Read up on composite primary keys -> this is basically what this is, it's more efficient
    username = Column(
        String,
        ForeignKey(User.username),
        primary_key=True,
    )
    story_id = Column(
        Integer,
        ForeignKey(Story.id),
        primary_key=True,
    )

    def __repr__(self):
        return "<Story(username='{}', story_id='{}'>".format(
            self.username,
            self.story_id,
        )
