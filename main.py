import datetime as dt
from datetime import datetime
from flask import Flask, abort, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, LoginManager, login_user, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, func, desc
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from forms import NewPostForm, RegisterForm, LoginForm, CommentForm
import os
from dotenv import load_dotenv
import smtplib
import re

from database import init_db, db
from models import User, BlogPost, Comment

load_dotenv()
APP_EMAIL = os.environ['APP_EMAIL']
PASS = os.environ['PASS']
ADMIN_EMAIL = os.environ['ADMIN_EMAIL']
G_URL = "smtp.gmail.com"

# Production configuration
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['DEL_CODE'] = os.environ['DELETION_CODE']

# Database configuration
if IS_PRODUCTION:
    # Handle Render PostgreSQL URL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback to SQLite if DATABASE_URL is not set (should not happen in production)
        print("Warning: DATABASE_URL not set, falling back to SQLite")
        sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{sqlite_path}'
else:
    # Use SQLite for local development
    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blog.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{sqlite_path}'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Security headers
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

ckeditor = CKEditor(app)
Bootstrap5(app)

init_db(app)

year = datetime.now().year

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

def find_phrase(text, query, max_length=250):
    """Finds a phrase containing the query."""
    match = re.search(re.escape(query), text, re.IGNORECASE)
    if match:
        start = match.start()
        sentence_start = max(
            text.rfind(". ", 0, start),
            text.rfind("! ", 0, start),
            text.rfind("? ", 0, start),
            text.rfind("\n", 0, start),
            0  # start of string
        )
        if sentence_start != 0:
            start = sentence_start + 2  # skip delimiter
            if text[start:start + 2].lower() == "p>":
                start += 2  # Skip the "<p>" tag

        end = min(len(text), start + max_length)
        return text[start:end].strip() + "..."

    return text[:max_length].strip() + "..."

def highlight_query(text, query):
    """Highlights the query in the text with orange color."""
    return re.sub(re.escape(query),
                  lambda m: f'<span class="highlighted">{m.group(0)}</span>',
                  text,
                  flags=re.IGNORECASE)

app.jinja_env.filters['highlight_query'] = highlight_query

@app.route('/register', methods=['GET','POST'])
def register():
    """Renders the Registration WTForm """
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        user = db.session.execute(db.select(User).where(User.email==email)).scalar()
        if user:
            flash("You've already signed up with this email, please log in.","info")
            return redirect(url_for('login'))

        new_user = User(
            name=form.name.data,  # type: ignore[call-arg]
            email=form.email.data,  # type: ignore[call-arg]
            password=generate_password_hash(form.password.data, method='pbkdf2:sha256',salt_length=10)  # type: ignore[call-arg]
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)

        flash(f'Registration successful<br>Welcome, {current_user.name}!<br>You are logged in',"success")
        return redirect(url_for('home'))
    return render_template("register.html",
                           form=form,
                           current_user=current_user,
                           title='Register',
                           subtitle='Start Contributing to the Blog!',
                           bg_image="register-bg.jpg"
                           )


@app.route('/login',methods=['GET','POST'])
def login():
    """Renders the Login Form for user authentication."""
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        passw = form.password.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if not user:
            flash("This email does not exist, please try again or Register","info")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, passw):
            flash('Password incorrect, please try again','error')
            return redirect(url_for('login'))
        else:
            login_user(user)
            flash(f"Welcome back, {current_user.name}!<br>You are logged in","success")
            return redirect(url_for('home'))

    return render_template("login.html",
                           form=form,
                           current_user=current_user,
                           title='Log In',
                           subtitle='Welcome back!',
                           bg_image="login-bg.jpg"
                           )


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.','success')
    return redirect(url_for('home'))


@app.route('/')
def home():
    if IS_PRODUCTION:
        # PostgreSQL query
        result = db.session.execute(
            db.select(BlogPost).order_by(desc(func.to_date(BlogPost.date, 'Month DD, YYYY')))
        )
    else:
        # SQLite query
        result = db.session.execute(
            db.select(BlogPost).order_by(func.strftime('%Y-%m-%d', func.replace(BlogPost.date, ',', '')).desc())
        )
    posts = result.scalars().all()
    visible_posts = posts[:3]  # Initial 3 posts
    all_posts_dicts = [
        {
            'id': post.id,
            'title': post.title,
            'subtitle': post.subtitle,
            'author': {'name': post.author.name},  # Ensure author is a dictionary
            'date': post.date
        }
        for post in posts
    ]
    user_id = -1
    if current_user.is_authenticated:
        user_id = current_user.id

    return render_template("index.html",
                           all_posts=all_posts_dicts,
                           visible_posts=visible_posts,
                           current_user=current_user,
                           user_id=user_id,
                           title='The Debug Diaries',
                           subtitle='A collection of random musings',
                           bg_image="home-bg.jpg"
                           )


@app.route('/search')
def search():
    query = request.args.get('query', '').lower()
    if not query:
        return redirect(url_for('home'))

    if IS_PRODUCTION:
        # PostgreSQL query
        result = db.session.execute(
            db.select(BlogPost).order_by(desc(func.to_date(BlogPost.date, 'Month DD, YYYY')))
        )
    else:
        # SQLite query
        result = db.session.execute(
            db.select(BlogPost).order_by(func.strftime('%Y-%m-%d', func.replace(BlogPost.date, ',', '')).desc())
        )
    
    posts = result.scalars().all()
    results = []
    
    for post in posts:
        if (query in post.title.lower() or 
            query in post.subtitle.lower() or 
            query in post.body.lower()):
            
            # Find a relevant snippet of text containing the query
            snippet = find_phrase(post.body, query)
            
            results.append({
                'id': post.id,
                'title': post.title,
                'subtitle': post.subtitle,
                'snippet': snippet,
                'query': query
            })

    return render_template("search.html",
                           results=results,
                           query=query,
                           current_user=current_user,
                           title='The Debug Diaries',
                           subtitle='A collection of random musings',
                           bg_image="home-bg.jpg"
                           )


@app.route("/post/<int:post_id>", methods=['GET','POST'])
def show_post(post_id):
    sel_post = db.get_or_404(BlogPost, post_id)
    # pass the posts to js as dictionary
    post_dict = {
        'id': sel_post.id,
        'title': sel_post.title,
        'subtitle': sel_post.subtitle,
        'author': {'name': sel_post.author.name},
        'date': sel_post.date
    }

    comment_form = CommentForm()
    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash('We are looking forward to reading your contributions!<br>It only takes 15 seconds to register/login','info')
            return redirect(url_for('register'))

        new_comm = Comment(
            text=comment_form.text.data,
            user_id=current_user.id,
            post_id=sel_post.id,
            date=dt.date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_comm)
        db.session.commit()

        return redirect(url_for('show_post',post_id=sel_post.id,post_dict=post_dict))

    return render_template("post.html",
                           current_user=current_user,
                           post=sel_post,
                           post_dict=post_dict,
                           form=comment_form)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = NewPostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=dt.date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("home"))
    return render_template("write-post.html",
                           form=form,
                           current_user=current_user,
                           title='New Post',
                           subtitle="You're going to make a great blog post!",
                           bg_image="edit-bg.jpg"
                           )


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = NewPostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("write-post.html",
                           form=edit_form,
                           is_edit=True,
                           current_user=current_user,
                           title='Edit Post',
                           subtitle="You're going to make a great blog post!",
                           bg_image="edit-bg.jpg"
                           )


@app.route("/delete-post/<int:post_id>", methods=["POST"])
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    del_code = request.form.get("delCode")

    if del_code == app.config['DEL_CODE']:
        try:
            comments_to_delete = Comment.query.filter_by(post_id=post_id).all()
            for comment in comments_to_delete:
                db.session.delete(comment)
            db.session.delete(post_to_delete)
            db.session.commit()
            return redirect(url_for('home'))
        except Exception as e:
            # Handle database errors (log, display message, etc.)
            print(f"Database error: {e}")
            abort(500)  # Internal Server Error
    else:
        abort(403)  # Forbidden (incorrect secret key)


@app.route("/about")
def about():
    return render_template("about.html",
                           current_user=current_user,
                           title='About Me',
                           subtitle='Welcome to the party!',
                           bg_image="about-bg.jpg"
                           )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        data = request.form
        try:
            # Create the email message
            msg = MIMEMultipart()
            msg['From'] = APP_EMAIL
            msg['To'] = ADMIN_EMAIL
            msg['Subject'] = "New Message from The Debug Diaries"
            
            body = f"""
            New message from your blog:
            
            Name: {data.get('name')}
            Email: {data.get('email')}
            Phone: {data.get('phone')}
            Message: {data.get('message')}
            """
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Send the email using Gmail SMTP
            with smtplib.SMTP(G_URL, port=587) as connection:
                connection.starttls()
                connection.login(user=APP_EMAIL, password=PASS)
                connection.send_message(msg)
            
            flash("Your message has been sent successfully!", "success")
            return render_template("contact.html", 
                                msg_sent=True,
                                current_user=current_user,
                                title="Contact Me",
                                subtitle="Have questions? I have answers.",
                                bg_image="contact-bg.jpg")
            
        except Exception as e:
            print(f"Error sending email: {e}")
            flash("Failed to send message. Please try again later.", "error")
            
    return render_template("contact.html",
                         msg_sent=False,
                         current_user=current_user,
                         title="Contact Me",
                         subtitle="Have questions? I have answers.",
                         bg_image="contact-bg.jpg")


if __name__ == "__main__":
    if IS_PRODUCTION:
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        app.run(debug=True, host='0.0.0.0', port=5001)