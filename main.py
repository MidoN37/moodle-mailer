import os
import requests
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
MOODLE_LOGIN_URL = "https://test.testcentr.org.ua/login/index.php"
MOODLE_ONLINE_USERS_URL = "https://test.testcentr.org.ua/blocks/online_users/view.php"
HISTORY_FILE = "history.txt"
MAX_EMAILS_PER_RUN = 20  # Safety limit to avoid spam blocks

# --- SECRETS ---
MOODLE_USER = os.environ.get("MOODLE_USER")
MOODLE_PASS = os.environ.get("MOODLE_PASS")
# NOTE: We reuse GMAIL_USER/PASS variable names for Outlook to avoid changing workflow file
SENDER_EMAIL = os.environ.get("GMAIL_USER") 
SENDER_PASSWORD = os.environ.get("GMAIL_APP_PASS") 
TELEGRAM_LINK = os.environ.get("TELEGRAM_LINK")

def get_sent_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_to_history(email):
    with open(HISTORY_FILE, "a") as f:
        f.write(email + "\n")

def send_email(to_email, user_name, city):
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
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # OUTLOOK SETTINGS
    smtp_server = "smtp.office365.com"
    smtp_port = 587

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"FAILED: Could not send email to {to_email}. Error: {e}")
        return False

def main():
    if not MOODLE_USER or not MOODLE_PASS:
        print("Error: Credentials missing.")
        return

    session = requests.Session()

    # 1. Login
    login_payload = {
        "username": MOODLE_USER,
        "password": MOODLE_PASS
    }
    
    response = session.post(MOODLE_LOGIN_URL, data=login_payload)
    if "login/index.php" in response.url: # If still on login page, it failed
        print("Login failed. Check credentials.")
        return
    print("Login successful.")

    # 2. Get Online Users
    response = session.get(MOODLE_ONLINE_USERS_URL)
    if response.status_code != 200:
        print("Failed to fetch online users page.")
        return

    # Simple parsing for user links (Regex is robust enough here)
    # Format: href=".../user/view.php?id=12345..."
    import re
    user_ids = set(re.findall(r'user/view\.php\?id=(\d+)', response.text))
    
    # Remove self (if known) or admin IDs usually low numbers, but safe to keep all
    print(f"Found {len(user_ids)} active users.")

    sent_history = get_sent_history()
    emails_sent_count = 0

    for user_id in user_ids:
        if emails_sent_count >= MAX_EMAILS_PER_RUN:
            print(f"SAFETY LIMIT REACHED: {MAX_EMAILS_PER_RUN} emails sent. Stopping.")
            break

        # Get User Profile
        profile_url = f"https://test.testcentr.org.ua/user/view.php?id={user_id}&course=1" # course=1 usually works for general view
        profile_page = session.get(profile_url).text

        # Extract Email
        email_match = re.search(r'mailto:([\w\.-]+@[\w\.-]+)', profile_page)
        # Extract Name (Title of page usually "Name - User profile")
        name_match = re.search(r'<title>(.*?)[:|-]', profile_page)
        # Extract City
        city_match = re.search(r'<dt>City/town</dt>\s*<dd>(.*?)</dd>', profile_page)

        if email_match:
            email = email_match.group(1)
            full_name = name_match.group(1).strip() if name_match else "Student"
            city = city_match.group(1).strip() if city_match else "Ukraine"

            if email in sent_history:
                print(f"Skipping {full_name} (Already sent).")
                continue

            print(f"Sending to {full_name} ({email})...")
            
            if send_email(email, full_name, city):
                print(f"SUCCESS: Email sent to {email}")
                save_to_history(email)
                emails_sent_count += 1
                # Sleep to be polite to SMTP server
                time.sleep(5) 
            else:
                print(f"FAILED: Could not send to {email}")
        
    print("Job Done.")

if __name__ == "__main__":
    main()
