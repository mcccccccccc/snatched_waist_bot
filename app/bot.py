import asyncio
import datetime
from datetime import date
from typing import Dict
from config import config
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import utils
import matplotlib.pyplot as plt
import io
from middleware import CommandLoggingMiddleware, CheckFillProfileMiddleware
from user_profile import Profile


# ex: {tg_user_id: Profile}
# todo store in RDBMS
db: Dict[int, Profile] = {}


class Form(StatesGroup):
    weight = State()
    height = State()
    age = State()
    city = State()
    activity = State()
    water_goal = State()
    calorie_goal = State()


# Создаем экземпляры бота и диспетчера
bot = Bot(token=config.bot_token.get_secret_value())

dp = Dispatcher()

profile_router = Router()
help_router = Router()
calc_router = Router()
dp.include_router(profile_router)
dp.include_router(calc_router)
dp.include_router(help_router)

# Register the middleware
dp.message.middleware(CommandLoggingMiddleware())
calc_router.message.middleware(CheckFillProfileMiddleware(db=db))


@help_router.message()
@dp.message(Command("start"))
@help_router.message(Command("help"))
async def show_help(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(user_id=message.from_user.id, is_fill_profile=False)
    await message.reply("Доступные команды:\n"
                        "/help - помощь\n"
                        "/set_profile - установить профиль\n"
                        "/clear_profile - очистить профиль\n"
                        "/start_day - начать день\n"
                        "/log_water - залогировать выпитую воду\n"
                        "/log_food - залогировать потребленные калории\n"
                        "/log_workout - залогировать тренировку\n"
                        "/check_progress - проверить прогресс\n"
                        "/start_new_day - начать новый день\n"
                        "/profile - показать профиль\n"
                        "/show_graph <workout, water, food> - показать график прогресса")



@profile_router.message(Command("set_profile"))
async def set_profile(message: Message, state: FSMContext):
    await state.clear()
    await message.reply("Введите ваш вес (в кг):")
    await state.set_state(Form.weight)

@profile_router.message(Form.weight)
async def set_weight(message: Message, state: FSMContext):
    try:
        await state.update_data(weight=int(message.text))
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите ваш вес в килограммах.")
        return
    await message.reply("Введите ваш рост (в см):")
    await state.set_state(Form.height)


@profile_router.message(Form.height)
async def set_height(message: Message, state: FSMContext):
    try:
        await state.update_data(height=int(message.text))
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите ваш рост в см.")
        return

    await message.reply("Введите ваш возраст:")
    await state.set_state(Form.age)


@profile_router.message(Form.age)
async def set_age(message: Message, state: FSMContext):
    try:
        await state.update_data(age=int(message.text))
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите ваш возраст.")
        return

    await message.reply("Сколько минут активности у вас в день?")
    await state.set_state(Form.activity)


@profile_router.message(Form.activity)
async def set_activity(message: Message, state: FSMContext):
    try:
        await state.update_data(activity=int(message.text))
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите количество минут активности в день.")
        return

    await message.reply("В каком городе вы находитесь?")
    await state.set_state(Form.city)



@profile_router.message(Form.city)
async def set_city(message: Message, state: FSMContext):
    await state.update_data(city=str(message.text))
    data = await state.get_data()
    profile = Profile(**data)
    profile.today = date.today()
    profile.calorie_goal = utils.get_calories_norma(profile)
    # save to profile storage
    db[message.from_user.id] = profile
    await state.update_data(is_fill_profile=True)
    await state.set_state(state=None)
    await message.reply("Ваши данные успешно сохранены.\n"
                        "Цель по калориям рассчитана автоматически. Если хотите, можете указать цель по калориям на день: /calorie_goal <число>\n"
                        "\n\n" + str(db[message.from_user.id]))


@profile_router.message(Command("clear_profile"))
async def clear_profile(message: Message, state: FSMContext):
    await state.clear()
    db.pop(message.from_user.id, None)
    await state.update_data(is_fill_profile=False)
    await message.reply("Профиль удален Надо заново заполнить его через /set_profile")


@profile_router.message(Command("start_day"))
async def start_day(message: Message, state: FSMContext):
    if not await state.get_value('is_fill_profile', False):
        await message.reply("Для начала работы введите /set_profile")
        return

    db[message.from_user.id].today = date.today()
    db[message.from_user.id].burned_calories = 0
    db[message.from_user.id].logged_calories = 0
    db[message.from_user.id].logged_water = 0

    await message.reply("День начат.")


@profile_router.message(Command("calorie_goal"))
async def set_calorie_goal(message: Message):
    arr = message.text.split()
    try:
        db[message.from_user.id].calorie_goal = int(arr[1])
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите количество калорий после команды /calorie_goal.")
        return

    await message.reply("Ваши данные успешно сохранены.\n\n" + str(db[message.from_user.id]))


@calc_router.message(Command("profile"))
async def profile(message: Message, profile: Profile):
    await message.reply(repr(profile))


@calc_router.message(Command("log_water"))
async def log_water(message: Message, profile: Profile):
    try:
        amount = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите количество воды в миллилитрах после команды /log_water.")
        return

    profile.logged_water += amount
    profile.trace_water.append((datetime.datetime.now(), amount))
    need_water, rest_water = await utils.get_water_norma(profile)
    rest_water = need_water - profile.logged_water

    await message.reply(f"Данные успешно сохранены.\nВыпито: {profile.logged_water} мл.\nОсталось: {rest_water} мл из {need_water} мл.")


@calc_router.message(Command("log_food"))
async def log_food(message: Message, profile: Profile):
    arr = message.text.split()
    try:
        food = str(arr[1])
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите что вы скушали /log_food <название_продукта>")
        return

    weight = int(arr[2]) if len(arr) >= 2 else 100
    cals_100 = await utils.get_food_calories_100g(food)
    cals_total = cals_100 * weight // 100
    profile.logged_calories += cals_total
    profile.trace_food.append((datetime.datetime.now(), cals_total))

    await message.reply(
        f"{food}  - {cals_100} ккал на 100 грамм.\nВы съели {weight} грамм.\n Записано {cals_total} ккал.\n"
        f"Ваша норма калорий на сегодня {profile.calorie_goal}.")


@calc_router.message(Command("log_workout"))
async def log_workout(message: Message, profile: Profile):
    arr = message.text.split()
    try:
        activity_type = str(arr[1])
        activity_duration = int(arr[2])
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите что вы скушали /log_workout <активность> <длительность>")
        return

    cals = await utils.get_workout_calories(activity_type, activity_duration, int(profile.weight), int(profile.height), int(profile.age))
    profile.logged_calories += cals
    need_water = 200 * activity_duration // 30

    profile.trace_workout.append((datetime.datetime.now(), activity_duration))
    left_to_norma = profile.calorie_goal - profile.logged_calories

    await message.reply(f"{activity_type} {activity_duration} - {cals} ккал. Не забудьте выпить {need_water} мл воды.\n"
                        f"Осталось {left_to_norma} из {profile.calorie_goal} ккал до цели на сегодня.")

@calc_router.message(Command("check_progress"))
async def check_progress(message: Message, profile: Profile):
    res = await utils.get_progress(profile)
    await message.reply(res)


@calc_router.message(Command("show_graph"))
async def show_graph(message: Message, profile: Profile):
    try:
        graph_type = message.text.split()[1]
    except IndexError:
        await message.reply("Please specify the graph type: /show_graph <workout, water, food>")
        return

    data = profile.to_dict()
    if graph_type == "workout":
        trace_data = data.get("trace_workout", [])
        title = "Workout Progress"
        ylabel = "Workout Duration (minutes)"
    elif graph_type == "water":
        trace_data = data.get("trace_water", [])
        title = "Water Intake Progress"
        ylabel = "Water Intake (ml)"
    elif graph_type == "food":
        trace_data = data.get("trace_food", [])
        title = "Food Intake Progress"
        ylabel = "Calories Intake (kcal)"
    else:
        await message.reply("Invalid graph type. Please specify: /show_graph <workout, water, food>")
        return

    if not trace_data:
        await message.reply(f"No data available for {graph_type}.")
        return

    # Plot the graph
    plt.figure()
    plt.plot([x[0] for x in trace_data], [x[1] for x in trace_data], marker='o')
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel(ylabel)
    plt.grid(True)

    # Save the plot to a BytesIO object
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # Send the plot as a photo
    await message.reply_photo(
        BufferedInputFile(
            buf.read(),
            filename=f"{graph_type}.jpg"
        ),
        caption=f"{graph_type}_progress"
    )


# Основная функция запуска бота
async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
