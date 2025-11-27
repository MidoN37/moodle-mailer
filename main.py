import os
import requests
import smtplib
import time
import re
import json
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
MOODLE_LOGIN_URL = "https://test.testcentr.org.ua/login/index.php"
MOODLE_ONLINE_USERS_URL = "https://test.testcentr.org.ua/?redirect=0" 
HISTORY_FILE = "history.txt"
STATE_FILE = "bot_state.json" # Stores daily count and current account
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

def load_state():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    default_state = {"date": today, "account": 1, "count_1": 0, "count_2": 0}
    
    if not os.path.exists(STATE_FILE):
        return default_state
    
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            # Reset if new day
            if state.get("date") != today:
                return default_state
            return state
    except:
        return default_state

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def get_sent_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_to_history(email):
    with open(HISTORY_FILE, "a") as f:
        f.write(email + "\n")

def send_email(sender_user, sender_pass, to_email, user_name, city):
    subject = "Оновлена база питань «Центр тестування» – доступна у PDF та Quiz"
    body = f"""
Вітаємо, {user_name} із {city}!

Ми підготували повну та актуальну базу всіх запитань із «Центр тестування» разом із правильними відповідями. Це найновіше оновлення, зібране у зручному форматі, щоб допомогти швидко та впевнено підготуватися.

Ми пропонуємо два варіанти:
PDF-файл з усіма запитаннями й відповідями – 299 грн
Quiz з інтерактивним тестуванням – 399 грн

Оплата приймається через картку Monobank. Після оплати ми одразу надсилаємо останню версію матеріалів.

Перед оплатою ви можете написати нам у Telegram, і ми відповімо на всі запитання та пояснимо, як усе працює.

Будемо раді допомогти вам у підготовці!

З повагою,
Команда підтримки
{TELEGRAM_LINK}

=====================

ENGLISH VERSION

Hello {user_name} from {city},

We have prepared the complete and fully updated database of all questions from “Center of Testing,” including the correct answers.

We offer two options:
PDF file with all questions and answers – 299 UAH
Quiz interactive test version – 399 UAH

We accept payment via Monobank card. Before paying, you can contact us on Telegram.

Best regards,
Support Team
{TELEGRAM_LINK}
"""
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
    print(f"Daily Stats | Acc 1: {state['count_1']} | Acc 2: {state['count_2']}")

    # Determine Active Account
    active_user = None
    active_pass = None
    
    if state['count_1'] < LIMIT_PER_ACCOUNT:
        active_user, active_pass = ACC1_USER, ACC1_PASS
        current_acc_id = 1
    elif state['count_2'] < LIMIT_PER_ACCOUNT:
        active_user, active_pass = ACC2_USER, ACC2_PASS
        current_acc_id = 2
    else:
        print("DAILY LIMIT REACHED FOR BOTH ACCOUNTS. Stopping.")
        return

    print(f"Using Account {current_acc_id}: {active_user}")

    # --- LOGIN MOODLE ---
    session = requests.Session()
    print("Attempting login...")
    login_page = session.get(MOODLE_LOGIN_URL)
    # Simple Regex for token
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

    # --- GET USERS ---
    response = session.get(MOODLE_ONLINE_USERS_URL)
    user_ids = set(re.findall(r'user/view\.php\?id=(\d+)', response.text))
    print(f"Found {len(user_ids)} active users.")

    sent_history = get_sent_history()
    emails_sent_this_run = 0

    for user_id in user_ids:
        # --- SAFETY CHECK (If limit hit mid-run) ---
        if current_acc_id == 1 and state['count_1'] >= LIMIT_PER_ACCOUNT:
            print("Account 1 Full. Switching to Account 2...")
            if state['count_2'] < LIMIT_PER_ACCOUNT:
                active_user, active_pass = ACC2_USER, ACC2_PASS
                current_acc_id = 2
            else:
                print("Both accounts full. Stopping.")
                break
        elif current_acc_id == 2 and state['count_2'] >= LIMIT_PER_ACCOUNT:
             print("Account 2 Full. Stopping.")
             break

        # --- PROFILE SCRAPE ---
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

            if "javascript" in email or "testcentr" in email or "mathjax" in email: continue
            if email in sent_history: 
                print(f"Skipping {full_name} (Already sent).")
                continue

            print(f"Sending to {full_name} ({email})...")
            
            if send_email(active_user, active_pass, email, full_name, city):
                print(f"SUCCESS")
                save_to_history(email)
                
                # Update State
                if current_acc_id == 1: state['count_1'] += 1
                else: state['count_2'] += 1
                save_state(state) # Save count immediately
                
                emails_sent_this_run += 1
                time.sleep(5)
            else:
                print(f"FAILED")
    
    print(f"Job Done. Sent {emails_sent_this_run} emails.")

if __name__ == "__main__":
    main()
