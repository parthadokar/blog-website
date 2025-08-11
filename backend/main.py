from fastapi import FastAPI,HTTPException,Depends
from pydantic import BaseModel
from datetime import datetime
from sqlmodel import Field,Session,SQLModel,create_engine,select
from typing import Annotated
from fastapi.middleware.cors import CORSMiddleware

class PostCreate(BaseModel):
    title: str
    description: str

class PostRead(BaseModel):
    id: int
    title: str
    description: str
    created_at: datetime

class PostUpdate(BaseModel):
    title: str | None = None
    description: str | None = None

class DeleteResponse(BaseModel):
    ok: bool

class Post(SQLModel,table=True):
    id: int = Field(primary_key=True,nullable=False)
    title: str = Field(index=True)
    description: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread":False}
engine = create_engine(sqlite_url,connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev, later restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

SessionDep = Annotated[Session, Depends(get_session)]

@app.post("/posts/",response_model=PostRead)
def create_post(post:PostCreate,session:SessionDep):
    db_post = Post(**post.dict())
    session.add(db_post)
    session.commit()
    session.refresh(db_post)
    return db_post

@app.get("/posts/",response_model=list[PostRead])
def read_posts(session:SessionDep):
    posts = session.exec(select(Post)).all()
    return posts

@app.get("/posts/{post_id}",response_model=PostRead)
def read_post(post_id:int,session:SessionDep):
    post = session.get(Post,post_id)
    if not post:
        raise HTTPException(status_code=404,detail="Post not found")
    return post

@app.put("/posts/{post_id}",response_model=PostRead)
def update_post(post_id:int,post_data:PostUpdate,session:SessionDep):
    post = session.get(Post,post_id)
    if not post:
        raise HTTPException(status_code=404,detail="Post not found")
    post_data_dict = post_data.dict(exclude_unset=True)
    for key, value in post_data_dict.items():
        setattr(post, key, value)

    session.add(post)
    session.commit()
    session.refresh(post)
    return post
    
@app.delete("/posts/{post_id}",response_model=DeleteResponse)
def delete_post(post_id:int,session:SessionDep):
    post = session.get(Post,post_id)
    if not post:
        raise HTTPException(status_code=404,detail="Post not found")
    session.delete(post)
    session.commit()
    return {"ok":True}
