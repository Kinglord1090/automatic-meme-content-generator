from flask_sqlalchemy import SQLAlchemy

# This will be initialized in app.py
db = SQLAlchemy()

class User(db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

class Meme(db.Model):
    """Meme model for storing meme data"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)  # Original Reddit URL
    image_path = db.Column(db.String(500))  # Local image file path
    text = db.Column(db.Text)
    subreddit = db.Column(db.String(100), nullable=False)  # Source subreddit
    discarded = db.Column(db.Boolean, default=False)

    # Audio storage
    audio_path = db.Column(db.String(500))  # Local audio file path

    # Workflow status tracking
    text_approved = db.Column(db.Boolean, default=False)  # Text phase approval
    audio_approved = db.Column(db.Boolean, default=False)  # Audio phase approval
    video_generated = db.Column(db.Boolean, default=False)  # Video generation status (legacy)

    # Video type tracking
    used_in_regular_video = db.Column(db.Boolean, default=False)  # Used in 16:9 videos
    used_in_shorts_video = db.Column(db.Boolean, default=False)   # Used in 9:16 shorts

    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Configuration(db.Model):
    """Configuration model for user settings"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    max_memes = db.Column(db.Integer, default=10)
    subreddits = db.Column(db.Text, default='memes')
    create_videos = db.Column(db.Boolean, default=True)  # Whether to create regular videos
    create_shorts = db.Column(db.Boolean, default=False)  # Whether to create shorts

class GeneratedVideo(db.Model):
    """Model for tracking generated videos"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_path = db.Column(db.String(500), nullable=False)  # Path to video file
    video_type = db.Column(db.String(20), nullable=False)  # 'regular' or 'shorts'
    duration = db.Column(db.Float, nullable=False)  # Duration in seconds
    memes_count = db.Column(db.Integer, nullable=False)  # Number of memes used
    meme_ids = db.Column(db.Text)  # JSON string of meme IDs used in this video
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())


