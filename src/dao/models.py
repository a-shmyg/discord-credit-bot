from sqlalchemy import Column, Date, Integer, String, Time
from sqlalchemy.ext.declarative import declarative_base

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
            self.submitted_stories_total, #remove this column, we don't need it
            self.read_stories_total,
            self.wordcount_read_total,
        )

class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True) # TODO - change to UUID
    author_username = Column(String)
    story_message = Column(String)
    date_posted = Column(Time)

    def __repr__(self):
        return "<Story(author_username='{}', story_message='{}', date_posted='{}'>".format(
            self.author_username,
            self.story_message,
            self.date_posted,
        )