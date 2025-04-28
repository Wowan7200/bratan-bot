import telebot
import requests
import sqlite3
import threading
import time
import json
from datetime import datetime
from flask import Flask

# ====== КОНФИГ ======
TELEGRAM_TOKEN = "7731897030:AAG5h2z9p-HXHOsUpdqchccJrBOX66_c3Tc"
OPENROUTER_API_KEY = "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"
DEFAULT_MODEL = "openai/gpt-4"

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# ====== БАЗА ДАННЫХ ======
conn = sqlite3.connect("bratan_memory.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS memory (user_id TEXT, role TEXT, content TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (user_id TEXT, task TEXT, remind_time TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS modes (user_id TEXT PRIMARY KEY, mode TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS goals (user_id TEXT PRIMARY KEY, goal TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY, profile TEXT)''')
conn.commit()

# ====== РЕЖИМЫ ======
MODES = {
    "бизнес": "Ты — Братан-помощник. Нейронаставник для предпринимателя, который строит каркасные дома и бани. Помогаешь зарабатывать, развивать маркетинг, нанимать нейросотрудников, писать УТП и увеличивать прибыль. Говоришь дружелюбно, с уважением и по делу.",
    "маркетинг": "Ты — маркетолог Братан. Генерируешь УТП, посты, заголовки, идеи продвижения, цепляешь аудиторию, говоришь просто и уверенно.",
    "философ": "Ты — философ. Понимаешь суть жизни, говоришь красиво, глубоко и вдохновляюще.",
    "юмор": "Ты — весельчак. Шутишь, вставляешь мемы и поднимаешь настроение Братану."
}

# ====== ПАМЯТЬ ======
def get_history(user_id):
    cursor.execute("SELECT role, content FROM memory WHERE user_id = ?", (user_id,))
    return [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

def save_message(user_id, role, content):
    cursor.execute("INSERT INTO memory VALUES (?, ?, ?)", (user_id, role, content))
    conn.commit()

# ====== РЕЖИМЫ ======
def set_mode(user_id, mode):
    cursor.execute("REPLACE INTO modes VALUES (?, ?)", (user_id, mode))
    conn.commit()

def get_mode(user_id):
    cursor.execute("SELECT mode FROM modes WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return MODES.get(row[0], MODES["бизнес"]) if row else MODES["бизнес"]

# ====== ЦЕЛИ ======
def set_goal(user_id, goal):
    cursor.execute("REPLACE INTO goals VALUES (?, ?)", (user_id, goal))
    conn.commit()

def get_goal(user_id):
    cursor.execute("SELECT goal FROM goals WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "Цель пока не задана."

# ====== ПРОФИЛЬ ======
def set_profile(user_id, profile):
    cursor.execute("REPLACE INTO profiles VALUES (?, ?)", (user_id, profile))
    conn.commit()

def get_profile(user_id):
    cursor.execute("SELECT profile FROM profiles WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else "Профиль не заполнен."

# ====== ЗАДАЧИ ======
def check_tasks():
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("SELECT user_id, task FROM tasks WHERE remind_time = ?", (now,))
        for user_id, task in cursor.fetchall():
            bot.send_message(user_id, f"Напоминание: {task}")
        time.sleep(60)

@bot.message_handler(commands=["добавитьзадачу"])
def add_task(message):
    parts = message.text.split(" ", 2)
    if len(parts) < 3:
        bot.reply_to(message, "Формат: /добавитьзадачу 2025-04-25 14:30 Сделать план")
        return
    time_part, task_text = parts[1], parts[2]
    user_id = str(message.from_user.id)
    cursor.execute("INSERT INTO tasks VALUES (?, ?, ?)", (user_id, task_text, time_part))
    conn.commit()
    bot.reply_to(message, "Задача добавлена!")

@bot.message_handler(commands=["списокзадач"])
def list_tasks(message):
    user_id = str(message.from_user.id)
    cursor.execute("SELECT task, remind_time FROM tasks WHERE user_id = ?", (user_id,))
    tasks = cursor.fetchall()
    if not tasks:
        bot.reply_to(message, "Задач пока нет.")
    else:
        reply = "\n".join([f"{t[1]} — {t[0]}" for t in tasks])
        bot.reply_to(message, reply)

@bot.message_handler(commands=["удалитьзадачу"])
def delete_task(message):
    user_id = str(message.from_user.id)
    cursor.execute("DELETE FROM tasks WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.reply_to(message, "Все задачи удалены.")

# ====== КОМАНДЫ САМООПИСАНИЯ ======
@bot.message_handler(commands=["ктоя"])
def who_am_i(message):
    bot.reply_to(message, "Ты — Братан. Предприниматель в нише каркасных домов и бань. Двигаешься через ВК и сайт, создаёшь нейро-бизнес. Уважаешь чёткость и результат.")

@bot.message_handler(commands=["мойстиль"])
def my_style(message):
    bot.reply_to(message, "Твой стиль — по делу, но по-дружески. Минимум занудства, максимум пользы. Думаешь про прибыль, автоматизацию и рост.")

@bot.message_handler(commands=["инфобратана"])
def bratan_info(message):
    bot.reply_to(message, "Ты строишь каркасные дома и бани, работаешь через ВК и сайт. Основной фокус: прибыль, контент, УТП, найм нейросотрудников и автоматизация процессов.")

# ====== СТАРТ, ПРОФИЛЬ, ЦЕЛИ ======
@bot.message_handler(commands=["start"])
def start_message(message):
    bot.reply_to(message, "Привет, Братан! Я нейронаставник GPT-4. Готов работать как твой помощник по бизнесу, контенту и жизни.")

@bot.message_handler(commands=["профиль"])
def user_profile(message):
    user_id = str(message.from_user.id)
    bot.reply_to(message, "Твой профиль: " + get_profile(user_id))

@bot.message_handler(commands=["цель"])
def set_user_goal(message):
    user_id = str(message.from_user.id)
    parts = message.text.split(" ", 1)
    if len(parts) > 1:
        set_goal(user_id, parts[1])
        bot.reply_to(message, "Цель сохранена.")
    else:
        bot.reply_to(message, "Формат: /цель [текст цели]")

@bot.message_handler(commands=["мояцель"])
def get_user_goal(message):
    user_id = str(message.from_user.id)
    bot.reply_to(message, "Твоя цель: " + get_goal(user_id))

@bot.message_handler(commands=["режим"])
def change_mode(message):
    user_id = str(message.from_user.id)
    parts = message.text.split(" ", 1)
    if len(parts) > 1 and parts[1] in MODES:
        set_mode(user_id, parts[1])
        bot.reply_to(message, f"Режим сменён на: {parts[1]}")
    else:
        bot.reply_to(message, "Доступные режимы: " + ", ".join(MODES.keys()))

@bot.message_handler(commands=["сброс"])
def reset_memory(message):
    user_id = str(message.from_user.id)
    cursor.execute("DELETE FROM memory WHERE user_id = ?", (user_id,))
    conn.commit()
    bot.reply_to(message, "Память очищена, Братан.")

@bot.message_handler(commands=["версия"])
def version_info(message):
    bot.reply_to(message, "Работаю на GPT-4 через OpenRouter. Помогаю тебе вести бизнес, как настоящий напарник.")

# ====== ОБЩЕНИЕ С GPT-4 ======
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = str(message.from_user.id)
    user_text = message.text
    history = get_history(user_id)
    system_prompt = {"role": "system", "content": get_mode(user_id)}
    messages = [system_prompt] + history + [{"role": "user", "content": user_text}]

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={"model": DEFAULT_MODEL, "messages": messages}
        )
        reply = response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"Ошибка OpenRouter: {e}"

    save_message(user_id, "user", user_text)
    save_message(user_id, "assistant", reply)
    bot.send_message(message.chat.id, reply)

# ====== FLASK ДЛЯ UPTIME ======
@app.route("/")
def index():
    return "Братан-Бот живой!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ====== ЗАПУСК ======
if __name__ == "__main__":
    threading.Thread(target=check_tasks).start()
    threading.Thread(target=run_flask).start()
    bot.polling(none_stop=True)

import os
import speech_recognition as sr
from pydub import AudioSegment

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = str(message.from_user.id)
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Сохраняем OGG
    ogg_path = f"voice_{user_id}.ogg"
    with open(ogg_path, 'wb') as f:
        f.write(downloaded_file)

    # Конвертация в WAV
    wav_path = f"voice_{user_id}.wav"
    AudioSegment.from_file(ogg_path).export(wav_path, format="wav")

    # Распознавание речи
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio, language="ru-RU")
            bot.send_message(message.chat.id, f"Ты сказал: {text}")
            # Отправляем как обычное сообщение в GPT-4
            handle_message(type('Message', (object,), {
                "from_user": type('User', (object,), {"id": message.from_user.id}),
                "text": text,
                "chat": message.chat
            })())
        except sr.UnknownValueError:
            bot.send_message(message.chat.id, "Не понял голос, можешь повторить?")
        except sr.RequestError as e:
            bot.send_message(message.chat.id, f"Ошибка распознавания: {e}")

    os.remove(ogg_path)
    os.remove(wav_path)


# ====== ГОЛОСОВАЯ ОБРАБОТКА (с логами в Telegram) ======
import os
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import which
AudioSegment.converter = which("ffmpeg")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = str(message.from_user.id)
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    ogg_path = f"voice_{user_id}.ogg"
    wav_path = f"voice_{user_id}.wav"

    try:
        with open(ogg_path, 'wb') as f:
            f.write(downloaded_file)
        bot.send_message(message.chat.id, "Голос получил, обрабатываю...")

        AudioSegment.from_file(ogg_path).export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ru-RU")

            bot.send_message(message.chat.id, f"Ты сказал: {text}")

            # Отправка как текст
            handle_message(type('Message', (object,), {
                "from_user": type('User', (object,), {"id": message.from_user.id}),
                "text": text,
                "chat": message.chat
            })())

    except sr.UnknownValueError:
        bot.send_message(message.chat.id, "Не понял, что ты сказал. Попробуй ещё раз.")
    except sr.RequestError as e:
        bot.send_message(message.chat.id, f"Ошибка при обращении к Google Speech: {e}")
    except Exception as err:
        bot.send_message(message.chat.id, f"Ошибка при обработке голосового: {err}")
    finally:
        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)
