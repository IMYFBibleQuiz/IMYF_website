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
    global db
    data = request.get_json()
    try:
        existing_user = User.query.filter_by(email=data['email']).first()

        if existing_user:
            return None, False

        last_user = User.query.with_entities(User.id).order_by(User.roll_no.desc()).first()
    except Exception as e:
        print(f"OperationalError with the database: {e}")
        
        # Close the existing session and create a new database engine
        db.session.rollback()
        db.engine.dispose()
        db.engine.connect()

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

    exam_center_codes = {
        "IM Gaya Campus": "B01",
        "IM Purnia Campus": "B02",
        "IM Nalanda Campus": "B03",
        "India Mission Campus": "B04",
        "Exam center Munger": "B05",
        "Exam Center Katihar": "B06",
        "IM campus, Lalganj": "B07",
        "IM Campus, Kochas": "B08",
        "Bhagalpur exam Centre": "B09",
        "Jhanjarpur exam centre": "B10",
        "Siwan exam Centre": "B11",
        "Aurangabad Campus": "B12",
        "Bihta Campus, Patna": "B13",
        "Bhopal Campus": "M01",
        "Baihar Campus": "M02",
        "Exam Center Madhupur": "U01",
        "Exam Center Pratappur": "U02",
        "Exam Center Bauri": "U03"
    }
    replacement = exam_center_codes[data['examCenterAddress']]
    # Construct the new id for the user
    new_user_id = data['age_group'][:2] + replacement + new_last_three_digits

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
    return jsonify(success=True, message="Hello there!")

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

@app.route('/ab42063c2d27be919de5f71d4ce83a848da47f53934a14c441f1c6f6f61c7d0c', methods=['GET'])
def get_users():
    global db
    try:
        users = User.query.all()
    except Exception as e:
        print(f"OperationalError with the database: {e}")
        
        # Close the existing session and create a new database engine
        db.session.rollback()
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
        examCenter = data.get('examCenter')
        if isinstance(examCenter, (list, tuple)):
            examCenter = examCenter[0]  # Take the first value
        else:
            examCenter = str(examCenter)
        
        examCenterAddress = data.get('examCenterAddress')
        if isinstance(examCenterAddress, (list, tuple)):
            examCenterAddress = examCenterAddress[0]  # Take the first value
        else:
            examCenterAddress = str(examCenterAddress)
        
        aadharCardNo = data.get('aadharCardNo')
        if isinstance(aadharCardNo, (list, tuple)):
            aadharCardNo = aadharCardNo[0]  # Take the first value
        else:
            aadharCardNo = str(aadharCardNo)
        whatsappNo = data['whatsappNo']
        print(examCenterAddress)
        print(type(examCenterAddress))
        print(type(aadharCardNo))
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

        
        exam_codes={
            'IM Gaya Campus': 'Address: Aganda, Karmouni, Baluwa Road, Bethel Academy, Gaya.Bodh Gaya, Bihar 824234 \nIncharge: Issac Mobile: +91 9020974864',
            'IM Purnia Campus': 'Address: Christ Mission School, Khaidalichak, Mirganj, Purnia, Bihar 854304 \nIncharge: Anu Jacob Mathew Mobile: +91 94964 62235',
            'IM Nalanda Campus': 'Address: Dayavihar, Badhauna, Chandi, Nalanda, 803108 \nIncharge: Jijo B Raj Mobile: +91 80896 76878',
            'India Mission Campus Motihari': 'Bara Bariyarpur P. O., Vankat, Motihari, East Champaran District. Bihar, Pin. 845401 Landmark: On the way to Engineering College Road, Opposite to Mayisthan \nIncharge: Shiby Thomas, Mobile: +91 94969 68034',
            'Exam center Munger': 'Grace church, Gyanvati bhawan, infront of Dr.Madan Mohan Prasad Ghoshi Tola, munger( Bihar), Pincode: 811201 \nIncharge: Justin George, Mobile: +91 6238 463 482',
            'Exam Center Katihar': 'Village Gopalpur, Panchayat patharwar, Post Baina, Thana pranpur, Dist katihar Bihar 854114 \nIncharge: Jijo Joseph, Mobile: +91 70126 14917',
            'IM campus, Lalganj': 'India Mission Church Campus, Purkhouli PO, Laganj, Vaishali, Bihar - 844121 \nIncharge: Jijo Joseph, Mobile: +91 70126 14917',
            'IM Campus, Kochas': 'Bojpur mission medical center. Dibhiya village, P. O. Dibhiya, P. S. Karaghar, Rohtas district, Bihar. Pin 821107 \nIncharge: Sam, Mobile: +91 90721 20054',
            'Bhagalpur exam Centre': 'Jyoti vihar colony, opposite Bajaj service centre, behind Ideal coaching centre Zeromile, Sabour Bhagalpur 813210 \nIncharge: Benison Hembrom, Mobile: +91 84347 07604',
            'Jhanjarpur exam centre': 'Village -laxmipur, Post office -kaithinia, Police station -lakhnaur, District -madhubani, Pincode -847403, State -bihar Mob no.-9110114165 \nIncharge: Anil Abraham, Mobile: +91 95465 24269',
            'Siwan exam Centre': 'Ander. Arar.tola, Post Ander, PS Ander, District Siwan, Bihar, Pin: 841231 Pr Arjun Kumar Das \nIncharge: Emmanuel Tirkey, Mobile: +91 88629 99243',
            'Aurangabad Campus': 'Bhairopur Highway, Aurangabad -Rajhara - Daltenganj Rd, Near Balaji Hotel Aurangabad District, Bihar 824102 Mobile number: 8084985022 \nIncharge: Sojan George Samuel, Mobile: +91 99618 91223',
            'Bihta Campus, Patna': 'India mission board trust, Wajidpur more Maner Subdistrict, Maner - 801108, Bihar \nIncharge: Jinesh KJ Mobile: +91 96451 39843',
            'Bhopal Campus': 'India Mission, House# 44, Tanvi Estate, Awadhpuri, Bhopal, MADHYA PRADESH 462022 Phone number: 7992356517 \nIncharge : Sohan Mahile, Mobile: +91 97536 25007',
            'Baihar Campus': 'Baihar Campus Gladwin Solomon, India Mission, Gohara Village, Near Kopra Fatak Church, Baihar, MADHYA PRADESH 481105 Phone number: 7992356517 \nIncharge : Sohan Mahile, Mobile: +91 97536 25007',
            'Exam Center Madhupur':'India Mission, Madhupur village, Sonbhadra Dist., Uttar Pradesh Pin 231216 Location-Near intercollege, Chandan basti Phone number: 6392294765 \nIncharge : Besky Livingstone, Mobile: +91 8590976147',
            'Exam Center Pratappur':'India mission, Village - Pratappur church, Post mirzamurad , District Varanasi, UP Pin code 221307, Location- Shitala temple khajuri rod jio tabar ke pas Phone number: 9307502609 \nIncharge : Besky Livingstone, Mobile: +91 8590976147',
            'Exam Center Bauri':'Pr.Santlal, Bauri village, Ghazipur Dist, Uttar Pradesh Pin-233303 Landmark - Near to ramesh gas agency (bauri bridge) Phone number: 9598269490 \nIncharge : Besky Livingstone, Mobile: +91 8590976147',
        }

        address=exam_codes[data.get('examCenterAddress')]
        pdf_data = generate_hall_ticket(roll_no, fullname, age, age_group, fathername, aadharCardNo, whatsappNo, examCenter, examCenterAddress, filename,address)
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


def generate_hall_ticket(roll_no, name, age, age_group, father_name, aadhar_no, mobile_no,  examCenter, examCenterAddress, filename,address):
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
    c.drawString(30, 295, f"Name: {name}")
    

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

    # add address with newline
    c.drawString(30, 135, f"Address:")
    
    address_lines = address.split('\n')  # Split address into lines
    y_position = 135  # Initial y position
    for line in address_lines:
        c.drawString(40, y_position,line)
        y_position -= 10

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
    





@app.route('/c636a0bdce995d424caae3bfaf3cd7736e1346880e9ff2f4cbdbee0168edc10f', methods=['GET'])
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


@app.route('/428821350e9691491f616b754cd8315fb86d797ab35d843479e732ef90665324', methods=['POST'])
def login():
    global db
    username = request.json.get('username')
    password = request.json.get('password')
    
    try:
        admin = Admin.query.filter_by(username=username).first()
    except Exception as e:
        print(f"OperationalError with the database: {e}")
        
        # Close the existing session and create a new database engine
        db.session.rollback()
        db.engine.dispose()
        db.engine.connect()
        
        admin = Admin.query.filter_by(username=username).first()
    if not admin or admin.password != hash_password(password):
        return jsonify({'success': False, 'message' : 'Invalid username or password'}), 401
    
    return jsonify({'success': True, 'message': 'Login successful', 'data': {'username': admin.username}})


@app.route('/cb8e4acdfbbe2c496ce12cb7a34df298addd8626412be65eeace8ce1cdd8f124', methods=['POST'])
def forgot_password():
    global db
    username = request.json.get('username')
    
    try:
        admin = Admin.query.filter_by(username=username).first()
    except Exception as e:
        print(f"OperationalError with the database: {e}")
        
        # Close the existing session and create a new database engine
        db.session.rollback()
        db.engine.dispose()
        db.engine.connect()
        
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

@app.route('/d5841ea40b948ab0312ef0e35e5eef8f01e9e2a6142401b3e4b57f57dbbdc28c', methods=['POST'])
def verify_otp():
    global db
    otp = request.json.get('otp')
    
    try:
        admin = Admin.query.first()
    except Exception as e:
        print(f"OperationalError with the database: {e}")
        
        # Close the existing session and create a new database engine
        db.session.rollback()
        db.engine.dispose()
        db.engine.connect()
        
        admin = Admin.query.first()
    admin.otp=int(admin.otp)
    if not admin or admin.otp != otp or admin.otp_expiry < datetime.now():
        return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
    
    return jsonify({'success': True, 'message': 'Valid OTP'}), 200

@app.route('/cfc941331dc7dbfc7bc3d075664b3565000cf38b395e69989487506be4d86476', methods=['POST'])
def reset_password():
    global db
    username = request.json.get('username')
    new_password = request.json.get('new_password')
    
    try:
        admin = Admin.query.filter_by(username=username).first()
    except Exception as e:
        print(f"OperationalError with the database: {e}")
        
        # Close the existing session and create a new database engine
        db.session.rollback()
        db.engine.dispose()
        db.engine.connect()
        
        admin = Admin.query.filter_by(username=username).first()
    if not admin:
        return jsonify({'success': False, 'message': 'Username not found'}), 404
    
    admin.password = hash_password(new_password)
    admin.otp = None  
    admin.otp_expiry = None
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password reset successful'}), 200
    
@app.route('/26d8a787f636d022f95db63ee0f572d2590cbe0ff5b63badf9f9b23d7343371c', methods=['GET'])
def send_email():
    email = request.args.get('email')
    pdf_filename = email
    subject = "Hall Ticket"
    pdf_data = download_from_dropbox(pdf_filename)
    if pdf_data:
        msg = Message(subject,
                      sender='samrig25@gmail.com',
                      recipients=[email])
        msg.body = 'Dear Registrant,\nWe have received your payment! Your can find your hall ticket attached to this email.'
        msg.attach('hall_ticket', 'application/pdf', pdf_data)
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Email sent successfully'}), 200
    else:
        return jsonify({'success': False, 'message': 'PDF not found'}), 404
    

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
