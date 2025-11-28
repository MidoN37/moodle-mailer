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

# Account 1
ACC1_USER = os.environ.get("GMAIL_USER")
ACC1_PASS = os.environ.get("GMAIL_APP_PASS")

# Account 2
ACC2_USER = os.environ.get("GMAIL_USER_2")
ACC2_PASS = os.environ.get("GMAIL_APP_PASS_2")

# ==========================================
# ANTI-SPAM CONTENT GENERATOR (LINK-FREE)
# ==========================================
def get_random_content(user_name):
    # --- UKRAINIAN VARIATIONS ---
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
    
    # NO LINKS HERE - ONLY INSTRUCTIONS
    ua_ctas = [
        "Щоб отримати матеріали, знайдіть нас у Telegram: введіть у пошук @kovalkatia",
        "Для замовлення просто відпишіть на цей лист, або напишіть у Telegram: @kovalkatia",
        "Цікавить? Напишіть нам у Telegram (пошук за ніком): @kovalkatia",
        "Щоб придбати, відкрийте Telegram і знайдіть: @kovalkatia"
    ]
    
    ua_signoffs = [
        "З повагою,\nКоманда підтримки", "Бажаємо успіхів!", 
        "Гарної підготовки!"
    ]

    # --- ENGLISH VARIATIONS ---
    en_greetings = [
        f"Hello {user_name},", f"Hi {user_name},"
    ]
    en_intros = [
        "We have the complete updated database of 'Center of Testing' questions with correct answers.",
        "Prepare for KROK faster with our full question bank (PDF & Quiz)."
    ]
    en_offers = [
        "Options available:\n- Full PDF (299 UAH)\n- Interactive Quiz (399 UAH)"
    ]
    
    # NO LINKS HERE
    en_ctas = [
        "To get access, open Telegram and search for: @kovalkatia",
        "Interested? Reply to this email or find us on Telegram: @kovalkatia",
        "Contact us on Telegram (search username): @kovalkatia"
    ]
    
    en_signoffs = [
        "Best regards,", "Good luck!"
    ]

    # --- ASSEMBLE BODY ---
    ua_part = f"{random.choice(ua_greetings)}\n\n{random.choice(ua_intros)}\n\n{random.choice(ua_offers)}\n\n{random.choice(ua_ctas)}\n\n{random.choice(ua_signoffs)}"
    
    en_part = f"{random.choice(en_greetings)}\n\n{random.choice(en_intros)}\n\n{random.choice(en_offers)}\n\n{random.choice(en_ctas)}\n\n{random.choice(en_signoffs)}"

    full_body = f"{ua_part}\n\n=====================\n\nENGLISH VERSION\n\n{en_part}"
    
    subject_options = [
        "База питань «Центр тестування» (PDF/Quiz)", 
        "Підготовка до КРОК: Всі відповіді",
        "Матеріали Центр Тестування 2025"
    ]
    
    return random.choice(subject_options), full_body

# ==========================================
# MAIN LOGIC
# ==========================================

def load_state():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    default_state = {"date": today, "account": 1, "count_1": 0, "count_2": 0}
    
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

def main():
    state = load_state()
    print(f"Stats | Acc 1: {state['count_1']} | Acc 2: {state['count_2']}")

    active_user, active_pass = None, None
    current_acc_id = 1
    
    if state['count_1'] < LIMIT_PER_ACCOUNT:
        active_user, active_pass = ACC1_USER, ACC1_PASS
        current_acc_id = 1
    elif state['count_2'] < LIMIT_PER_ACCOUNT:
        active_user, active_pass = ACC2_USER, ACC2_PASS
        current_acc_id = 2
    else:
        print("DAILY LIMIT REACHED.")
        return

    print(f"Using Account {current_acc_id}: {active_user}")

    # --- LOGIN ---
    session = requests.Session()
    print("Logging in...")
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
    response = session.get(MOODLE_ONLINE_USERS_URL)
    user_ids = set(re.findall(r'user/view\.php\?id=(\d+)', response.text))
    print(f"Found {len(user_ids)} active users.")

    sent_history = get_sent_history()
    emails_sent_this_run = 0

    for user_id in user_ids:
        if current_acc_id == 1 and state['count_1'] >= LIMIT_PER_ACCOUNT:
            if state['count_2'] < LIMIT_PER_ACCOUNT:
                active_user, active_pass = ACC2_USER, ACC2_PASS
                current_acc_id = 2
            else: break
        elif current_acc_id == 2 and state['count_2'] >= LIMIT_PER_ACCOUNT:
             break

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

                print(f"Sending to {full_name} ({email})...")
                
                if send_email(active_user, active_pass, email, full_name, city):
                    print(f" -> SUCCESS")
                    save_to_history(email)
                    if current_acc_id == 1: state['count_1'] += 1
                    else: state['count_2'] += 1
                    save_state(state)
                    emails_sent_this_run += 1
                    time.sleep(random.randint(10, 20)) # Higher delay for safety
                else:
                    print(f" -> FAILED")
        except: continue
    
    print(f"Job Done. Sent {emails_sent_this_run} emails.")

if __name__ == "__main__":
    main()
