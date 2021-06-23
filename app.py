from flask import Flask, render_template, request, redirect, url_for, session
from flask_cors import cross_origin
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from flask_socketio import SocketIO, join_room, leave_room
import datetime

app = Flask(__name__)
app.secret_key = '09cd6cb8206a12b54a7ddb28566be757'
socketio = SocketIO(app, cors_allowed_origins="*")
bcrypt = Bcrypt(app)

cluster = MongoClient(
        "mongodb+srv://mdyamin:yamin787898@cluster0.5bduk.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = cluster['aidoctor']

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/bot', methods=['GET', 'POST'])
@cross_origin()
def chat_bot():
    if "email" in session:
        return render_template('bot.html')
    else:
        return redirect(url_for('login', next='/bot'))

@app.route('/dashboard')
@cross_origin()
def dashboard():
    if "email" in session:
        return render_template('dashboard.html')
    else:
        return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@cross_origin()
def profile():
    if request.method == 'GET':
        if "email" in session:
            return render_template('profile.html')
        else:
            return redirect(url_for('login', next='/bot'))
    else:
        pass

@app.route('/contact')
@cross_origin()
def contact_us():
    return render_template('contactUs.html')

@app.route('/services')
@cross_origin()
def services():
    return render_template('services.html')

@app.route('/signup', methods=['POST'])
@cross_origin()
def sign_up():
    collection = db['users']
    form_data = request.form
    pw_hash =  bcrypt.generate_password_hash(form_data['password']).decode('utf-8')
    result = collection.find_one({'email': form_data['email']})
    if result == None:
        id = collection.insert_one({
            'name': form_data['name'],
            'email': form_data['email'],
            'password': pw_hash,
            'userType': form_data['userType']
        }).inserted_id
        response = ''
        if id == '':
            response = 'failed'
        else:
            response = 'success'
    else:
        response = 'failed'
    return render_template('signup.html', response=response)


@app.route('/login', methods=['GET', 'POST'])
@cross_origin()
def login():
    if request.method == 'POST':
        collection = db['users']
        form_data = request.form
        next_url = request.form.get('next')
        query_data = {
            "email": form_data['email']
        }
        result = collection.find_one(query_data)
        response = ''
        if result == None:
            response = 'failed'
        else:
            pw = form_data['password']
            if bcrypt.check_password_hash(result['password'], pw) == True:
                response = 'succeeded'
                session['email'] = form_data['email']
            else:
                response = 'failed'
        
        if response == 'failed':
            return render_template('login.html', response=response)
        else:
            if next_url:
                return redirect(next_url)
            else:
                return redirect(url_for('dashboard'))
    else:
        if "email" in session:
            return redirect(url_for("dashboard"))
        else:
            return render_template('login.html')

@app.route('/logout')
@cross_origin()
def logout():
    if 'email' in session:
        session.pop("email", None)
        return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))

@app.route('/resetdb')
@cross_origin()
def reset_database():
    collection1 = db['user_symptomps']
    collection2 = db['users']
    collection1.delete_many({})
    collection2.delete_many({})
    return "Database Cleared"

@app.route('/chat')
@cross_origin()
def chat():
    return render_template('chat.html', username=session['email'])


@socketio.on('send_message')
def handle_send_message_event(data):
    app.logger.info("{} has sent message to the room: {}".format(data['username'], data['message']))
    data['created_at'] = datetime.datetime.now().strftime("%d %b, %H:%M")
    # save_message(data['room'], data['message'], data['username'])
    socketio.emit('receive_message', data)


@socketio.on('join_room')
def handle_join_room_event(data):
    app.logger.info("{} has joined the room".format(data['username']))
    # join_room(data['room'])
    socketio.emit('join_room_announcement', data)


@socketio.on('leave_room')
def handle_leave_room_event(data):
    app.logger.info("{} has left the room".format(data['username']))
    leave_room(data['room'])
    socketio.emit('leave_room_announcement', data)



import webhook


if __name__ == '__main__':
    socketio.run(app, debug=True)
