import sqlite3
import json
import datetime

from flask import Flask, render_template, redirect, g, request, session, jsonify
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import get_db, login_required, apology, rupees, rating, distance, percent
from helpers import adding_vendor, recommend_vendors
from config import PROFESSIONS, CITIES_BY_STATE

app = Flask(__name__)
app.config['DATABASE'] = 'dummy_database.db'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Custom filter for Rupees format
app.template_filter("INR")(rupees)
app.template_filter("RATING")(rating)
app.template_filter("KM")(distance)
app.template_filter("MEASURE")(percent)


def verify_db():
    current_date_time = datetime.datetime.now().strftime("%d-%m-%Y %I-%M %p")
    try:
        with open(app.config['DATABASE'], "r"):
            pass
    except FileNotFoundError:
        open("error.txt", "a").write(f"{current_date_time} - Database file not found!\n")
        return redirect("/logout")


@app.teardown_appcontext
def close_db(error="Database connection closed!"):
    """Closing db connection after each request"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        print(error)


@app.after_request
def after_request(response):
    """Cache system must be re-validated and to not store"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    verify_result = verify_db()
    if verify_result: return verify_result

    if request.method == "GET":
        user_location = session.setdefault("user_location", "Pune")
        cursor = get_db().cursor()
        all_services = cursor.execute(
            "SELECT services FROM city_services WHERE city_name = ?", (user_location,)
        ).fetchone()
        all_services = json.loads(all_services[0]) if all_services else []

        all_cities = [city for cities in CITIES_BY_STATE.values() for city in cities]
        all_professions = {
            profession: f'static/service_images/{profession}.png'
            for profession in all_services
        }
        close_db()

        return render_template(
            "index.html",
            location=user_location,
            cities=all_cities,
            services=all_professions
        )

    elif request.method == "POST":
        session["user_location"] = request.form.get("locationInput")
        return redirect("/")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "GET":
        return render_template("login.html")

    elif request.method == "POST":
        if not request.form.get("username") or not request.form.get("password"):
            return apology("At least provide a username/password!")

        db = get_db()
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        try:
            existing_username = dict(cursor.execute(
                "SELECT * FROM users WHERE username = ?", (request.form.get("username"),)).fetchone())
        except TypeError:
            return apology(f"Username '{request.form.get('username')}' does not exists!")
        finally:
            close_db()

        if not check_password_hash(existing_username["hash"], request.form.get("password")):
            return apology("Incorrect password!")

        session["user_id"] = existing_username["id"]
        return redirect("/")


@app.route("/logout")
@login_required
def logout():
    """Clear session id and return to log in"""
    session.clear()
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    elif request.method == "POST":
        if not request.form.get("username") or not request.form.get("password"):
            return apology("At least enter user/password")
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords mismatch!")

        db = get_db()
        cursor = db.cursor()

        existing_username = cursor.execute(
            "SELECT username FROM users WHERE username = ?",
            (request.form.get("username"),)
        ).fetchone()
        if existing_username is not None:
            return apology("Username already taken!")

        cursor.execute(
            "INSERT INTO users (username, hash) VALUES (?, ?)",
            (request.form.get("username"), generate_password_hash(request.form.get("password")))
        )
        db.commit()
        close_db()

        return redirect("/")


@app.route("/add_vendor", methods=["GET", "POST"])
@login_required
def add_vendor():
    if request.method == "GET":
        return render_template("add_vendor.html", professions=PROFESSIONS)

    elif request.method == "POST":
        adding_vendor(
            request.form.get("profession"),
            request.form.get("state"),
            request.form.get("city"),
            request.form.get("name"),
            request.form.get("charge"),
            request.form.get("phone"),
            request.form.get("email"),
            request.form.get("rating"),
            request.form.get("distance")
        )
        return redirect("/")


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    db = get_db()
    cursor = db.cursor()
    user_info = cursor.execute(
        "SELECT username FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if request.method == "GET":
        close_db()
        return render_template("account.html", userinfo=user_info)

    elif request.method == "POST":

        current_hash = cursor.execute(
            "SELECT hash FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()

        if not request.form.get("newPassword") or not request.form.get("confirmPassword"):
            return apology("Enter password/confirm password!")
        elif request.form.get("newPassword") != request.form.get("confirmPassword"):
            return apology("Password mismatch!")
        elif check_password_hash(current_hash[0], request.form.get("newPassword")):
            return apology("New password can't be same as old password!")

        cursor.execute(
            "UPDATE users SET hash = ? WHERE id = ?",
            (generate_password_hash(request.form.get("newPassword")), session["user_id"],)
        )
        db.commit()
        close_db()

        return redirect("/")


@app.route("/service/<city>/<profession>")
@login_required
def history(city, profession):
    """Recommend vendor on user preference type"""
    # Can be upgraded to implement sophisticated user preference model
    recommended_vendors = recommend_vendors(city, profession, "budget")
    return render_template("service.html", vendors=recommended_vendors)


@app.route('/get-cities')
def get_cities():
    state = request.args.get('state')
    cities = CITIES_BY_STATE.get(state, [])
    return jsonify({'cities': cities})


if __name__ == "__main__":
    app.run(debug=True)
