from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from models.user import User as UserModel
from schemas.user import CreateUser


def create_user(new_user: CreateUser, db: Session = Depends(get_db)):
    db_user = UserModel(
        id=new_user.id,
        given_name=new_user.given_name,
        family_name=new_user.family_name,
        username=new_user.username,
        email=new_user.email,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def get_user_by_username(username: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user