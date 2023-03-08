import os

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
import sqlite3

from helpers import error, login_required, in_household_required

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.debug = True


# Configure SQLite database
def get_db():
    db = getattr(Flask, 'roomies.db', None)
    if db is None:
        db = Flask._database = sqlite3.connect('roomies.db')
    return db
    
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(Flask, '_database', None)
    if db is not None:
        db.close()

# Make sure API key is set
#if not os.environ.get("API_KEY"):
    #raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
def index():

    # Forget any user_id
    session.clear()
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Create variables for username, password & confirmation
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submimitted
        if not username:
            return error("Please provide username",400)
        # Validate if username exists already or not
        with sqlite3.connect('roomies.db') as conn:
            rows = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            if len(rows.fetchall()) != 0:
                return error("Username already exists",400)

        # Ensure password & confirmation were submimitted
        if not password or not confirmation:
            return error("Please provide password & confirmation",400)

        # Ensure password = confirmation
        elif password != confirmation:
            return error("Password does not equal confirmation",400)

        # Insert username and hash of password into database
        hash = generate_password_hash(password)
        with sqlite3.connect('roomies.db') as conn:
            conn.execute("INSERT INTO users (username, hash) VALUES (?,?)", (username, hash))


        # Redirect to index page and provide confirmation to users
        flash("Congrats, you were succesfully registered!")
        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    #Variables
    username = request.form.get("username")
    password = request.form.get("password")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not username:
            return error("must provide username", 403)

        # Ensure password was submitted
        elif not password:
            return error("must provide password", 403)

        # Query database for username
        with sqlite3.connect('roomies.db') as conn:
            cursor = conn.execute("SELECT * FROM users WHERE username = ?", (username,))
            rows = cursor.fetchall()

        # Ensure username exists and password is correct
        if not check_password_hash(rows[0][2], password):
            return error("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        flash("You were succesfully logged in!")
        return redirect("/homepage")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/homepage", methods=["GET", "POST"])
@login_required
def home():
    # Get the user ID from the session
    user_id = session["user_id"]

    # Get username
    with sqlite3.connect('roomies.db') as conn:
        rows = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        username = rows.fetchone()[0]

    # Get the user's household from the database
    with sqlite3.connect("roomies.db") as conn:
        row = conn.execute("SELECT household FROM users WHERE id = ?", (user_id,)).fetchone()
        household = row[0] if row else None
    
    # Configure session for household
    session["household"] = household

    # Render the appropriate template based on whether the user is part of a household or not
    if household:
        return render_template("household.html", household=household, username=username)
    else:
        return render_template("no_household.html")

@app.route("/no_household", methods=["GET", "POST"])
def no_household():
    user = session.get("user_id")

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Variables
        action = request.form.get("action")
        household = request.form.get("household")

        # Validate household name
        if not household:
            return error("Must provide household name", 400)

        # Perform action based on user selection
        if action == "create":
            # Check if household name already exists
            with sqlite3.connect('roomies.db') as conn:
                rows = conn.execute("SELECT household FROM users WHERE household = ?", (household,))
                if len(rows.fetchall()) != 0:
                    return error("Household with this name already exists", 400)

            # Create new household
            with sqlite3.connect('roomies.db') as conn:
                conn.execute("UPDATE users SET household = ? WHERE id = ?", (household, user))

        elif action == "join":
            # Check if household name exists
            with sqlite3.connect('roomies.db') as conn:
                rows = conn.execute("SELECT household FROM users WHERE household = ?", (household,))
                if len(rows.fetchall()) == 0:
                    return error("Household with this name does not exist", 400)

            # Join existing household
            with sqlite3.connect('roomies.db') as conn:
                conn.execute("UPDATE users SET household = ? WHERE id = ?", (household, user))

        else:
            return error("Invalid action selected", 400)
        
        # Remember household that is logged in
        with sqlite3.connect('roomies.db') as conn:
            cursor = conn.execute("SELECT household FROM users WHERE id = ?", (user,))
            rows = cursor.fetchall
        session["household"] = rows[0][0]

        return redirect("/household")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("no_household.html")

@app.route("/household")
@login_required
@in_household_required
def household():
    user_id = session.get("user_id")

    return render_template("household.html")

@app.route("/shopping")
@in_household_required
def shopping():
    return render_template("shopping.html")


# Enable debug mode so changes are visible immediatly
if __name__ == '__main__':
    app.run()
