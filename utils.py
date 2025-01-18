import aiohttp
from config import config
from user_profile import Profile


async def get_food_calories_100g(product_name: str) -> int:
    url = f"https://world.openfoodfacts.org/cgi/search.pl?search_terms={product_name}&search_simple=1&action=process&json=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

    if not data['products']:
        raise ValueError("Product not found")

    product = data['products'][0]
    calories_per_100g = product['nutriments']['energy-kcal_100g']
    # total_calories = (calories_per_100g * weight) / 100

    return int(calories_per_100g)



async def get_weather(city: str):
    api_key = config.openweathermap_api_key.get_secret_value()
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    response = await fetch_async(url)
    current_temp = response['main']['temp'] if 'main' in response else None
    return current_temp



async def get_workout_calories(activity: str, minutes: int, weight_kg, height, age) -> float:
    """
    Получает количество сожженных калорий для указанной активности через Nutritionix API.

    :param activity: Вид спорта (например, 'running', 'cycling').
    :param minutes: Количество минут занятия.
    :param weight_kg: Вес пользователя в килограммах.
    :param app_id: App ID от Nutritionix.
    :param app_key: App Key от Nutritionix.
    :return: Количество сожженных калорий.
    """
    app_id = config.nutritionix_app_id
    app_key = config.nutritionix_app_key.get_secret_value()
    url = "https://trackapi.nutritionix.com/v2/natural/exercise"
    headers = {
        "x-app-id": app_id,
        "x-app-key": app_key,
        "Content-Type": "application/json",
    }
    data = {
        "query": f"{minutes} minutes of {activity}",
        "weight_kg": weight_kg,
        # "gender": "male",
        "height_cm": height,
        "age": age,
    }

    # response = requests.post(url, headers=headers, json=data)
    async with (aiohttp.ClientSession() as session):
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                data = await response.json()
                exercises = data.get("exercises", [])
                if exercises:
                    return round(exercises[0].get("nf_calories", 0), 2)
                else:
                    raise ValueError("API не вернул данные об активности.")
            else:
                raise ValueError(f"Ошибка API: {response.status}, {await response.text()}")


async def get_water_norma(profile: Profile):
    # data = await state.get_data()
    need_water = profile.weight * 30 + 500
    need_water += 500 * profile.activity // 30

    temp = await get_weather(profile.city)
    if temp > 25:
        need_water += 500
    rest_water = need_water - profile.logged_water

    return need_water, rest_water

async def get_progress(profile: Profile) -> str:
    data = profile.to_dict()
    need_water = data['weight'] * 30 + 500
    need_water += 500 * data['activity'] // 30

    temp = await get_weather(data['city'])
    if temp > 25:
        need_water += 500
    rest_water = need_water - data['logged_water']

    cal_norma = 10 * data['weight'] + 6.25 * data['height'] - 5 * data['age']
    cal_get = data['logged_calories']
    cal_burn = data['burned_calories']
    cal_balance = cal_get - cal_burn

    res = f"📊 Прогресс:\nВода:\n- Выпито: {data['logged_water']} мл из {need_water} мл.\n- Осталось: {rest_water} мл.\n\nКалории:\n- Потреблено: {cal_get} ккал из {cal_norma} ккал.\n- Сожжено: {cal_burn} ккал.\n- Баланс: {cal_balance} ккал."

    return res

async def fetch_async(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


if __name__ == "__main__":
    import asyncio
    # res = asyncio.run(get_workout_calories("running", 60, 70, 180, 25))
    res = asyncio.run(get_weather("Moscow"))
    print(res)
