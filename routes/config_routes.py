from flask import Blueprint, render_template, request, redirect, url_for, session
from models import db
from services.helpers import require_login, get_user_config
import re

config_bp = Blueprint('config', __name__)

def extract_subreddit_name(input_text):
    """Extract subreddit name from URL or return the name as-is"""
    input_text = input_text.strip()

    # Check if it's a Reddit URL
    reddit_url_pattern = r'(?:https?://)?(?:www\.)?reddit\.com/r/([a-zA-Z0-9_]+)'
    match = re.match(reddit_url_pattern, input_text)

    if match:
        return match.group(1)

    # Remove 'r/' prefix if present
    if input_text.startswith('r/'):
        return input_text[2:]

    # Return as-is (assume it's just the subreddit name)
    return input_text

@config_bp.route('/config')
@require_login
def config():
    """Configuration page"""
    user_id = session['user_id']
    config = get_user_config(user_id)

    # Default available subreddits
    available_subreddits = ['memes', 'dankmemes', 'wholesomememes', 'memeeconomy', 'prequelmemes']
    selected_subreddits = [s.strip() for s in config.subreddits.split(',') if s.strip()]

    return render_template('config.html',
                         config=config,
                         available_subreddits=available_subreddits,
                         selected_subreddits=selected_subreddits)

@config_bp.route('/update_config', methods=['POST'])
@require_login
def update_config():
    """Update user configuration"""
    user_id = session['user_id']
    config = get_user_config(user_id)

    # Update configuration
    config.max_memes = min(100, max(1, int(request.form.get('max_memes', 10))))

    # Handle subreddits
    selected_subreddits = request.form.getlist('subreddits')
    new_subreddit = request.form.get('new_subreddit', '').strip()

    if new_subreddit:
        # Extract subreddit name from URL or use as-is
        subreddit_name = extract_subreddit_name(new_subreddit)
        if subreddit_name and subreddit_name not in selected_subreddits:
            selected_subreddits.append(subreddit_name)

    # Clean up subreddit names (extract from URLs if needed)
    cleaned_subreddits = []
    for subreddit in selected_subreddits:
        cleaned_name = extract_subreddit_name(subreddit)
        if cleaned_name and cleaned_name not in cleaned_subreddits:
            cleaned_subreddits.append(cleaned_name)

    config.subreddits = ','.join(cleaned_subreddits) if cleaned_subreddits else 'memes'

    # Handle video/shorts preferences
    config.create_videos = 'create_videos' in request.form
    config.create_shorts = 'create_shorts' in request.form

    db.session.commit()

    return redirect(url_for('config.config'))
