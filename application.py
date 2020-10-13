import os, sqlalchemy, csv

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd


# Configure application
app = Flask(__name__)
app.secret_key ='12345'

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure postgress
engine = create_engine("postgres://axsjbatuinzkdr:5f6713832d769e73ceaf17e580665fce3161c61a206ee6dd0f7803125c8f0123@ec2-23-23-36-227.compute-1.amazonaws.com:5432/d88q9qg34dtglm")
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods=["GET"])
@login_required
def index():
    
    return apology("hope", 403)



@app.route("/import", methods=["GET", "POST"])
@login_required
def importcsv():
    """import csv files"""
    if request.method == "GET":
        username = db.execute("SELECT username FROM users WHERE id =:id", {"id": session["user_id"]}).fetchone()
        return render_template("import.html", username=username)
    else:
        #sales_file = request.files['csv']
        #sales_file.save(os.path.join(app.config["SALES_DATA"], sales_file.filename))
        f = open("flights.csv")
        read = csv.reader(f)
        date = request.form.get("date")

        for item, salesamount, quantity in read:
            db.execute("INSERT INTO sales(userid, item, sales_amount, quantity) VALUES(:userid, :item, :sales_amount, :quantity)", 
                {"userid": session["user_id"], "item": item, "sales_amount": salesamount, "quantity": quantity}) 
        db.commit

        return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        username = request.form.get("username")
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                        {"username":username})
        
        # Ensure username exists and password is correct
        if db.execute("SELECT * FROM users WHERE username =:username", {"username":username}).rowcount != 1:
            if check_password_hash(rows[0]["hash"], request.form.get("password")):
                return apology("invalid username and/or password", 403)
 
        # Remember which user has logged in
         
        sessionid = (''.join(map(str, rows)))
        session["user_id"] = sessionid




        # Redirect user to home page
        return redirect("/")

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


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method =="GET":
        return render_template("register.html")
    else:
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password", 403)

        #password req check
        #if len(request.form.get("password")) < 6:
        #    return apology("pass length should be at least 6 char", 403)
        #if len(request.form.get("password")) > 20:
        #    return apology("pass length should not be greater than 19 char", 403)
        #if not any(char.isdigit() for char in request.form.get("password")):
        #    return apology("pass should have at least one number", 403)
        #if not any(char.isupper() for char in request.form.get("password")):
        #    return apology("pass should have at least one uppercase letter", 403)
        #if not any(char.islower() for char in request.form.get("password")):
        #    return apology("pass should have at least one lowercase letter", 403)
        #password
        if request.form.get("confirm password") != request.form.get("password"):
            return apology("passwords do not match", 403)
        
        username = request.form.get("username")  
        password = generate_password_hash(request.form.get("password"))

        if db.execute("SELECT * FROM users WHERE username =:username", {"username": username}).rowcount == 0:
            db.execute("INSERT INTO users(username, hash) VALUES(:username, :hash)", {"username": username, "hash": password})
            db.commit()
            
            user = db.execute("SELECT id FROM users WHERE username =:username", {"username": username}).fetchone()
            sessionid = (''.join(map(str, user)))
            session["user_id"] = sessionid
            
            return redirect("/")
        else:
            return apology("Username already taken")
        


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)

# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


