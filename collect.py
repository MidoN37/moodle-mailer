import os
import re
import json
import requests

# --- CONFIGURATION ---
MOODLE_LOGIN_URL = "https://test.testcentr.org.ua/login/index.php"
MOODLE_ONLINE_USERS_URL = "https://test.testcentr.org.ua/?redirect=0" 
CONTACTS_FILE = "contacts.json"

# --- SECRETS ---
MOODLE_USER = os.environ.get("MOODLE_USER")
MOODLE_PASS = os.environ.get("MOODLE_PASS")

def load_json(filepath):
    if not os.path.exists(filepath): return []
    with open(filepath, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return []

def save_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    session = requests.Session()

    # 1. LOGIN
    print("Logging in...")
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

    # 2. GET USER IDs
    print("Fetching active users...")
    response = session.get(MOODLE_ONLINE_USERS_URL)
    user_ids = set(re.findall(r'user/view\.php\?id=(\d+)', response.text))
    print(f"Found {len(user_ids)} IDs.")

    # 3. LOAD EXISTING CONTACTS
    contacts = load_json(CONTACTS_FILE)
    existing_emails = {c['email'] for c in contacts}

    # 4. PROCESS USERS
    new_contacts = 0
    for uid in user_ids:
        try:
            profile = session.get(f"https://test.testcentr.org.ua/user/view.php?id={uid}&course=1").text
            
            # Extract Data
            email_m = re.search(r'<dt>Email address</dt>\s*<dd><a href="[^"]*">([^<]+)</a></dd>', profile)
            name_m = re.search(r'<h1 class="h2">(.*?)</h1>', profile)
            city_m = re.search(r'<dt>City/town</dt>\s*<dd>(.*?)</dd>', profile)

            if email_m:
                from urllib.parse import unquote
                import html
                email = html.unescape(unquote(email_m.group(1).strip()))
                name = name_m.group(1).strip() if name_m else "Student"
                city = city_m.group(1).strip() if city_m else "Ukraine"

                # Filters
                if any(x in email for x in ['javascript', 'testcentr', 'mathjax']): continue
                if email in existing_emails: continue

                # Add New Contact
                contacts.append({
                    "email": email,
                    "name": name,
                    "city": city,
                    "id": uid
                })
                existing_emails.add(email)
                new_contacts += 1
                print(f" + Added: {name}")
                
        except Exception as e:
            print(f"Error extracting {uid}: {e}")

    # 5. SAVE
    if new_contacts > 0:
        save_json(CONTACTS_FILE, contacts)
        print(f"Saved {new_contacts} new contacts. Total: {len(contacts)}")
    else:
        print("No new contacts found.")

if __name__ == "__main__":
    main()
