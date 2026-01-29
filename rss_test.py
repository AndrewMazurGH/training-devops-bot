import feedparser
import time
import os
import re
import requests
from openai import OpenAI
from dotenv import load_dotenv

# 1. Завантаження конфігурації
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")

if not api_key:
    print("❌ ПОМИЛКА: Не знайдено OPENAI_API_KEY")
    exit()

client = OpenAI(api_key=api_key)

# --- ФУНКЦІЯ ВІДПРАВКИ В TELEGRAM ---
def send_telegram_message(text):
    if not tg_token or not tg_chat_id:
        print("⚠️ Пропускаю відправку в Telegram (немає токена або ID)")
        return
    
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    payload = {
        "chat_id": tg_chat_id,
        "text": text,
        "parse_mode": "HTML", # Дозволяє форматування (жирний шрифт, посилання)
        "disable_web_page_preview": False
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("📩 Повідомлення відправлено в Telegram!")
        else:
            print(f"❌ Помилка Telegram: {response.text}")
    except Exception as e:
        print(f"❌ Помилка з'єднання з Telegram: {e}")

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

rss_url = "https://thenewstack.io/feed/"
print(f"📡 Підключаюсь до: {rss_url} ...")

feed = feedparser.parse(rss_url)

# Беремо 1 новину для тесту
for entry in feed.entries[:1]:
    title = entry.title
    link = entry.link
    raw_summary = clean_html(entry.summary)
    
    print(f"🔹 ОРИГІНАЛ: {title}")
    print("⏳ AI генерує самарі...")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "Ти — технічний асистент. Зроби стислий підсумок статті українською мовою (до 3 речень). Використовуй емодзі для структурування."
                },
                {
                    "role": "user", 
                    "content": f"Заголовок: {title}\nТекст: {raw_summary}"
                }
            ]
        )
        
        ai_summary = response.choices[0].message.content

        # Формуємо красиве повідомлення для Telegram (HTML розмітка)
        final_message = (
            f"<b>{title}</b>\n\n"
            f"{ai_summary}\n\n"
            f"🔗 <a href='{link}'>Читати статтю</a>"
        )

        # Відправка
        send_telegram_message(final_message)
        
    except Exception as e:
        print(f"❌ Помилка: {e}")

    print("-" * 60)