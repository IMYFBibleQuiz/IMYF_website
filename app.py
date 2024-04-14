from flask import Flask, request, jsonify, send_file
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
import os
from flask_mail import Mail, Message
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from io import BytesIO
import dropbox
from reportlab.pdfgen import canvas



app = Flask(__name__)
CORS(app)

# Sender email and password
sender_email = os.environ.get('SENDER_EMAIL')
sender_password = os.environ.get('SENDER_PASSWORD')

# Dropbox credentials
client_id = os.environ.get('DROPBOX_CLIENT_ID')
client_secret = os.environ.get('DROPBOX_CLIENT_SECRET')
refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN')
dropbox_access_token = os.environ.get('DROPBOX_ACCESS_TOKEN')

# Database configuration
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_host = os.environ.get('DB_HOST')
db_name = os.environ.get('DB_NAME')

# Constructing the database URI
db_uri = f"mysql://{db_user}:{db_password}@{db_host}/{db_name}"

app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['MAIL_SERVER'] = 'smtp.gmail.com' 
app.config['MAIL_PORT'] = 587  
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = sender_email 
app.config['MAIL_PASSWORD'] = sender_password
db = SQLAlchemy(app)
mail = Mail(app)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    otp = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)


class User(db.Model):
    roll_no = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.String(15), nullable=False )
    fullname = db.Column(db.String(100), nullable=False)
    fathername = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.String(20), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    age_group = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    examCenter = db.Column(db.String(100), nullable=False)
    examCenterAddress = db.Column(db.String(100), nullable=False)
    aadharCardNo = db.Column(db.String(14), nullable=False)
    whatsappNo = db.Column(db.String(100), nullable=False)
def create_tables():
    with app.app_context():
        db.create_all()

def register_user(data):
    data = request.get_json()
    existing_user = User.query.filter_by(email=data['email']).first()

    if existing_user:
        return None, False

    last_user = User.query.with_entities(User.id).order_by(User.roll_no.desc()).first()

    # Extract the last 3 digits from the id and increment it
    if last_user:
        last_three_digits = int(last_user.id[-3:])
        new_last_three_digits = f"{last_three_digits + 1:03d}"
    else:
        new_last_three_digits = "001"  # Initial value if no users exist

    # Construct the new id for the user
    new_user_id = data['age_group'][:2] + data['examCenter'][:2].lower() + new_last_three_digits

    new_user = User(
        # roll_no = 0,
        id = new_user_id,
        fullname=data['fullname'],
        fathername=data['fathername'],
        dob=data['dob'],
        age=data['age'],
        age_group=data['age_group'],
        email=data['email'],
        examCenter=data['examCenter'],
        examCenterAddress=data['examCenterAddress'],
        aadharCardNo = data['aadharCardNo'],
        whatsappNo = data['whatsappNo']
        
    )
    db.session.add(new_user)
    db.session.commit()
    return new_user.id, True




def send_confirmation_email(email, fullname, roll_no):
    msg = Message('Confirmation of Registration and Payment Process for IMYF Bible Quiz 2024',
                  sender='samrig25@gmail.com',
                  recipients=[email])
    msg.body = f'Dear {fullname},\n\nWe hope this message finds you well. We would like to express our sincere gratitude for your registration for the IMYF Bible Quiz 2024. Your participation is highly valued, and we are thrilled to have you on board for this event.\nYour roll number :{roll_no}\n\nPayment Process: \nTo complete your registration, we kindly request you to make the payment of Rs. 50 using one of the following methods:\nKindly ensure to include your roll number as the reference when making the payment\nAccount Transfer:\n\nBank: State Bank of India\n Account holder Name : Anu Jacob Mathew\n Account number : 67185607028\n Branch : Mangatu kavala\n IFSC: SBIN0070886\n\n UPI (Unified Payments Interface): \nName - Anu Jacob Mathew\n UPI Handle - 9496462235709@paytm\n\nReceipt of Hall Ticket:\nUpon successful confirmation of your payment, the hall ticket for the IMYF Bible Quiz 2024 will be promptly sent to your email address. This hall ticket is essential for your participation in the event.\nShould you encounter any challenges or require further assistance with the payment process, please do not hesitate to contact our support team at 9496462235.\nWe eagerly anticipate your involvement in the IMYF Bible Quiz 2024 and look forward to a rewarding and enriching experience for all participants.\nWarm regards,\nIMYF Bible Quiz 2024 Organizing Committee'
    
    mail.send(msg)


@app.route('/')
def hello():
    return 'hello there'

@app.route('/test', methods=['GET'])
def test_endpoint():
    """
    A test endpoint to verify application functionality and database connection.
    """
    try:
        # Attempt to insert a new user into the User table for testing
        new_user = User(
            id='TEST001',
            fullname='Test User',
            fathername='Test Father',
            dob='2000-01-01',
            age=24,
            age_group='Adult',
            email='testuser@example.com',
            examCenter='Test Center',
            examCenterAddress='Test Address',
            aadharCardNo='123456789012',
            whatsappNo='9876543210'
        )
        db.session.add(new_user)
        db.session.commit()

        # Query the inserted user to confirm insertion
        user = User.query.filter_by(id='TEST001').first()

        if user:
            return jsonify({'message': 'Test successful! Database connection and insertion established.'})
        else:
            return jsonify({'message': 'Test failed. User insertion or query issue.'})

    except Exception as e:
        # Catch any exceptions during database interaction
        return jsonify({'message': f'Test failed. Error: {e}  Database host: {db_host if db_host else "Not set"}'})


@app.route('/api/generate_pdf', methods=['OPTIONS'])
def handle_options():
    return '', 200, {
        'Access-Control-Allow-Origin': 'http://localhost:4200',
        'Access-Control-Allow-Methods': 'POST',
        'Access-Control-Allow-Headers': 'Content-Type'
    }

# @app.route('/')
# def hello():
#     return 'hello there'

@app.route('/get_users', methods=['GET'])
def get_users():
    # Query the User table to retrieve data
    try:
        users = User.query.all()
    except Exception as e:
        print(f"OperationalError with the database: {e}")
        
        # Close the existing session and create a new database engine
        session.close()
        db.engine.dispose()
        db.engine.connect()
        
    users = User.query.all()
    # Serialize the data into JSON format
    users_json = [
        {
            'roll_no': user.roll_no,
            'id': user.id,
            'fullname': user.fullname,
            'fathername': user.fathername,
            'dob': user.dob,
            'age': user.age,
            'age_group': user.age_group,
            'email': user.email,
            'examCenter': user.examCenter,
            'examCenterAddress': user.examCenterAddress,
            'aadharCardNo': user.aadharCardNo,
            'whatsappNo': user.whatsappNo
        }
        for user in users
    ]

    # Return the JSON response
    return jsonify(users_json)

@app.route('/generate_pdf', methods=['POST'])
def generate_certificate_route():
    data = request.get_json()
    roll_no, registration_status = register_user(data)
    
    if registration_status:
        # id = User.id
        fullname = data.get('fullname')
        fathername = data.get('fathername')
        dob = data.get('date')
        age = data.get('age')
        age_group = data.get('age_group')
        email = data.get('email')
        examCenter=data['examCenter'],
        examCenterAddress=data['examCenterAddress'],
        aadharCardNo = data['aadharCardNo'],
        whatsappNo = data['whatsappNo']
        print(examCenterAddress)
            
        data = request.get_json()
        user_data = {
        'fullname' : data.get('fullname'),
        'fathername' : data.get('fathername'),
        'dob': data.get('date'),
        'age': data.get('age'),
        'age_group': data.get('age_group'),
        'email': data.get('email'),
        'examCenter' : data.get('examCenter'),
        'examCenterAddress' : data.get('examCenterAddress'),
        'aadharCardNo' : data.get('aadharCardNo'),
        'whatsappNo' : data.get('whatsappNo')
        }
        # logo_path = data.get('logoPath')
        filename = email

        
        

        pdf_data = generate_hall_ticket(roll_no, fullname, age, age_group, fathername, aadharCardNo, whatsappNo, examCenter, examCenterAddress, filename)
        save_to_dropbox(pdf_data, filename)
        send_confirmation_email(email, fullname,roll_no)
        return jsonify({'success': True, 'filename': filename})
    else:
        return jsonify({'success': False, 'message': 'User already exists'}), 400


def save_to_dropbox(pdf_data, filename):
    global dropbox_access_token
    try:
        dbx = dropbox.Dropbox(dropbox_access_token)
        with dropbox.Dropbox(dropbox_access_token) as dbx:
            dbx.files_upload(pdf_data, f'/generated_pdfs/{filename}'+'.pdf')
    except:
        print('refresh')
        dropbox_access_token=refresh_access_token(refresh_token, client_id, client_secret)
        print(dropbox_access_token)
        dbx = dropbox.Dropbox(dropbox_access_token)
        with dropbox.Dropbox(dropbox_access_token) as dbx:
            dbx.files_upload(pdf_data, f'/generated_pdfs/{filename}'+'.pdf')
        print("Access token refreshed")
    

def refresh_access_token(refresh_token, client_id, client_secret):
    # Endpoint for refreshing access token
    endpoint = 'https://api.dropbox.com/oauth2/token'

    # Parameters for refreshing token
    data = {
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret
    }

    try:
        # Send POST request to refresh access token
        response = requests.post(endpoint, data=data)
        response_data = response.json()

        # Extract new access token from response
        new_access_token = response_data.get('access_token')

        # Return the new access token
        return new_access_token
    except Exception as e:
        # Handle any errors that occur during token refresh
        print("Error refreshing access token:", e)
        return None


def generate_hall_ticket(roll_no, name, age, age_group, father_name, aadhar_no, mobile_no,  examCenter, examCenterAddress, filename):
    buffer = BytesIO()  # Create a BytesIO object to store PDF data

    # Create the PDF content
    c = canvas.Canvas(buffer, pagesize=(505, 405))  # shorter page size
    c.setStrokeColorRGB(1, 0.5, 0)
    # Draw border for entire document
    c.rect(5, 5, 495, 395)

    # Draw border for main content area
    c.rect(20, 20, 460, 360)

    c.setStrokeColorRGB(1, 0.5, 0)

    # Roll No/Ref No
    c.drawString(30, 350, f"Roll No/Ref No.: {roll_no}")

    # Name
    c.drawString(30, 300, f"Name: {name}")

    # Age
    c.drawString(30, 275, f"Age: {age}")

    # Age Group
    c.drawString(30, 255, f"Age Group: {age_group}")

    # Father's Name
    c.drawString(30, 235, f"Father's Name: {father_name}")

    # Aadhar Card Number
    c.drawString(30, 215, f"Aadhar Card Number: {aadhar_no}")

    # Mobile Number
    c.drawString(30, 195, f"Mobile Number: {mobile_no}")

    # Exam Date
    # c.drawString(30, 175, f"Exam Date: {exam_date}")

    # Exam Centre
    c.drawString(30, 175, f"Exam Centre: {examCenter}")

    # Exam Centre Address
    c.drawString(30, 155, f"Exam Centre Address: {examCenterAddress}")

    # Signature of Participant
    c.drawString(180, 100, "Signature of Participant:")
    c.line(320, 100, 460, 100)

    # Signature of Bible Quiz Convener
    c.drawString(180, 60, "Signature of Bible Quiz Convener:")
    c.line(365, 60, 460, 60)

    # Draw the logo in the top right corner
    c.drawImage('IMYF_logo.jpg', 400, 315, width=60, height=60)
    c.save()

    pdf_data = buffer.getvalue() 
    buffer.close()  

    return pdf_data

# Example usage:
# generate_hall_ticket("AG/EC.123", "John Doe", "25", "AG", "John Doe Sr.", "1234 5678 9012", "9876543210", "March 15, 2024", "Exam Centre A", "123 Main St, City, Country", "hall_ticket_shorter.pdf")

# def generate_refNo(age_group, examCenter, mobile_no):
    





@app.route('/get_pdf', methods=['GET'])
def get_pdf():
    pdf_filename = request.args.get('email') 

    pdf_data = download_from_dropbox(pdf_filename)

    if pdf_data:
        return send_file(
            BytesIO(pdf_data),
            mimetype='application/pdf',
            as_attachment=True,
			download_name=f'{pdf_filename}.pdf'
        )
    else:
        return jsonify({'error': 'PDF not found'})

def download_from_dropbox(filename):
    global dropbox_access_token
    try:
        dbx = dropbox.Dropbox(dropbox_access_token)
        metadata, res = dbx.files_download('/generated_pdfs/' + filename+'.pdf')
        print("File downloaded successfully")
        return res.content
    except dropbox.exceptions.AuthError as err:
        dropbox_access_token=refresh_access_token(refresh_token, client_id, client_secret)
        print(dropbox_access_token)

        dbx = dropbox.Dropbox(dropbox_access_token)
        print("Access token refreshed")
        metadata, res = dbx.files_download('/generated_pdfs/' + filename+'.pdf')
        print("File downloaded successfully")
        return res.content
    except dropbox.exceptions.HttpError as err:
        if err.status_code == 404:
            return None  # PDF file not found
        else:
            raise





def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp():
    return ''.join(secrets.choice(string.digits) for _ in range(6))

def send_otp_email(username, otp):
    msg = Message('Password Reset OTP', sender='samrig25@gmail.com', recipients=[username])
    msg.body = f'Your OTP for password reset is: {otp}'
    mail.send(msg)


@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    admin = Admin.query.filter_by(username=username).first()
    if not admin or admin.password != hash_password(password):
        return jsonify({'success': False, 'message' : 'Invalid username or password'}), 401
    
    return jsonify({'success': True, 'message': 'Login successful', 'data': {'username': admin.username}})


@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    username = request.json.get('username')
    
    admin = Admin.query.filter_by(username=username).first()
    if not admin:
        print(username)
        return jsonify({'success': False, 'message': 'Username is not found', 'username' : username }), 404
    
    otp = generate_otp()
    admin.otp = otp
    admin.otp_expiry = datetime.now() + timedelta(minutes=10)  
    db.session.commit()
    send_otp_email(admin.username, otp)
    
    return jsonify({'success': True, 'message': 'OTP sent successfully'}), 200

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    otp = request.json.get('otp')
    
    admin = Admin.query.first()
    admin.otp=int(admin.otp)
    if not admin or admin.otp != otp or admin.otp_expiry < datetime.now():
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
    
    return jsonify({'success': True, 'message': 'Valid OTP'}), 200

@app.route('/reset_password', methods=['POST'])
def reset_password():
    username = request.json.get('username')
    new_password = request.json.get('new_password')
    
    
    admin = Admin.query.filter_by(username=username).first()
    if not admin:
        return jsonify({'success': False, 'message': 'Username not found'}), 404
    
    admin.password = hash_password(new_password)
    admin.otp = None  
    admin.otp_expiry = None
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password reset successful'}), 200
    
@app.route('/send_email', methods=['GET'])
def send_email():
    email = request.args.get('email')
    pdf_filename = email
    subject = "Hall Ticket"
    pdf_data = download_from_dropbox(pdf_filename)
    if pdf_data:
        msg = Message(subject,
                      sender='samrig25@gmail.com',
                      recipients=[email])
        msg.body = 'Some message content'
        msg.attach('hall_ticket', 'application/pdf', pdf_data)
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Email sent successfully'}), 200
    else:
        return jsonify({'success': False, 'message': 'PDF not found'}), 404
    

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
