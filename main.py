import feedparser
import time
import os
import re
import json
import requests
from datetime import datetime, timedelta
from time import mktime
from openai import OpenAI
from dotenv import load_dotenv
from config import RSS_FEEDS

# --- НАЛАШТУВАННЯ ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def clean_html(raw_html):
    return re.sub(re.compile('<.*?>'), '', raw_html)

def send_telegram(text):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    # Telegram має ліміт 4096 символів.
    if len(text) > 4000:
        text = text[:4000] + "\n...(обрізано через ліміт Telegram)"
        
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True})
    except Exception as e:
        print(f"❌ Помилка Telegram: {e}")

def is_yesterday(struct_time):
    """Перевіряє, чи дата новини була вчора"""
    if not struct_time:
        return False
    pub_date = datetime.fromtimestamp(mktime(struct_time)).date()
    yesterday = datetime.now().date() - timedelta(days=1)
    return pub_date == yesterday

def collect_yesterday_news():
    """Збирає новини ТІЛЬКИ за вчорашній день"""
    all_news = []
    print("📡 Сканую новини за вчора...")
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed') and is_yesterday(entry.published_parsed):
                    all_news.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": clean_html(entry.summary)[:500] if 'summary' in entry else "",
                        "source": feed.feed.title if 'title' in feed.feed else url
                    })
        except Exception as e:
            print(f"⚠️ Помилка з {url}: {e}")
            
    print(f"✅ Знайдено {len(all_news)} новин за вчора.")
    return all_news

def select_top_news(news_list):
    """Вибирає ТОП-3 найважливіших новини"""
    # Якщо новин мало, просто повертаємо скільки є, але не більше 3
    if len(news_list) <= 3:
        return news_list

    print(f"🧠 AI фільтрує {len(news_list)} новин до 3 найкращих...")
    
    titles_text = ""
    for i, item in enumerate(news_list):
        titles_text += f"{i}. [{item['source']}] {item['title']}\n"

    prompt = f"""
    Ти - Tech Lead. Вибери 3 найкритичніші новини для DevOps інженера.
    Ігноруй маркетинг, шукай технологічні зміни.
    Список:
    {titles_text}
    Поверни ТІЛЬКИ JSON список індексів, наприклад: [0, 2, 5].
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        indices = json.loads(content)
        # Обрізаємо список до 3 елементів, про всяк випадок
        selected = [news_list[i] for i in indices if i < len(news_list)]
        return selected[:3]
    except Exception as e:
        print(f"❌ Помилка при виборі: {e}")
        return news_list[:3]

def generate_daily_digest(news_list):
    """Генерує дайджест з персональними порадами"""
    print("✍️ AI пише фінальний дайджест з аналізом...")
    
    context_text = ""
    for item in news_list:
        context_text += f"TITLE: {item['title']}\nSOURCE: {item['source']}\nLINK: {item['link']}\nCONTENT: {item['summary']}\n\n"

    today_date = datetime.now().strftime("%d.%m.%Y")
    
    prompt = f"""
    Ти — ментор з DevOps. Сьогодні {today_date}.
    Напиши дайджест із 3 новин.
    
    Для КОЖНОЇ новини ти повинен дати:
    1. Суть (1 речення).
    2. Пораду для Джуна (що вивчити, на що звернути увагу, який термін загуглити).
    
    ВАЖЛИВО: Не використовуй markdown блоків коду (```html). Просто поверни чистий текст з тегами.

    Формат повідомлення (використовуй HTML):
    
    📅 <b>DevOps Дайджест: {today_date}</b>
    (Короткий вступ)

    ----------
    (Блок новини):
    🔹 <b>Заголовок новини</b>
    <i>Джерело</i>
    
    📝 <b>Суть:</b> (Текст суті)
    💡 <b>Для Джуна:</b> (Твій аналіз і порада)
    
    🔗 <a href="посилання">Читати далі</a>
    ----------

    Ось новини:
    {context_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        content = response.choices[0].message.content
        
        # --- ОСЬ ЦЕ ВИПРАВЛЕННЯ ---
        # Видаляємо ```html та ``` якщо AI їх додав
        content = content.replace("```html", "").replace("```", "").strip()
        
        return content
    except Exception as e:
        return f"❌ Помилка генерації: {e}"

# --- ОСНОВНИЙ ЦИКЛ ---
def main():
    raw_news = collect_yesterday_news()
    
    if not raw_news:
        print("🤷‍♂️ За вчора важливих новин не знайдено.")
        # Можна відправляти пустий звіт, або нічого не робити
        return

    top_news = select_top_news(raw_news)
    digest_message = generate_daily_digest(top_news)

    send_telegram(digest_message)
    print("📨 Дайджест відправлено!")

if __name__ == "__main__":
    main()