"""
Состояния для FSM (Finite State Machine)
"""
from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния процесса бронирования"""
    choosing_date = State()
    choosing_time = State()
    choosing_duration = State()
    choosing_table = State()
    entering_phone = State()
    confirming = State()
