from db.database import engine
from models.task import Task
from models.user import User


def create_tables():
    User.metadata.create_all(bind=engine)
    Task.metadata.create_all(bind=engine)