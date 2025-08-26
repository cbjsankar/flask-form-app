import os
import json
from flask import Flask, request, render_template, jsonify
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# Google Sheets Setup

credentials_info = json.loads(os.environ['GOOGLE_SHEETS_JSON'])

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '17JO6P0OkcEIH4RCCQLjcNqYsuetw5f0kAfITko629Rc'
SHEET_NAME = 'Sheet1'

creds = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()


# Columns:
# A: Email | B: MobileCode | C: MobileNumber | D: WhatsAppCode | E: WhatsAppNumber |
# F: First Name | G: Last Name | H: Family Members | I: Event Fee | J: Membership Fee | K: Donation Fee

# Fetch all users
def get_all_users():
    result = sheet.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!A2:K"
    ).execute()
    return result.get('values', [])

# Find a user by email, mobile, or WhatsApp
def find_user(email=None, mobile=None, whatsapp=None):
    users = get_all_users()
    for user in users:
        # Ensure correct length check before indexing
        if len(user) < 11:
            continue
        if (email and user[0] == email) \
           or (mobile and (user[1] + user[2]) == mobile) \
           or (whatsapp and (user[3] + user[4]) == whatsapp):
            return {
                'email': user[0],
                'mobile_code': user[1],
                'mobile_number': user[2],
                'whatsapp_code': user[3],
                'whatsapp_number': user[4],
                'first_name': user[5],
                'last_name': user[6],
                'family_members': user[7],
                'event_fee': user[8],
                'membership_fee': user[9],
                'donation_fee': user[10],
            }
    return None

# Register or update user
def register_user(email, mobile_code, mobile_number, whatsapp_code,
                  whatsapp_number, first_name, last_name,
                  family_members, event_fee, membership_fee, donation_fee):

    users = get_all_users()
    row_index = None
    for i, user in enumerate(users):
        if (len(user) > 0 and user[0] == email) \
           or (len(user) > 2 and (user[1], user[2]) == (mobile_code, mobile_number)) \
           or (len(user) > 4 and (user[3], user[4]) == (whatsapp_code, whatsapp_number)):
            row_index = i + 2  # header offset
            break

    if row_index:
        # Update existing
        sheet.values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A{row_index}:K{row_index}",
            valueInputOption="RAW",
            body={"values": [[email, mobile_code, mobile_number,
                              whatsapp_code, whatsapp_number,
                              first_name, last_name, family_members,
                              event_fee, membership_fee, donation_fee]]}
        ).execute()
        return "Registration updated"
    else:
        # Append new
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:K",
            valueInputOption="RAW",
            body={"values": [[email, mobile_code, mobile_number,
                              whatsapp_code, whatsapp_number,
                              first_name, last_name, family_members,
                              event_fee, membership_fee, donation_fee]]}
        ).execute()
        return "Registration updated"

@app.route('/', methods=['GET', 'POST'])
def register():
    user_data = {}
    message = None

    if request.method == 'POST':
        email = request.form['email']
        mobile_code = request.form.get('mobile_code', '')
        mobile_number = request.form.get('mobile_number', '')
        whatsapp_code = request.form.get('whatsapp_code', '')
        whatsapp_number = request.form.get('whatsapp_number', '')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        family_members = request.form.get('family_members', '')
        event_fee = request.form.get('event_fee', '')
        membership_fee = request.form.get('membership_fee', '')
        donation_fee = request.form.get('donation_fee', '')

        if not first_name and not last_name and not family_members:
            # Auto lookup
            user_data = find_user(email, mobile_code+mobile_number, whatsapp_code+whatsapp_number) or {}
        else:
            message = register_user(email, mobile_code, mobile_number,
                                    whatsapp_code, whatsapp_number,
                                    first_name, last_name, family_members,
                                    event_fee, membership_fee, donation_fee)
            user_data = {}

    return render_template('form.html', user=user_data, message=message)

@app.route('/get_user', methods=['GET'])
def get_user_api():
    email = request.args.get('email')
    mobile = request.args.get('mobile')
    whatsapp = request.args.get('whatsapp')
    user = find_user(email, mobile, whatsapp)
    return jsonify(user or {})

if __name__ == '__main__':
    app.run(debug=True)
