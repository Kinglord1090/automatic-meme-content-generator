from flask import Blueprint, render_template, session
from models import Meme, GeneratedVideo
from services.helpers import require_login
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@require_login
def dashboard():
    """Main dashboard page with workflow statistics"""
    user_id = session['user_id']

    # Calculate workflow statistics
    stats = {}

    # Total memes fetched
    stats['total_memes'] = Meme.query.filter_by(user_id=user_id, discarded=False).count()

    # Workflow stage statistics
    stats['memes_pending_text'] = Meme.query.filter_by(
        user_id=user_id, discarded=False, text_approved=False
    ).count()

    stats['memes_text_approved'] = Meme.query.filter_by(
        user_id=user_id, discarded=False, text_approved=True
    ).count()

    stats['memes_pending_audio'] = Meme.query.filter_by(
        user_id=user_id, discarded=False, text_approved=True, audio_approved=False
    ).filter((Meme.text != None) & (Meme.text != '')).count()

    stats['memes_audio_approved'] = Meme.query.filter_by(
        user_id=user_id, discarded=False, audio_approved=True
    ).count()

    # Memes without text (will create image-only videos)
    stats['memes_without_text'] = Meme.query.filter_by(user_id=user_id, discarded=False).filter(
        (Meme.text == None) | (Meme.text == '')
    ).count()

    # Memes with text (will create videos with audio)
    stats['memes_with_text'] = Meme.query.filter_by(user_id=user_id, discarded=False).filter(
        (Meme.text != None) & (Meme.text != '')
    ).count()

    # Video generation statistics
    stats['memes_ready_for_video'] = Meme.query.filter_by(
        user_id=user_id, discarded=False, text_approved=True, audio_approved=True, video_generated=False
    ).count()

    stats['memes_video_generated'] = Meme.query.filter_by(
        user_id=user_id, discarded=False, video_generated=True
    ).count()

    # Generated videos count
    stats['total_videos'] = GeneratedVideo.query.filter_by(user_id=user_id).count()
    stats['regular_videos'] = GeneratedVideo.query.filter_by(user_id=user_id, video_type='regular').count()
    stats['shorts_videos'] = GeneratedVideo.query.filter_by(user_id=user_id, video_type='shorts').count()

    # Discarded content
    stats['discarded_memes'] = Meme.query.filter_by(user_id=user_id, discarded=True).count()

    # Recent activity - memes added today
    from datetime import datetime
    today = datetime.now().date()
    stats['memes_today'] = Meme.query.filter_by(user_id=user_id, discarded=False).filter(
        func.date(Meme.created_at) == today
    ).count()

    # Subreddit breakdown
    subreddit_stats = {}
    memes_by_subreddit = Meme.query.filter_by(user_id=user_id, discarded=False).all()
    for meme in memes_by_subreddit:
        if meme.subreddit not in subreddit_stats:
            subreddit_stats[meme.subreddit] = {
                'total': 0, 'text_approved': 0, 'audio_approved': 0
            }
        subreddit_stats[meme.subreddit]['total'] += 1
        if meme.text_approved:
            subreddit_stats[meme.subreddit]['text_approved'] += 1
        if meme.audio_approved:
            subreddit_stats[meme.subreddit]['audio_approved'] += 1

    stats['subreddit_stats'] = subreddit_stats

    return render_template('dashboard.html', stats=stats)
