from flask import Blueprint, render_template, request, redirect, url_for, session
from models import User, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def home():
    """Home page redirects to login or dashboard if already logged in"""
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('login.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('dashboard.dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('dashboard.dashboard'))
        else:
            return render_template('login.html', error='Invalid email or password. Please try again.')
    return render_template('login.html')

@auth_bp.route('/register', methods=['POST'])
def register():
    """Handle user registration"""
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    # Basic validation
    if not username or not password:
        return render_template('login.html', error='Email and password are required.', show_register=True)

    if password != confirm_password:
        return render_template('login.html', error='Passwords do not match.', show_register=True)

    if len(password) < 6:
        return render_template('login.html', error='Password must be at least 6 characters long.', show_register=True)

    # Check if user already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return render_template('login.html', error='An account with this email already exists.', show_register=True)

    # Create new user
    try:
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        # Auto-login the new user
        session['user_id'] = new_user.id
        return redirect(url_for('dashboard.dashboard'))
    except Exception as e:
        db.session.rollback()
        return render_template('login.html', error='Registration failed. Please try again.', show_register=True)

@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    session.pop('user_id', None)
    return redirect(url_for('auth.login'))
