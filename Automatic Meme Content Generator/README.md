# 🎭 AI-Powered Meme Video Generator

A beautiful, modern web application that transforms memes into engaging videos with AI-generated narration.

## ✨ Features

- **🎭 Reddit Integration**: Fetch trending memes from multiple subreddits
- **✏️ Text Editor**: Add custom text to memes with an intuitive interface
- **🎵 AI Voice Generation**: Convert text to natural-sounding speech using pyttsx3
- **🎬 Video Creation**: Combine memes with AI-generated audio using FFmpeg
- **📱 Beautiful UI**: Modern, responsive design with glassmorphism effects
- **🗄️ Persistent Storage**: SQLite database that survives server restarts

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- pip package manager
- FFmpeg (for video generation)

### Installation

1. **Clone or download the project**
   ```bash
   cd "Automatic Meme Content Generator"
   ```

2. **Install FFmpeg**
   - **Windows**: Download from https://ffmpeg.org/download.html or use `winget install FFmpeg`
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Ubuntu/Debian) or `sudo yum install ffmpeg` (CentOS/RHEL)

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up Reddit API credentials**
   - Go to https://www.reddit.com/prefs/apps
   - Create a new application (script type)
   - Note down your client ID and secret

5. **Set up environment variables** (copy `.env.example` to `.env` and fill in your values)
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` with your actual credentials:
   ```env
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   REDDIT_USERNAME=your_reddit_username
   SECRET_KEY=your_secret_key_here
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Open your browser**
   Navigate to: http://127.0.0.1:5000

### Demo Login
After running the application for the first time, you can register a new account or use the registration feature on the login page.

## 🎯 How to Use

1. **Register/Login** - Create an account or login
2. **Configure Settings** - Set max memes and select subreddits
3. **Fetch Memes** - Get fresh memes from Reddit
4. **Add Text** - Edit meme text for narration
5. **Generate Videos** - Create videos with AI voice narration
6. **Download Content** - Save your generated videos and audio

## 🛠️ Technology Stack

- **Backend**: Flask, SQLAlchemy
- **Frontend**: HTML5, CSS3 (Modern design with CSS Grid/Flexbox)
- **Database**: SQLite (persistent storage)
- **APIs**: Reddit API (PRAW)
- **Audio**: pyttsx3 (Text-to-Speech)
- **Video**: FFmpeg (Video generation)

## 📁 Project Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── modules/
│   ├── __init__.py
│   └── reddit_scraper.py  # Reddit API integration
├── templates/
│   ├── login.html         # Beautiful landing page
│   ├── dashboard.html     # Main dashboard
│   ├── config.html        # Settings page
│   ├── review_memes.html  # Meme text editor
│   ├── review_audio.html  # Audio review page
│   └── review_videos.html # Video review page
├── static/
│   ├── styles.css         # Modern CSS styling
│   ├── audio/            # Generated audio files
│   └── videos/           # Generated video files
└── instance/
    └── app.db            # SQLite database
```

## 🎨 UI Features

- **Modern Landing Page**: Hero section with floating animations
- **Glassmorphism Design**: Translucent cards with backdrop blur
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Interactive Elements**: Hover effects and smooth transitions
- **Color Scheme**: Professional gradient backgrounds
- **Typography**: Inter font for modern readability

## 🔧 Configuration

The application supports:
- **Subreddit Selection**: Choose from popular meme subreddits
- **Meme Limits**: Set maximum number of memes to fetch (1-100)
- **Voice Settings**: Automatic voice selection for TTS
- **Video Quality**: 720p output with optimized settings

## 📊 Database Schema

- **Users**: Authentication and user management
- **Memes**: Fetched memes with text and metadata
- **Configurations**: User preferences and settings
- **Videos**: Generated content with file paths

## 🚀 Performance

- **Fast Loading**: Optimized CSS and minimal JavaScript
- **Efficient Processing**: OpenCV for quick video generation
- **Persistent Data**: All content survives server restarts
- **Error Handling**: Graceful fallbacks and user feedback

## 🎉 Ready to Use!

The application is fully functional and ready for creating amazing meme videos. The beautiful UI makes it easy to navigate through the entire workflow from fetching memes to downloading finished videos.

---

**Enjoy creating viral meme content! 🎬✨**
