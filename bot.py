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
    u = users.get(update.effective_user.id)
    if not u:
        await update.message.reply_text("Сначала задай профиль: /profile")
        return

    await update.message.reply_text(
        f"📊 Статус за день:\n\n"
        f"💧 Вода: {u['water']} мл\n"
        f"🍔 Калории: {u['food']} ккал\n"
        f"🔥 Сожжено: {u['burned']} ккал"
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


