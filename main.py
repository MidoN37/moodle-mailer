import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import time

# --- CONFIGURATION FROM ENVIRONMENT VARIABLES ---
MOODLE_USER = os.environ["MOODLE_USER"]
MOODLE_PASS = os.environ["MOODLE_PASS"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASS = os.environ["GMAIL_APP_PASS"]
TELEGRAM_LINK = os.environ["TELEGRAM_LINK"]

# --- SETUP SESSION ---
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

def load_history():
    if not os.path.exists("history.txt"):
        return set()
    with open("history.txt", "r") as f:
        return set(line.strip() for line in f)

def append_to_history(user_id):
    with open("history.txt", "a") as f:
        f.write(f"{user_id}\n")

def send_email(to_email, user_name, city):
    subject = "Оновлена база питань «Центр тестування» – доступна у PDF та Google Form"
    
    body = f"""
To: {to_email}
Subject: {subject}

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
    msg['From'] = GMAIL_USER
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"SUCCESS: Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"FAILED: Could not send email to {to_email}. Error: {e}")
        return False

def login():
    login_url = "https://test.testcentr.org.ua/login/index.php"
    try:
        r = session.get(login_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        token = soup.find('input', {'name': 'logintoken'})['value']
        
        payload = {'username': MOODLE_USER, 'password': MOODLE_PASS, 'logintoken': token}
        r = session.post(login_url, data=payload)
        
        if "login/index.php" in r.url:
            print("Login failed.")
            return False
        print("Login successful.")
        return True
    except Exception as e:
        print(f"Login error: {e}")
        return False

def get_profile_info(profile_url):
    try:
        r = session.get(profile_url)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        email_dt = soup.find('dt', string="Email address")
        email = email_dt.find_next('dd').get_text(strip=True) if email_dt else None
        
        city_dt = soup.find('dt', string="City/town")
        city = city_dt.find_next('dd').get_text(strip=True) if city_dt else "your city"
        
        return email, city
    except:
        return None, None

def main():
    sent_users = load_history()
    
    if not login():
        return

    main_url = "https://test.testcentr.org.ua/?redirect=0"
    response = session.get(main_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    user_links = soup.select('li.listentry div.user a')
    print(f"Found {len(user_links)} active users.")

    for user in user_links:
        name = user.get_text(strip=True)
        initials = user.find('span', class_='userinitials')
        if initials:
            name = name.replace(initials.get_text(strip=True), "").strip()

        if "el mahdi nih" in name.lower():
            continue

        # Extract User ID from URL to prevent duplicates
        profile_url = user['href']
        user_id = profile_url.split('id=')[1].split('&')[0]

        if user_id in sent_users:
            print(f"Skipping {name} (Already sent).")
            continue

        email, city = get_profile_info(profile_url)
        
        if email and email != "Email not found":
            success = send_email(email, name, city)
            if success:
                append_to_history(user_id)
                sent_users.add(user_id)
                # Wait 10 seconds between emails to allow Gmail to breathe
                time.sleep(10) 
        else:
            print(f"Skipping {name} (No email found).")

if __name__ == "__main__":
    main()
