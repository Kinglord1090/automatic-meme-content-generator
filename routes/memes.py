from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from models import Meme, GeneratedVideo, db
from services.helpers import require_login, get_user_config, save_meme_to_db
from services.reddit_service import get_top_memes

memes_bp = Blueprint('memes', __name__)

def auto_approve_textless_memes(user_id):
    """Auto-approve textless memes for audio phase since they don't need audio generation"""
    textless_memes = Meme.query.filter_by(
        user_id=user_id,
        discarded=False,
        text_approved=True,
        audio_approved=False
    ).filter(db.or_(Meme.text == None, Meme.text == '')).all()

    for meme in textless_memes:
        meme.audio_approved = True

    if textless_memes:
        db.session.commit()
        return len(textless_memes)
    return 0

@memes_bp.route('/fetch_memes')
@require_login
def fetch_memes():
    """Fetch memes from Reddit"""
    user_id = session['user_id']
    config = get_user_config(user_id)

    # Parse subreddits from config
    subreddits = [s.strip() for s in config.subreddits.split(',') if s.strip()]

    try:
        # Get existing meme URLs to avoid duplicates
        existing_urls = set(meme.url for meme in Meme.query.filter_by(user_id=user_id, discarded=False).all())

        # Fetch memes from Reddit with existing URLs for duplicate detection
        reddit_memes = get_top_memes(limit=config.max_memes, subreddits=subreddits, existing_urls=existing_urls)

        if not reddit_memes:
            session['flash_message'] = "No memes could be fetched from Reddit. Please check your internet connection and try again."
            return redirect(url_for('memes.meme_workshop'))

        new_memes_count = 0
        error_count = 0

        for meme_info in reddit_memes:
            try:
                meme_url = meme_info.get('url', '')

                if not meme_url:
                    error_count += 1
                    continue

                # Save new meme to database with subreddit information
                # No need to check for duplicates here since Reddit service already filtered them
                save_meme_to_db(user_id, meme_url, "", meme_info.get('subreddit', 'memes'))
                new_memes_count += 1

            except Exception:
                error_count += 1
                continue

        # Set flash message for user feedback - only show if there are issues
        if new_memes_count == 0:
            session['flash_message'] = "No new memes could be fetched. They may all be duplicates or there might be a connection issue."

        session['flash_context'] = ['meme_workshop']

    except Exception as e:
        session['flash_message'] = f"Error fetching memes: {str(e)}"
        session['flash_context'] = ['meme_workshop']

    return redirect(url_for('memes.meme_workshop'))

@memes_bp.route('/clear_memes', methods=['GET', 'POST'])
@require_login
def clear_memes():
    """Clear all existing memes for the user"""
    user_id = session['user_id']

    try:
        # Count memes before deletion
        meme_count = Meme.query.filter_by(user_id=user_id, discarded=False).count()

        # Clear existing memes for this user
        Meme.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        # Clear audio session data
        audio_keys_to_remove = [key for key in session.keys() if key.startswith('audio_path_')]
        for key in audio_keys_to_remove:
            session.pop(key, None)

        session['flash_message'] = f"Cleared {meme_count} memes from your collection."
        session['flash_context'] = ['meme_workshop']

    except Exception as e:
        session['flash_message'] = f"Error clearing memes: {str(e)}"
        session['flash_context'] = ['meme_workshop']

    return redirect(url_for('memes.meme_workshop'))

@memes_bp.route('/clear_all_data', methods=['POST'])
@require_login
def clear_all_data():
    """Clear all meme data but preserve user settings"""
    try:
        # Clear all memes
        Meme.query.delete()

        # Note: We no longer clear configurations to preserve user's subreddit settings
        # The user can manually reset their settings in the config page if needed

        db.session.commit()

        # Clear all session data except user_id
        user_id = session.get('user_id')
        session.clear()
        session['user_id'] = user_id

        session['flash_message'] = "All meme data cleared successfully."
        session['flash_context'] = ['dashboard']

    except Exception as e:
        db.session.rollback()
        session['flash_message'] = f"Error clearing data: {str(e)}"
        session['flash_context'] = ['dashboard']

    return redirect(url_for('dashboard.dashboard'))

@memes_bp.route('/meme_workshop')
@require_login
def meme_workshop():
    """Meme Workshop - Combined fetching and editing interface"""
    return render_template('meme_workshop.html')

@memes_bp.route('/review_memes')
@require_login
def review_memes():
    """Review and edit memes - organized by subreddit (only non-approved memes)"""
    user_id = session['user_id']
    # Only show memes that haven't been approved for text yet
    memes = Meme.query.filter_by(user_id=user_id, discarded=False, text_approved=False).all()

    # Group memes by subreddit
    memes_by_subreddit = {}
    for meme in memes:
        if meme.subreddit not in memes_by_subreddit:
            memes_by_subreddit[meme.subreddit] = []
        memes_by_subreddit[meme.subreddit].append(meme)

    return render_template('review_memes.html', memes_by_subreddit=memes_by_subreddit)

@memes_bp.route('/update_meme_text', methods=['POST'])
@require_login
def update_meme_text():
    """Update meme text and clear any existing audio"""
    import os

    user_id = session['user_id']
    meme_id = request.form.get('meme_id')
    new_text = request.form.get('text', '')

    meme = Meme.query.filter_by(id=meme_id, user_id=user_id).first()
    if meme:
        # Check if text actually changed
        text_changed = meme.text != new_text

        meme.text = new_text

        # If text changed, clear any existing audio and reset audio approval
        if text_changed:
            # Clear audio session data
            audio_key = f'audio_path_{meme.id}'
            if audio_key in session:
                # Try to delete the old audio file
                old_audio_path = session[audio_key]
                try:
                    if os.path.exists(old_audio_path):
                        os.remove(old_audio_path)
                except Exception:
                    pass  # Ignore file deletion errors

                # Remove from session
                session.pop(audio_key, None)

            # Reset audio approval since text changed
            meme.audio_approved = False

        db.session.commit()

    return redirect(url_for('memes.review_memes'))

@memes_bp.route('/discard_meme', methods=['POST'])
@require_login
def discard_meme():
    """Discard a meme via AJAX"""
    user_id = session['user_id']
    meme_id = request.form.get('meme_id')

    meme = Meme.query.filter_by(id=meme_id, user_id=user_id).first()
    if meme:
        meme.discarded = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Meme discarded successfully'})
    else:
        return jsonify({'success': False, 'message': 'Meme not found'}), 404

@memes_bp.route('/approve_meme_text', methods=['POST'])
@require_login
def approve_meme_text():
    """Save text and approve meme for text phase in one action via AJAX"""
    import os

    user_id = session['user_id']
    meme_id = request.form.get('meme_id')
    new_text = request.form.get('text', '')

    meme = Meme.query.filter_by(id=meme_id, user_id=user_id).first()
    if meme:
        # Check if text actually changed
        text_changed = meme.text != new_text

        # Save text and approve in one action
        meme.text = new_text
        meme.text_approved = True

        # If text changed, clear any existing audio and reset audio approval
        if text_changed:
            # Clear audio from both database and session
            old_audio_path = meme.audio_path or session.get(f'audio_path_{meme.id}')

            if old_audio_path:
                # Try to delete the old audio file
                try:
                    if os.path.exists(old_audio_path):
                        os.remove(old_audio_path)
                except Exception:
                    pass  # Ignore file deletion errors

            # Clear from database and session
            meme.audio_path = None
            session.pop(f'audio_path_{meme.id}', None)

            # Reset audio approval since text changed
            meme.audio_approved = False

        db.session.commit()

        # Auto-approve textless memes for audio phase
        auto_approve_textless_memes(user_id)

        return jsonify({'success': True, 'message': 'Meme approved successfully'})
    else:
        return jsonify({'success': False, 'message': 'Meme not found'}), 404



@memes_bp.route('/audio_workshop')
@require_login
def audio_workshop():
    """Audio Workshop - Show memes approved for audio generation"""
    import os

    user_id = session['user_id']

    # Automatically clean up stale audio session data
    audio_keys_to_remove = []
    for key in list(session.keys()):
        if key.startswith('audio_path_'):
            audio_path = session[key]
            # Remove session entry if file doesn't exist
            if not os.path.exists(audio_path):
                audio_keys_to_remove.append(key)

    for key in audio_keys_to_remove:
        session.pop(key, None)

    # Auto-approve textless memes for audio phase (they don't need audio generation)
    auto_approve_textless_memes(user_id)

    # Get memes that are approved for text but not yet processed for audio
    # Only include memes that have text content for audio generation
    memes = Meme.query.filter_by(
        user_id=user_id,
        discarded=False,
        text_approved=True,
        audio_approved=False
    ).filter((Meme.text != None) & (Meme.text != '')).all()

    # Group by subreddit
    memes_by_subreddit = {}
    for meme in memes:
        if meme.subreddit not in memes_by_subreddit:
            memes_by_subreddit[meme.subreddit] = []
        memes_by_subreddit[meme.subreddit].append(meme)

    return render_template('workflow_audio.html', memes_by_subreddit=memes_by_subreddit)

@memes_bp.route('/workflow_audio')
@require_login
def workflow_audio():
    """Legacy route - redirect to audio workshop"""
    return redirect(url_for('memes.audio_workshop'))

@memes_bp.route('/approve_meme_audio', methods=['POST'])
@require_login
def approve_meme_audio():
    """Approve meme audio and move to video generation via AJAX"""
    user_id = session['user_id']
    meme_id = request.form.get('meme_id')

    meme = Meme.query.filter_by(id=meme_id, user_id=user_id).first()
    if meme:
        meme.audio_approved = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Audio approved successfully'})
    else:
        return jsonify({'success': False, 'message': 'Meme not found'}), 404

@memes_bp.route('/generate_audio', methods=['POST'])
@require_login
def generate_audio():
    """Generate audio for specific meme(s) - handles both individual and bulk generation"""
    from services.audio_service import generate_audio_from_text
    import uuid
    import os

    user_id = session['user_id']
    meme_id = request.form.get('meme_id')  # If provided, generate for specific meme
    generate_all = request.form.get('generate_all')  # If 'true', generate for all

    generated_count = 0
    failed_count = 0

    if meme_id:
        # Generate audio for specific meme
        meme = Meme.query.filter_by(id=meme_id, user_id=user_id, text_approved=True).first()
        if meme and meme.text and meme.text.strip():
            try:
                # Clear any existing audio first from both database and session
                old_audio_path = meme.audio_path or session.get(f'audio_path_{meme.id}')

                if old_audio_path:
                    try:
                        if os.path.exists(old_audio_path):
                            os.remove(old_audio_path)
                    except Exception:
                        pass  # Ignore file deletion errors

                # Clear from database and session
                meme.audio_path = None
                session.pop(f'audio_path_{meme.id}', None)

                # Generate unique audio filename
                audio_filename = f"audio_{meme.id}_{uuid.uuid4().hex[:8]}.wav"
                audio_path = os.path.join('static', 'audio', audio_filename)

                # Get the current text from database (ensure it's fresh)
                current_text = meme.text.strip()

                # Generate audio using the current text
                if generate_audio_from_text(current_text, audio_path):
                    # Store audio path in both database and session
                    meme.audio_path = audio_path
                    db.session.commit()
                    session[f'audio_path_{meme.id}'] = audio_path
                    generated_count = 1
                else:
                    failed_count = 1
                    session['flash_message'] = f"Failed to generate audio for meme {meme.id}."
            except Exception as e:
                failed_count = 1
                session['flash_message'] = f"Error generating audio: {str(e)}"
        else:
            session['flash_message'] = "Invalid meme or no text content."

    elif generate_all == 'true':
        # Generate audio for all approved memes with text
        memes = Meme.query.filter_by(
            user_id=user_id,
            discarded=False,
            text_approved=True,
            audio_approved=False
        ).filter((Meme.text != None) & (Meme.text != '')).all()

        for meme in memes:
            try:
                # Clear any existing audio first (regenerate all) from both database and session
                old_audio_path = meme.audio_path or session.get(f'audio_path_{meme.id}')

                if old_audio_path:
                    try:
                        if os.path.exists(old_audio_path):
                            os.remove(old_audio_path)
                    except Exception:
                        pass  # Ignore file deletion errors

                # Clear from database and session
                meme.audio_path = None
                session.pop(f'audio_path_{meme.id}', None)

                # Generate unique audio filename
                audio_filename = f"audio_{meme.id}_{uuid.uuid4().hex[:8]}.wav"
                audio_path = os.path.join('static', 'audio', audio_filename)

                # Get the current text from database (ensure it's fresh)
                current_text = meme.text.strip()

                # Generate audio using the current text
                if generate_audio_from_text(current_text, audio_path):
                    # Store audio path in both database and session
                    meme.audio_path = audio_path
                    session[f'audio_path_{meme.id}'] = audio_path
                    generated_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1
                continue

        # Commit all changes for bulk generation
        if generated_count > 0:
            db.session.commit()

        # Set appropriate flash message only for failures
        if generated_count > 0 and failed_count > 0:
            session['flash_message'] = f"Generated audio for {generated_count} memes. {failed_count} failed to generate."
        elif generated_count == 0 and failed_count > 0:
            session['flash_message'] = f"Failed to generate audio for {failed_count} memes."
        elif generated_count == 0 and failed_count == 0:
            session['flash_message'] = "No audio files could be generated."
    else:
        session['flash_message'] = "Invalid request parameters."

    session['flash_context'] = ['audio_workshop', 'workflow_audio']

    # Return JSON response for AJAX requests, otherwise redirect
    if request.headers.get('Content-Type') == 'application/x-www-form-urlencoded':
        # This is likely an AJAX request, return JSON
        if generated_count > 0 and failed_count == 0:
            return jsonify({'success': True})  # No message for successful generation
        elif generated_count > 0 and failed_count > 0:
            return jsonify({'success': True, 'message': f'Generated audio for {generated_count} memes. {failed_count} failed.'})
        elif generated_count == 0 and failed_count > 0:
            return jsonify({'success': False, 'message': f'Failed to generate audio for {failed_count} memes.'})
        else:
            return jsonify({'success': False, 'message': 'No audio files could be generated.'})
    else:
        # Regular form submission, redirect as before
        return redirect(url_for('memes.audio_workshop'))

@memes_bp.route('/video_workshop')
@require_login
def video_workshop():
    """Video Workshop - Show memes ready for video generation and generated videos"""
    from services.video_service import calculate_video_requirements, get_audio_duration
    import os

    user_id = session['user_id']
    config = get_user_config(user_id)

    # Auto-approve textless memes for audio phase (they don't need audio generation)
    auto_approve_textless_memes(user_id)

    # Get memes that are approved and ready for video generation
    # Include memes that are text_approved (even without text) and audio_approved
    ready_memes = Meme.query.filter_by(
        user_id=user_id,
        discarded=False,
        text_approved=True,
        audio_approved=True
    ).order_by(Meme.created_at).all()

    # Prepare memes data for requirements calculation
    memes_data = []
    for meme in ready_memes:
        # Get audio path from database first, then fall back to session
        audio_path = meme.audio_path or session.get(f'audio_path_{meme.id}')

        # Calculate duration
        if audio_path and os.path.exists(audio_path):
            duration = get_audio_duration(audio_path)
        else:
            duration = 3.0  # Default for memes without audio

        memes_data.append({
            'meme_id': meme.id,
            'image_path': meme.image_path,
            'audio_path': audio_path,
            'duration': duration,
            'used_in_regular_video': meme.used_in_regular_video,
            'used_in_shorts_video': meme.used_in_shorts_video
        })

    # Calculate video requirements
    requirements = calculate_video_requirements(memes_data, session)

    # Filter memes for display (only show those that can still be used)
    display_memes = [meme for meme in ready_memes if
                    (config.create_videos and not meme.used_in_regular_video) or
                    (config.create_shorts and not meme.used_in_shorts_video)]

    # Group by subreddit
    memes_by_subreddit = {}
    for meme in display_memes:
        if meme.subreddit not in memes_by_subreddit:
            memes_by_subreddit[meme.subreddit] = []
        memes_by_subreddit[meme.subreddit].append(meme)

    # Get generated videos
    generated_videos = GeneratedVideo.query.filter_by(user_id=user_id).order_by(GeneratedVideo.created_at.desc()).all()

    return render_template('video_workshop.html',
                         memes_by_subreddit=memes_by_subreddit,
                         generated_videos=generated_videos,
                         config=config,
                         requirements=requirements)

@memes_bp.route('/generate_videos', methods=['POST'])
@require_login
def generate_videos():
    """Generate compilation videos based on user settings"""
    from services.video_service import generate_compilation_video, get_audio_duration
    import os
    import logging

    user_id = session['user_id']
    config = get_user_config(user_id)

    # Check if specific video type is requested
    requested_type = request.form.get('video_type')  # 'regular' or 'shorts'

    logging.info(f"Starting video generation for user {user_id}")
    logging.info(f"Config: create_videos={config.create_videos}, create_shorts={config.create_shorts}")
    logging.info(f"Requested type: {requested_type}")

    # Get memes ready for video generation
    ready_memes = Meme.query.filter_by(
        user_id=user_id,
        discarded=False,
        text_approved=True,
        audio_approved=True
    ).order_by(Meme.created_at).all()

    logging.info(f"Found {len(ready_memes)} ready memes")

    if not ready_memes:
        return jsonify({'success': False, 'message': 'No memes ready for video generation.'})

    # Prepare memes data for video generation
    memes_data = []
    for meme in ready_memes:
        # Get audio path from database first, then fall back to session
        audio_path = meme.audio_path or session.get(f'audio_path_{meme.id}')

        # Verify image path exists
        if not meme.image_path or not os.path.exists(meme.image_path):
            logging.error(f"Image not found for meme {meme.id}: {meme.image_path}")
            continue

        # Calculate duration
        if audio_path and os.path.exists(audio_path):
            duration = get_audio_duration(audio_path)
            logging.info(f"Meme {meme.id}: audio duration {duration}s")
        else:
            duration = 3.0  # Default for memes without audio
            audio_path = None
            logging.info(f"Meme {meme.id}: no audio, using default 3s duration")

        memes_data.append({
            'meme_id': meme.id,
            'image_path': meme.image_path,
            'audio_path': audio_path,
            'duration': duration
        })

    logging.info(f"Prepared {len(memes_data)} memes for video generation")

    if not memes_data:
        return jsonify({'success': False, 'message': 'No valid memes found for video generation.'})

    videos_generated = []
    errors = []

    # Generate regular videos if enabled and requested
    if config.create_videos and (not requested_type or requested_type == 'regular'):
        # Filter memes that haven't been used in regular videos
        regular_memes = [m for m in memes_data if not ready_memes[memes_data.index(m)].used_in_regular_video]

        logging.info(f"Regular videos enabled. Total memes_data: {len(memes_data)}, Available for regular: {len(regular_memes)}")
        for i, _ in enumerate(memes_data):
            meme = ready_memes[i]
            logging.info(f"Meme {meme.id}: used_in_regular_video={meme.used_in_regular_video}")

        if regular_memes:
            success, video_path, actual_duration, memes_used, used_meme_ids = generate_compilation_video(
                regular_memes, 'regular', 600
            )

            if success:
                # Save video record
                import json
                video_record = GeneratedVideo(
                    user_id=user_id,
                    video_path=video_path,
                    video_type='regular',
                    duration=actual_duration,
                    memes_count=memes_used,
                    meme_ids=json.dumps(used_meme_ids)
                )
                db.session.add(video_record)

                # Mark memes as used in regular videos
                for meme_id in used_meme_ids:
                    meme = next(m for m in ready_memes if m.id == meme_id)
                    meme.used_in_regular_video = True
                    # Update legacy field if used in all enabled types
                    if not config.create_shorts or meme.used_in_shorts_video:
                        meme.video_generated = True

                videos_generated.append(f'Regular video ({memes_used} memes, {actual_duration:.1f}s)')
            else:
                errors.append('Insufficient content for 10-minute regular video')
        else:
            errors.append('No memes available for regular video (all already used)')

    # Generate shorts if enabled and requested
    if config.create_shorts and (not requested_type or requested_type == 'shorts'):
        # Filter memes that haven't been used in shorts
        shorts_memes = [m for m in memes_data if not ready_memes[memes_data.index(m)].used_in_shorts_video]

        logging.info(f"Shorts enabled. Total memes_data: {len(memes_data)}, Available for shorts: {len(shorts_memes)}")
        for i, _ in enumerate(memes_data):
            meme = ready_memes[i]
            logging.info(f"Meme {meme.id}: used_in_shorts_video={meme.used_in_shorts_video}")

        if shorts_memes:
            success, video_path, actual_duration, memes_used, used_meme_ids = generate_compilation_video(
                shorts_memes, 'shorts', 180
            )

            if success:
                # Save video record
                import json
                video_record = GeneratedVideo(
                    user_id=user_id,
                    video_path=video_path,
                    video_type='shorts',
                    duration=actual_duration,
                    memes_count=memes_used,
                    meme_ids=json.dumps(used_meme_ids)
                )
                db.session.add(video_record)

                # Mark memes as used in shorts
                for meme_id in used_meme_ids:
                    meme = next(m for m in ready_memes if m.id == meme_id)
                    meme.used_in_shorts_video = True
                    # Update legacy field if used in all enabled types
                    if not config.create_videos or meme.used_in_regular_video:
                        meme.video_generated = True

                videos_generated.append(f'Shorts video ({memes_used} memes, {actual_duration:.1f}s)')
            else:
                errors.append('No content available for shorts video')
        else:
            errors.append('No memes available for shorts (all already used)')

    # Commit changes
    if videos_generated:
        db.session.commit()

    # Prepare response
    if videos_generated and not errors:
        message = f"Generated: {', '.join(videos_generated)}"
        logging.info(f"Video generation completed successfully: {message}")
        return jsonify({'success': True, 'message': message})
    elif videos_generated and errors:
        message = f"Generated: {', '.join(videos_generated)}. Errors: {', '.join(errors)}"
        logging.warning(f"Video generation completed with errors: {message}")
        return jsonify({'success': True, 'message': message})
    else:
        message = f"Failed to generate videos. Errors: {', '.join(errors)}"
        logging.error(f"Video generation failed: {message}")
        return jsonify({'success': False, 'message': message})

@memes_bp.route('/discard_video', methods=['POST'])
@require_login
def discard_video():
    """Discard a generated video and optionally return memes to available pool"""
    import json
    import os
    import logging

    user_id = session['user_id']
    video_id = request.form.get('video_id')
    action = request.form.get('action')  # 'return_memes' or 'discard_memes'

    if not video_id or not action:
        return jsonify({'success': False, 'message': 'Missing video ID or action'})

    try:
        # Get the video record
        video = GeneratedVideo.query.filter_by(id=video_id, user_id=user_id).first()
        if not video:
            return jsonify({'success': False, 'message': 'Video not found'})

        # Get the memes used in this video
        meme_ids = json.loads(video.meme_ids) if video.meme_ids else []

        if action == 'return_memes':
            # Return memes to available pool
            for meme_id in meme_ids:
                meme = Meme.query.get(meme_id)
                if meme and meme.user_id == user_id:
                    if video.video_type == 'regular':
                        meme.used_in_regular_video = False
                    elif video.video_type == 'shorts':
                        meme.used_in_shorts_video = False

                    # Update legacy field
                    meme.video_generated = meme.used_in_regular_video and meme.used_in_shorts_video

        elif action == 'discard_memes':
            # Mark memes as permanently discarded
            for meme_id in meme_ids:
                meme = Meme.query.get(meme_id)
                if meme and meme.user_id == user_id:
                    meme.discarded = True

        # Delete video file from filesystem
        if os.path.exists(video.video_path):
            try:
                os.remove(video.video_path)
            except Exception as e:
                logging.error(f"Failed to delete video file {video.video_path}: {e}")

        # Delete video record from database
        db.session.delete(video)
        db.session.commit()

        action_text = "returned to available pool" if action == 'return_memes' else "permanently discarded"
        return jsonify({
            'success': True,
            'message': f'Video discarded and {len(meme_ids)} memes {action_text}'
        })

    except Exception as e:
        db.session.rollback()
        logging.error(f"Error discarding video: {e}")
        return jsonify({'success': False, 'message': f'Error discarding video: {str(e)}'})