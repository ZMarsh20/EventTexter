import os
from dotenv import load_dotenv

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from twilio.twiml.messaging_response import MessagingResponse

project_folder = os.path.expanduser('~/mysite')
load_dotenv(os.path.join(project_folder, '.env'))

app = Flask(__name__, static_url_path='/static/')

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://zmarshall:'
app.config['SQLALCHEMY_DATABASE_URI'] += os.getenv("PASSWORD")
app.config['SQLALCHEMY_DATABASE_URI'] += '@zmarshall.mysql.pythonanywhere-services.com/zmarshall$planner'
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUM = os.getenv("TWILIO_NUM")
proxy_client = TwilioHttpClient(proxy={'http': os.environ['http_proxy'], 'https': os.environ['https_proxy']})
twilio_api = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, http_client=proxy_client)

db = SQLAlchemy(app)

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
# A = announce

class Contacts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    number = db.Column(db.String(15), unique=True, nullable=False)

class Person:
    name = ""
    mode = ""
    buffer = ""
    option = 0
    textPayment = 0
    paid = False
    starting = True
    going = False

    def __init__(self,name,starting=True,dad=False):
        self.answers = []
        self.name = name
        self.starting = starting
        self.going = dad
        if dad:
            self.mode = "s"

class Question:
    text = ""
    yes = 0
    no = 0

class Vote:
    text = ""

    def __init__(self):
        self.options = []
        self.tally = []

    def setText(self):
        msg = self.options.pop(0)
        for i in range(len(self.options)):
            msg += '\n' + str(i+1) + ". " + self.options[i]
        self.text = msg

    def addTally(self,msg,negate=False):
        val = 1
        if negate:
            val = -1
        if msg == 'none':
            return True
        else:
            try:
                votes = msg.split(',')
                weight = len(self.options)
                for vote in votes:
                    if 0 < int(vote) <= len(self.options):
                        self.tally[int(vote)] += weight
                        weight -= val
                    else:
                        return False
                return True
            except:
                return False


#DAD = os.getenv("DAD_NUM")
DAD = os.getenv("ADMIN_NUM")
ADMIN = os.getenv("ADMIN_NUM")
currentEvent = False
payment = False
people = {DAD : Person('Todd', False, True)}
Event = []
annoucements = []
Welcome = "Welcome to my dad's birthday gift. Respond yes or no to be a part of this"

@app.route('/', methods=['GET', 'POST'])
def root():
    incoming_msg = request.values.get('Body', '')
    incoming_number = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()
    if incoming_number in people:
        msg.body(decode(incoming_msg, incoming_number))
    return str(resp)


def send(msg,user):
    return twilio_api.messages.create(body=msg, from_=TWILIO_NUM, to=user)

def decode(oMsg, user):
    global currentEvent, payment, people, Event, annoucements
    msg = oMsg.lower().strip()
    mode = people[user].mode
    if len(msg) < 1:
        return fail()

    if people[user].starting:
        if 'y' == msg[0]:
            people[user].going = True
            people[user].starting = False
            announced = ""
            if len(annoucements) > 0:
                announceHistory(user)
                announced = "Those are all the announcements you missed. "
            if len(Event) > 0:
                people[user].mode = 'r'
                msg = Event[people[user].option].text
                return announced + "Now getting you ramped up...\n" + msg
            else:
                people[user].mode = 'h'
                return 'Welcome. Type "?" to see your options'
        elif people[user].going:
            if 'n' == msg[0]:
                return "Just reply 'y' if you change your mind"
            else:
                return "Only expecting 'y' or 'n'"

    if msg == 'back':
        if currentEvent or 's' not in mode:
            return clean(user)
        elif 'r' in mode:
            startOver()
            return "Starting sign over sign up"
        else:
            currentEvent = True
            return "Typing back again will finalize the event. Make sure you're ready"

    if msg == "?":
        return help(user)

    if 'h' in mode:
        if msg == "status":
            return status(user)
        elif msg == "message":
            people[user].mode = 'm1'
            return "Who would you like to message? (name)"
        elif msg == "pay":
            return pay(user)
        elif msg == "add":
            people[user].mode = 'a1'
            return "Who would you like to add?"
        elif msg == "end":
            people[user].mode = 'e'
            return "Are you sure you want to" + (" end " if user == DAD else " leave ") + "this event??"
        elif user == DAD or user == ADMIN:
            if currentEvent:
                if msg == "announce":
                    people[user].mode = 'A1'
                    return "What would you like to message?"
                elif msg == "pole":
                    return "pole"

    elif 'm' in mode:
        if '1' in mode:
            return checkPerson(msg,user)
        else:
            send((people[user].name + " says:\n" + msg), people[user].buffer)
            clean(user)
            return "Message sent"

    elif 'a' in mode:
        if '1' in mode:
            if len(msg) > 40:
                return "Name is to long please retype it. Try again"
            if ',' in msg:
                return "No commas allowed in name. Try again"
            people[user].buffer = msg
            if Contacts.query.filter_by(name=msg).first() is None:
                people[user].mode = 'a2'
                return "What's their number?"
            else:
                num = Contacts.query.filter_by(name=msg).first().number
                people[user].mode = 'a3'
                return "This name is already in the database. Add number ending in " + num[-4:]
        else:
            if 'y' == msg[0] or '2' in mode:
                if '2' in mode:
                    num = ''.join(list(filter(lambda x: x.isdigit(), msg)))
                    if len(num) != 10:
                        return "Phone number must be exactly 10 numbers"
                    people[user].buffer += ',+1' + num
                else:
                    people[user].buffer += ',' + Contacts.query.filter_by(name=people[user].buffer).first().number
                return addNum(user)
            elif 'n' == msg[0]:
                clean(user)
                return "Maybe add last name and try again"
            else:
                return "Only expecting 'y' or 'n'"

    elif 'A' in mode:
        if '1' in mode:
            people[user].buffer = oMsg
            people[user].mode = 'A2'
            return "Announce this?: " + oMsg
        else:
            broadcast(people[user].buffer, user)
            clean(user)
            return "Messages Sent"

    elif 's' in mode:
        if msg == "question":
            Event.append(Question())
            return addQuestion()
        elif msg == "vote":
            Event.append(Vote())
            return addVote(0)
        elif msg == "pay":
            payment = not payment
            msg = 'Now party members'
            msg += ' ' if payment else " don't "
            msg += 'need to keep track of payment'
            return msg
        elif msg == "end":
            restart()
            return "Clean slate"

    elif 'r' in mode:
        i = people[user].option
        if isinstance(Event[i], Vote) and not Event[i].addTally(msg):
            return 'Answers should be comma separated numbers. "?" for examples'
        elif isinstance(Event[i], Question) and ('y' in msg or 'n' in msg):
            if 'y' in msg:
                Event[i].yes += 1
            elif 'n' in msg:
                Event[i].no += 1
        elif isinstance(Event[i], Question):
            return "Only expecting 'y' or 'n'"
        people[user].answers.append(msg)
        people[user].option += 1
        if i+1 >= len(Event):
            clean(user)
            return 'Those are all the questions. Thank you. Type "?" to see what you can do now'
        else:
            msg = Event[people[user].option].text
            return "Answer locked in. Next question:\n" + msg


    elif 'e' in mode:
        if 'y' in msg:
            if user == DAD or user == ADMIN:
                if '1' in mode:
                    return "Double checking again because all your set up and everything will be gone"
                else:
                    restart()
                    return "Ok then. Deleting..."
            else:
                people[user].going = False
                people[user].starting = True
                return "Just reply 'y' if you change your mind"
        else:
            return 'Ok. "?" for further options'

    elif 'q' in mode:
        if '1' in mode:
            people[DAD].mode = 'q2'
            people[DAD].buffer = oMsg
            return "Are you sure that you want to ask: " + oMsg
        else:
            if 'y' == msg[0]:
                people[DAD].mode = 's'
                Event[-1].text = people[DAD].buffer
                people[DAD].buffer = ''
                return "Question now in sign up"
            elif 'n' == msg[0]:
                return addQuestion()
            else:
                return "Only expecting 'y' or 'n'"

    elif 'v' in mode:
        if msg == 'end':
            people[DAD].mode = 'v3'
            return "Are you sure you want to end your options?"
        i = people[DAD].option
        if '1' in mode:
            people[DAD].mode = 'v2'
            people[DAD].buffer = oMsg
            if i > 0:
                return "Are you sure that you want option " + str(people[DAD].option) + " to be: " + oMsg
            else:
                return "You want that to be the theme?: " + oMsg
        else:
            if 'y' == msg[0]:
                if '3' in mode:
                    clean(DAD)
                    return "A preview:\n" + Event[-1].text
                Event[-1].options.append(people[DAD].buffer)
                Event[-1].tally.append(0)
                return addVote(i+1)
            elif 'n' == msg[0]:
                return addVote(i)
            else:
                return "Only expecting 'y' or 'n'"

    elif 'P' in mode:
        present, num = getName(msg)
        people[DAD].mode = 'h'
        if present:
            people[num].paid = not people[num].paid
            return msg.title() + " has been marked as " + "" if people[num].paid else "not" + "paid"
        else:
            return 'Name not found in group. Type "status" to see all who are present'

    return fail()

def fail():
    return 'Unrecognized response. Type "?" to see command options'

def clean(user):
    mode = people[user].mode
    if 's' in mode:
        people[DAD].mode = 'h'
        return "Event set. Now you can add everyone to the event"
    elif 'v' in mode or 'q' in mode:
        people[DAD].mode = 's'
        people[DAD].option = 0
        if 'v3' in mode:
            Event[-1].setText()
            send("Vote set for sign up", DAD)
        else:
            Event.pop(-1)
            send("Removed", DAD)
    elif people[user].going:
        people[user].mode = 'h'
    people[user].buffer = ""

def checkPerson(msg,user):
    mode = people[user].mode
    for key,val in people.items():
        if msg in val.name.lower():
            if 'm' in mode:
                val.mode = 'm2'
                msg = "What would you like to send to " + val.name.title() + "?"
                people[user].buffer = key
                break
            elif 'p' in mode:
                val.mode = 'p2'
                msg = "You want to check off " + val.name.title() + " for paying?"
                break
    else:
        msg = 'Didn\'t find that name in the group. "status" will show you all names in group'
    return msg

def getName(number):
    for k,v in people.items():
        if k == number and v.going:
            return True, v.name
    else:
        return False, ""

def addNum(user):
    msg = "Got it"
    if user != DAD:
        send("Please add " + people[user].buffer.title() + " - " + people[user].name.title(), DAD)
        msg += ". Once Todd approves them, they will be added to the event"
    else:
        name = people[user].buffer.split(',')[0].lower()
        number = people[user].buffer.split(',')[1]
        if number not in people:
            if Contacts.query.filter_by(number=number).first() is None:
                contact = Contacts(name=name, number=number)
                db.session.add(contact)
                db.session.commit()
            people[number] = Person(name)
            send(Welcome, number)
        else:
            return "They are already signed up for the event"
    clean(user)
    return msg

def broadcast(msg, user):
    mode = people[user].mode
    if 'a' in mode:
        annoucements.append(msg)
    pole = False
    if 'p' in mode:
        pole = True
    for key,val in people.items():
        if val.going:
            if pole:
                val.mode = 'p'
            elif key == user:
                continue
            send(msg,key)

def announceHistory(user):
    for msg in annoucements:
        send(msg, user)

def help(user):
    mode = people[user].mode
    msg = '"?" shows available commands\n'
    if 's' in mode:
        msg += '"question" to add a yes or no question when signing up\n'
        msg += '"vote" to add a vote when signing up\n'
        msg += '"pay" change whether or not you are expecting payment\n'
        msg += '"back" to end sign up and start adding people\n'
        msg += '"end" to restart'
    elif 'r' in mode:
        msg += 'If there is a list with numbers then expected replies are as follows:\n'
        msg += '1,2,3,4,5,6,ect. or 1,2,3 to add only to those options (help prioritize your choices) or "none" for no choice\n'
        msg += 'If there is no list then only a yes or no is expected\n'
        msg += '"back" to start over questionnaire'
    elif 'v' in mode or 'q' in mode:
        msg += '"back" to not add this to sign up'
        if 'v' in mode:
            msg += '\n"end" to finish list of vote'
    elif 'p' in mode:
        '"back" cast no vote in the pole'
    elif 'P' in mode:
        '"back" exit payment checklist mode'
    elif 'a' in mode:
        '"back" stop adding number'
    elif 'A' in mode:
        '"back" Exit announcement mode'
    elif 'm' in people[user].mode:
        msg += '"back" to stop messaging'
    elif people[user].going:
        if not people[user].paid and payment:
            msg += '"pay" to request Todd to check you off for paying everything. Send image proof to him directly\n'
        elif user == DAD:
            msg += '"pay" to check someone off for paying\n'
        else:
            msg += '"message" to begin message to someone\n'
            msg += '"status" to see people in the event'
            msg += ', your payment status ' if payment else ' '
            msg += 'and current results of all votes and also sometimes more\n'
            msg += '"add" to add someone to the group\n'
            if user == DAD or user == ADMIN:
                msg += '"announce" to send a message to everyone\n'
                msg += '"pole" to start a pole (e.g. dinner choices)\n'
            msg += '"end" to end the event for ' + "everyone" if user == DAD else "yourself"
    return msg

def status(user):
    msg = "status"
    return msg

def pay(user):
    if user == DAD:
        people[DAD].mode = 'P'
        return "Who would you like to check off as paid?"
    else:
        send(people[user].name.title() + ' says they have paid. Type "pay" to check someone off for paying', DAD)
        return "Request sent. Send Todd a screenshot or image of your payment just in case he's drunk :)"

def addQuestion():
    people[DAD].mode = 'q1'
    return "Type now your yes or no question"

def addVote(i):
    people[DAD].option = i
    people[DAD].mode = 'v1'
    if i > 0:
        return "Type now option " + str(i)
    else:
        return "Type now the theme of the selection"

def startOver(user):
    answers = people[user].answers
    for i in len(range(answers)):
        if 'y' in answers[i]:
            Event[i].yes -= 1
        elif 'n' in answers[i]:
            Event[i].no -= 1
        else:
            Event[i].addTally(answers[i],True)

    people[user].option = 0
    people[user].answers = []

def restart():
    global currentEvent, payment, people, Event, annoucements
    currentEvent = False
    payment = False
    people = {DAD : Person('Todd', False, True)}
    Event = []
    annoucements = []

if __name__ == '__main__':
    app.run(debug=True)
