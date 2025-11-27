import os
import smtplib
import time
import json
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
CONTACTS_FILE = "contacts.json"
HISTORY_FILE = "history.json"
DAILY_LIMIT = 495

# --- SECRETS ---
TELEGRAM_LINK = os.environ.get("TELEGRAM_LINK")

def get_credentials_by_time():
    """
    Decides which account to use based on the current UTC hour.
    13:00 UTC (15:00 UA) -> Account 2
    18:00 UTC (20:00 UA) -> Account 1
    """
    # Get current hour in UTC
    current_hour = datetime.datetime.utcnow().hour
    
    user1 = os.environ.get("GMAIL_USER")
    pass1 = os.environ.get("GMAIL_APP_PASS")
    
    user2 = os.environ.get("GMAIL_USER_2")
    pass2 = os.environ.get("GMAIL_APP_PASS_2")

    print(f"Current UTC Hour: {current_hour}")

    # If it's around 13:00 UTC, use Account 2
    if 12 <= current_hour < 14:
        print(f"Time for Batch 1 (15:00 UA). Using Account 2: {user2}")
        return user2, pass2
    
    # If it's around 18:00 UTC, use Account 1
    elif 17 <= current_hour < 19:
        print(f"Time for Batch 2 (20:00 UA). Using Account 1: {user1}")
        return user1, pass1
    
    # Default (Manual Run) -> Use Account 1
    else:
        print(f"Manual/Off-hour run. Defaulting to Account 1: {user1}")
        return user1, pass1

def load_json(filepath):
    if not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return []

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_email(sender_email, sender_pass, to_email, user_name, city):
    subject = "Оновлена база питань «Центр тестування» – доступна у PDF та Google Form"
    body = f"""
УКРАЇНСЬКА ВЕРСІЯ

Вітаємо, {user_name} із {city}!

Ми отримали вашу електронну адресу з відкритих даних «Центру тестування» – це публічна інформація, доступна всім.

Хочемо запропонувати вам повну та актуальну базу всіх запитань із «Центр тестування» разом із правильними відповідями. На відміну від офіційних 150-питань тестів, які постійно оновлюються та видаляються — і де складно побачити весь банк запитань — ми надаємо всю базу повністю.

Доступні два формати:
	•	PDF-файл з усіма запитаннями та відповідями — 299 грн
	•	QUIZ-формат, у якому вся база поділена на блоки по 50 питань. Ви можете проходити кожен блок необмежену кількість разів, поки не вивчите всі варіанти напам’ять — 399 грн

Оплата здійснюється через картку Monobank, і після оплати ви одразу отримуєте найновішу версію.

Перед оплатою ви можете написати нам у Telegram: @kovalkatia , де ми детально пояснимо, як працюють матеріали, і відповімо на всі ваші запитання.

Будемо раді допомогти у вашій підготовці!

З повагою,
Команда підтримки
{TELEGRAM_LINK}

=====================

ENGLISH VERSION

Subject: Updated “Center of Testing” Question Database – Now in PDF & Google Form

Hello {user_name} from {city},

We received your email from publicly available “Center of Testing” data — this information is open and accessible to anyone.

We offer the complete and fully updated database of all “Center of Testing” questions with correct answers. Unlike the official 150-question tests that constantly rotate, disappear, and never show you the full bank, we provide the entire database in one place.

You can choose between two formats:
	•	PDF file with all questions and answers — 299 UAH
	•	QUIZ format, where the full database is divided into convenient 50-question chunks. You can retake each chunk unlimited times until you fully memorize all variations — 399 UAH

Payment is accepted via Monobank card, and once payment is confirmed, you immediately receive the latest updated version.

Before paying, you can contact us on Telegram @kovalkatia , where we will explain everything clearly and answer any questions.

Best regards,
Support Team
{TELEGRAM_LINK}
"""
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"   FAILED: {e}")
        return False

def main():
    # 1. Determine Account
    active_user, active_pass = get_credentials_by_time()
    
    if not active_user or not active_pass:
        print("Error: Missing credentials for this time slot.")
        return

    # 2. Load Data
    contacts = load_json(CONTACTS_FILE)
    history = load_json(HISTORY_FILE)
    
    # Filter: People NOT in history
    history_emails = {h['email'] for h in history}
    to_send = [c for c in contacts if c['email'] not in history_emails]
    
    print(f"Total Contacts Collected: {len(contacts)}")
    print(f"Total Already Emailed: {len(history)}")
    print(f"Queue Size: {len(to_send)}")

    if not to_send:
        print("No new contacts to email.")
        return

    # 3. Send Loop
    count = 0
    for person in to_send:
        if count >= DAILY_LIMIT:
            print("Daily limit reached for this account. Stopping.")
            break

        print(f"[{count+1}/{DAILY_LIMIT}] Sending to {person['name']} via {active_user}...")
        
        if send_email(active_user, active_pass, person['email'], person['name'], person['city']):
            # Add to history
            history.append({
                "email": person['email'],
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "sender": active_user
            })
            # Save immediately
            save_json(HISTORY_FILE, history)
            count += 1
            time.sleep(5) # Polite delay
        else:
            print("   Skipping due to error.")

    print("Blast finished.")

if __name__ == "__main__":
    main()
