import os 
from functools import wraps
from flask import Flask, g, render_template, request, redirect, session, flash, send_from_directory
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
Session(app)

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    hash = db.Column(db.String(255), nullable=False)

    def __init__(self, username, email, hash):
        self.username = username
        self.email = email
        self.hash = hash

with app.app_context():
    db.create_all()

# Close the database connection after each request
@app.teardown_appcontext
def close_db(exception=None):
    db.session.remove()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['identifier']
        password = request.form['password']

        # Use the or_ operator to check if the provided identifier matches either username or email
        user = User.query.filter(or_(User.username == identifier, User.email == identifier)).first()
    
        if user and check_password_hash(user.hash, password):
            session["user_id"] = user.id
            return ("invalid username and/or password")
        
        return redirect("/")  # Redirect to the index page on successful login
        
    else:
        return render_template('login.html', error='Invalid Username and Password.')

@app.route('/logout')
def logout():
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html") 
    
    else:
        username = request.form['signupUsername']
        email = request.form['signupEmail']
        password = request.form['signupPassword']
        confirm_password = request.form['confirm_password']

        hash = generate_password_hash(password)

        try:
            new_user = User(username=username, email=email, hash=hash)
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}"

        session["user_id"] = new_user.id

        return redirect("/")
    

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session.get("user_id")
    user = User.query.get(user_id)

    if request.method == "POST":
        # Handle profile settings form submission
        user.username = request.form['username']
        user.email = request.form['email']

        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']

            if file and allowed_file(file.filename):
                # Remove the old profile picture if exists
                old_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
                if os.path.exists(old_picture_path):
                    os.remove(old_picture_path)

                # Save the new profile picture
                filename = f"user_{user.id}_profile_picture.{file.filename.rsplit('.', 1)[1].lower()}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.profile_picture = filename

        # Commit changes to the database
        db.session.commit()
    else:
        return render_template("profile.html", user=user)

# Serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)