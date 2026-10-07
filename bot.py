import os
import io
import uuid
import json
import urllib3
import telebot
import requests
import pandas as pd

import parser
import analytics
from bot_functions import FUNCTIONS_SCHEMA, call_function

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== НАСТРОЙКИ (берутся из переменных Amvera) ==========
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
AUTHORIZATION_KEY = os.getenv('AUTHORIZATION_KEY')
# =============================================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Хранилище: chat_id -> объект Analytics
user_analytics = {}


# ========== GIGACHAT ==========
def get_gigachat_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    payload = 'scope=GIGACHAT_API_PERS'
    clean_key = ''.join(AUTHORIZATION_KEY.split())
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {clean_key}'
    }
    try:
        response = requests.post(url, headers=headers, data=payload, verify=False)
        response.raise_for_status()
        return response.json().get('access_token')
    except Exception as e:
        print(f"Ошибка GigaChat: {e}")
        return None


def ask_gigachat_with_functions(question, analytics_obj, max_iterations=5):
    token = get_gigachat_token()
    if not token:
        return "Ошибка авторизации в GigaChat."

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    system_prompt = (
        "Ты — финансовый аналитик. Ты работаешь с таблицей финансовых данных. "
        "ВСЕ расчёты делай ТОЛЬКО через функции. НИКОГДА не считай в уме и не выдумывай числа. "
        "Если пользователь спрашивает про конкретный показатель за год — вызови get_value. "
        "Если сравнивает годы — вызови compare_years. "
        "Если нужен тренд — вызови get_series. "
        "Если не знаешь точного названия показателя — вызови find_metrics или list_metrics. "
        "После получения результата сформулируй краткий ответ пользователю на русском языке."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    for iteration in range(max_iterations):
        payload = {
            "model": "GigaChat",
            "messages": messages,
            "functions": FUNCTIONS_SCHEMA,
            "temperature": 0.1,
            "max_tokens": 1500
        }

        try:
            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            return f"Ошибка запроса к GigaChat: {e}"

        message = data['choices'][0]['message']

        if 'function_call' in message and message['function_call']:
            func_call = message['function_call']
            func_name = func_call['name']
            try:
                func_args = json.loads(func_call['arguments']) if isinstance(func_call['arguments'], str) else func_call['arguments']
            except json.JSONDecodeError:
                func_args = {}

            print(f"🔧 GigaChat вызвал: {func_name}({func_args})")
            result = call_function(func_name, func_args, analytics_obj)
            print(f"📊 Результат: {result}")

            messages.append(message)
            messages.append({
                "role": "function",
                "name": func_name,
                "content": json.dumps(result, ensure_ascii=False, default=str)
            })
            continue

        return message.get('content', 'Нет ответа.')

    return "Превышено максимальное число итераций."


# ========== ОБРАБОТЧИКИ ==========
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(
        message.chat.id,
        "Я — ИИ-аналитик финансовых данных.\n\n"
        "Что я умею:\n"
        "• Принимаю Excel и CSV файлы\n"
        "• Отвечаю на вопросы по данным\n"
        "• Считаю проценты, разницы, тренды\n"
        "1. Отправь мне файл\n"
        "2. Задай любой вопрос\n\n"
        "📋 /help — примеры вопросов\n"
        "🗑 /reset — забыть текущую таблицу"
    )


@bot.message_handler(commands=['help'])
def help_message(message):
    bot.send_message(
        message.chat.id,
        "Примеры вопросов:\n\n"
        "• Какая выручка была в 2024?\n"
        "• На сколько % упала чистая прибыль в 2025?\n"
        "• Сравни выручку за 2023 и 2024\n"
        "• Как менялась выручка по годам?\n"
        "• Какие показатели есть в таблице?\n"
        "• В каком году выручка была максимальной?\n"
        "• Покажи все показатели за 2024"
    )


@bot.message_handler(commands=['reset'])
def reset_message(message):
    chat_id = message.chat.id
    if chat_id in user_analytics:
        del user_analytics[chat_id]
        bot.send_message(chat_id, "Таблица удалена. Отправь новый файл.")
    else:
        bot.send_message(chat_id, "У тебя нет загруженной таблицы.")


@bot.message_handler(content_types=['document'])
def handle_document(message):
    chat_id = message.chat.id
    filename = message.document.file_name or 'file'

    if not filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        bot.send_message(chat_id, "⚠️ Поддерживаются .xlsx, .xls, .csv")
        return

    bot.send_message(chat_id, f"Загружаю «{filename}»...")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)

        records, raw_text, error = parser.parse_excel(downloaded)

        if records:
            user_analytics[chat_id] = analytics.Analytics(records)
            a = user_analytics[chat_id]
            bot.send_message(
                chat_id,
                f"✅ Файл загружен\n"
                f"Записей: {len(records)}\n"
                f"Показателей: {len(a.list_metrics())}\n"
                f"Годы: {a.list_years()}\n\n"
                "Задавай вопросы!"
            )
        else:
            bot.send_message(
                chat_id,
                f"⚠️ Не удалось разобрать структуру файла.\n\n"
                f"Ошибка: {error}"
            )
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {e}")


@bot.message_handler(content_types=['text'])
def handle_text(message):
    chat_id = message.chat.id

    if chat_id not in user_analytics:
        bot.send_message(chat_id, "Сначала отправь Excel или CSV файл.")
        return

    data = user_analytics[chat_id]
    bot.send_message(chat_id, "Думаю...")
    answer = ask_gigachat_with_functions(message.text, data)
    bot.send_message(chat_id, answer)


if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
