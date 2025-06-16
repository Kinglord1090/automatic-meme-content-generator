import praw
import os
from dotenv import load_dotenv

load_dotenv()

def get_top_memes(limit=100, subreddits=None, existing_urls=None):
    """Fetch new memes from specified subreddits - limit applies PER subreddit"""
    client_id = os.getenv('REDDIT_CLIENT_ID')
    client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    username = os.getenv('REDDIT_USERNAME')

    if not all([client_id, client_secret, username]):
        return []

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=f'AutomaticMemeContentGenerator/0.1 by {username}'
        )
    except Exception:
        return []

    memes = []
    seen_urls = set()  # Track URLs to prevent duplicates within this fetch
    if existing_urls:
        seen_urls.update(existing_urls)  # Include existing URLs to avoid duplicates

    if not subreddits:
        subreddits = ['memes']

    for subreddit_name in subreddits:
        try:
            subreddit = reddit.subreddit(subreddit_name)

            subreddit_memes = []
            posts_checked = 0
            max_posts_to_check = limit * 10  # Check up to 10x the limit to find non-duplicates

            # Fetch from 'new' instead of 'top' for fresh content
            for submission in subreddit.new(limit=max_posts_to_check):
                posts_checked += 1

                if submission.url.endswith(('jpg', 'jpeg', 'png', 'gif', 'webp')):
                    # Check for duplicates (both within this fetch and against existing)
                    if submission.url not in seen_urls:
                        seen_urls.add(submission.url)
                        subreddit_memes.append({
                            'url': submission.url,
                            'title': submission.title,
                            'subreddit': subreddit_name,
                            'score': submission.score,
                            'created_utc': submission.created_utc
                        })

                        # Stop when we reach the limit for this subreddit
                        if len(subreddit_memes) >= limit:
                            break

                # Safety check to avoid infinite loops
                if posts_checked >= max_posts_to_check:
                    break

            memes.extend(subreddit_memes)

        except Exception:
            continue

    return memes
