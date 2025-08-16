# Clanker

A simple Clanker built with Flask and vanilla JavaScript, featuring user authentication, posts, likes, and replies.

## Features

- **User Authentication**: Register and login with username/password
- **Posts**: Create posts up to 280 characters
- **Engagement**: Like and unlike posts, reply to posts
- **User Profiles**: View individual user profiles and their posts
- **Real-time Updates**: Like counts and reply counts update in real-time
- **Modern UI**: Clean, responsive design inspired by Twitter

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: Vanilla HTML, CSS, JavaScript
- **Database**: SQLite with WAL mode for parallel writes
- **Authentication**: Session-based with password hashing

## Setup

1. **Install Dependencies**:
   ```bash
   cd blog
   uv pip install -r requirements.txt
   ```

2. **Run the Application**:

   **Development Mode (with Hot Reload)**:
   ```bash
   python run.py
   # or
   FLASK_ENV=development python run.py
   ```

   **Production Mode (no Hot Reload)**:
   ```bash
   FLASK_ENV=production python run.py
   ```

3. **Access the Application**:
   Open your browser and go to `http://localhost:8080`

## Routes

### Web Routes
- `/` - Home page with recent posts
- `/u/<username>` - User profile page
- `/t/<id>` - Individual post page
- `/login` - User login
- `/register` - User registration
- `/logout` - User logout

### API Routes
- `/api/users/` - User CRUD operations
- `/api/posts/` - Post CRUD operations
- `/api/engagements/` - Engagement (like/reply) operations

## Database Schema

The application uses SQLite with the following tables:

- **users**: User accounts with username and hashed password
- **posts**: User posts with content and timestamp
- **engagements**: Likes and replies linked to posts

## Usage

1. **Create an Account**: Click "Sign Up" to create a new account
2. **Login**: Use your credentials to log in
3. **Post**: Write posts up to 280 characters on the home page
4. **Engage**: Like posts and reply to them
5. **Explore**: Click on usernames to view profiles, or click on posts to view details

## Development

- The application runs on port 8080
- Database file is located at `../data/tweets.db`
- WAL mode is enabled for concurrent database access
- **Hot Reload**: Automatically restarts server when code changes (development mode only)
- **Environment Configuration**: Use `FLASK_ENV` to switch between development and production modes

## Security Features

- Password hashing using SHA-256
- Session-based authentication
- Input validation and sanitization
- SQL injection protection through parameterized queries
