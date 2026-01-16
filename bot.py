import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

TOKEN = "8290385393:AAEYp0TBb3b7e1EmvtibLXQr6QSFUC6QAtg"

logging.basicConfig(level=logging.INFO)

# Хранилище данных
users = {}

# Вспомогательные функции
def calculate_water(weight, activity):
    return weight * 35 + activity * 500  # мл

def calculate_calories(weight, height, age, gender, activity):
    if gender == "м":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    return int(bmr * activity)

def get_food_info(product_name):
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {
            "action": "process",
            "search_terms": product_name,
            "json": 1,
            "page_size": 1,
        }

        response = requests.get(url, params=params, timeout=5)

        if response.status_code != 200:
            return None

        data = response.json()
        products = data.get("products")

        if not products:
            return None

        nutriments = products[0].get("nutriments", {})
        kcal = nutriments.get("energy-kcal_100g")

        return kcal

    except Exception as e:
        print("Ошибка API еды:", e)
        return None

# Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🤖\n\n"
        "Я помогу рассчитать норму воды и калорий.\n\n"
        "Сначала введи профиль:\n"
        "/profile вес рост возраст пол активность\n\n"
        "Пример:\n"
        "/profile 70 175 22 м 1.55"
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight, height, age, gender, activity = context.args
        weight, height, age = map(int, [weight, height, age])
        activity = float(activity)

        users[update.effective_user.id] = {
            "weight": weight,
            "height": height,
            "age": age,
            "gender": gender,
            "activity": activity,
            "water": 0,
            "food": 0,
            "burned": 0,
            "water_history": [],
            "calorie_history": [],
        }

        water_norm = calculate_water(weight, activity)
        cal_norm = calculate_calories(weight, height, age, gender, activity)

        await update.message.reply_text(
            f"Профиль сохранён ✅\n\n"
            f"💧 Норма воды: {water_norm} мл\n"
            f"🔥 Норма калорий: {cal_norm} ккал"
        )
    except:
        await update.message.reply_text("Ошибка формата 😕")

async def water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Сначала задай профиль: /profile")
        return

    if not context.args:
        await update.message.reply_text("Пример: /water 250")
        return

    try:
        amount = int(context.args[0])
        users[user_id]["water"] += amount
        users[user_id]["water_history"].append(users[user_id]["water"])
        await update.message.reply_text(f"💧 Добавлено {amount} мл воды")
    except:
        await update.message.reply_text("Объём должен быть числом 😕")


async def food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Сначала задай профиль: /profile")
        return

    if not context.args:
        await update.message.reply_text("Пример: /food apple")
        return

    product = " ".join(context.args)
    kcal = get_food_info(product)

    if kcal is None:
        kcal = 100  # среднее значение
        users[user_id]["food"] += kcal

        await update.message.reply_text(
            f"🍔 {product}\n"
            f"⚠️ Данные не найдены, использовано среднее значение: {kcal} ккал"
        )
        return

    users[user_id]["food"] += int(kcal)
    users[user_id]["calorie_history"].append(users[user_id]["food"])

    await update.message.reply_text(
        f"🍔 {product}\n"
        f"≈ {int(kcal)} ккал (на 100г)"
    )

async def workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Сначала задай профиль: /profile")
        return

    if not context.args:
        await update.message.reply_text("Пример: /workout 300")
        return

    try:
        calories = int(context.args[0])
        users[user_id]["burned"] += calories
        await update.message.reply_text(f"🏃 Сожжено {calories} ккал")
    except:
        await update.message.reply_text("Калории должны быть числом 😕")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users:
        await update.message.reply_text("Сначала задай профиль: /profile")
        return

    u = users[user_id]

    # Расчёт норм
    water_norm = calculate_water(u["weight"], u["activity"])
    cal_norm = calculate_calories(
        u["weight"], u["height"], u["age"], u["gender"], u["activity"]
    )

    # Текущие значения
    water_drunk = u["water"]
    calories_eaten = u["food"]
    calories_burned = u["burned"]
    calories_balance = calories_eaten - calories_burned

    # Прогресс
    water_left = max(0, water_norm - water_drunk)

    # Рекомендации
    recommendations = []

    if water_left > 0:
        recommendations.append("💧 Рекомендуется выпить ещё воды.")

    if calories_balance < cal_norm * 0.8:
        recommendations.append("🍽 Можно немного поесть для набора калорий.")
    elif calories_balance > cal_norm:
        recommendations.append("🏃 Рекомендуется лёгкая тренировка.")

    if not recommendations:
        recommendations.append("✅ Вы отлично соблюдаете дневные нормы!")

    # Ответ пользователю
    await update.message.reply_text(
        f"📊 Прогресс за день:\n\n"
        f"💧 Вода: {water_drunk} / {water_norm} мл\n"
        f"Осталось: {water_left} мл\n\n"
        f"🔥 Калории: {calories_balance} / {cal_norm} ккал\n"
        f"(съедено: {calories_eaten}, сожжено: {calories_burned})\n\n"
        f"💡 Рекомендации:\n" + "\n".join(recommendations)
    )

# Запуск
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("water", water))
    app.add_handler(CommandHandler("food", food))
    app.add_handler(CommandHandler("workout", workout))
    app.add_handler(CommandHandler("status", status))

    app.run_polling()

if __name__ == "__main__":
    main()




