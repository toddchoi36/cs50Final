import os, sqlalchemy

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd


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
engine = create_engine("")
db = scoped_session(sessionmaker(bind=engine))

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    if request.method == "GET":
        assets = db.execute("SELECT * FROM assets WHERE userid =:userID ORDER BY symbol", {"userID": session["user_id"]}).fetchall()
        user_cash = db.execute("SELECT cash FROM users WHERE id =:id", {"id": session["user_id"]}).fetchall()
        for row in user_cash:
            cash = row[0]

        display_assets = []
        shares_total = 0
        hope = request.form.getlist('hope[]')

        for row in assets:
            Symbol = row["symbol"]
            Stock = lookup(Symbol) #create dictionary to look up current price for Price column
            Name = row["companyname"]
            Shares = row["shares"]
            Price = float(Stock["price"])
            Total = float(Shares)*Price #Total column of table for each stock
            shares_total = shares_total + Total #total of all shares in the table... to be added with cash to generate grand total
            display_assets.append({'Symbol':Symbol, 'CompanyName':Name, 'Shares':Shares, 'Price':Price, 'Total':Total})

        grand_total = shares_total + int(cash)
        return render_template("index.html", display_assets=display_assets, cash=cash, grand_total=grand_total, hope=hope)

    else:
        if not request.form.get("options"): #make sure to choose buy or sell
            return apology("choose buy or sell", 403)

        option = request.form['options']
        if option =="buy":
            assets = db.execute("SELECT Symbol FROM assets WHERE userID =:userID ORDER BY symbol", {"userID": session["user_id"]})
            a = 0 #initalize buy share getlist
            for row in assets:
                Symbol = row["symbol"]
                Stock = lookup(Symbol)
                buy_share = int(request.form.getlist("buy_sell_qty")[a])
                db.execute("UPDATE assets SET Shares = Shares + :buy_share, Price=:Price WHERE userID=:id AND Symbol=:symbol", {"buy_share": buy_share, "id": session["user_id"], "symbol": Symbol, "Price": Stock["price"]})

                user_cash = db.execute("SELECT cash FROM users WHERE id=:id", {"id": session["user_id"]})
                for row in user_cash:
                    cash = row[0]
                new_cash = cash - buy_share * int(Stock["price"])
                if new_cash < 0:
                    return apology("not enough money", 403)
                db.execute("UPDATE users SET cash =:new_cash WHERE id=:id", {"new_cash": new_cash, "id": session["user_id"]})
                db.commit()

                if buy_share != 0: #only add to history if buy qty is not 0
                    db.execute("INSERT INTO history (user_ID, Symbol, Shares, Price) VALUES(:userID, :Symbol, :buy_share, :Price)", {"userID": session["user_id"], "Symbol": Symbol, "buy_share": buy_share, "Price": Stock["price"]})
                    db.commit()
                a = a + 1 #increment row

            return redirect("/")

        elif option =="sell":
            assets = db.execute("SELECT * FROM assets WHERE userID =:userID ORDER BY symbol", {"userID": session["user_id"]})
            a = 0 #initalize buy share getlist
            for row in assets:
                Symbol = row["symbol"]
                Shares = row["shares"]
                Stock = lookup(Symbol)
                sell_share = int(request.form.getlist("buy_sell_qty")[a])
                if Shares < sell_share:
                    return apology("not enough shares")
                elif Shares == sell_share:
                    db.execute("UPDATE assets SET Shares = Shares - :sell_share, Price=:Price WHERE userID=:id AND Symbol=:symbol", {"sell_share": sell_share, "id": session["user_id"], "symbol":Symbol, "Price":Stock["price"]})
                    db.execute("DELETE FROM assets WHERE userID=:id AND Symbol=:Symbol", {"id": session["user_id"], "Symbol":Symbol})
                    db.commit()
                else:
                    db.execute("UPDATE assets SET Shares = Shares - :sell_share, Price=:Price WHERE userID=:id AND Symbol=:symbol", {"sell_share": sell_share, "id": session["user_id"], "symbol":Symbol, "Price":Stock["price"]})
                    db.commit()

                user_cash = db.execute("SELECT cash FROM users WHERE id=:id", {"id": session["user_id"]})
                for row in user_cash:
                    cash = row[0]
                new_cash = cash + sell_share * int(Stock["price"])

                db.execute("UPDATE users SET cash =:new_cash WHERE id=:id", {"new_cash": new_cash, "id": session["user_id"]})
                db.commit()
                if sell_share != 0: #only add to history if buy qty is not 0
                    db.execute("INSERT INTO history (user_ID, Symbol, Shares, Price) VALUES(:userID, :Symbol, :sell_share, :Price)", {"userID":session["user_id"], "Symbol": Symbol, "sell_share": 0-float(sell_share), "Price": Stock["price"]})
                    db.commit()
                    
                a = a + 1 #increment to next row for getlist

            return redirect("/")





@app.route("/import", methods=["GET", "POST"])
@login_required
def importcsv():
    """import csv files"""
    if request.method == "GET":
        return render_template("import.html")
    else:
        if not request.form.get("csv"):
            return apology("enter csv file", 403)

        filename = request.form.get("csv")
        f = open(filename)
        reader = csv.reader(f)

        for x, y, z in reader:
            db.execute("INSERT INTO Sales")
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

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                        {"username":request.form.get("username")})

        # Ensure username exists and password is correct
        if db.execute("SELECT * FROM users WHERE username = :username", {"username":request.form.get("username")}).rowcount != 1:
            if check_password_hash(rows[0]["hash"], request.form.get("password")):
                return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        for r in rows:
            sessionid = r[0]
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
            db.commit
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


