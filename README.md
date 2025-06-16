# Automatic Meme Content Generator 🎭

This project is a Flask-based web application that automates the creation of memes using top Reddit posts. Users can log in, configure their preferences (like subreddit, duration, caption templates), and generate memes with audio, video, and image support. Ideal for content creators, social media managers, or anyone who wants to automate meme production with a customizable pipeline.

## Features

- **User Authentication**: Secure login system to manage individual meme generation sessions.
- **Reddit Integration**: Uses Reddit's API via `PRAW` to fetch top posts from user-selected subreddits.
- **Meme Workflow Configurator**: Set preferences for content type, template styles, captions, durations, and more.
- **Video + Audio Meme Generator**: Automatically generates memes in video format with synchronized audio.
- **Image Meme Creation**: For static meme generation with flexible captioning.
- **Review Dashboard**: Interface to view, manage, and edit generated meme content.
- **Extensible and Modular**: Easily adaptable for new features like watermarking, scheduling posts, or platform-specific exports.

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Kinglord1090/automatic-meme-content-generator.git
cd automatic-meme-content-generator
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env.example .env
# Fill in Reddit API credentials and Flask secret key in the .env file
```

## Usage

1. Run the Flask app:

```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`.

3. Register or log in to start configuring your meme generation pipeline.

4. Use the dashboard to fetch Reddit content and generate memes automatically.

## Folder Structure

- `routes/`: Handles different views and user interaction routes.
- `services/`: Logic for audio, video, Reddit fetching, and helper utilities.
- `templates/`: Jinja2 HTML templates for rendering frontend.
- `static/`: CSS, images, audio, and video assets.
- `models.py`: Stores configuration state and user-specific session data.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to [PRAW](https://praw.readthedocs.io/) for Reddit API integration.
- Built with Flask, and inspired by the need to streamline meme content creation.
