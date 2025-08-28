from sqlalchemy import Column, Date, Integer, String
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
            self.submitted_stories_total,
            self.read_stories_total,
            self.wordcount_read_total,
        )
