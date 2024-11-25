import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email import encoders
import os
import sqlite3
import streamlit as st


# Database setup
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT
                )""")
    conn.commit()
    conn.close()


# Register a new user
def register_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


# Verify login credentials
def login_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None


# Email configuration
EMAIL = ""
PASSWORD = ""
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993


# Function to send email with or without attachment
def send_email_with_attachment(to_email, subject, body, file_path=None):
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL, PASSWORD)

        msg = MIMEMultipart()
        msg['From'] = EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        if file_path:
            try:
                with open(file_path, "rb") as attachment:
                    part = email.mime.base.MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{os.path.basename(file_path)}"',
                    )
                    msg.attach(part)
                st.success(f"File '{file_path}' attached successfully.")
            except Exception as e:
                st.error(f"Error attaching file: {e}")

        server.sendmail(EMAIL, to_email, msg.as_string())
        st.success("Email sent successfully!")
        server.quit()
    except Exception as e:
        st.error(f"Error sending email: {e}")


# Function to read emails
def read_emails():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, 'ALL')
        email_ids = messages[0].split()

        st.header("Last 5 Emails:")
        for eid in email_ids[-5:]:
            status, data = mail.fetch(eid, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            st.subheader(f"From: {msg['From']}")
            st.write(f"Subject: {msg['Subject']}")

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        st.write(f"Body: {part.get_payload(decode=True).decode()}")
            else:
                st.write(f"Body: {msg.get_payload(decode=True).decode()}")
            st.write("-" * 50)

        mail.logout()
    except Exception as e:
        st.error(f"Error reading emails: {e}")


# Initialize the database
init_db()

# Streamlit UI
st.title("Email Client with Persistent Login")

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Login/Register switch
if not st.session_state.logged_in:
    auth_option = st.sidebar.radio("Choose an option:", ["Login", "Register"])

    if auth_option == "Register":
        st.header("Register")
        reg_username = st.text_input("Username")
        reg_password = st.text_input("Password", type="password")
        if st.button("Register"):
            if register_user(reg_username, reg_password):
                st.success("Registration successful! Please log in.")
            else:
                st.error("Username already exists. Please try a different one.")

    elif auth_option == "Login":
        st.header("Login")
        login_username = st.text_input("Username")
        login_password = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(login_username, login_password):
                st.session_state.logged_in = True
                st.session_state.username = login_username
                st.success(f"Welcome {login_username}!")
            else:
                st.error("Invalid username or password. Please try again.")

# If logged in, show email client options
if st.session_state.logged_in:
    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    menu = st.sidebar.selectbox("Menu", ["Send Email", "Read Emails", "Compose Email with Attachment", "Logout"])

    if menu == "Send Email":
        st.header("Send Email")
        to_email = st.text_input("Recipient's Email")
        subject = st.text_input("Subject")
        body = st.text_area("Message")
        if st.button("Send Email"):
            send_email_with_attachment(to_email, subject, body)

    elif menu == "Read Emails":
        st.header("Inbox")
        if st.button("Fetch Emails"):
            read_emails()

    elif menu == "Compose Email with Attachment":
        st.header("Compose Email with Attachment")
        to_email = st.text_input("Recipient's Email")
        subject = st.text_input("Subject")
        body = st.text_area("Message")
        uploaded_file = st.file_uploader("Choose a file to attach", type=["txt", "pdf", "png", "jpg", "jpeg", "zip"])
        if st.button("Send Email with Attachment"):
            file_path = None
            if uploaded_file:
                file_path = f"./{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            send_email_with_attachment(to_email, subject, body, file_path)
            if file_path:
                os.remove(file_path)

    elif menu == "Logout":
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.success("You have logged out.")