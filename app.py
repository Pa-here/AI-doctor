from flask import Flask, render_template, url_for, request, jsonify, make_response
from flask_cors import CORS, cross_origin
import pandas as pd
import numpy as np
import pickle
from pymongo import MongoClient
import json
import os
from dialogflow_v2.types import TextInput, QueryInput
from dialogflow_v2 import SessionsClient
from google.api_core.exceptions import InvalidArgument
import requests
import urllib


app = Flask(__name__)

test_data = pd.read_csv('Testing.csv', sep=',')
test_data = test_data.drop('prognosis', axis=1)
symptoms = list(test_data.columns)
model = pickle.load(open('model.pkl', 'rb'))
cluster = MongoClient(
        "mongodb+srv://mdyamin:yamin787898@cluster0.5bduk.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = cluster['aidoctor']

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/webhook', methods=['POST'])
@cross_origin()
def webhook():
    req = request.get_json(silent=True, force=True)
    res = ProcessRequest(req)
    res = json.dumps(res, indent=4)
    print(res)
    response = make_response(res)
    response.headers['Content-Type'] = 'application/json'
    return response


def ProcessRequest(req):
    collection = db['user_symptoms']
    result = req.get('queryResult')
    intent = result.get('intent').get('displayName')

    if intent == 'get_info':
        name = result.get('parameters').get('any')
        age = result.get('parameters').get('number')
        collection.insert_one({
            'name': name,
            'age': age,
            'symptoms': []
        })

        webhookresponse = 'Hey {}, what symptoms do you have? please enter one of your symptoms.(Ex. headache, vomiting etc.)'.format(
            name)

        return {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            webhookresponse
                        ]

                    }
                }
            ]
        }

    elif intent == 'get_symptom':
        name = result.get('outputContexts', [])[0].get('parameters').get('any')
        symptom = result.get('parameters').get('symptom')

        document = collection.find_one_and_update(
            {'name': name},
            {'$push': {'symptoms': symptom}}
        )

        webhookresponse = "Enter one more symptom beside {}. (Enter 'No' if not)".format(
            symptom)

        return {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            webhookresponse
                        ]
                    }
                }
            ]
        }
    elif intent == 'get_symptom - no':
        name = result.get('outputContexts', [])[1].get('parameters').get('any')
        user_symptoms = collection.find_one({'name': name})
        user_symptoms = list(user_symptoms.get('symptoms'))
        y = []
        for i in range(len(symptoms)):
            y.append(0)
        for i in range(len(user_symptoms)):
            y[symptoms.index(user_symptoms[i])] = 1
        disease = model.predict([np.array(y)])
        disease = disease[0]

        webhookresponse = f"Hey {name}. You may have {disease}."

        return {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            webhookresponse
                        ]
                    }
                }
            ]
        }


@app.route('/chatapi', methods=['POST'])
@cross_origin()
def chat_response():
    req = request.get_json(force=True)
    msg = req.get('MSG')
    res = DialogflowInteraction(msg)
    response = make_response(res)
    response.headers['Content-Type'] = 'application/json'
    return response


def DialogflowInteraction(userText):

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = 'private_key.json'
    DIALOGFLOW_PROJECT_ID = 'ai-doctor-ebfe'
    DIALOGFLOW_LANGUAGE_CODE = 'en'
    SESSION_ID = 'me'

    text_to_be_analyzed = userText

    session_client = SessionsClient()
    session = session_client.session_path(DIALOGFLOW_PROJECT_ID, SESSION_ID)
    text_input = TextInput(text=text_to_be_analyzed,
                           language_code=DIALOGFLOW_LANGUAGE_CODE)
    query_input = QueryInput(text=text_input)
    try:
        response = session_client.detect_intent(
            session=session, query_input=query_input)
    except InvalidArgument:
        raise

    botText = response.query_result.fulfillment_text
    intent = response.query_result.intent.display_name

    if intent == 'get_info' or intent == 'get_symptom' or intent == 'get_symptom - no':
        return {
            'Reply': response.query_result.fulfillment_messages[0].text.text[0]
        }

    else:
        return {
            'Reply': botText
        }


@app.route('/bot')
@cross_origin()
def chat_bot():
    return render_template('bot.html')


@app.route('/dashboard')
@cross_origin()
def dashboard():
    return render_template('dashboard.html')

@app.route('/contact')
@cross_origin()
def contact_us():
    return render_template('contactUs.html')

@app.route('/services')
@cross_origin()
def Services():
    return render_template('services.html')

@app.route('/signup', methods=['POST'])
@cross_origin()
def sign_up():
    collection = db['users']
    form_data = request.form
    id = collection.insert_one({
        'name': form_data['name'],
        'email': form_data['email'],
        'password': form_data['password'],
        'userType': form_data['userType']
    }).inserted_id
    response = ''
    if id == '':
        response = 'failed'
    else:
        response = 'success'
    return render_template('signup.html', response=response)


@app.route('/login', methods=['POST'])
@cross_origin()
def login():
    collection = db['users']
    form_data = request.form
    query_data = {
        "email": form_data['email'],
        "password": form_data['password']
    }
    result = collection.find_one(query_data)
    response = ''
    if result == None:
        response = 'failed'
    else:
        response = 'succeeded'
    
    return response


@app.route('/resetdb')
@cross_origin()
def reset_database():
    collection1 = db['user_symptomps']
    collection2 = db['users']
    collection1.delete_many({})
    collection2.delete_many({})
    return "Database Cleared"

if __name__ == '__main__':
    app.run(debug=True)
