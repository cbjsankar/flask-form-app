from flask import Flask, render_template, request, jsonify
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import CellNotFound
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# Google Sheets setup
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)
client = gspread.authorize(creds)

# Open sheet (replace with your own name or URL)
sheet = client.open("Kairali Registration").sheet1

# Gmail setup (replace with your email + app password)
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
    emails = sheet.col_values(1)  # assuming email is column 1
    return jsonify(emails)


@app.route("/get_user")
def get_user():
    """Fetch user data by email"""
    email = request.args.get("email")
    try:
        cell = sheet.find(email)
        row = sheet.row_values(cell.row)
        return jsonify(row)
    except CellNotFound:
        return jsonify([])
    except Exception as e:
        print("Error fetching user:", e)
        return jsonify([])


@app.route("/submit", methods=["POST"])
def submit():
    """Handle form submission"""
    data = request.form.to_dict()
    print("📥 Received form data:", data)

    try:
        # Try to find if email already exists
        cell = sheet.find(data["email"])
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
        message = f"Updated existing entry for {data['first_name']} {data['last_name']}!"
        print("✅ Updated row:", cell.row)

    except CellNotFound:
        try:
            # Get headers length to align properly
            headers = sheet.row_values(1)
            row_data = [
                data["email"], data["first_name"], data["last_name"],
                data["mobile_code"], data["mobile_number"],
                data["whatsapp_code"], data["whatsapp_number"],
                data["family_members"], data["event_fee"],
                data["membership_fee"], data["donation_fee"]
            ]

            # Adjust row length to match sheet columns
            if len(row_data) < len(headers):
                row_data.extend([""] * (len(headers) - len(row_data)))
            elif len(row_data) > len(headers):
                row_data = row_data[:len(headers)]

            print("📝 Appending new row:", row_data)
            print("Header length:", len(headers), "Row length:", len(row_data))

            sheet.append_row(row_data)
            message = f"Registration successful for {data['first_name']} {data['last_name']}!"
            print("✅ New row added successfully")

            # Send email
            send_confirmation_email(data["email"], data["first_name"], data["last_name"])

        except Exception as e:
            print("❌ Error appending new row:", e)
            message = "Error saving new registration."

    return render_template("form.html", message=message)


if __name__ == "__main__":
    app.run(debug=True)
