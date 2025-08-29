from flask import Flask, render_template, request, jsonify
import gspread
import json
from google.oauth2 import service_account
from google.oauth2.service_account import Credentials
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Load credentials from Docker secret file
with open('/etc/secrets/google_sheets_json.json') as f:
    credentials_info = json.load(f)

creds = service_account.Credentials.from_service_account_info(
    credentials_info, scopes=SCOPES
)
client = gspread.authorize(creds)

# Open Google Sheet
sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/17JO6P0OkcEIH4RCCQLjcNqYsuetw5f0kAfITko629Rc/edit#gid=0"
).sheet1

# Gmail setup
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"


def send_confirmation_email(to_email, first_name, last_name):
    """Send confirmation email after successful registration"""
    try:
        subject = "Registration Successful - Kairali Syracuse"
        body = f"Hello {first_name} {last_name},\n\nYour registration was successful!\n\nRegards,\nKairali Syracuse"
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print("❌ Email sending failed:", e)


@app.route("/")
def index():
    return render_template("form.html")


@app.route("/get_emails")
def get_emails():
    """Return all emails from sheet for auto-complete"""
    try:
        emails = sheet.col_values(1)[1:]  # skip header row
        return jsonify(emails)
    except Exception as e:
        print("Error fetching emails:", e)
        return jsonify([])


@app.route("/get_user")
def get_user():
    """Fetch user data by email"""
    email = request.args.get("email", "").strip()
    if not email:
        return jsonify([])

    try:
        cell = sheet.find(email)
        row = sheet.row_values(cell.row)
        return jsonify(row)
    except Exception:
        # If not found, just return empty
        return jsonify([])


@app.route("/submit", methods=["POST"])
def submit():
    """Handle form submission"""
    data = request.form.to_dict()
    print("📥 Received form data:", data)

    try:
        # Try updating existing user
        cell = sheet.find(data["email"])
        sheet.update(
            f"A{cell.row}:K{cell.row}", [[
                data.get("email", ""), data.get("first_name", ""), data.get("last_name", ""),
                data.get("mobile_code", ""), data.get("mobile_number", ""),
                data.get("whatsapp_code", ""), data.get("whatsapp_number", ""),
                data.get("family_members", ""), data.get("event_fee", ""),
                data.get("membership_fee", ""), data.get("donation_fee", "")
            ]]
        )
        message = f"Updated existing entry for {data['first_name']} {data['last_name']}!"
        print("✅ Updated row:", cell.row)

    except Exception:  # Not found → append new row
        try:
            headers = sheet.row_values(1)
            row_data = [
                data.get("email", ""), data.get("first_name", ""), data.get("last_name", ""),
                data.get("mobile_code", ""), data.get("mobile_number", ""),
                data.get("whatsapp_code", ""), data.get("whatsapp_number", ""),
                data.get("family_members", ""), data.get("event_fee", ""),
                data.get("membership_fee", ""), data.get("donation_fee", "")
            ]

            if len(row_data) < len(headers):
                row_data.extend([""] * (len(headers) - len(row_data)))
            elif len(row_data) > len(headers):
                row_data = row_data[:len(headers)]

            print("📝 Appending new row:", row_data)
            sheet.append_row(row_data)
            message = f"Registration successful for {data['first_name']} {data['last_name']}!"
            print("✅ New row added successfully")

            send_confirmation_email(data["email"], data["first_name"], data["last_name"])

        except Exception as e:
            print("❌ Error appending new row:", e)
            message = "Error saving new registration."

    return render_template("form.html", message=message)


if __name__ == "__main__":
    app.run(debug=True)
