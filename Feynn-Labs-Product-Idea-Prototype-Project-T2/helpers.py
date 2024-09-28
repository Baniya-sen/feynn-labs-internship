import json
import sqlite3

import pandas as pd
from scipy.spatial.distance import euclidean
from sklearn.preprocessing import MinMaxScaler

from flask import redirect, render_template, session, g, current_app
from functools import wraps


def get_db():
    """Opens database connection if doesn't exists"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DATABASE'])
        cursor = db.cursor()
        cursor.execute("BEGIN TRANSACTION;")
        create_tables(cursor)
        cursor.execute("COMMIT;")
        db.commit()
    return db


def login_required(f):
    """Checks if a user is currently logged in or not"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def apology(message, code=400):
    """Render message as an apology to user"""

    def string_handle(s):
        """Filters invalid symbols from message"""
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=string_handle(message)), code


def rupees(value):
    """Format value as Indian Rupees $"""
    return f"₹{value:,.2f}"


def rating(stars):
    """Format rating to round to 2 decimals"""
    return f"{stars:,.1f}"


def distance(measure):
    """Format distance to KM"""
    return f"{measure} KM"


def percent(number):
    """Format number as percent"""
    return f"{number}%"


def create_tables(database_cursor):
    """Creates tables to store data in finance.db if doesnt exists"""
    database_cursor.execute("""CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                username TEXT NOT NULL,
                                hash TEXT NOT NULL)""")

    database_cursor.execute("""CREATE TABLE IF NOT EXISTS city_services (
                                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                                city_name TEXT NOT NULL,
                                state_name TEXT NOT NULL,
                                services TEXT
                                )""")

    database_cursor.execute("""CREATE TABLE IF NOT EXISTS all_vendors (
                                city_id,
                                vendor_type TEXT NOT NULL,
                                vendor_name TEXT NOT NULL,
                                visit_charge INTEGER,
                                vendor_number INTEGER NOT NULL,
                                vendor_email TEXT,
                                city_name TEXT NOT NULL,
                                state_name TEXT NOT NULL,
                                vendor_rating INTEGER,
                                vendor_distance INTEGER,
                                FOREIGN KEY(city_id) REFERENCES city_services(id))""")


def adding_vendor(profession, state, city, name, charge, phone, email, ratings, distances):
    """Stores user sell transaction into database"""
    db = get_db()

    try:
        cursor = db.cursor()
        cursor.execute("BEGIN TRANSACTION;")

        services_in_city = cursor.execute(
            """SELECT id, services FROM city_services WHERE city_name = ? AND state_name = ?""",
            (city, state)
        ).fetchone()
        if not services_in_city:
            cursor.execute(
                """INSERT INTO city_services (city_name, state_name, services) VALUES (?, ?, ?)""",
                (city, state, json.dumps([profession]))
            )
            city_id = cursor.lastrowid
            services = [profession]
        else:
            city_id, services = services_in_city
            services = json.loads(services)

        if profession not in services:
            services.append(profession)
            services = json.dumps(services)

            cursor.execute(
                """UPDATE city_services SET services = ?
                         WHERE city_name = ? AND state_name = ?;""",
                (services, city, state)
            )

        cursor.execute(
            """INSERT INTO all_vendors VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (city_id, profession, name, charge, phone, email, city, state, ratings, distances)
        )

        cursor.execute("COMMIT;")

    except sqlite3.OperationalError:
        db.rollback()
        print("SOMETHING WENT WRONG")


def get_vendors(city, profession):
    db = get_db()
    cursor = db.cursor()

    query = """
        SELECT * FROM all_vendors 
        INNER JOIN city_services 
        ON all_vendors.city_id = city_services.id
        WHERE city_services.city_name = ? AND all_vendors.vendor_type = ?
    """
    cursor.execute(query, (city, profession))
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()

    vendors = pd.DataFrame(rows, columns=columns)
    return vendors


def normalize_scaler(data):
    scaler = MinMaxScaler()

    columns_to_normalize = ['visit_charge', 'vendor_rating', 'vendor_distance']
    data[columns_to_normalize] = scaler.fit_transform(data[columns_to_normalize])

    return data


def recommend_vendors(city, profession, user_preference):
    vendors = get_vendors(city, profession)

    if vendors.empty:
        return []

    original_vendors = vendors.copy()
    normalized_vendors = normalize_scaler(vendors)

    preferences = {
        "budget": [0.01, 0.6, 0.3],  # low cost, medium rating, distance bit a problem
        "mainstream": [0.3, 0.8, 0.3],  # medium cost, a bit high rating, distance bit a problem
        "premium": [0.9, 0.9, 0.2]  # cost doesn't matter, high rating, low distance matters
    }

    original_vendors['euclidean_distance'] = normalized_vendors.apply(
        lambda row: euclidean(
            [row['visit_charge'], row['vendor_rating'], row['vendor_distance']],
            preferences[user_preference]
        ), axis=1
    )

    original_vendors['match_percentage'] = original_vendors['euclidean_distance'].apply(
        lambda dist: round((1 - round(dist, 2)) * 100)
    )

    sorted_vendors = original_vendors.sort_values(
        by='match_percentage', ascending=False
    ).reset_index(drop=True)

    sorted_vendors_list = sorted_vendors.to_dict(orient='records')
    return sorted_vendors_list
