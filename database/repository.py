"""
Репозиторий для работы с данными
"""
from datetime import datetime, timedelta
from typing import List, Optional
from database.database import get_db
from database.models import Table, Booking, Hold
from config import settings


class BookingRepository:
    """Репозиторий для работы с бронированиями"""
    
    @staticmethod
    def create_booking(booking: Booking) -> int:
        """Создание нового бронирования"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bookings 
                (user_id, username, table_id, start_time, end_time, phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                booking.user_id,
                booking.username,
                booking.table_id,
                booking.start_time,
                booking.end_time,
                booking.phone,
                booking.created_at
            ))
            return cursor.lastrowid
    
    @staticmethod
    def get_user_bookings(user_id: int) -> List[Booking]:
        """Получение будущих бронирований пользователя"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bookings 
                WHERE user_id = ? AND status = 'active' AND end_time > ?
                ORDER BY start_time
            """, (user_id, datetime.now()))
            
            rows = cursor.fetchall()
            return [BookingRepository._row_to_booking(row) for row in rows]
    
    @staticmethod
    def get_today_bookings() -> List[Booking]:
        """Получение броней на сегодня"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bookings 
                WHERE status = 'active' 
                AND start_time >= ? AND start_time < ?
                ORDER BY start_time
            """, (today_start, today_end))
            
            rows = cursor.fetchall()
            return [BookingRepository._row_to_booking(row) for row in rows]
    
    @staticmethod
    def get_bookings_by_date(date: datetime) -> List[Booking]:
        """Получение всех броней на конкретную дату (включая отмененные)"""
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bookings 
                WHERE start_time >= ? AND start_time < ?
                ORDER BY start_time, status DESC
            """, (date_start, date_end))
            
            rows = cursor.fetchall()
            return [BookingRepository._row_to_booking(row) for row in rows]
    
    @staticmethod
    def cancel_booking(booking_id: int) -> bool:
        """Отмена бронирования"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bookings SET status = 'cancelled' 
                WHERE id = ? AND status = 'active'
            """, (booking_id,))
            return cursor.rowcount > 0
    
    @staticmethod
    def get_booking_by_id(booking_id: int) -> Optional[Booking]:
        """Получение бронирования по ID"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            row = cursor.fetchone()
            return BookingRepository._row_to_booking(row) if row else None
    
    @staticmethod
    def check_availability(table_id: Optional[int], start_time: datetime, 
                          end_time: datetime, exclude_user: Optional[int] = None) -> bool:
        """Проверка доступности слота"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Проверка бронирований
            query = """
                SELECT COUNT(*) as count FROM bookings 
                WHERE status = 'active'
                AND start_time < ? AND end_time > ?
            """
            params = [end_time, start_time]
            
            if table_id is not None:
                query += " AND table_id = ?"
                params.append(table_id)
            
            cursor.execute(query, params)
            if cursor.fetchone()['count'] > 0:
                return False
            
            # Проверка holds (исключая текущего пользователя)
            query = """
                SELECT COUNT(*) as count FROM holds 
                WHERE expires_at > ? 
                AND start_time < ? AND end_time > ?
            """
            params = [datetime.now(), end_time, start_time]
            
            if exclude_user:
                query += " AND user_id != ?"
                params.append(exclude_user)
            
            if table_id is not None:
                query += " AND table_id = ?"
                params.append(table_id)
            
            cursor.execute(query, params)
            return cursor.fetchone()['count'] == 0
    
    @staticmethod
    def _row_to_booking(row) -> Booking:
        """Преобразование строки БД в объект Booking"""
        return Booking(
            id=row['id'],
            user_id=row['user_id'],
            username=row['username'],
            table_id=row['table_id'],
            start_time=datetime.fromisoformat(row['start_time']),
            end_time=datetime.fromisoformat(row['end_time']),
            phone=row['phone'],
            created_at=datetime.fromisoformat(row['created_at']),
            status=row['status']
        )


class HoldRepository:
    """Репозиторий для работы с временными удержаниями"""
    
    @staticmethod
    def create_hold(hold: Hold) -> int:
        """Создание нового hold"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO holds 
                (user_id, table_id, start_time, end_time, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                hold.user_id,
                hold.table_id,
                hold.start_time,
                hold.end_time,
                hold.created_at,
                hold.expires_at
            ))
            return cursor.lastrowid
    
    @staticmethod
    def delete_user_holds(user_id: int):
        """Удаление всех holds пользователя"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM holds WHERE user_id = ?", (user_id,))
    
    @staticmethod
    def cleanup_expired():
        """Удаление истёкших holds"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM holds WHERE expires_at < ?", (datetime.now(),))
            return cursor.rowcount


class TableRepository:
    """Репозиторий для работы со столами"""
    
    @staticmethod
    def get_all_tables() -> List[Table]:
        """Получение всех столов"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tables WHERE is_active = 1")
            rows = cursor.fetchall()
            return [Table(
                id=row['id'],
                name=row['name'],
                is_active=bool(row['is_active'])
            ) for row in rows]
    
    @staticmethod
    def get_table_by_id(table_id: int) -> Optional[Table]:
        """Получение стола по ID"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tables WHERE id = ?", (table_id,))
            row = cursor.fetchone()
            if row:
                return Table(
                    id=row['id'],
                    name=row['name'],
                    is_active=bool(row['is_active'])
                )
            return None
