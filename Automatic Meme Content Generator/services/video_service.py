import subprocess
import os
import logging
from datetime import datetime
import tempfile
from PIL import Image

def get_audio_duration(media_path):
    """Get duration of audio or video file using FFmpeg"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', media_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return 3.0  # Default fallback
    except Exception:
        return 3.0  # Default fallback

def prepare_image_for_video(image_path, target_width, target_height, output_path):
    """Prepare image for video by resizing and adding letterbox/pillarbox"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Calculate scaling to fit within target dimensions while maintaining aspect ratio
            img_ratio = img.width / img.height
            target_ratio = target_width / target_height
            
            if img_ratio > target_ratio:
                # Image is wider - fit to width
                new_width = target_width
                new_height = int(target_width / img_ratio)
            else:
                # Image is taller - fit to height
                new_height = target_height
                new_width = int(target_height * img_ratio)
            
            # Resize image
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create new image with target dimensions and black background
            final_img = Image.new('RGB', (target_width, target_height), (0, 0, 0))
            
            # Paste resized image in center
            x_offset = (target_width - new_width) // 2
            y_offset = (target_height - new_height) // 2
            final_img.paste(img, (x_offset, y_offset))
            
            # Save as temporary image
            final_img.save(output_path, 'JPEG', quality=95)
            return True
    except Exception as e:
        logging.error(f"Error preparing image {image_path}: {e}")
        return False

def is_gif(image_path):
    """Check if the image is a GIF"""
    try:
        return image_path.lower().endswith('.gif')
    except:
        return False

def get_gif_duration(gif_path):
    """Get the natural duration of a GIF animation"""
    try:
        # Use ffprobe to get the duration of the GIF
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'csv=p=0', gif_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            duration = float(result.stdout.strip())
            # GIFs often have very short durations, ensure minimum of 0.1s
            return max(duration, 0.1)
        return 1.0  # Default fallback
    except Exception:
        return 1.0  # Default fallback

def calculate_video_requirements(memes_data, session_data):
    """Calculate video generation requirements and progress"""
    requirements = {
        'regular': {
            'min_duration': 600,  # 10 minutes
            'max_duration': 660,  # 11 minutes
            'current_duration': 0,
            'available_memes': 0,
            'can_generate': False,
            'progress_percent': 0
        },
        'shorts': {
            'min_duration': 60,   # 1 minute
            'max_duration': 180,  # 3 minutes
            'current_duration': 0,
            'available_memes': 0,
            'can_generate': False,
            'progress_percent': 0
        }
    }

    # Calculate durations for available memes
    for meme_data in memes_data:
        # Get audio path from session
        audio_path = session_data.get(f'audio_path_{meme_data["meme_id"]}')

        # Calculate duration (including 2 seconds of gaps)
        if audio_path and os.path.exists(audio_path):
            duration = get_audio_duration(audio_path) + 2.0  # Add gap time
        else:
            duration = 5.0  # 3s content + 2s gaps

        # Check availability for regular videos
        if not meme_data.get('used_in_regular_video', False):
            requirements['regular']['current_duration'] += duration
            requirements['regular']['available_memes'] += 1

        # Check availability for shorts
        if not meme_data.get('used_in_shorts_video', False):
            requirements['shorts']['current_duration'] += duration
            requirements['shorts']['available_memes'] += 1

    # Calculate progress and generation capability
    for video_type in ['regular', 'shorts']:
        req = requirements[video_type]
        if req['current_duration'] >= req['min_duration']:
            req['can_generate'] = True
            req['progress_percent'] = 100
        else:
            req['progress_percent'] = min(100, (req['current_duration'] / req['min_duration']) * 100)

    return requirements

def create_video_segment(image_path, audio_path, output_path, video_width, video_height):
    """Create a video segment from image and audio - always includes audio track for concatenation compatibility"""
    try:
        logging.info(f"Creating video segment: {image_path} -> {output_path}")

        # Check if image file exists
        if not os.path.exists(image_path):
            logging.error(f"Image file not found: {image_path}")
            return False

        # Handle GIFs differently to preserve animation
        if is_gif(image_path):
            logging.info(f"Processing GIF: {image_path}")
            # Get audio duration or use default
            if audio_path and os.path.exists(audio_path):
                duration = get_audio_duration(audio_path)
                logging.info(f"Using audio duration: {duration}s")

                # Get GIF's natural duration and calculate loops needed
                gif_duration = get_gif_duration(image_path)
                loops_needed = max(1, int((duration / gif_duration) + 1))  # +1 to ensure we have enough
                logging.info(f"GIF natural duration: {gif_duration:.3f}s, loops needed: {loops_needed}")

                # Build FFmpeg command with audio for GIF
                # Convert path separators for FFmpeg compatibility and use absolute path
                gif_path_normalized = os.path.abspath(image_path).replace('\\', '/')
                audio_path_normalized = os.path.abspath(audio_path).replace('\\', '/')

                # Use stream_loop for better GIF looping compatibility with older FFmpeg
                # Calculate how many times we need to loop the GIF
                loop_count = max(10, int((duration / gif_duration) * 2))

                cmd = [
                    'ffmpeg', '-y',  # Overwrite output file
                    '-stream_loop', str(loop_count),  # Loop the input stream
                    '-i', gif_path_normalized,  # GIF input
                    '-i', audio_path_normalized,  # Audio input
                    '-t', str(duration),  # Set duration to match audio
                    '-c:v', 'libx264',  # Video codec
                    '-preset', 'medium',  # Encoding preset for better compatibility
                    '-crf', '23',  # Constant rate factor for good quality
                    '-c:a', 'aac',  # Audio codec
                    '-strict', '-2',  # Allow experimental AAC encoder
                    '-b:a', '128k',  # Audio bitrate
                    '-ar', '44100',  # Audio sample rate
                    '-ac', '2',  # Audio channels (stereo)
                    '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                    '-r', '30',  # Frame rate
                    '-g', '60',  # GOP size for better seeking
                    '-movflags', '+faststart',  # Enable fast start for web playback
                    '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',
                    '-shortest',  # End when shortest stream ends
                    output_path
                ]
            else:
                duration = 3.0  # Default 3 seconds for memes without audio
                logging.info(f"No audio, using default duration: {duration}s")

                # Get GIF's natural duration and calculate loops needed
                gif_duration = get_gif_duration(image_path)
                loops_needed = max(1, int((duration / gif_duration) + 1))  # +1 to ensure we have enough
                logging.info(f"GIF natural duration: {gif_duration:.3f}s, loops needed: {loops_needed}")

                # Build FFmpeg command with silent audio track for GIF
                # Convert path separators for FFmpeg compatibility and use absolute path
                gif_path_normalized = os.path.abspath(image_path).replace('\\', '/')

                # Use stream_loop for better GIF looping compatibility with older FFmpeg
                # Calculate how many times we need to loop the GIF
                loop_count = max(10, int((duration / gif_duration) * 2))

                cmd = [
                    'ffmpeg', '-y',  # Overwrite output file
                    '-stream_loop', str(loop_count),  # Loop the input stream
                    '-i', gif_path_normalized,  # GIF input
                    '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',  # Silent audio
                    '-t', str(duration),  # Set duration
                    '-c:v', 'libx264',  # Video codec
                    '-preset', 'medium',  # Encoding preset for better compatibility
                    '-crf', '23',  # Constant rate factor for good quality
                    '-c:a', 'aac',  # Audio codec
                    '-strict', '-2',  # Allow experimental AAC encoder
                    '-b:a', '128k',  # Audio bitrate
                    '-ar', '44100',  # Audio sample rate
                    '-ac', '2',  # Audio channels (stereo)
                    '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                    '-r', '30',  # Frame rate
                    '-g', '60',  # GOP size for better seeking
                    '-movflags', '+faststart',  # Enable fast start for web playback
                    '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',
                    '-shortest',  # End when shortest stream ends
                    output_path
                ]
        else:
            # Handle static images (JPEG, PNG, etc.)
            # Prepare image for video
            temp_image = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            temp_image.close()

            if not prepare_image_for_video(image_path, video_width, video_height, temp_image.name):
                os.unlink(temp_image.name)
                return False

            # Get audio duration or use default
            if audio_path and os.path.exists(audio_path):
                duration = get_audio_duration(audio_path)
                logging.info(f"Using audio duration: {duration}s")
                # Build FFmpeg command with audio
                cmd = [
                    'ffmpeg', '-y',  # Overwrite output file
                    '-loop', '1', '-i', temp_image.name,  # Loop image
                    '-i', audio_path,  # Audio input
                    '-t', str(duration),  # Duration
                    '-c:v', 'libx264',  # Video codec
                    '-preset', 'medium',  # Encoding preset for better compatibility
                    '-crf', '23',  # Constant rate factor for good quality
                    '-c:a', 'aac',  # Audio codec
                    '-strict', '-2',  # Allow experimental AAC encoder
                    '-b:a', '128k',  # Audio bitrate
                    '-ar', '44100',  # Audio sample rate
                    '-ac', '2',  # Audio channels (stereo)
                    '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                    '-r', '30',  # Frame rate
                    '-g', '60',  # GOP size for better seeking
                    '-movflags', '+faststart',  # Enable fast start for web playback
                    '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',  # Scale and pad
                    '-shortest',  # End when shortest stream ends
                    output_path
                ]
            else:
                duration = 3.0  # Default 3 seconds for memes without audio
                logging.info(f"No audio, using default duration: {duration}s")
                # Build FFmpeg command with silent audio track for concatenation compatibility
                cmd = [
                    'ffmpeg', '-y',  # Overwrite output file
                    '-loop', '1', '-i', temp_image.name,  # Loop image
                    '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',  # Silent audio
                    '-t', str(duration),  # Duration
                    '-c:v', 'libx264',  # Video codec
                    '-preset', 'medium',  # Encoding preset for better compatibility
                    '-crf', '23',  # Constant rate factor for good quality
                    '-c:a', 'aac',  # Audio codec
                    '-strict', '-2',  # Allow experimental AAC encoder
                    '-b:a', '128k',  # Audio bitrate
                    '-ar', '44100',  # Audio sample rate
                    '-ac', '2',  # Audio channels (stereo)
                    '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                    '-r', '30',  # Frame rate
                    '-g', '60',  # GOP size for better seeking
                    '-movflags', '+faststart',  # Enable fast start for web playback
                    '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',  # Scale and pad
                    '-shortest',  # End when shortest stream ends
                    output_path
                ]

        logging.info(f"Running FFmpeg command: {' '.join(cmd)}")

        # Run FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        # If stream_loop failed and this is a GIF, try fallback approach
        if result.returncode != 0 and is_gif(image_path) and '-stream_loop' in cmd:
            logging.info("Stream loop failed, trying fallback approach for GIF")

            # Try a simpler approach without stream_loop
            gif_path_normalized = os.path.abspath(image_path).replace('\\', '/')

            if audio_path and os.path.exists(audio_path):
                # With audio
                audio_path_normalized = os.path.abspath(audio_path).replace('\\', '/')
                duration = get_audio_duration(audio_path)

                fallback_cmd = [
                    'ffmpeg', '-y',
                    '-i', gif_path_normalized,
                    '-i', audio_path_normalized,
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-strict', '-2',
                    '-b:a', '128k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-pix_fmt', 'yuv420p',
                    '-r', '30',
                    '-g', '60',
                    '-movflags', '+faststart',
                    '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',
                    '-shortest',
                    output_path
                ]
            else:
                # Without audio
                duration = 3.0

                fallback_cmd = [
                    'ffmpeg', '-y',
                    '-i', gif_path_normalized,
                    '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-strict', '-2',
                    '-b:a', '128k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-pix_fmt', 'yuv420p',
                    '-r', '30',
                    '-g', '60',
                    '-movflags', '+faststart',
                    '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',
                    '-shortest',
                    output_path
                ]

            logging.info(f"Running fallback FFmpeg command: {' '.join(fallback_cmd)}")
            result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=120)

        # Clean up temp image if it was created
        if not is_gif(image_path):
            os.unlink(temp_image.name)

        if result.returncode == 0:
            # Verify output file was created and has reasonable size
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logging.info(f"Successfully created video segment: {output_path} ({os.path.getsize(output_path)} bytes)")
                return True
            else:
                logging.error(f"Output file not created or too small: {output_path}")
                return False
        else:
            logging.error(f"FFmpeg error creating segment: {result.stderr}")
            logging.error(f"FFmpeg stdout: {result.stdout}")
            return False

    except Exception as e:
        logging.error(f"Error creating video segment: {e}")
        return False

def create_gap_segment(duration, video_width, video_height, output_path, image_path=None):
    """Create a gap segment - shows image if provided, otherwise black"""
    try:
        if image_path and os.path.exists(image_path):
            # Handle GIFs differently to preserve animation in gaps
            if is_gif(image_path):
                # Create gap with animated GIF
                # Get GIF's natural duration and calculate loops needed
                gif_duration = get_gif_duration(image_path)
                loops_needed = max(1, int((duration / gif_duration) + 1))  # +1 to ensure we have enough
                logging.info(f"Gap GIF - natural duration: {gif_duration:.3f}s, loops needed: {loops_needed}")

                # Convert path separators for FFmpeg compatibility and use absolute path
                gif_path_normalized = os.path.abspath(image_path).replace('\\', '/')

                # Calculate how many times we need to loop the GIF
                loop_count = max(10, int((duration / gif_duration) * 2))

                cmd = [
                    'ffmpeg', '-y',
                    '-stream_loop', str(loop_count),  # Loop the input stream
                    '-i', gif_path_normalized,  # GIF input
                    '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',  # Silent audio
                    '-t', str(duration),
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-strict', '-2',  # Allow experimental AAC encoder
                    '-b:a', '128k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-pix_fmt', 'yuv420p',
                    '-r', '30',
                    '-g', '60',
                    '-movflags', '+faststart',
                    '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',
                    '-shortest',
                    output_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                # If stream_loop failed, try fallback approach
                if result.returncode != 0 and '-stream_loop' in cmd:
                    logging.info("Stream loop failed for gap GIF, trying fallback approach")

                    # Try a simpler approach without stream_loop
                    fallback_cmd = [
                        'ffmpeg', '-y',
                        '-i', gif_path_normalized,
                        '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',
                        '-t', str(duration),
                        '-c:v', 'libx264',
                        '-preset', 'medium',
                        '-crf', '23',
                        '-c:a', 'aac',
                        '-strict', '-2',
                        '-b:a', '128k',
                        '-ar', '44100',
                        '-ac', '2',
                        '-pix_fmt', 'yuv420p',
                        '-r', '30',
                        '-g', '60',
                        '-movflags', '+faststart',
                        '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',
                        '-shortest',
                        output_path
                    ]

                    result = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=30)

                return result.returncode == 0
            else:
                # Create gap with static image
                temp_image = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                temp_image.close()

                if prepare_image_for_video(image_path, video_width, video_height, temp_image.name):
                    cmd = [
                        'ffmpeg', '-y',
                        '-loop', '1', '-i', temp_image.name,
                        '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',  # Silent audio
                        '-t', str(duration),
                        '-c:v', 'libx264',
                        '-preset', 'medium',
                        '-crf', '23',
                        '-c:a', 'aac',
                        '-strict', '-2',  # Allow experimental AAC encoder
                        '-b:a', '128k',
                        '-ar', '44100',
                        '-ac', '2',
                        '-pix_fmt', 'yuv420p',
                        '-r', '30',
                        '-g', '60',
                        '-movflags', '+faststart',
                        '-vf', f'scale={video_width}:{video_height}:force_original_aspect_ratio=decrease,pad={video_width}:{video_height}:(ow-iw)/2:(oh-ih)/2:black',
                        '-shortest',
                        output_path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    os.unlink(temp_image.name)
                    return result.returncode == 0
                else:
                    os.unlink(temp_image.name)
                    # Fall back to black if image processing fails

        # Create black gap segment with audio track for concatenation compatibility
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi', '-i', f'color=black:size={video_width}x{video_height}:duration={duration}',
            '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',  # Silent audio
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',
            '-strict', '-2',  # Allow experimental AAC encoder
            '-b:a', '128k',
            '-ar', '44100',
            '-ac', '2',
            '-pix_fmt', 'yuv420p',
            '-r', '30',
            '-g', '60',
            '-movflags', '+faststart',
            '-shortest',
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0

    except Exception as e:
        logging.error(f"Error creating gap segment: {e}")
        return False

def concatenate_video_segments(segment_paths, output_path):
    """Concatenate video segments into final video"""
    try:
        # Create concat file
        concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        for segment_path in segment_paths:
            concat_file.write(f"file '{os.path.abspath(segment_path)}'\n")
        concat_file.close()
        
        # Run FFmpeg concat with re-encoding for better compatibility
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat', '-safe', '0', '-i', concat_file.name,
            '-c:v', 'libx264',  # Re-encode video for consistency
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'aac',  # Re-encode audio for consistency
            '-strict', '-2',
            '-b:a', '128k',
            '-ar', '44100',
            '-ac', '2',
            '-pix_fmt', 'yuv420p',
            '-r', '30',
            '-g', '60',
            '-movflags', '+faststart',  # Enable fast start for web playback
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Clean up concat file
        os.unlink(concat_file.name)
        
        if result.returncode == 0:
            return True
        else:
            logging.error(f"FFmpeg concat error: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"Error concatenating video segments: {e}")
        return False

def generate_compilation_video(memes_data, video_type='regular', target_duration=600):
    """
    Generate compilation video from memes data
    
    Args:
        memes_data: List of dicts with 'image_path', 'audio_path', 'duration' keys
        video_type: 'regular' (16:9) or 'shorts' (9:16)
        target_duration: Target duration in seconds
    
    Returns:
        tuple: (success, output_path, actual_duration, memes_used, used_meme_ids)
    """
    try:
        # Video dimensions and duration requirements
        if video_type == 'shorts':
            video_width, video_height = 1080, 1920  # 9:16 vertical
            min_duration = 60   # 1 minute minimum
            max_duration = 180  # 3 minutes max
        else:
            video_width, video_height = 1920, 1080  # 16:9 horizontal
            min_duration = 600  # 10 minutes minimum
            max_duration = 660  # 11 minutes max
        
        # Calculate which memes to include
        selected_memes = []
        used_meme_ids = []
        total_duration = 0

        for meme_data in memes_data:
            # Each meme segment: 1s gap + meme duration + 1s gap
            meme_duration = meme_data.get('duration', 3.0)
            segment_duration = 1.0 + meme_duration + 1.0

            # Check if adding this meme would exceed limits
            if total_duration + segment_duration > max_duration:
                break

            selected_memes.append(meme_data)
            used_meme_ids.append(meme_data.get('meme_id'))
            total_duration += segment_duration

            # For regular videos, stop if we have enough content
            if video_type == 'regular' and total_duration >= target_duration:
                break

        # Check if we have enough content for regular videos
        if video_type == 'regular' and total_duration < target_duration:
            return False, None, 0, 0, []

        if not selected_memes:
            return False, None, 0, 0, []
        
        # Create output directory
        output_dir = 'static/videos'
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if video_type == 'shorts':
            output_filename = f'shorts_compilation_{timestamp}.mp4'
        else:
            output_filename = f'video_compilation_{timestamp}.mp4'
        
        output_path = os.path.join(output_dir, output_filename)
        
        # Create temporary directory for segments
        temp_dir = tempfile.mkdtemp()
        segment_paths = []
        
        try:
            for i, meme_data in enumerate(selected_memes):
                # Create gap before meme (showing the meme image)
                gap_before_path = os.path.join(temp_dir, f'gap_before_{i}.mp4')
                if create_gap_segment(1.0, video_width, video_height, gap_before_path, meme_data['image_path']):
                    segment_paths.append(gap_before_path)

                # Create meme segment
                meme_segment_path = os.path.join(temp_dir, f'meme_{i}.mp4')
                if create_video_segment(
                    meme_data['image_path'],
                    meme_data.get('audio_path'),
                    meme_segment_path,
                    video_width,
                    video_height
                ):
                    segment_paths.append(meme_segment_path)

                # Create gap after meme (showing the meme image)
                gap_after_path = os.path.join(temp_dir, f'gap_after_{i}.mp4')
                if create_gap_segment(1.0, video_width, video_height, gap_after_path, meme_data['image_path']):
                    segment_paths.append(gap_after_path)
            
            # Concatenate all segments
            if segment_paths and concatenate_video_segments(segment_paths, output_path):
                # Measure the actual duration of the final video
                actual_duration = get_audio_duration(output_path)  # This works for video files too
                logging.info(f"Video generation completed. Planned duration: {total_duration:.3f}s, Actual duration: {actual_duration:.3f}s")
                return True, output_path, actual_duration, len(selected_memes), used_meme_ids
            else:
                return False, None, 0, 0, []
                
        finally:
            # Clean up temporary files
            for segment_path in segment_paths:
                try:
                    if os.path.exists(segment_path):
                        os.remove(segment_path)
                except Exception:
                    pass
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass
        
    except Exception as e:
        logging.error(f"Error generating compilation video: {e}")
        return False, None, 0, 0, []
