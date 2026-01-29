import feedparser
import time
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

# 1. Завантажуємо API ключ з файлу .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Перевірка, чи ключ знайшовся
if not api_key:
    print("❌ ПОМИЛКА: Не знайдено API ключ. Перевірте файл .env")
    exit()

# Ініціалізація клієнта OpenAI
client = OpenAI(api_key=api_key)

# Допоміжна функція для очищення тексту від HTML тегів (<img>, <br> тощо)
def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

rss_url = "https://thenewstack.io/feed/"
print(f"📡 Підключаюсь до: {rss_url} ...")

feed = feedparser.parse(rss_url)
print(f"✅ Знайдено новин: {len(feed.entries)}")
print("-" * 60)

# Беремо тільки ПЕРШУ новину для тесту (щоб економити гроші на етапі розробки)
# Коли все буде готово, змінимо [:1] на [:5]
for entry in feed.entries[:1]:
    
    title = entry.title
    link = entry.link
    # Чистимо текст від HTML сміття
    raw_summary = clean_html(entry.summary)
    
    print(f"🔹 ОРИГІНАЛ: {title}")
    print("⏳ AI думає над перекладом та самарі...")

    # --- МАГІЯ OPENAI ---
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Дешева і швидка модель
            messages=[
                {
                    "role": "system", 
                    "content": "Ти — досвідчений DevOps інженер. Твоє завдання: прочитати технічний текст, виділити головну суть і написати стислий підсумок (summary) українською мовою (максимум 3 речення). Не втрачай технічні терміни."
                },
                {
                    "role": "user", 
                    "content": f"Заголовок: {title}\nТекст: {raw_summary}"
                }
            ]
        )
        
        ai_summary = response.choices[0].message.content

        print(f"\n🤖 AI САМАРІ:\n{ai_summary}")
        print(f"\n🔗 Читати повну статтю: {link}")
        
    except Exception as e:
        print(f"❌ Помилка OpenAI: {e}")

    print("-" * 60)