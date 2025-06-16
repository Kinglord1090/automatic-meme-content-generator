from functools import wraps
from flask import session, redirect, url_for
from models import Configuration, Meme, db
import requests
import os
import uuid

def require_login(f):
    """Decorator to require user login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_user_config(user_id):
    """Get user configuration or create default"""
    config = Configuration.query.filter_by(user_id=user_id).first()
    if not config:
        config = Configuration(user_id=user_id)
        db.session.add(config)
        db.session.commit()
    return config

def download_image(url, save_path):
    """Download image from URL and save locally"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception:
        return False

def save_meme_to_db(user_id, url, text="", subreddit="memes"):
    """Save meme to database and download image locally"""
    # Check for existing meme with same URL to prevent duplicates
    existing_meme = Meme.query.filter_by(user_id=user_id, url=url).first()
    if existing_meme:
        return existing_meme

    # Create unique filename for the image
    file_extension = url.split('.')[-1].lower()
    if file_extension not in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        file_extension = 'jpg'

    image_filename = f"meme_{uuid.uuid4().hex[:8]}.{file_extension}"
    image_path = os.path.join('static', 'images', image_filename)

    # Ensure images directory exists
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    # Download image
    image_downloaded = download_image(url, image_path)

    # Save meme to database
    meme = Meme(
        user_id=user_id,
        url=url,
        text=text,
        subreddit=subreddit,
        image_path=image_path if image_downloaded else None
    )
    db.session.add(meme)
    db.session.commit()
    return meme
