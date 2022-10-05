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

# Legend
# h = home
# m = message
# s = start
# r = ramp up
# p = pole mode
# P = pay mode
# e = end
# v = vote set up or vote
# q = question
# a = add person

class Person:
    name = ""
    mode = ""
    buffer = ""
    option = 0
    textPayment = 0
    paid = False
    starting = True
    going = True
    answers = []

    def __init__(self,name,starting=True,dad=False):
        self.name = name
        self.starting = starting
        if dad:
            self.mode = "s"

class Question:
    text = ""
    yes = 0
    no = 0

class Vote:
    options = []
    tally = []

Event = []

#DAD = os.getenv("DAD_NUM")
DAD = os.getenv("ADMIN_NUM")
ADMIN = os.getenv("ADMIN_NUM")
currentEvent = False
payment = False
people = {DAD : Person('Todd', False, True)}

@app.route('/', methods=['GET', 'POST'])
def root():
    if request.method != 'GET':
        try:
            msg = next(twilio_api.messages.stream())
        except:
            print("\nFailed\n")
        if msg.from_ in people:
            decode(msg.body, msg.from_)
    return ':3'

def send(msg,user):
    return twilio_api.messages.create(body=msg, from_=TWILIO_NUM, to=user)

def decode(msg, user):
    global payment, currentEvent, people
    msg = msg.strip().lower()
    mode = people[user].mode
    if len(msg) < 1:
        return fail(user)

    if people[user].starting:
        if 'y' == msg[0]:
            people[user].going = True
            people[user].mode = "r"
            announceHistory(user)
        elif people[user].going:
            if 'n' == msg[0]:
                people[user].going = False
                send("Just reply 'y' if you change your mind", user)
            else:
                return send("Only expecting 'y' or 'n'", user)

    if msg == 'back':
        if currentEvent or 's' not in mode:
            return clean(user)
        else:
            currentEvent = True
            return send("Typing back again will finalize the event. Make sure you're ready", DAD)

    if msg == "?":
        return help(user)

    if 'h' in mode:
        if msg == "status":
            return status(user)
        elif msg == "message":
            return message(user)
        elif msg == "pay":
            return pay(user)
        elif msg == "add":
            return addPerson(user)
        elif msg == "end":
            return end(user)
        elif user == DAD or user == ADMIN:
            if currentEvent:
                if msg == "announce":
                    return announce()
                elif msg == "pole":
                    return startPole()

    elif 'm' in mode:
        if '1' in mode:
            return send(checkPerson(msg,user),user)
        else:
            sent = send("Message sent",user)
            send((people[user].name + " says:\n" + msg), people[user].buffer)
            clean(user)
            return sent

    elif 's' in mode:
        if msg == "question":
            event = Question()
            Event.append(event)
            return addQuestion()
        elif msg == "vote":
            event = Vote()
            Event.append(event)
            return addVote(1)
        elif msg == "pay":
            payment = not payment
            msg = 'Now party members'
            msg += ' ' if payment else " don't "
            msg += 'need to keep track of payment'
            return send(msg, DAD)

    elif 'e' in mode:
        if user == DAD or user == ADMIN:
            if 'y' in msg:
                return None
            else:
                return None
        else:
            return None

    elif 'q' in mode:
        if '1' in mode:
            people[DAD].mode = 'q2'
            people[DAD].buffer = msg
            return send("Are you sure that you want to ask: " + msg,user)
        else:
            if 'y' == msg[0]:
                people[DAD].mode = 's'
                Event[-1].text = people[DAD].buffer
                people[DAD].buffer = ''
                return send("Question now in sign up",user)
            if 'n' == msg[0]:
                return addQuestion()
            else:
                return send("Only expecting 'y' or 'n'", user)

    elif 'v' in mode:
        if msg == '-end':
            return clean(DAD)
        i = people[DAD].option
        if '1' in mode:
            people[DAD].mode = 'v2'
            people[DAD].buffer = msg
            return send("Are you sure that you want option " + str(people[DAD].option) + " to be: " + msg,user)
        else:
            if 'y' == msg[0]:
                Event[-1].options.append(people[DAD].buffer)
                Event[-1].tally.append(0)
                return addVote(i+1)
            if 'n' == msg[0]:
                return addVote(i)
            else:
                return send("Only expecting 'y' or 'n'", user)

    return fail(user)

def fail(user):
    msg = 'Unrecognized response. Type "?" to see command options'
    send(msg,user)

def clean(user):
    mode = people[user].mode
    if 's' in mode:
        people[DAD].mode = 'h'
        return send("Event set. Now you can add everyone to the event", DAD)
    elif 'v' in mode or 'q' in mode:
        people[DAD].mode = 's'
        Event.pop(-1)
        return send("Removed", DAD)
    elif 'p' in mode:
        return None
    if people[user].going:
        people[user].mode = 'h'
    people[user].buffer = ""

def checkPerson(msg,user):
    mode = people[user].mode
    for key,val in people.items():
        if msg in val.name.lower():
            if 'm' in mode:
                val.mode = 'm2'
                msg = "What would you like to send to " + val.name + "?"
                people[user].buffer = key
                break
            elif 'p' in mode:
                val.mode = 'p2'
                msg = "You want to check off " + val.name + " for paying?"
                break
    else:
        msg = 'Didn\'t find that name in the group. "status" will show you all names in group'
    return msg

def commandList(user):
    mode = people[user].mode
    msg = '"?" shows available commands\n'
    if 's' in mode:
        msg += '"question" to add a yes or no question when signing up\n'
        msg += '"vote" to add a vote when signing up\n'
        msg += '"pay" change whether or not you are expecting payment\n'
        msg += '"back" to end sign up and start adding people'
    elif 'v' in mode or 'q' in mode:
        msg += '"back" to not add this to sign up'
        if 'v' in mode:
            msg += '\n"-end" to finish list of vote'
    elif 'p' in mode:
        '"back" cast no vote in the pole'
    elif people[user].going:
        if not people[user].paid and payment:
            msg += '"pay" to request Todd to check you off for paying everything. Send image proof to him directly\n'
        elif user == DAD:
            msg += '"pay" to check someone off for paying\n'
        if 'm' in people[user].mode:
            msg += '"back" to stop messaging'
        else:
            msg += '"message" to begin message to someone\n'
            msg += '"status" to see people in the event'
            msg += ', your payment status ' if payment else ' '
            msg += 'and current results of all votes and also sometimes more\n'
            msg += '"add" to add someone to the group'
            if user == DAD or user == ADMIN:
                msg += '\n"announce" to send a message to everyone\n'
                msg += '"pole" to start a pole (e.g. dinner choices)'
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
def pay(user):
    return
    #ask for proof of payment
def addPerson(user):
    return
    #add number to current event (update database)
    #initial confirm
def end(user):
    people[user].mode = "e"
    return
    #end current event

###Admin###

def addQuestion():
    people[DAD].mode = 'q1'
    msg = "Type now your yes or no question"
    return send(msg, DAD)
    #add yes or no question
def addVote(i):
    people[DAD].option = i
    people[DAD].mode = 'v1'
    msg = "Type now option " + str(i)
    return send(msg, DAD)
    #add tally count for new field
def announce():
    return
    #message all
def announceHistory(user):
    return
    # give all announcements to newcomers
def startPole():
    return
    #send a text pole and announce winner

##################

if __name__ == '__main__':
    app.run(debug=True)
