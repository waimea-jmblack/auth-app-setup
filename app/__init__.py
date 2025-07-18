#===========================================================
# App Creation and Launch
#===========================================================

from flask import Flask, render_template, request, flash, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import html

from app.helpers.session import init_session
from app.helpers.db import connect_db
from app.helpers.errors import init_error, not_found_error
from app.helpers.logging import init_logging
from app.helpers.auth import login_required


# Create the app
app = Flask(__name__)

# Configure app
init_session(app)   # Setup a session for messages, etc.
init_logging(app)   # Log requests
init_error(app)     # Handle errors and exceptions


#-----------------------------------------------------------
# Home page route
#-----------------------------------------------------------
@app.get("/")
def index():
    if "logged_in" in session:
        # Get the user id from the session
        user_id = session["user_id"]

        with connect_db() as client:
            # Get all the things from the data base
            sql = """
            SELECT from task.id, tasks.name, task.priority
            FROM tasks
            JOIN users ON task.user_id = users
            WHERE user.id=?
            ORDER BY priority DESC
        """
        values=[user_id]
        result = client.execute(sql, values)
        tasks = result.rows

        # And show them on the page
        return render_template("pages/home.jinja", tasks = tasks)
    else:
        return render_template("pages/welcome.jinja")


#-----------------------------------------------------------
# User registration form route
#-----------------------------------------------------------
@app.get("/register")
def register_form():
    return render_template("pages/register.jinja")


#-----------------------------------------------------------
# User login form route
#-----------------------------------------------------------
@app.get("/login")
def login_form():
    return render_template("pages/login.jinja")


#-----------------------------------------------------------
# Things page route - Show all the things, and new thing form
#-----------------------------------------------------------
@app.get("/things/")
def show_all_things():
    with connect_db() as client:
        # Get all the things from the DB
        sql = """
            SELECT things.id,
                   things.name,
                   users.name AS owner

            FROM things
            JOIN users ON things.user_id = users.id

            ORDER BY things.name ASC
        """
        result = client.execute(sql)
        things = result.rows

        # And show them on the page
        return render_template("pages/things.jinja", things=things)


#-----------------------------------------------------------
# Thing page route - Show details of a single thing
#-----------------------------------------------------------
@app.get("/thing/<int:id>")
def show_one_thing(id):
    with connect_db() as client:
        # Get the thing details from the DB, including the owner info
        sql = """
            SELECT things.id,
                   things.name,
                   things.price,
                   things.user_id,
                   users.name AS owner

            FROM things
            JOIN users ON things.user_id = users.id

            WHERE things.id=?
        """
        values = [id]
        result = client.execute(sql, values)

        # Did we get a result?
        if result.rows:
            # yes, so show it on the page
            thing = result.rows[0]
            return render_template("pages/thing.jinja", thing=thing)

        else:
            # No, so show error
            return not_found_error()


#-----------------------------------------------------------
# Route for adding a thing, using data posted from a form
# - Restricted to logged in users
#-----------------------------------------------------------
@app.post("/add")
@login_required
def add_a_thing():
    # Get the data from the form
    name  = request.form.get("name")
    price = request.form.get("price")

    # Sanitise the inputs
    name = html.escape(name)
    price = html.escape(price)

    # Get the user id from the session
    user_id = session["user_id"]

    with connect_db() as client:
        # Add the thing to the DB
        sql = "INSERT INTO things (name, price, user_id) VALUES (?, ?, ?)"
        values = [name, price, user_id]
        client.execute(sql, values)

        # Go back to the home page
        flash(f"Thing '{name}' added", "success")
        return redirect("/things")


#-----------------------------------------------------------
# Route for deleting a thing, Id given in the route
# - Restricted to logged in users
#-----------------------------------------------------------
@app.get("/delete/<int:id>")
@login_required
def delete_a_thing(id):
    # Get the user id from the session
    user_id = session["user_id"]

    with connect_db() as client:
        # Delete the thing from the DB only if we own it
        sql = "DELETE FROM things WHERE id=? AND user_id=?"
        values = [id, user_id]
        client.execute(sql, values)

        # Go back to the home page
        flash("Thing deleted", "success")
        return redirect("/things")


#-----------------------------------------------------------
# Route for adding a user when registration form submitted
#-----------------------------------------------------------
@app.post("/add-user")
def add_user():
    # Get the data from the form
    name = request.form.get("name")
    username = request.form.get("username")
    password = request.form.get("password")

    with connect_db() as client:
        # Attempt to find an existing record for that user
        sql = "SELECT * FROM users WHERE username = ?"
        values = [username]
        result = client.execute(sql, values)

        # No existing record found, so safe to add the user
        if not result.rows:
            # Sanitise the name
            name = html.escape(name)

            # Salt and hash the password
            hash = generate_password_hash(password)

            # Add the user to the users table
            sql = "INSERT INTO users (name, username, password_hash) VALUES (?, ?, ?)"
            values = [name, username, hash]
            client.execute(sql, values)

            # And let them know it was successful and they can login
            flash("Registration successful", "success")
            return redirect("/login")

        # Found an existing record, so prompt to try again
        flash("Username already exists. Try again...", "error")
        return redirect("/register")


#-----------------------------------------------------------
# Route for processing a user login
#-----------------------------------------------------------
@app.post("/login-user")
def login_user():
    # Get the login form data
    username = request.form.get("username")
    password = request.form.get("password")

    with connect_db() as client:
        # Attempt to find a record for that user
        sql = "SELECT * FROM users WHERE username = ?"
        values = [username]
        result = client.execute(sql, values)

        # Did we find a record?
        if result.rows:
            # Yes, so check password
            user = result.rows[0]
            hash = user["password_hash"]

            # Hash matches?
            if check_password_hash(hash, password):
                # Yes, so save info in the session
                session["user_id"]   = user["id"]
                session["user_name"] = user["name"]
                session["logged_in"] = True

                # And head back to the home page
                flash("Login successful", "success")
                return redirect("/")

        # Either username not found, or password was wrong
        flash("Invalid credentials", "error")
        return redirect("/login")


#-----------------------------------------------------------
# Route for processing a user logout
#-----------------------------------------------------------
@app.get("/logout")
def logout():
    # Clear the details from the session
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("logged_in", None)

    # And head back to the home page
    flash("Logged out successfully", "success")
    return redirect("/")



#-------------------------------------------------------------------------------------------    _/(o.o)\_ 
# Liquidity is the amount of liquid cash you have on you (not your assets and liabilities). 
# Broke people see liabilities as assists (Transportation, Technological appliances, Power, etc.). 
# Great minds use assets to build wealth and have few liabilities (Student loan, House (kind of)). 
# A house can be both a liability and an asset. It is a liability if it does not make you money; it is an asset when it does (Air BNB for example). 
# The power of compounding starts small but becomes unfathomably enormous over many years. 
# Start investing at a young age, Warren buffet was 10 when he began. 
# At 18 you want to get a credit card and buy a few small things with it at least once a month, then pay it back. This boosts your credit score (Banks happy). 
# Forex, or also know as Foreign Exchange, is a place where you can exchange global currencies as prices fluctuate. 
# Discipline over Motivation 
# Live by the Law of Attraction. You need to be delusional to achieve the dreams of the few. 
# Your Mind is your greatest asset. Keep on expanding it otherwise you will lose it.
# As a man you can't build yourself while also focusing on a girlfriend, there will be a time and a place in the future. 
# Everyone is delt their own set of cards. Life is unfair and they will use their cards to their advantage to win. How will you use yours? 
# School is only a brick in my fortress, use it as a building block to learn from, but now something to determine your future. 
# History shows us that school was made to turn thinkers into workers. You must remember to be a thinker while others work. 
# Japanese candles tell us a story of what has happened to the market and what is to come. 
# Cut out all detractions, people like to see you doing well, but never better than them. Don't stand out or you will be pulled down. Stay silent. 
# This game that we call life will make you lose your mind, but in the end, you will make it. But you must never give up. 
# Failure is a learning experience but giving up is giving up. NEVER GIVE UP. 
#========================================================================================
#