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

# --- SECRETS (GitHub Actions Secrets) ---
MOODLE_USER = os.environ.get("MOODLE_USER")
MOODLE_PASS = os.environ.get("MOODLE_PASS")
TELEGRAM_LINK = os.environ.get("TELEGRAM_LINK")

# Account 1
ACC1_USER = os.environ.get("GMAIL_USER")
ACC1_PASS = os.environ.get("GMAIL_APP_PASS")

# Account 2
ACC2_USER = os.environ.get("GMAIL_USER_2")
ACC2_PASS = os.environ.get("GMAIL_APP_PASS_2")

# ==========================================
# ANTI-SPAM CONTENT GENERATOR
# ==========================================
def get_random_content(user_name):
    # --- UKRAINIAN VARIATIONS ---
    ua_greetings = [
        f"Вітаємо, {user_name}!", f"Привіт, {user_name}!", f"Добрий день, {user_name}!", 
        f"Вітаю, {user_name}!", f"Доброго часу доби, {user_name}!"
    ]
    ua_intros = [
        "Ми підготували повну та актуальну базу всіх запитань із «Центр тестування» разом із правильними відповідями.",
        "У нас з'явилася найновіша база питань та відповідей для «Центру тестування».",
        "Пропонуємо вам оновлений список питань для підготовки до іспитів у «Центрі тестування» (з відповідями).",
        "Якщо ви готуєтесь до тестів, наша нова база запитань із правильними відповідями стане вам у нагоді."
    ]
    ua_offers = [
        "Ми пропонуємо два зручні варіанти:\nPDF-файл – 299 грн\nQuiz-тест – 399 грн",
        "Доступні формати:\n1. PDF з усіма відповідями (299 грн)\n2. Інтерактивний Quiz (399 грн)",
        "Ви можете обрати:\n- Повний PDF-файл за 299 грн\n- Інтерактивний тренажер (Quiz) за 399 грн"
    ]
    ua_ctas = [
        "Перед оплатою пишіть нам у Telegram, все розкажемо",
        "Усі деталі та оплата через Telegram",
        "Зв'яжіться з нами в Telegram для отримання матеріалів",
        "Пишіть в особисті для замовлення"
    ]
    ua_signoffs = [
        "З повагою,\nКоманда підтримки", "Бажаємо успіхів у підготовці!", 
        "Гарного дня,\nКоманда підтримки", "Успіхів на іспитах!"
    ]

    # --- ENGLISH VARIATIONS ---
    en_greetings = [
        f"Hello {user_name},", f"Hi {user_name},", f"Greetings {user_name},"
    ]
    en_intros = [
        "We have prepared the complete and fully updated database of all questions from “Center of Testing,” including correct answers.",
        "We are offering the newest database of questions and answers for the “Center of Testing” exams.",
        "Get ready for your exams with our updated question bank containing all correct answers."
    ]
    en_offers = [
        "We offer two options:\nPDF file – 299 UAH\nInteractive Quiz – 399 UAH",
        "Choose your format:\n1. PDF with answers (299 UAH)\n2. Interactive Quiz (399 UAH)"
    ]
    en_ctas = [
        "Before paying, you can contact us on Telegram",
        "Contact us on Telegram for details and payment",
        "Message us on Telegram to get started"
    ]
    en_signoffs = [
        "Best regards,\nSupport Team", "Good luck with your exams!", 
        "Sincerely,\nSupport Team"
    ]

    # --- ASSEMBLE BODY ---
    # Note: We append TELEGRAM_LINK at the end of CTAs or Signoffs to ensure it appears
    
    ua_part = f"{random.choice(ua_greetings)}\n\n{random.choice(ua_intros)}\n\n{random.choice(ua_offers)}\n\nОплата приймається через картку Monobank.\n\n{random.choice(ua_ctas)}: {TELEGRAM_LINK}\n\n{random.choice(ua_signoffs)}"
    
    en_part = f"{random.choice(en_greetings)}\n\n{random.choice(en_intros)}\n\n{random.choice(en_offers)}\n\nWe accept payment via Monobank card.\n\n{random.choice(en_ctas)}: {TELEGRAM_LINK}\n\n{random.choice(en_signoffs)}"

    full_body = f"{ua_part}\n\n=====================\n\nENGLISH VERSION\n\n{en_part}"
    
    subject_options = [
        "Оновлена база питань «Центр тестування»", 
        "Матеріали для підготовки: PDF та Quiz",
        "Центр тестування: Правильні відповіді",
        "Важливе оновлення для підготовки (Крок/Іспити)"
    ]
    
    return random.choice(subject_options), full_body

# ==========================================
# MAIN LOGIC
# ==========================================

def load_state():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    default_state = {"date": today, "account": 1, "count_1": 0, "count_2": 0}
    
    if not os.path.exists(STATE_FILE):
        return default_state
    
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
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
    # GET RANDOMIZED CONTENT
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
    print(f"Daily Stats | Acc 1: {state['count_1']} | Acc 2: {state['count_2']}")

    active_user = None
    active_pass = None
    current_acc_id = 1
    
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
        print(f"Connection Error: {e}")
        return

    # --- GET USERS ---
    response = session.get(MOODLE_ONLINE_USERS_URL)
    user_ids = set(re.findall(r'user/view\.php\?id=(\d+)', response.text))
    print(f"Found {len(user_ids)} active users on Moodle.")

    sent_history = get_sent_history()
    emails_sent_this_run = 0

    for user_id in user_ids:
        # CHECK LIMITS
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

        # SCRAPE PROFILE
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

                if "javascript" in email or "testcentr" in email or "mathjax" in email: continue
                if email in sent_history: 
                    # Silent skip
                    continue

                print(f"Sending to {full_name} ({email})...")
                
                if send_email(active_user, active_pass, email, full_name, city):
                    print(f" -> SUCCESS")
                    save_to_history(email)
                    
                    if current_acc_id == 1: state['count_1'] += 1
                    else: state['count_2'] += 1
                    save_state(state) 
                    
                    emails_sent_this_run += 1
                    
                    # Random delay between 10 and 20 seconds
                    delay = random.randint(10, 20)
                    time.sleep(delay)
                else:
                    print(f" -> FAILED")
        except Exception as e:
            print(f"Error scraping user {user_id}: {e}")
            continue
    
    print(f"Job Done. Sent {emails_sent_this_run} emails.")

if __name__ == "__main__":
    main()
