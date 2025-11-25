import os
import requests
import smtplib
import time
import re
import html
import json
import datetime
from urllib.parse import unquote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
MOODLE_LOGIN_URL = "https://test.testcentr.org.ua/login/index.php"
MOODLE_ONLINE_USERS_URL = "https://test.testcentr.org.ua/?redirect=0" 
HISTORY_FILE = "history.txt"
QUOTA_FILE = "brevo_quota.json"

# --- LIMITS ---
MAX_EMAILS_PER_RUN = 100        
BREVO_DAILY_LIMIT = 295         

# --- SECRETS ---
MOODLE_USER = os.environ.get("MOODLE_USER")
MOODLE_PASS = os.environ.get("MOODLE_PASS")
TELEGRAM_LINK = os.environ.get("TELEGRAM_LINK")

# --- SMTP CONFIG ---
# BREVO
BREVO_HOST = "smtp-relay.brevo.com"
BREVO_PORT = 587
BREVO_USER = os.environ.get("BREVO_USER") 
BREVO_PASS = os.environ.get("BREVO_PASS") 

# GMAIL
GMAIL_HOST = "smtp.gmail.com"
GMAIL_PORT = 587
GMAIL_USER = os.environ.get("GMAIL_USER") 
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS") 

SENDER_EMAIL = "kathryncoleman77@gmail.com" 

# --- QUOTA MANAGEMENT ---
def get_brevo_usage():
    """Reads the quota file. Resets if date has changed."""
    today_str = str(datetime.date.today())
    
    # If file doesn't exist, create it with 0
    if not os.path.exists(QUOTA_FILE):
        return 0

    try:
        with open(QUOTA_FILE, "r") as f:
            data = json.load(f)
            
        # If the date in file is not today, it means it's a new day.
        # We return 0. The file will be updated with the new date 
        # when we call increment_brevo_usage().
        if data.get("date") != today_str:
            return 0
        
        return data.get("count", 0)
    except:
        return 0

def increment_brevo_usage():
    """Increments the counter for today."""
    today_str = str(datetime.date.today())
    current_count = get_brevo_usage()
    
    data = {
        "date": today_str,
        "count": current_count + 1
    }
    
    with open(QUOTA_FILE, "w") as f:
        json.dump(data, f)

# --- HISTORY ---
def get_sent_history():
    if not os.path.exists(HISTORY_FILE):
        # Create file if missing
        open(HISTORY_FILE, 'a').close()
        return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_to_history(email):
    with open(HISTORY_FILE, "a") as f:
        f.write(email + "\n")

# --- SENDING ---
def send_via_smtp(host, port, user, password, msg):
    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"SMTP Error on {host}: {e}")
        return False

def send_smart_email(to_email, user_name, city):
    subject = "Оновлена база питань «Центр тестування» – доступна у PDF та Quiz"
    
    body = f"""
Вітаю, {user_name} із {city}!
Ми підготували повну та актуальну базу всіх запитань із «Центр тестування» разом із правильними відповідями. Це найновіше оновлення, зібране у зручному форматі, щоб допомогти швидко та впевнено підготуватися.

Ми пропонуємо два варіанти:
	•	PDF-файл з усіма запитаннями й відповідями – 299 грн
	•	Quiz з інтерактивним тестуванням – 399 грн

Оплата приймається через картку Monobank. Після оплати ми одразу надсилаємо останню версію матеріалів.

Перед оплатою ви можете написати нам у Telegram, і ми відповімо на всі запитання та пояснимо, як усе працює.

Будемо раді допомогти вам у підготовці!

З повагою,

{TELEGRAM_LINK}
"""

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # 1. CHECK QUOTA
    brevo_usage = get_brevo_usage()
    
    # Logic: Only use Brevo if usage is low AND credentials exist
    use_brevo = (brevo_usage < BREVO_DAILY_LIMIT) and (BREVO_USER is not None)

    # 2. ATTEMPT BREVO
    if use_brevo:
        if send_via_smtp(BREVO_HOST, BREVO_PORT, BREVO_USER, BREVO_PASS, msg):
            print(f"Sent via Brevo (Count: {brevo_usage + 1}/{BREVO_DAILY_LIMIT})")
            increment_brevo_usage()
            return True, "brevo"
        else:
            print("Brevo failed (Error). Switching to Gmail...")

    # 3. FALLBACK TO GMAIL
    print("Using Gmail (Backup Provider)...")
    if send_via_smtp(GMAIL_HOST, GMAIL_PORT, GMAIL_USER, GMAIL_PASS, msg):
        return True, "gmail"
    
    return False, None

def main():
    usage = get_brevo_usage()
    print(f"--- STATUS: Brevo Usage Today: {usage}/{BREVO_DAILY_LIMIT} ---")

    if not MOODLE_USER or not MOODLE_PASS:
        print("Error: Credentials missing.")
        return

    session = requests.Session()

    # 1. LOGIN
    print("Attempting login...")
    try:
        login_page = session.get(MOODLE_LOGIN_URL)
        token_match = re.search(r'name="logintoken" value="([^"]+)"', login_page.text)
        login_token = token_match.group(1) if token_match else ""

        login_payload = {
            "username": MOODLE_USER,
            "password": MOODLE_PASS,
            "logintoken": login_token
        }
        
        response = session.post(MOODLE_LOGIN_URL, data=login_payload)
        
        if "login/logout.php" not in response.text:
            print("Login failed.")
            return
        
        print("Login successful.")
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # 2. GET USERS
    try:
        response = session.get(MOODLE_ONLINE_USERS_URL)
        user_ids = set(re.findall(r'user/view\.php\?id=(\d+)', response.text))
        print(f"Found {len(user_ids)} active users.")
    except Exception as e:
        print(f"Scraping error: {e}")
        return

    sent_history = get_sent_history()
    emails_sent_count = 0

    for user_id in user_ids:
        if emails_sent_count >= MAX_EMAILS_PER_RUN:
            print(f"SAFETY LIMIT REACHED: {MAX_EMAILS_PER_RUN} emails sent. Stopping.")
            break

        try:
            profile_url = f"https://test.testcentr.org.ua/user/view.php?id={user_id}&course=1"
            profile_page = session.get(profile_url).text

            email_match = re.search(r'<dt>Email address</dt>\s*<dd><a href="[^"]*">([^<]+)</a></dd>', profile_page)
            name_match = re.search(r'<h1 class="h2">(.*?)</h1>', profile_page)
            city_match = re.search(r'<dt>City/town</dt>\s*<dd>(.*?)</dd>', profile_page)

            if email_match:
                raw_email = email_match.group(1).strip()
                email = html.unescape(unquote(raw_email))
                full_name = name_match.group(1).strip() if name_match else "Student"
                city = city_match.group(1).strip() if city_match else "Ukraine"

                if "javascript" in email or "testcentr" in email or "mathjax" in email:
                    continue

                if email in sent_history:
                    continue

                print(f"Processing {full_name} ({email})...")
                
                success, provider_used = send_smart_email(email, full_name, city)
                
                if success:
                    print(f"SUCCESS: Email sent to {email}")
                    save_to_history(email)
                    emails_sent_count += 1
                    
                    if provider_used == "gmail":
                        time.sleep(5)
                    else:
                        time.sleep(2)
                else:
                    print(f"FAILED: Could not send to {email}")
        except Exception as e:
            print(f"Error on user {user_id}: {e}")
            continue
        
    print("Job Done.")

if __name__ == "__main__":
    main()
