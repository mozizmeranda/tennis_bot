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

    def table_to_delete(self):
        sql = "CREATE TABLE IF NOT EXISTS deletes(telegram_id INTEGER, message_id INTEGER)"
        self.execute(sql, commit=True)

    def create_pending(self):
        sql = "CREATE TABLE IF NOT EXISTS pending_table(location TEXT, day TEXT, time_slot TEXT)"
        self.execute(sql, commit=True)

    def create_booking_table(self):
        sql = """CREATE TABLE IF NOT EXISTS bookings (
                    telegram_id INTEGER NOT NULL,
                    location TEXT NOT NULL,
                    booking_date DATE NOT NULL,
                    time_slot TEXT NOT NULL,
                    screenshot_path TEXT
                )"""
        self.execute(sql, commit=True)

    def insert_into(self, id, name, username, number):
        sql = "INSERT OR IGNORE INTO users (id, name, username, number) VALUES (?, ?, ?, ?)"
        params = (id, name, username, number)
        self.execute(sql, parameters=params, commit=True)

    def create_booking(self, telegram_id, location, booking_date, time_slot, screenshot):
        sql = ("INSERT OR IGNORE INTO bookings "
               "(telegram_id, location, booking_date, time_slot, screenshot_path) "
               "VALUES (?, ?, ?, ?, ?)")
        params = (telegram_id,location, booking_date, time_slot, screenshot)
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

    def get_user_data_by_id(self, id):
        sql = "SELECT number, username FROM users WHERE id=?"
        params = (id,)
        return self.execute(sql, parameters=params, fetchone=True)

    def insert_table_deletes(self, telegram_id, message_id):
        sql = "INSERT OR IGNORE INTO deletes (telegram_id, message_id) VALUES (?, ?)"
        params = (telegram_id, message_id)
        self.execute(sql, parameters=params, commit=True)

    def delete_from_deletes_table(self, telegram_id):
        sql = "DELETE FROM deletes WHERE telegram_id=?"
        params = (telegram_id,)
        self.execute(sql, parameters=params, commit=True)

    def get_all_users(self):
        sql = "SELECT id FROM users"
        return self.execute(sql, fetchall=True)

    def get_all_bookings(self, telegram_id):
        sql = f"SELECT * FROM bookings WHERE telegram_id={telegram_id}"
        # params = (telegram_id,)
        data = self.execute(sql, fetchall=True)
        return data

    def get_day_bookings(self, day):
        sql = "SELECT * FROM bookings WHERE booking_date=?"
        params = (day,)
        return self.execute(sql, parameters=params, fetchall=True)

    def delete_booking(self, day):
        sql = "DELETE FROM bookings WHERE booking_date=?"
        params = (day,)
        self.execute(sql, parameters=params, commit=True)

    # ---------- DELETES BEGIN -----------

    def get_message_id(self, telegram_id):
        sql = "SELECT message_id FROM deletes WHERE telegram_id=?"
        params = (telegram_id,)
        return self.execute(sql, parameters=params, fetchone=True)

    def delete_message_id(self, telegram_id):
        sql = "DELETE FROM deletes WHERE telegram_id=?"
        params = (telegram_id,)
        return self.execute(sql, parameters=params, commit=True)

    # ----------------- DELETES END ---------------------


   # ---------------- PENDING TABLE ------------------------

    def create_pending_rent(self, location, day, time_slot):
        sql = "INSERT INTO pending_table(location, day, time_slot) VALUES (?, ?, ?)"
        params = (location, day, time_slot)
        self.execute(sql, parameters=params, commit=True)

    def is_it_pending(self, location, day, time_slot):
        sql = "SELECT * FROM pending_table WHERE location=? AND day=? AND time_slot=?"
        params = (location, day, time_slot)
        data = self.execute(sql, parameters=params, fetchone=True)
        if data:
            return 1
        else:
            return 0
        # return data

    def kill_pending(self, location, date, time_slot):
        sql = "DELETE FROM pending_table WHERE location=? AND day=? AND time_slot=?"
        params = (location, date, time_slot)
        self.execute(sql, parameters=params, commit=True)


db = Database()
# print(db.is_it_pending("A", "2025-11-12", "12:00-13:00"))
# db.create_pending()
# db.table_to_delete()
# db.create_table()


