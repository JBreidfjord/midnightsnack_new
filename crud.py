from sqlalchemy import select, delete, update, insert
from sqlalchemy.orm import Session
from sqlalchemy.exc import DataError, IntegrityError
from models import User, Post, Tag, tag_assoc_table
from typing import List
from pathlib import Path
import schema, shutil


# Post
def tag_handler(db: Session, tags: List[Tag], post: Post):
    for tag in tags:
        tag_obj = db.execute(select(Tag).where(Tag.name == tag.name)).scalar()
        if not tag_obj:
            tag.posts.append(post)
            db.add(tag)
            db.commit()
        else:
            tag_id = db.execute(select(Tag.id).where(Tag.name == tag.name)).scalar()
            post_id = db.execute(select(Post.id).where(Post.title == post.title)).scalar()
            try:
                db.execute(insert(tag_assoc_table).values(post_id=post_id, tag_id=tag_id))
                db.commit()
            except IntegrityError:
                db.rollback()
    old_tags = db.execute(select(Post).where(Post.id == post_id)).scalar().tags
    tag_names = [tag.name for tag in tags]
    for old_tag in old_tags:
        if old_tag.name not in tag_names:
            db.execute(delete(tag_assoc_table).where(Post.id == post_id).where(Tag.id == old_tag.id))
            db.commit()


def create_post(db: Session, post: schema.PostCreate, tags: List[Tag]):
    '''
    Creates an instance of the Post class, taking the database session and post info defined by the schema as inputs
    Tags must be a list of Tag objects
    '''
    obj = Post(**post)
    db.add(obj)
    db.commit()
    tag_handler(db=db, tags=tags, post=obj)
    return obj

def get_all_posts(db: Session):
    return db.execute(select(Post)).scalars()

def get_post(db: Session, slug: str = None, post_id: int = None):
    # split this to 2 functions
    # this one should just return the post object
    # the other will return the data dict, calling this one for the post object
    # could probably eliminate the if/elif block this way too
    if slug:
        obj = db.execute(select(Post).where(Post.slug == slug)).scalar()
    elif post_id:
        obj = db.execute(select(Post).where(Post.id == post_id)).scalar()
        slug = obj.slug
    if not obj:
        return None
    content_path = Path(f'./static/posts/{slug}/')
    for file in content_path.iterdir():
        if 'headerImage' in file.name:
            img = str(Path(*file.parts[1:]))
        if '.html' in file.name:
            article = file
    return {'post_obj': obj, 'img_path': img, 'article_path': article, 'content_path': content_path}

def del_post(db: Session, slug: str):
    db.execute(delete(Post).where(Post.slug == slug))
    db.commit()
    shutil.rmtree(Path(f'./static/posts/{slug}'))

def edit_post(db: Session, post_id: int, data: dict, tags: List[Tag]):
    db.execute(update(Post).where(Post.id == post_id).values(**data))
    db.commit()

    post = db.execute(select(Post).where(Post.id == post_id)).scalar()
    tag_handler(db=db, tags=tags, post=post)

# Tags
def create_tag(db: Session, tags: List[str]):
    tag_objs = []
    for tag in tags:
        try:
            obj = Tag(name=tag)
            db.add(obj)
            db.commit()
            obj.append(tag_objs)
        except IntegrityError:
            pass
    return tag_objs

# User
def get_user(db: Session, username: str):
    return db.execute(select(User).where(User.username == username)).scalar()