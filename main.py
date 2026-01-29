import feedparser
import time
import os
import re
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
from config import RSS_FEEDS # Імпортуємо наш список сайтів

# --- НАЛАШТУВАННЯ ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def clean_html(raw_html):
    """Очищає текст від HTML тегів"""
    return re.sub(re.compile('<.*?>'), '', raw_html)

def send_telegram(text):
    """Відправляє повідомлення в Telegram"""
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False})
    except Exception as e:
        print(f"❌ Помилка Telegram: {e}")

def collect_news():
    """Збирає по 2 найсвіжіші новини з кожного сайту"""
    all_news = []
    print("📡 Починаю сканування 10 ресурсів...")
    
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            # Беремо тільки 2 перші новини з кожного сайту, щоб не перевантажувати
            for entry in feed.entries[:2]:
                all_news.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": clean_html(entry.summary)[:1000] if 'summary' in entry else "",
                    "source": feed.feed.title if 'title' in feed.feed else url
                })
        except Exception as e:
            print(f"⚠️ Помилка з {url}: {e}")
            
    print(f"✅ Зібрано {len(all_news)} заголовків.")
    return all_news

def select_top_news(news_list):
    """Вибирає ТОП-3 новини"""
    print("🧠 AI вибирає 3 головні новини...")
    
    titles_text = ""
    for i, item in enumerate(news_list):
        titles_text += f"{i}. [{item['source']}] {item['title']}\n"

    prompt = f"""
    Ти - Tech Lead. У тебе обмаль часу. Вибери 3 найкритичніші статті для DevOps інженера.
    Ігноруй маркетинг. Тільки технологічні зміни або важливі релізи.
    
    Список:
    {titles_text}

    Поверни ТІЛЬКИ JSON список індексів, наприклад: [0, 2, 5].
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # Тут краще розумна модель для точного вибору
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message.content
        content = content.replace("```json", "").replace("```", "").strip()
        indices = json.loads(content)
        
        # Обрізаємо, якщо AI раптом повернув більше 3
        return [news_list[i] for i in indices if i < len(news_list)][:3]
    except Exception as e:
        print(f"❌ Помилка при виборі: {e}")
        return news_list[:3]

def summarize_article(article):
    """Максимально стисле самарі"""
    prompt = f"""
    Ти пишеш для дуже зайнятого інженера. Будь лаконічним.
    
    Напиши 2 пункти українською:
    1. 🔹 Суть: ОДНЕ речення про те, що сталося.
    2. 💡 Джуну: ОДНЕ речення, що саме загуглити або вивчити у зв'язку з цим.
    
    Стаття: {article['title']}
    Текст: {article['summary']}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Тут вистачить і міні
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except:
        return "Не вдалося обробити."

def summarize_article(article):
    """Створює самарі + пораду для джуніора"""
    prompt = f"""
    Ти — досвідчений DevOps ментор. Твоє завдання — пояснити цю новину своєму студенту (Junior DevOps).
    
    Зроби аналіз українською мовою у такому форматі:
    
    📝 **Про що це:** (2-3 речення стислого змісту статті)
    
    🎓 **Для Junior DevOps:**
    (Поясни простими словами, чому це важливо. Напиши, яку технологію варто довчити, або на яку концепцію звернути увагу, щоб бути в тренді. Якщо це складна тема — дай пораду, що саме загуглити).
    
    Стаття:
    Заголовок: {article['title']}
    Текст: {article['summary']}
    """
    
    try:
        # Тут можна спробувати 'gpt-4o', якщо поради 'gpt-4o-mini' будуть занадто банальними
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except:
        return "Не вдалося згенерувати аналіз."

# --- ОСНОВНИЙ ЦИКЛ ---
def main():
    # 1. Збір
    raw_news = collect_news()
    if not raw_news:
        print("Новин не знайдено.")
        return

    # 2. Відбір (AI Filtering)
    top_news = select_top_news(raw_news)
    print(f"💎 AI відібрав топ-{len(top_news)} новин. Генерую описи...")

    # 3. Обробка та відправка
    for news in top_news:
        summary_and_tips = summarize_article(news)
        
        message = (
            f"<b>{news['title']}</b>\n"
            f"<i>Джерело: {news['source']}</i>\n\n"
            f"{summary_and_tips}\n\n"
            f"👉 <a href='{news['link']}'>Читати в оригіналі</a>"
        )
        
        send_telegram(message)
        print(f"📨 Відправлено: {news['title']}")
        time.sleep(2)

if __name__ == "__main__":
    main()