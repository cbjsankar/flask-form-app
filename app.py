from flask import Flask, render_template, request, jsonify
import gspread
import json
from google.oauth2 import service_account
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# ---------------- GOOGLE SHEETS ---------------- #
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# Load credentials from Docker secret file
with open('/etc/secrets/google_sheets_json.json') as f:
    credentials_info = json.load(f)

creds = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
client = gspread.authorize(creds)

# Open Google Sheet
sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/17JO6P0OkcEIH4RCCQLjcNqYsuetw5f0kAfITko629Rc/edit#gid=0"
).sheet1

def get_all_users():
    return sheet.get_all_values()[1:]

# ---------------- EMAIL FUNCTION ---------------- #
def send_email(to_email, data):
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

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(from_email, app_password)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print("Error sending email:", e)


# ---------------- ROUTES ---------------- #
@app.route("/", methods=["GET", "POST"])
def register():
    message = ""
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

    if request.method == "POST":
        data = {
            "email": request.form["email"],
            "first_name": request.form["first_name"],
            "last_name": request.form["last_name"],
            "mobile_code": request.form["mobile_code"],
            "mobile_number": request.form["mobile_number"],
            "whatsapp_code": request.form["whatsapp_code"],
            "whatsapp_number": request.form["whatsapp_number"] or request.form["mobile_number"],
            "family_members": request.form.get("family_members", "0"),
            "event_fee": request.form.get("event_fee", "0"),
            "membership_fee": request.form.get("membership_fee", "0"),
            "donation_fee": request.form.get("donation_fee", "0")
        }

        # Check if email exists in sheet → update row, else append
        try:
            cell = sheet.find(data["email"])
            row_number = cell.row
            sheet.update(
                f"A{row_number}:K{row_number}",
                [[
                    data["email"], data["first_name"], data["last_name"],
                    data["mobile_code"], data["mobile_number"],
                    data["whatsapp_code"], data["whatsapp_number"],
                    data["family_members"], data["event_fee"],
                    data["membership_fee"], data["donation_fee"]
                ]]
            )
            message = f"Registration updated for {data['first_name']} {data['last_name']}!"
        except gspread.exceptions.CellNotFound:
            sheet.append_row(list(data.values()))
            message = f"Registration successful for {data['first_name']} {data['last_name']}!"

        # Send confirmation email
        send_email(data["email"], data)

    return render_template("form.html", user=user, message=message)


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
        # Assuming columns: email, first_name, last_name, mobile_code, mobile_number, whatsapp_code, whatsapp_number, family_members, event_fee, membership_fee, donation_fee
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


if __name__ == "__main__":
    app.run(debug=True)
