from database import Database



class CalendarDB(Database):

    async def get_user(self, telegram_id: int) -> Optional[dict]:
        sql = "SELECT telegram_id, username, full_name, created_at FROM calendar_users WHERE telegram_id=?"
        params = (telegram_id,)
        try:
            row = await self.execute(sql, parameters=params, fetchone=True)
            if not row:
                return None
            return {
                "telegram_id": row[0],
                "username": row[1],
                "full_name": row[2],
                "created_at": row[3],
            }
        except Exception:
            logger.exception("get_user failed: telegram_id=%s", telegram_id)
            return None

    async def get_all_calendar_users(self) -> List[dict]:
        sql = "SELECT telegram_id, username, full_name, created_at FROM calendar_users"
        try:
            rows = await self.execute(sql, fetchall=True)
            if not rows:
                return []
            return [
                {
                    "telegram_id": r[0],
                    "username": r[1],
                    "full_name": r[2],
                    "created_at": r[3],
                }
                for r in rows
            ]
        except Exception:
            logger.exception("get_all_users failed")
            return []

    @serialized_transaction
    async def create_user(
            self,
            telegram_id: int,
            username: Optional[str],
            full_name: str,
    ) -> Optional[dict]:
        sql = "INSERT OR IGNORE INTO calendar_users (telegram_id, username, full_name) VALUES (?, ?, ?)"
        params = (telegram_id, username, full_name)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return await self.get_user(telegram_id)
        except Exception:
            logger.exception("create_user failed: telegram_id=%s", telegram_id)
            return None

    @serialized_transaction
    async def delete_user(self, telegram_id: int) -> bool:
        sql = "DELETE FROM calendar_users WHERE telegram_id=?"
        params = (telegram_id,)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return True
        except Exception:
            logger.exception("delete_user failed: telegram_id=%s", telegram_id)
            return False

    # ──────────────────────────────────────────────────────────────────────────
    #  CALENDARS
    # ──────────────────────────────────────────────────────────────────────────

    async def get_calendar(self, calendar_id: int) -> Optional[dict]:
        sql = "SELECT id, name, max_events_per_hour, created_at FROM calendars WHERE id=?"
        params = (calendar_id,)
        try:
            row = await self.execute(sql, parameters=params, fetchone=True)
            if not row:
                return None
            return {
                "id": row[0],
                "name": row[1],
                "max_events_per_hour": row[2],
                "created_at": row[3],
            }
        except Exception:
            logger.exception("get_calendar failed: calendar_id=%s", calendar_id)
            return None

    async def get_user_calendars(self, telegram_id: int) -> List[dict]:
        sql = """
            SELECT c.id, c.name, c.max_events_per_hour, c.created_at
            FROM calendars c
            JOIN calendar_members cm ON c.id = cm.calendar_id
            WHERE cm.telegram_id=?
        """
        params = (telegram_id,)
        try:
            rows = await self.execute(sql, parameters=params, fetchall=True)
            if not rows:
                return []
            return [
                {
                    "id": r[0],
                    "name": r[1],
                    "max_events_per_hour": r[2],
                    "created_at": r[3],
                }
                for r in rows
            ]
        except Exception:
            logger.exception("get_user_calendars failed: telegram_id=%s", telegram_id)
            return []

    @serialized_transaction
    async def create_calendar(
            self,
            name: str,
            max_events_per_hour: int = 1,
            owner_telegram_id: Optional[int] = None,
    ) -> Optional[dict]:
        try:
            await self.connection.execute(
                "INSERT INTO calendars (name, max_events_per_hour) VALUES (?, ?)",
                (name, max_events_per_hour),
            )
            cursor = await self.connection.execute("SELECT last_insert_rowid()")
            row = await cursor.fetchone()
            calendar_id = row[0]

            if owner_telegram_id is not None:
                await self.connection.execute(
                    "INSERT OR IGNORE INTO calendar_members (calendar_id, telegram_id) VALUES (?, ?)",
                    (calendar_id, owner_telegram_id),
                )

            await self.connection.commit()
            return await self.get_calendar(calendar_id)
        except Exception:
            await self.connection.rollback()
            logger.exception("create_calendar failed: name=%s", name)
            return None

    @serialized_transaction
    async def delete_calendar(self, calendar_id: int) -> bool:
        sql = "DELETE FROM calendars WHERE id=?"
        params = (calendar_id,)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return True
        except Exception:
            logger.exception("delete_calendar failed: calendar_id=%s", calendar_id)
            return False

    @serialized_transaction
    async def update_calendar_capacity(
            self, calendar_id: int, max_events_per_hour: int
    ) -> Optional[dict]:
        sql = "UPDATE calendars SET max_events_per_hour=? WHERE id=?"
        params = (max_events_per_hour, calendar_id)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return await self.get_calendar(calendar_id)
        except Exception:
            logger.exception("update_calendar_capacity failed: calendar_id=%s", calendar_id)
            return None

    # ──────────────────────────────────────────────────────────────────────────
    #  CALENDAR MEMBERS
    # ──────────────────────────────────────────────────────────────────────────

    async def check_member_access(self, calendar_id: int, telegram_id: int) -> bool:
        sql = "SELECT 1 FROM calendar_members WHERE calendar_id=? AND telegram_id=?"
        params = (calendar_id, telegram_id)
        try:
            row = await self.execute(sql, parameters=params, fetchone=True)
            return row is not None
        except Exception:
            logger.exception("check_member_access failed: calendar_id=%s, telegram_id=%s", calendar_id, telegram_id)
            return False

    async def get_calendar_members(self, calendar_id: int) -> List[dict]:
        sql = "SELECT calendar_id, telegram_id FROM calendar_members WHERE calendar_id=?"
        params = (calendar_id,)
        try:
            rows = await self.execute(sql, parameters=params, fetchall=True)
            if not rows:
                return []
            return [{"calendar_id": r[0], "telegram_id": r[1]} for r in rows]
        except Exception:
            logger.exception("get_calendar_members failed: calendar_id=%s", calendar_id)
            return []

    @serialized_transaction
    async def add_member(self, calendar_id: int, telegram_id: int) -> Optional[dict]:
        sql = "INSERT OR IGNORE INTO calendar_members (calendar_id, telegram_id) VALUES (?, ?)"
        params = (calendar_id, telegram_id)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return {"calendar_id": calendar_id, "telegram_id": telegram_id}
        except Exception:
            logger.exception("add_member failed: calendar_id=%s, telegram_id=%s", calendar_id, telegram_id)
            return None

    @serialized_transaction
    async def remove_member(self, calendar_id: int, telegram_id: int) -> bool:
        sql = "DELETE FROM calendar_members WHERE calendar_id=? AND telegram_id=?"
        params = (calendar_id, telegram_id)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return True
        except Exception:
            logger.exception("remove_member failed: calendar_id=%s, telegram_id=%s", calendar_id, telegram_id)
            return False

    # ──────────────────────────────────────────────────────────────────────────
    #  SINGLE EVENTS
    # ──────────────────────────────────────────────────────────────────────────

    async def get_single_event(self, event_id: int) -> Optional[dict]:
        sql = """
            SELECT id, calendar_id, created_by, title,
                   start_datetime, end_datetime, status, recurring_event_id, created_at
            FROM single_events WHERE id=?
        """
        params = (event_id,)
        try:
            row = await self.execute(sql, parameters=params, fetchone=True)
            if not row:
                return None
            return {
                "id": row[0],
                "calendar_id": row[1],
                "created_by": row[2],
                "title": row[3],
                "start_datetime": row[4],
                "end_datetime": row[5],
                "status": row[6],
                "recurring_event_id": row[7],
                "created_at": row[8],
            }
        except Exception:
            logger.exception("get_single_event failed: event_id=%s", event_id)
            return None

    async def get_single_events_for_calendar(
            self,
            calendar_id: int,
            from_dt: str,
            to_dt: str,
            statuses: Optional[List[str]] = None,
    ) -> List[dict]:
        """
        from_dt / to_dt — строки в формате 'YYYY-MM-DD HH:MM:SS'.
        statuses — опциональный список статусов (напр. ['confirmed', 'pending_payment']).
        """
        try:
            if statuses:
                placeholders = ", ".join("?" * len(statuses))
                sql = f"""
                    SELECT id, calendar_id, created_by, title,
                           start_datetime, end_datetime, status, recurring_event_id, created_at
                    FROM single_events
                    WHERE calendar_id=? AND start_datetime>=? AND end_datetime<=?
                      AND status IN ({placeholders})
                """
                params = (calendar_id, from_dt, to_dt, *statuses)
            else:
                sql = """
                    SELECT id, calendar_id, created_by, title,
                           start_datetime, end_datetime, status, recurring_event_id, created_at
                    FROM single_events
                    WHERE calendar_id=? AND start_datetime>=? AND end_datetime<=?
                """
                params = (calendar_id, from_dt, to_dt)

            rows = await self.execute(sql, parameters=params, fetchall=True)
            if not rows:
                return []
            return [
                {
                    "id": r[0],
                    "calendar_id": r[1],
                    "created_by": r[2],
                    "title": r[3],
                    "start_datetime": r[4],
                    "end_datetime": r[5],
                    "status": r[6],
                    "recurring_event_id": r[7],
                    "created_at": r[8],
                }
                for r in rows
            ]
        except Exception:
            logger.exception("get_single_events_for_calendar failed: calendar_id=%s", calendar_id)
            return []

    @serialized_transaction
    async def create_single_event(
            self,
            calendar_id: int,
            created_by: int,
            title: str,
            start_datetime: str,
            end_datetime: str,
            status: str,
            recurring_event_id: Optional[int] = None,
    ) -> Optional[dict]:
        """start_datetime / end_datetime — строки 'YYYY-MM-DD HH:MM:SS'."""
        sql = """
            INSERT INTO single_events
                (calendar_id, created_by, title, start_datetime, end_datetime, status, recurring_event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (calendar_id, created_by, title, start_datetime, end_datetime, status, recurring_event_id)
        try:
            await self.execute(sql, parameters=params, commit=True)
            row = await self.execute("SELECT last_insert_rowid()", fetchone=True)
            return await self.get_single_event(row[0])
        except Exception:
            logger.exception("create_single_event failed: calendar_id=%s", calendar_id)
            return None

    @serialized_transaction
    async def update_single_event(
            self,
            event_id: int,
            start_datetime: str,
            end_datetime: str,
    ) -> Optional[dict]:
        sql = "UPDATE single_events SET start_datetime=?, end_datetime=? WHERE id=?"
        params = (start_datetime, end_datetime, event_id)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return await self.get_single_event(event_id)
        except Exception:
            logger.exception("update_single_event failed: event_id=%s", event_id)
            return None

    @serialized_transaction
    async def update_single_event_status(self, event_id: int, status: str) -> Optional[dict]:
        sql = "UPDATE single_events SET status=? WHERE id=?"
        params = (status, event_id)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return await self.get_single_event(event_id)
        except Exception:
            logger.exception("update_single_event_status failed: event_id=%s", event_id)
            return None

    @serialized_transaction
    async def delete_single_event(self, event_id: int) -> bool:
        sql = "DELETE FROM single_events WHERE id=?"
        params = (event_id,)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return True
        except Exception:
            logger.exception("delete_single_event failed: event_id=%s", event_id)
            return False

    # ──────────────────────────────────────────────────────────────────────────
    #  RECURRING EVENTS
    # ──────────────────────────────────────────────────────────────────────────

    async def get_recurring_event(self, event_id: int) -> Optional[dict]:
        sql = """
            SELECT id, calendar_id, created_by, title,
                   day_of_week, start_time, end_time, created_at
            FROM recurring_events WHERE id=?
        """
        params = (event_id,)
        try:
            row = await self.execute(sql, parameters=params, fetchone=True)
            if not row:
                return None
            return {
                "id": row[0],
                "calendar_id": row[1],
                "created_by": row[2],
                "title": row[3],
                "day_of_week": row[4],
                "start_time": row[5],
                "end_time": row[6],
                "created_at": row[7],
            }
        except Exception:
            logger.exception("get_recurring_event failed: event_id=%s", event_id)
            return None

    async def get_recurring_events_for_calendar(
            self,
            calendar_id: int,
            days_of_week: Optional[List[int]] = None,
    ) -> List[dict]:
        try:
            if days_of_week is not None:
                placeholders = ", ".join("?" * len(days_of_week))
                sql = f"""
                    SELECT id, calendar_id, created_by, title,
                           day_of_week, start_time, end_time, created_at
                    FROM recurring_events
                    WHERE calendar_id=? AND day_of_week IN ({placeholders})
                """
                params = (calendar_id, *days_of_week)
            else:
                sql = """
                    SELECT id, calendar_id, created_by, title,
                           day_of_week, start_time, end_time, created_at
                    FROM recurring_events WHERE calendar_id=?
                """
                params = (calendar_id,)

            rows = await self.execute(sql, parameters=params, fetchall=True)
            if not rows:
                return []
            return [
                {
                    "id": r[0],
                    "calendar_id": r[1],
                    "created_by": r[2],
                    "title": r[3],
                    "day_of_week": r[4],
                    "start_time": r[5],
                    "end_time": r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]
        except Exception:
            logger.exception("get_recurring_events_for_calendar failed: calendar_id=%s", calendar_id)
            return []

    @serialized_transaction
    async def create_recurring_event(
            self,
            calendar_id: int,
            created_by: int,
            title: str,
            day_of_week: int,
            start_time: str,
            end_time: str,
    ) -> Optional[dict]:
        """start_time / end_time — строки 'HH:MM:SS'."""
        sql = """
            INSERT INTO recurring_events
                (calendar_id, created_by, title, day_of_week, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (calendar_id, created_by, title, day_of_week, start_time, end_time)
        try:
            await self.execute(sql, parameters=params, commit=True)
            row = await self.execute("SELECT last_insert_rowid()", fetchone=True)
            return await self.get_recurring_event(row[0])
        except Exception:
            logger.exception("create_recurring_event failed: calendar_id=%s", calendar_id)
            return None

    @serialized_transaction
    async def create_recurring_events_bulk(
            self,
            calendar_id: int,
            created_by: int,
            title: str,
            days_of_week: List[int],
            start_time: str,
            end_time: str,
    ) -> List[dict]:
        """Создать события для нескольких дней недели в одном коммите."""
        sql = """
            INSERT INTO recurring_events
                (calendar_id, created_by, title, day_of_week, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        try:
            ids = []
            for day in days_of_week:
                await self.connection.execute(sql, (calendar_id, created_by, title, day, start_time, end_time))
                cursor = await self.connection.execute("SELECT last_insert_rowid()")
                row = await cursor.fetchone()
                ids.append(row[0])
            await self.connection.commit()

            result = []
            for event_id in ids:
                event = await self.get_recurring_event(event_id)
                if event:
                    result.append(event)
            return result
        except Exception:
            await self.connection.rollback()
            logger.exception("create_recurring_events_bulk failed: calendar_id=%s", calendar_id)
            return []

    @serialized_transaction
    async def delete_recurring_event(self, event_id: int) -> bool:
        sql = "DELETE FROM recurring_events WHERE id=?"
        params = (event_id,)
        try:
            await self.execute(sql, parameters=params, commit=True)
            return True
        except Exception:
            logger.exception("delete_recurring_event failed: event_id=%s", event_id)
            return False

    @serialized_transaction
    async def cancel_recurring_instance(
            self,
            recurring_event_id: int,
            cancel_date: str,
            created_by: int,
    ) -> Optional[dict]:
        """
        Отменить конкретный экземпляр повторяющегося события.
        cancel_date — строка 'YYYY-MM-DD'.
        Создаёт запись в single_events со статусом 'cancelled'.
        Возвращает None если событие не найдено или дата не совпадает с днём недели.
        """
        try:
            rec = await self.get_recurring_event(recurring_event_id)
            if not rec:
                return None

            dt = datetime.strptime(cancel_date, "%Y-%m-%d")
            if dt.weekday() != rec["day_of_week"]:
                return None

            start_dt = f"{cancel_date} {rec['start_time']}"
            end_dt = f"{cancel_date} {rec['end_time']}"

            sql = """
                INSERT INTO single_events
                    (calendar_id, created_by, title, start_datetime, end_datetime, status, recurring_event_id)
                VALUES (?, ?, ?, ?, ?, 'cancelled', ?)
            """
            params = (rec["calendar_id"], created_by, rec["title"], start_dt, end_dt, recurring_event_id)
            await self.execute(sql, parameters=params, commit=True)

            row = await self.execute("SELECT last_insert_rowid()", fetchone=True)
            return await self.get_single_event(row[0])
        except Exception:
            logger.exception("cancel_recurring_instance failed: recurring_event_id=%s", recurring_event_id)
            return None

    # ──────────────────────────────────────────────────────────────────────────
    #  STATS
    # ──────────────────────────────────────────────────────────────────────────

    async def get_calendar_stats(self, calendar_id: int) -> dict:
        """Статистика: активные, отменённые, кол-во повторяющихся серий."""
        try:
            active_row = await self.execute(
                "SELECT COUNT(*) FROM single_events WHERE calendar_id=? AND status IN ('confirmed', 'pending_payment')",
                parameters=(calendar_id,),
                fetchone=True,
            )
            cancelled_row = await self.execute(
                "SELECT COUNT(*) FROM single_events WHERE calendar_id=? AND status='cancelled'",
                parameters=(calendar_id,),
                fetchone=True,
            )
            recurring_row = await self.execute(
                "SELECT COUNT(*) FROM recurring_events WHERE calendar_id=?",
                parameters=(calendar_id,),
                fetchone=True,
            )
            return {
                "calendar_id": calendar_id,
                "active_single_events": active_row[0] if active_row else 0,
                "cancelled_events": cancelled_row[0] if cancelled_row else 0,
                "recurring_series": recurring_row[0] if recurring_row else 0,
            }
        except Exception:
            logger.exception("get_calendar_stats failed: calendar_id=%s", calendar_id)
            return {
                "calendar_id": calendar_id,
                "active_single_events": 0,
                "cancelled_events": 0,
                "recurring_series": 0,
            }

    async def get_events_on_date(self, calendar_id: int, target_date: str) -> dict:
        """
        Все активные события на конкретную дату.
        target_date — строка 'YYYY-MM-DD'.

        Возвращает: {"date": ..., "single_events": [...], "recurring_instances": [...]}
        """
        try:
            from_dt = f"{target_date} 00:00:00"
            to_dt = f"{target_date} 23:59:59"

            # Одиночные (confirmed / pending_payment)
            single_rows = await self.execute(
                """
                SELECT id, calendar_id, created_by, title,
                       start_datetime, end_datetime, status, recurring_event_id, created_at
                FROM single_events
                WHERE calendar_id=? AND start_datetime>=? AND end_datetime<=?
                  AND status IN ('confirmed', 'pending_payment')
                """,
                parameters=(calendar_id, from_dt, to_dt),
                fetchall=True,
            )

            # Отменённые экземпляры повторяющихся (чтобы исключить из виртуальных)
            cancelled_rows = await self.execute(
                """
                SELECT recurring_event_id FROM single_events
                WHERE calendar_id=? AND start_datetime>=? AND end_datetime<=?
                  AND status='cancelled' AND recurring_event_id IS NOT NULL
                """,
                parameters=(calendar_id, from_dt, to_dt),
                fetchall=True,
            )
            cancelled_ids = {r[0] for r in cancelled_rows} if cancelled_rows else set()

            # Повторяющиеся на нужный день недели (0=Пн, 6=Вс)
            weekday = datetime.strptime(target_date, "%Y-%m-%d").weekday()
            recurring_rows = await self.execute(
                """
                SELECT id, title, start_time, end_time
                FROM recurring_events
                WHERE calendar_id=? AND day_of_week=?
                """,
                parameters=(calendar_id, weekday),
                fetchall=True,
            )

            recurring_instances = [
                {
                    "recurring_event_id": r[0],
                    "title": r[1],
                    "start_datetime": f"{target_date} {r[2]}",
                    "end_datetime": f"{target_date} {r[3]}",
                    "status": "confirmed",
                    "type": "recurring_instance",
                }
                for r in (recurring_rows or [])
                if r[0] not in cancelled_ids
            ]

            return {
                "date": target_date,
                "single_events": [
                    {
                        "id": r[0],
                        "calendar_id": r[1],
                        "created_by": r[2],
                        "title": r[3],
                        "start_datetime": r[4],
                        "end_datetime": r[5],
                        "status": r[6],
                        "recurring_event_id": r[7],
                        "created_at": r[8],
                    }
                    for r in (single_rows or [])
                ],
                "recurring_instances": recurring_instances,
            }
        except Exception:
            logger.exception("get_events_on_date failed: calendar_id=%s, target_date=%s", calendar_id, target_date)
            return {"date": target_date, "single_events": [], "recurring_instances": []}


