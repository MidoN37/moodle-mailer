import os
import requests
import smtplib
import time
import re
import json
import datetime
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
MOODLE_LOGIN_URL = "https://test.testcentr.org.ua/login/index.php"
MOODLE_ONLINE_USERS_URL = "https://test.testcentr.org.ua/?redirect=0" 
HISTORY_FILE = "history.txt"
STATE_FILE = "bot_state.json" 
LIMIT_PER_ACCOUNT = 495

# --- SECRETS ---
MOODLE_USER = os.environ.get("MOODLE_USER")
MOODLE_PASS = os.environ.get("MOODLE_PASS")
TELEGRAM_LINK = os.environ.get("TELEGRAM_LINK")

# Account 1
ACC1_USER = os.environ.get("GMAIL_USER")
ACC1_PASS = os.environ.get("GMAIL_APP_PASS")

# Account 2
ACC2_USER = os.environ.get("GMAIL_USER_2")
ACC2_PASS = os.environ.get("GMAIL_APP_PASS_2")

# --- CONTENT GENERATOR (Link-Free) ---
def get_random_content(user_name):
    ua_greetings = [
        f"Вітаємо, {user_name}!", f"Привіт, {user_name}!", f"Добрий день, {user_name}!", 
        f"Вітаю, {user_name}!"
    ]
    ua_intros = [
        "Ми підготували повну базу всіх запитань «Центр тестування» (КРОК) разом із правильними відповідями.",
        "Маємо оновлену базу тестів та відповідей для підготовки до іспитів «Центру тестування».",
        "Якщо ви готуєтесь до КРОК, наша повна база питань із відповідями зекономить ваш час."
    ]
    ua_offers = [
        "Є два варіанти:\n1. PDF-файл з усіма питаннями (299 грн)\n2. Інтерактивний Quiz для тренування (399 грн)",
        "Доступні формати:\n- PDF з відповідями (299 грн)\n- Quiz-тренажер (399 грн)"
    ]
    ua_ctas = [
        "Щоб отримати матеріали, знайдіть нас у Telegram: введіть у пошук @kovalkatia",
        "Для замовлення просто відпишіть на цей лист, або напишіть у Telegram: @kovalkatia",
        "Цікавить? Напишіть нам у Telegram (пошук за ніком): @kovalkatia",
        "Щоб придбати, відкрийте Telegram і знайдіть: @kovalkatia"
    ]
    ua_signoffs = ["З повагою,\nКоманда підтримки", "Бажаємо успіхів!", "Гарної підготовки!"]

    en_greetings = [f"Hello {user_name},", f"Hi {user_name},"]
    en_intros = ["We have the complete updated database of 'Center of Testing' questions with correct answers."]
    en_offers = ["Options available:\n- Full PDF (299 UAH)\n- Interactive Quiz (399 UAH)"]
    en_ctas = ["To get access, open Telegram and search for: @kovalkatia", "Interested? Reply to this email or find us on Telegram: @kovalkatia"]
    en_signoffs = ["Best regards,", "Good luck!"]

    ua_part = f"{random.choice(ua_greetings)}\n\n{random.choice(ua_intros)}\n\n{random.choice(ua_offers)}\n\n{random.choice(ua_ctas)}\n\n{random.choice(ua_signoffs)}"
    en_part = f"{random.choice(en_greetings)}\n\n{random.choice(en_intros)}\n\n{random.choice(en_offers)}\n\n{random.choice(en_ctas)}\n\n{random.choice(en_signoffs)}"

    full_body = f"{ua_part}\n\n=====================\n\nENGLISH VERSION\n\n{en_part}"
    
    subject_options = [
        "База питань «Центр тестування» (PDF/Quiz)", 
        "Підготовка до КРОК: Всі відповіді",
        "Матеріали Центр Тестування 2025"
    ]
    
    return random.choice(subject_options), full_body

# --- STATE MANAGEMENT ---
def load_state():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    # 'last_used': 0 means start with 1. 1 means next is 2. 2 means next is 1.
    default_state = {"date": today, "count_1": 0, "count_2": 0, "last_used": 2}
    
    if not os.path.exists(STATE_FILE): return default_state
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            if state.get("date") != today: return default_state
            return state
    except: return default_state

def save_state(state):
    with open(STATE_FILE, 'w') as f: json.dump(state, f)

def get_sent_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r") as f: return set(line.strip() for line in f)

def save_to_history(email):
    with open(HISTORY_FILE, "a") as f: f.write(email + "\n")

# --- EMAIL LOGIC ---
def send_email(sender_user, sender_pass, to_email, user_name, city):
    subject, body = get_random_content(user_name)
    msg = MIMEMultipart()
    msg['From'] = sender_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_user, sender_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"   FAILED ({sender_user}): {e}")
        return False

def get_next_account(state):
    """Logic to alternate accounts and respect limits"""
    # If last was 1, try 2. If last was 2, try 1.
    if state['last_used'] == 1:
        preferred = 2
    else:
        preferred = 1

    # Check if preferred is full
    if preferred == 1 and state['count_1'] >= LIMIT_PER_ACCOUNT:
        preferred = 2 # Fallback to 2
    if preferred == 2 and state['count_2'] >= LIMIT_PER_ACCOUNT:
        preferred = 1 # Fallback to 1

    # Final Check: Are BOTH full?
    if (preferred == 1 and state['count_1'] >= LIMIT_PER_ACCOUNT) or \
       (preferred == 2 and state['count_2'] >= LIMIT_PER_ACCOUNT):
        return None, None, None # STOP

    # Return credentials
    if preferred == 1:
        return 1, ACC1_USER, ACC1_PASS
    else:
        return 2, ACC2_USER, ACC2_PASS

def main():
    # --- LOGIN MOODLE ---
    session = requests.Session()
    print("Attempting login...")
    try:
        login_page = session.get(MOODLE_LOGIN_URL)
        token_match = re.search(r'name="logintoken" value="([^"]+)"', login_page.text)
        payload = {
            "username": MOODLE_USER,
            "password": MOODLE_PASS,
            "logintoken": token_match.group(1) if token_match else ""
        }
        response = session.post(MOODLE_LOGIN_URL, data=payload)
        if "login/logout.php" not in response.text:
            print("Login failed.")
            return
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # --- GET USERS ---
    print("Login successful. Fetching users...")
    response = session.get(MOODLE_ONLINE_USERS_URL)
    user_ids = set(re.findall(r'user/view\.php\?id=(\d+)', response.text))
    print(f"Found {len(user_ids)} active users.")

    sent_history = get_sent_history()
    state = load_state()
    emails_sent_this_run = 0

    print(f"Daily Stats: Acc1={state['count_1']} | Acc2={state['count_2']}")

    for user_id in user_ids:
        # 1. Get Next Sender Account
        acc_id, active_user, active_pass = get_next_account(state)
        
        if not active_user:
            print("Daily limits reached for BOTH accounts. Stopping.")
            break

        # 2. Scrape Profile
        try:
            profile_url = f"https://test.testcentr.org.ua/user/view.php?id={user_id}&course=1"
            profile_page = session.get(profile_url).text
            
            email_match = re.search(r'<dt>Email address</dt>\s*<dd><a href="[^"]*">([^<]+)</a></dd>', profile_page)
            name_match = re.search(r'<h1 class="h2">(.*?)</h1>', profile_page)
            city_match = re.search(r'<dt>City/town</dt>\s*<dd>(.*?)</dd>', profile_page)

            if email_match:
                from urllib.parse import unquote
                import html
                email = html.unescape(unquote(email_match.group(1).strip()))
                full_name = name_match.group(1).strip() if name_match else "Student"
                city = city_match.group(1).strip() if city_match else "Ukraine"

                if any(x in email for x in ["javascript", "testcentr", "mathjax"]): continue
                if email in sent_history: continue

                print(f"Sending to {full_name} ({email}) via {active_user}...")
                
                if send_email(active_user, active_pass, email, full_name, city):
                    print(f" -> SUCCESS")
                    save_to_history(email)
                    
                    # Update State
                    if acc_id == 1: state['count_1'] += 1
                    else: state['count_2'] += 1
                    state['last_used'] = acc_id # Flip for next turn
                    save_state(state)
                    
                    emails_sent_this_run += 1
                    time.sleep(random.randint(10, 20)) 
                else:
                    print(f" -> FAILED")
        except Exception as e:
            print(f"Error processing user {user_id}: {e}")
            continue
    
    print(f"Job Done. Sent {emails_sent_this_run} emails.")

if __name__ == "__main__":
    main()
