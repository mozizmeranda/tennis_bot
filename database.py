import sqlite3 as sq
# import asyncpg
# import aiosqlite


class Database:

    def __init__(self, db_name="users.db"):
        self.path_to_db = db_name

    @property
    def connection(self):
        return sq.connect(self.path_to_db)

    def execute(self, sql: str, parameters: tuple = None, fetchone=False, fetchall=False, commit=False):
        if not parameters:
            parameters = tuple()

        connection = self.connection
        cursor = connection.cursor()
        data = None
        cursor.execute(sql, parameters)
        if fetchone:
            data = cursor.fetchone()
        if fetchall:
            data = cursor.fetchall()
        if commit:
            connection.commit()
        connection.close()

        return data

    def create_table(self):
        sql = ("CREATE TABLE IF NOT EXISTS users ("
               "id INTEGER UNIQUE NOT NULL, name TEXT, username TEXT, number TEXT)")
        self.execute(sql, commit=True)

    def create_booking_table(self):
        sql = """CREATE TABLE IF NOT EXISTS bookings (
                    telegram_id INTEGER NOT NULL,
                    court_number INTEGER NOT NULL,
                    location TEXT NOT NULL,
                    booking_date DATE NOT NULL,
                    time_slot TEXT NOT NULL,
                    screenshot_path TEXT
                )"""
        self.execute(sql)

    def insert_into(self, id, name, username, number):
        sql = "INSERT OR IGNORE INTO users (id, name, username, number) VALUES (?, ?, ?, ?)"
        params = (id, name, username, number)
        self.execute(sql, parameters=params, commit=True)

    def create_booking(self, telegram_id, court_number, location, booking_date, time_slot, screenshot):
        sql = ("INSERT OR IGNORE INTO bookings "
               "(telegram_id, court_number, location, booking_date, time_slot, screenshot_path) "
               "VALUES (?, ?, ?, ?, ?, ?)")
        params = (telegram_id, court_number, location, booking_date, time_slot, screenshot)
        self.execute(sql, parameters=params, commit=True)

    def check_free_courts(self, date, time, location):
        sql = "SELECT * FROM bookings WHERE booking_date=? AND time_slot=? AND location=?"
        params = (date, time, location)
        lst = []
        bookings = self.execute(sql, parameters=params, fetchall=True)
        for booking in bookings:
            lst.append(booking[1])
        return lst

    def get_number_by_id(self, id):
        sql = "SELECT number FROM users WHERE id=?"
        params = (id,)
        return self.execute(sql, parameters=params, fetchone=True)[0]


db = Database()
# db.create_table()


