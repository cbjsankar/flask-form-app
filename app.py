from flask import Flask, render_template, request, jsonify
import gspread
import json
from google.oauth2 import service_account
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# ---------------- GOOGLE SHEETS ---------------- #
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

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

# ---------------- UTILITIES ---------------- #
def get_all_users():
    """Return all users from the Google Sheet, excluding the header row."""
    try:
        rows = sheet.get_all_values()
        return rows[1:] if len(rows) > 1 else []
    except Exception as e:
        print("Error fetching users:", e)
        return []

def send_confirmation_email(to_email, data):
    """Send confirmation email after successful registration"""
    from_email = "kairalisyr@gmail.com"
    app_password = "owgg dgjq phip ekwx"  # Replace with Gmail app password

    subject = "Kairali Onam 2025 - Event Registration Confirmation"
    body = f"""
Dear {data['first_name']} {data['last_name']},

Thank you for registering with us! Here are your submitted details:

Name: {data['first_name']} {data['last_name']}
Email: {data['email']}
Mobile: {data['mobile_code']} {data['mobile_number']}
WhatsApp: {data['whatsapp_code']} {data['whatsapp_number']}
Family Members: {data['family_members']}
Event Fee: {data['event_fee']}
Membership Fee: {data['membership_fee']}
Donation Fee: {data['donation_fee']}

We look forward to seeing you!

Regards,
Kairali Syracuse Team
"""
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, [to_email], msg.as_string())
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print("❌ Email sending failed:", e)

# ---------------- ROUTES ---------------- #
@app.route("/", methods=["GET"])
def index():
    user = {
        "email": "",
        "first_name": "",
        "last_name": "",
        "mobile_code": "+91",
        "mobile_number": "",
        "whatsapp_code": "+91",
        "whatsapp_number": "",
        "family_members": "0",
        "event_fee": "0",
        "membership_fee": "0",
        "donation_fee": "0"
    }
    return render_template("form.html", user=user)

@app.route("/get_emails", methods=["GET"])
def get_emails():
    users = get_all_users()
    emails = [u[0] for u in users if len(u) > 0 and u[0]]
    return jsonify(emails)

@app.route("/get_user", methods=["GET"])
def get_user():
    email = request.args.get("email")
    mobile = request.args.get("mobile")
    users = get_all_users()
    user_data = {}

    for u in users:
        if (email and u[0].lower() == email.lower()) or (mobile and u[3] + u[4] == mobile):
            user_data = {
                "email": u[0],
                "first_name": u[1],
                "last_name": u[2],
                "mobile_code": u[3],
                "mobile_number": u[4],
                "whatsapp_code": u[5],
                "whatsapp_number": u[6],
                "family_members": u[7],
                "event_fee": u[8],
                "membership_fee": u[9],
                "donation_fee": u[10]
            }
            break
    return jsonify(user_data)

@app.route("/submit", methods=["POST"])
def submit():
    data = request.form.to_dict()
    print("📥 Received form data:", data)

    message = ""

    try:
        # Check if email exists
        cell = None
        try:
            cell = sheet.find(data["email"])
        except Exception:
            cell = None

        if cell:
            # Update existing row
            sheet.update(
                f"A{cell.row}:K{cell.row}",
                [[
                    data["email"], data["first_name"], data["last_name"],
                    data["mobile_code"], data["mobile_number"],
                    data["whatsapp_code"], data["whatsapp_number"],
                    data["family_members"], data["event_fee"],
                    data["membership_fee"], data["donation_fee"]
                ]]
            )
            message = f"Registration updated for {data['first_name']} {data['last_name']}!"
            print("✅ Updated existing row:", cell.row)
        else:
            # Append new row
            headers = sheet.row_values(1)
            row_data = [
                data["email"], data["first_name"], data["last_name"],
                data["mobile_code"], data["mobile_number"],
                data["whatsapp_code"], data["whatsapp_number"],
                data["family_members"], data["event_fee"],
                data["membership_fee"], data["donation_fee"]
            ]

            if len(row_data) < len(headers):
                row_data.extend([""] * (len(headers) - len(row_data)))
            elif len(row_data) > len(headers):
                row_data = row_data[:len(headers)]

            sheet.append_row(row_data)
            message = f"Registration successful for {data['first_name']} {data['last_name']}!"
            print("✅ New row added:", row_data)

            # Send confirmation email
            send_confirmation_email(data["email"], data)

    except Exception as e:
        print("❌ Error handling registration:", e)
        message = "Error saving registration. Please try again."

    return render_template("form.html", user=data, message=message)

# ---------------- RUN APP ---------------- #
if __name__ == "__main__":
    app.run(debug=True)
