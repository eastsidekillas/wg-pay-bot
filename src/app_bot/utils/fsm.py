from aiogram.fsm.state import State, StatesGroup


class NewConfig(StatesGroup):
    waiting_for_config_name = State()


class NewPayment(StatesGroup):
    waiting_for_screenshot = State()
    selected_plan_id = State()
