from flask import Flask, request
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
import flask_mysqldb
import os
from dotenv import load_dotenv
project_folder = os.path.expanduser('~/mysite')
load_dotenv(os.path.join(project_folder, '.env'))

app = Flask(__name__, static_url_path='/static/')

app.config['MYSQL_HOST'] = 'zmarshall.mysql.pythonanywhere-services.com'
app.config['MYSQL_USER'] = 'zmarshall'
app.config['MYSQL_PASSWORD'] = os.getenv("PASSWORD")
app.config['MYSQL_DB'] = 'zmarshall$planner'

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUM = os.getenv("TWILIO_NUM")
proxy_client = TwilioHttpClient(proxy={'http': os.environ['http_proxy'], 'https': os.environ['https_proxy']})
twilio_api = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, http_client=proxy_client)

mysql = flask_mysqldb.MySQL(app)

class Person():
    name = ""
    mode = "h"
    buffer = ""

    def __init__(self,name):
        self.name = name

#DAD = os.getenv("DAD_NUM")
DAD = os.getenv("ADMIN_NUM")
ADMIN = os.getenv("ADMIN_NUM")
currentEvent = False
payment = False
people = {DAD : Person('Todd')}

@app.route('/', methods=['GET', 'POST'])
def root():
    if request.method != 'GET':
        msg = next(twilio_api.messages.stream())
        if msg.from_ in people:
            decode(msg.body, msg.from_)
    return ':3'

def send(msg,user):
    return twilio_api.messages.create(body=msg, from_=TWILIO_NUM, to=user)

def decode(msg, user):
    global payment, currentEvent, people
    msg = msg.strip().lower()
    mode = people[user].mode

    if msg == '-quit':
        return clean(user)

    if msg == "-help":
        return help(user)

    if 'h' in mode:
        if msg == "-status":
            return status(user)
        elif msg == "-message":
            return message(user)
        elif user == DAD or user == ADMIN:
            if currentEvent:
                if msg == "-announce":
                    return announce()
                elif msg == "-pole":
                    return startPole()
            elif user == DAD:
                if people[DAD].mode == "s":
                    if msg == "-start":
                        return startEnd()
                else:
                    if msg == "-add":
                        return addPerson()
                    elif msg == "-vote":
                        return addVote()
                    elif msg == "-pay":
                        payment = not payment
                        msg = 'Now party members'
                        msg += ' ' if payment else " don't "
                        msg += 'need to keep track of payment'
                        return send(msg, DAD)
        elif msg == "-pay":
            return pay()

    elif 'm' in mode:
        if '1' in mode:
            return send(checkPerson(msg,user),user)
        else:
            sent = send("Message sent",user)
            send((people[user].name + " says:\n" + msg), people[user].buffer)
            clean(user)
            return sent

    return fail(user)

def fail(user):
    msg = 'Type "-help" to see command options'
    send(msg,user)

def clean(user):
    people[user].mode = 'h'
    people[user].buffer = ""

def checkPerson(msg,user):
    for key,val in people.items():
        if msg in val.name.lower():
            val.mode = 'm2'
            msg = "What would you like to send to " + val.name + "?"
            people[user].buffer = key
            break
    else:
        msg = 'Didn\'t find that name in the group. "-status" will show you all names in group'
    return msg

def commandList(user):
    msg = '"-help" shows available commands\n'
    if 'pm' in people[user].mode:
        '"-quit" cast no vote in the pole'
    else:
        if 'p' not in people[user].mode and payment:
            msg += '"-pay" to request Todd to check you off for paying everything. Send image proof to him directly\n'
        if 'm' in people[user].mode:
            msg += '"-quit" to stop messaging'
        else:
            msg += '"-message" to begin message to someone\n'
            msg += '"-status" to see people in the event'
            msg += ', your payment status ' if payment else ' '
            msg += 'and current results of all votes'
            if user == DAD or user == ADMIN:
                msg += '\n"-announce" to send a message to everyone\n'
                msg += '"-pole" to start a pole (e.g. "Mexican or Burgers")'
    return msg

#####commands#####

def help(user):
    msg = commandList(user);
    return send(msg, user)
    #list all commands
def status(user):
    msg = "status"
    return send(msg, user)
    #show who's going, payment, votes
def message(user):
    msg = "Who would you like to message?"
    people[user].mode = 'm1'
    return send(msg, user)
    #send message to someone specific

###Admin###

def startEnd():
    return
    #start new event or end current event
    #add/remove table and update status
def addPerson():
    return
    #add number to current event (update database)
    #initial confirm
def addVote():
    return
    #add tally count for new field
def pay():
    return
    #ask for proof of payment
def announce():
    return
    #message all
def startPole():
    return
    #send a text pole and announce winner

##################

if __name__ == '__main__':
    app.run(debug=True)
