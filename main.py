import os
import telebot
import random
import sqlite3
import time
from datetime import datetime
from keep_alive import keep_alive  # Импортируем ТВОЙ файл

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8257786365:AAEVPxQbssUDhRe-wLJkM_mLn50-1m_ym8o")
bot = telebot.TeleBot(BOT_TOKEN)

# ========== БАЗА ДАННЫХ ==========
def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect('bot_memory.db')
    cursor = conn.cursor()

    # Основная таблица шаблонов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS response_patterns (
            id INTEGER PRIMARY KEY,
            user_message_pattern TEXT,
            bot_response TEXT,
            usage_count INTEGER DEFAULT 0
        )
    ''')

    # Таблица фактов о пользователях
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_facts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            fact_type TEXT,
            fact_content TEXT,
            created_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Проверяем и добавляем базовые шаблоны
    cursor.execute("SELECT COUNT(*) FROM response_patterns")
    if cursor.fetchone()[0] == 0:
        base_patterns = [
            # Приветствия
            ('привет', 'Привет! Рад тебя видеть! 🌟'),
            ('хай', 'Привет! Как твои дела? 💫'),
            ('доброе утро', 'Доброе утро! Хорошего дня! ☀️'),
            ('добрый день', 'Добрый день! Как настроение? 🌞'),
            ('добрый вечер', 'Добрый вечер! Как прошёл день? 🌙'),

            # Эмоции
            ('грустно', 'Понимаю... Иногда грусть — это просто туча, которая скоро пройдет 🌧️➡️🌈'),
            ('устал', 'Отдых — это важно. Давай найдём минутку для передышки 🛋️'),
            ('тяжело', 'Знаю, бывает нелегко... Но ты справишься! 💪'),
            ('рад', 'Здорово! Радость — это так прекрасно! 🎉'),
            ('скучно', 'Может, расскажешь, о чём думаешь? 💭'),

            # Темы
            ('погода', 'Погода — как настроение: постоянно меняется 🌦️'),
            ('осень', 'Осень — время уютных разговоров и горячего чая 🍂☕'),
            ('зима', 'Зима — пора тепла и размышлений у окна ❄️'),
            ('код', 'Код — это искусство, доступное каждому 💻'),
            ('бот', 'Боты — наши цифровые друзья! 🤖'),

            # Философские
            ('смысл жизни', 'Смысл в том, чтобы находить его в каждом дне 🌟'),
            ('зачем всё это', 'Всё имеет значение, даже маленькие разговоры 💫'),
        ]

        for pattern in base_patterns:
            cursor.execute(
                "INSERT INTO response_patterns (user_message_pattern, bot_response) VALUES (?, ?)",
                pattern)

    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

# ========== СИСТЕМА ПАМЯТИ ==========
def remember_fact(user_id, fact_type, content):
    """Запоминает факт о пользователе"""
    try:
        conn = sqlite3.connect('bot_memory.db')
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO user_facts (user_id, fact_type, fact_content) VALUES (?, ?, ?)",
            (user_id, fact_type, content)
        )
        conn.commit()
        conn.close()
        print(f"✅ Запомнил факт: {fact_type} - {content}")
        return True
    except Exception as e:
        print(f"❌ Ошибка записи факта: {e}")
        return False

def recall_facts(user_id, fact_type=None):
    """Вспоминает факты о пользователе"""
    try:
        conn = sqlite3.connect('bot_memory.db')
        cursor = conn.cursor()

        if fact_type:
            cursor.execute(
                "SELECT fact_content FROM user_facts WHERE user_id = ? AND fact_type = ?",
                (user_id, fact_type)
            )
        else:
            cursor.execute(
                "SELECT fact_type, fact_content FROM user_facts WHERE user_id = ?",
                (user_id,)
            )

        facts = cursor.fetchall()
        conn.close()
        return facts
    except Exception as e:
        print(f"❌ Ошибка чтения фактов: {e}")
        return []

def extract_facts_from_message(text, user_id):
    """Извлекает факты из сообщения"""
    text_lower = text.lower()
    facts_found = []

    # Города
    city_keywords = ['город', 'живу в', 'из города', 'в городе']
    if any(keyword in text_lower for keyword in city_keywords):
        words = text.split()
        for i, word in enumerate(words):
            if word.lower() in ['город', 'городе'] and i + 1 < len(words):
                city = words[i + 1]
                if len(city) > 2:  # Минимальная длина названия
                    remember_fact(user_id, 'city', city)
                    facts_found.append(('city', city))

    # Имена
    name_keywords = ['зовут', 'имя', 'меня зовут', 'мое имя']
    if any(keyword in text_lower for keyword in name_keywords):
        words = text.split()
        for i, word in enumerate(words):
            if word.lower() in ['зовут', 'имя'] and i + 1 < len(words):
                name = words[i + 1]
                if name[0].isupper():  # Имена с большой буквы
                    remember_fact(user_id, 'name', name)
                    facts_found.append(('name', name))

    return facts_found

# ========== ПОИСК ОТВЕТОВ ==========
def find_response(user_message):
    """Поиск ответа в базе данных"""
    try:
        conn = sqlite3.connect('bot_memory.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT bot_response FROM response_patterns WHERE ? LIKE '%' || user_message_pattern || '%' LIMIT 1",
            (user_message.lower(), ))

        result = cursor.fetchone()

        if result:
            cursor.execute(
                "UPDATE response_patterns SET usage_count = usage_count + 1 WHERE bot_response = ?",
                (result[0], ))
            conn.commit()
            conn.close()
            return result[0]

        conn.close()
        return None

    except Exception as e:
        print(f"❌ Ошибка базы: {e}")
        return None

# ========== УМНЫЕ ОТВЕТЫ ==========
def generate_smart_response(text):
    """Генерация умного ответа, если нет в базе"""
    text_lower = text.lower()

    if any(word in text_lower for word in ['привет', 'хай', 'здравств', 'добр']):
        return random.choice([
            "Привет! Что нового? 🎯", 
            "Здравствуй! Рад нашему разговору 💫",
            "Привет! Как твой день? 🌟"
        ])

    elif any(word in text_lower for word in ['грустно', 'печаль', 'тоска', 'плохо']):
        return random.choice([
            "Понимаю... Иногда нужно просто выговориться 🍂",
            "Грусть — как дождь: очищает душу для новых чувств 🌧️",
            "Ты не один в своих переживаниях. Я с тобой 💛"
        ])

    elif any(word in text_lower for word in ['рад', 'счастлив', 'хорошо', 'отлично']):
        return random.choice([
            "Здорово! Позитив — это заразительно! 🌈",
            "Как приятно слышать! Пусть таких моментов будет больше! 🎉",
            "Твоя радость согревает! ☀️"
        ])

    elif any(word in text_lower for word in ['как дела', 'как ты', 'что делаешь']):
        return random.choice([
            "Всё хорошо, работаю над собой! А у тебя? 🔧",
            "Отлично! Готов к новым беседам. А как твои дела? 💫",
            "Прекрасно! Слушаю тебя внимательно 👂"
        ])

    elif any(word in text_lower for word in ['пока', 'до свидан', 'спокойной']):
        return random.choice([
            "До встречи! Буду ждать наших разговоров! 👋",
            "Пока! Отличного дня! 🌟", 
            "До скорого! Помни: я всегда здесь 💛"
        ])

    else:
        return random.choice([
            "Интересно... Расскажи подробнее? 💭",
            "Понял тебя. Что ещё хочешь обсудить? 🎯",
            "Слушаю внимательно... Продолжаем разговор? 👂",
            "Задумался над твоими словами... 💫"
        ])

def create_personalized_response(original_text, user_id, new_facts, known_facts):
    """Создаёт ответ с учётом знаний о пользователе"""

    response = find_response(original_text)
    if not response:
        response = generate_smart_response(original_text)

    personal_touch = ""

    for fact_type, content in new_facts:
        if fact_type == 'city':
            personal_touch = f"\n\nКстати, запомнил что ты из {content}! Расскажешь про этот город? 🏙️"
        elif fact_type == 'name':
            personal_touch = f"\n\nПриятно познакомиться, {content}! Буду помнить твоё имя 💫"

    if known_facts and not new_facts:
        for fact_type, content in known_facts:
            if fact_type == 'city':
                personal_touch = f"\n\nКак дела в {content}? 🌆"
                break
            elif fact_type == 'name':
                personal_touch = f"\n\nРад снова тебя видеть, {content}! 💫"
                break

    return response + personal_touch

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = ("Привет! Я *Тихий друг* 🤖\n\n"
                    "Я здесь, чтобы:\n"
                    "• Слушать и поддерживать 👂\n" 
                    "• Вести осмысленные беседы 💭\n"
                    "• Помогать в трудные моменты 💛\n\n"
                    "Просто напиши что-нибудь — и я отвечу!\n\n"
                    "Также есть команды:\n"
                    "/learn - научить меня новым ответам\n"
                    "/stats - статистика базы знаний")

    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['learn'])
def teach_bot(message):
    try:
        parts = message.text.split('||')
        if len(parts) == 2:
            question = parts[0].replace('/learn', '').strip()
            answer = parts[1].strip()

            if not question or not answer:
                bot.reply_to(message, "❌ Нужно указать и вопрос, и ответ")
                return

            conn = sqlite3.connect('bot_memory.db')
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO response_patterns (user_message_pattern, bot_response) VALUES (?, ?)",
                (question.lower(), answer))
            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM response_patterns")
            total = cursor.fetchone()[0]
            conn.close()

            bot.reply_to(message, f"✅ Запомнил!\n\n"
                         f"*Вопрос:* {question}\n"
                         f"*Ответ:* {answer}\n\n"
                         f"📚 Теперь в базе: {total} ответов",
                         parse_mode='Markdown')
        else:
            bot.reply_to(message, "📝 *Формат обучения:*\n"
                         "`/learn вопрос || ответ`\n\n"
                         "*Пример:*\n"
                         "`/learn расскажи шутку || Коты — это маленькие программисты!`",
                         parse_mode='Markdown')

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    conn = sqlite3.connect('bot_memory.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM response_patterns")
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT user_message_pattern, usage_count FROM response_patterns ORDER BY usage_count DESC LIMIT 5"
    )
    popular = cursor.fetchall()

    conn.close()

    stats_text = f"📊 *Статистика базы знаний*\n\n"
    stats_text += f"🧠 Всего ответов: {total}\n\n"

    if popular:
        stats_text += "🔥 *Популярные запросы:*\n"
        for pattern, count in popular:
            stats_text += f"• '{pattern}': {count} раз\n"

    bot.reply_to(message, stats_text, parse_mode='Markdown')

# ========== ОСНОВНОЙ ОБРАБОТЧИК ==========
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        user_id = message.from_user.id
        text = message.text

        print(f"📨 Сообщение от {user_id}: {text}")

        facts = extract_facts_from_message(text, user_id)
        known_facts = recall_facts(user_id)

        personalized_response = create_personalized_response(text, user_id, facts, known_facts)

        bot.reply_to(message, personalized_response)
        print(f"✅ Ответ отправлен")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        bot.reply_to(message, "🔧 Произошла ошибка. Уже работаю над исправлением!")

# ========== ЗАПУСК СИСТЕМЫ ==========
if __name__ == "__main__":
    print("🎯 Тихий друг запускается...")

    # Инициализируем базу
    init_database()

    # Запускаем ТВОЙ keep_alive
    keep_alive()

    print("🚀 Запуск Тихого друга...")
    print("✅ База данных готова")
    print("🧠 Система ответов активирована")
    print("🛡️ Keep-alive работает")

    try:
        bot.polling(none_stop=True, interval=1)
        print("🤖 Бот успешно запущен!")
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        print("🔄 Перезапуск через 5 секунд...")
        time.sleep(5)
