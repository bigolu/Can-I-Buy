from pymongo import MongoClient
from flask import Flask, request
from twilio import twiml
from twilio.rest import TwilioRestClient
import requests
import json
import config

app = Flask(__name__)

# mongodb setup
mongo_client = MongoClient()
alldata = mongo_client.alldata

"""
Parse incoming text message and send arguments to the proper handler.
"""
@app.route('/', methods=['GET', 'POST'])
def parse_text():
    # twilio authentification
    account_sid = config.twilio['account_sid']
    auth_token = config.twilio['auth_token']
    twilio_client = TwilioRestClient(account_sid, auth_token)

    text_body = request.values.get('Body')
    text_body = text_body.lower()
    from_number = request.values.get('From')
    command = text_body.split()[0]

    # use proper handler based on the command and get the response text message
    response_msg = ''
    if command == 'register':
        response_msg = register(from_number, text_body.split()[1])
    elif command == 'cib':
        cursor = alldata.users.find_one({"phone_number": from_number})
        response_msg = cib(cursor['account_number'], int(text_body.split()[1]))
    response_msg = 'Sorry, that is not a valid command, please try again.' if response_msg == '' else response_msg

    # build response text message
    twiml_response = twiml.Response()
    twiml_response.message(response_msg)

    return str(twiml_response)

def register(from_number, account_number):
    alldata.users.insert_one(
        {
            'phone_number': from_number,
            'account_number': account_number
        }
    )

    for doc in alldata.users.find():
        print doc

    return 'register'

def cib(account_number, item_price):
    apiKey = '68adc0a7ae6d8926a13d5e652af30c1a' #to access capital one data
    
    getAccounturl = 'http://api.reimaginebanking.com/accounts/{}?key={}'.format(account_number,apiKey)
    balance = requests.get(getAccounturl)
    balance = balance.json()
    balance = balance['balance']

    getExpensesurl = 'http://api.reimaginebanking.com/accounts/{}/withdrawals?key={}'.format(account_number,apiKey)
    expenses = requests.get(getExpensesurl)
    expenses = expenses.json()
    expenses = expenses[0]['amount']

    getIncomeurl = 'http://api.reimaginebanking.com/accounts/{}/deposits?key={}'.format(account_number,apiKey)
    income = requests.get(getIncomeurl)
    income = income.json()
    income = income[0]['amount']

    balance = balance - item_price

    if balance > expenses*2:
        response = 'You can afford this because you will have {} left in your account which is more than 2 times your monthly expenses ({})'.format(balance,expenses)

    else: 
        if income > expenses:
            print 'income: %d expenses %d' %(income, expenses)
            profit = income-expenses
            futureBalance = balance
            months = 0
            while futureBalance < expenses*2:
                futureBalance = futureBalance+profit
                months=months+1
            response = 'You cannot afford this currently because your balance will be {} upon purchase of this item, which is below 2 months of expenses ({}). However, with your current expense and income level, you will be able to purchase this in {} months.'.format(balance,expenses*2, months)
        else:
            response = 'You cannot afford this because your balance will be {} upon purchase of this item, which is below 2 months of expenses({})). To buy this you need to increase your income and/or reduce your expenses.'.format(balance,expenses*2)



    return response

if __name__ == '__main__':
    app.run(debug=True)
