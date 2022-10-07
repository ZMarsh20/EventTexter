import os
import random
import jsonpickle
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
# pi = pole initiate
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
    def __init__(self,name,starting=True,dad=False):
        self.mode = ""
        self.buffer = ""
        self.option = 0
        self.textPayment = 0
        self.paid = False
        self.limitOutput = False

        self.answers = []
        self.name = name
        self.starting = starting
        self.going = dad
        if dad:
            self.mode = "s"

class Question:
    def __init__(self):
        self.text = ""
        self.yes = 0
        self.no = 0

    def getText(self):
        return self.text

class Vote:
    def __init__(self):
        self.text = ""
        self.theme = ""
        self.options = []
        self.tally = []

    def setText(self):
        self.theme = self.options.pop(0)
        msg = self.theme
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
                votesTemp = msg.split(',')
                votes = []
                for vote in votesTemp:
                    if vote not in votes:
                        votes.append(vote)
                weight = len(self.options)
                for vote in votes:
                    if 0 < int(vote) <= len(self.options):
                        self.tally[int(vote)-1] += (weight * val)
                        weight -= 1
                    else:
                        return False
                return True
            except:
                return False

    def getText(self):
        return self.theme

class Pole:
    def __init__(self):
        self.text = ""
        self.theme = ""
        self.winner = ""
        self.count = 0
        self.options = []
        self.tally = []

    def setText(self):
        self.theme = self.options.pop(0)
        msg = self.theme
        for i in range(len(self.options)):
            msg += '\n' + str(i+1) + ". " + self.options[i]
        self.text = msg

    def findWinner(self):
        winners = []
        for i in range(len(self.options)):
            if self.tally[i] == max(self.tally):
                winners.append(self.options[i])
        if len(winners) > 1:
            self.winner = "After a coinflip, " + random.choice(winners) + "!"
            return True
        self.winner = winners[0] + "!"
        return True

    def endPole(self, users):
        if users == self.count:
            return self.findWinner()
        first = 0
        second = 0
        for tick in self.tally:
            if tick > first:
                second = first
                first = tick
            elif tick > second:
                second = tick
        if (first-second) > (users - self.count):
            return self.findWinner()
        return False

    def addTally(self,msg):
        try:
            if 0 < int(msg) <= len(self.options):
                self.count += 1
                self.tally[int(msg)-1] += 1
                return True
            else:
                return False
        except:
            return False

    def getText(self):
        return self.theme


#DAD = os.getenv("DAD_NUM")
DAD = os.getenv("ADMIN_NUM")
ADMIN = os.getenv("ADMIN_NUM")
currentEvent = False
payment = False
people = {DAD : Person('Todd', False, True)}
Event = []
announcements = []
currentPole = None
Welcome = "Welcome to my dad's birthday gift. Respond yes or no to be a part of this"

@app.route('/', methods=['GET', 'POST'])
def root():
    incoming_msg = request.form['Body']
    incoming_number = request.form['From']
    resp = MessagingResponse()
    msg = resp.message()
    if incoming_number in people:
        msg.body(decode(incoming_msg, incoming_number))
    return str(resp)


def send(msg,user):
    return twilio_api.messages.create(body=msg, from_=TWILIO_NUM, to=user)

def decode(oMsg, user):
    global currentEvent, payment, people, Event, announcements, currentPole
    msg = oMsg.lower().strip()
    mode = people[user].mode
    if len(msg) < 1:
        return fail()

    if user == ADMIN:
        if msg == 'save':
            return save()
        elif msg == 'load':
            return load()

    if people[user].starting:
        if 'y' == msg[0]:
            people[user].going = True
            people[user].starting = False
            if len(Event) > 0:
                people[user].mode = 'r'
                msg = Event[people[user].option].text
                return "Now getting you ramped up...\n" + msg
            else:
                people[user].mode = 'h'
                return 'Welcome. Type "?" to see your options' + announceHistory()
        elif not people[user].limitOutput:
            if 'n' == msg[0]:
                people[user].limitOutput = True
                return "Just reply 'y' if you change your mind"
            else:
                return "Only expecting 'y' or 'n'"

    if not people[user].going:
        return ""

    if msg == 'back':
        if 'r' in mode:
            return startOver(user)
        elif currentEvent or 's' not in mode:
            return clean(user)
        else:
            currentEvent = True
            return "Typing back again will finalize the event. Make sure you're ready"

    if msg == "?":
        return help(user)

    if 'h' in mode:
        if "status" in msg:
            if msg == "status":
                return status(user, None)
            elif user == DAD:
                try:
                    name = msg.split(' ',1)[1]
                    return status(user,name)
                except:
                    return fail()
        elif msg == "message":
            people[user].mode = 'm1'
            return "Who would you like to message? (name)"
        elif msg == "pay" and payment:
            return pay(user)
        elif "add" in msg:
            if msg == "add":
                people[user].mode = 'a1'
                return "Who would you like to add?"
            else:
                try:
                    name = msg.split(' ',1)[1]
                    return add1(name,user)
                except:
                    return fail()
        elif msg == "end":
            people[user].mode = 'e'
            return "Are you sure you want to" + (" end " if user == DAD else " leave ") + "this event??"
        elif user == DAD or user == ADMIN:
            if currentEvent:
                if msg == "announce":
                    return announce(user)
                elif msg == "pole":
                    currentPole = Pole()
                    return pole(0,user)

    elif 'm' in mode:
        if '1' in mode:
            return checkPerson(msg,user)
        else:
            send((people[user].name.title() + " says:\n" + msg), people[user].buffer)
            clean(user)
            return "Message sent"

    elif 'a' in mode:
        if '1' in mode:
            add1(msg,user)
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
            people[user].buffer = "Announcement: " + oMsg
            people[user].mode = 'A2'
            return "Announce this? " + oMsg
        else:
            if 'y' == msg[0]:
                broadcast(people[user].buffer, user)
                clean(user)
                return "Messages Sent"
            elif 'n' == msg[0]:
                return announce(user)
            else:
                return "Only expecting 'y' or 'n'"

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
        if msg == "end":
            people[user].going = False
            people[user].starting = True
            return "Just reply 'y' if you change your mind"
        i = people[user].option
        if isinstance(Event[i], Vote) and not Event[i].addTally(msg):
            return 'Answers should be comma separated numbers. "?" for examples'
        elif isinstance(Event[i], Question) and ('y' == msg[0] or 'n' == msg[0]):
            if 'y' == msg[0]:
                Event[i].yes += 1
            elif 'n' == msg[0]:
                Event[i].no += 1
            else:
                return "Only expecting 'y' or 'n'"
        people[user].answers.append(msg)
        people[user].option += 1
        if i+1 >= len(Event):
            clean(user)
            return 'Thank you. Type "?" for help\n' + announceHistory(user)
        else:
            msg = Event[people[user].option].text
            return "Answer locked in. Next question:\n" + msg


    elif 'e' in mode:
        if 'y' in msg:
            if user == DAD or user == ADMIN:
                if '1' in mode:
                    return "Double checking again because everything will be gone"
                else:
                    restart()
                    return "Ok then. Deleting..."
            else:
                people[user].going = False
                people[user].starting = True
                startOver(user)
                return "Just reply 'y' if you change your mind"
        else:
            return 'Ok'

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
            people[DAD].mode = 'v2'
            clean(DAD)
            return "Vote set for sign up"
        i = people[DAD].option
        if '1' in mode:
            Event[-1].options.append(oMsg)
            Event[-1].tally.append(0)
            return addVote(i+1)

    elif 'p' in mode:
        if 'i' in mode:
            if msg == 'end':
                people[user].mode = 'pi2'
                clean(user)
                return "Pole is now running. Cast your vote too\n" + broadcast(currentPole.text, user)
            i = people[user].option
            if '1' in mode:
                currentPole.options.append(people[user].buffer)
                currentPole.tally.append(0)
                return pole(i+1,user)
        else:
            if currentPole.addTally(msg):
                msg = "Your vote has been cast"
                if currentPole.endPole(len(people)):
                    msg = broadcast(currentPole.winner, user)
                    currentPole = None
                return msg
            return 'Not valid. "?" for help'


    elif 'P' in mode:
        present, num = getNumber(msg)
        people[DAD].mode = 'h'
        if present:
            people[num].paid = not people[num].paid
            return msg.title() + " has been marked as " + ("" if people[num].paid else "not") + "paid"
        else:
            return 'Name not found in group. Type "status" to see all who are present'

    return fail()

def fail():
    return 'Unrecognized response. Type "?" to see command options'

def add1(msg,user):
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

def clean(user):
    global currentPole
    mode = people[user].mode
    if 'p' in mode:
        if 'i' in mode:
            if '2' in mode:
                people[user].mode = 'p'
                currentPole.setText()
                return
            else:
                currentPole = None
        else:
            currentPole.count += 1
    if 's' in mode:
        people[DAD].mode = 'h'
        return "Event set. Now you can add everyone to the event"
    elif 'v' in mode or 'q' in mode:
        people[DAD].mode = 's'
        people[DAD].option = 0
        if 'v2' in mode:
            Event[-1].setText()
        else:
            Event.pop(-1)
            send("Removed", DAD)
    elif people[user].going:
        people[user].mode = 'h'
    people[user].buffer = ""

def checkPerson(msg,user):
    mode = people[user].mode
    for k,v in people.items():
        if msg in v.name.lower():
            if 'm' in mode:
                people[user].mode = 'm2'
                msg = "What would you like to send to " + v.name.title() + "?"
                people[user].buffer = k
                break
            elif 'p' in mode:
                v.mode = 'p2'
                msg = "You want to check off " + v.name.title() + " for paying?"
                break
    else:
        msg = 'Didn\'t find that name in the group. "status" will show you all names in group'
    return msg

def getNumber(name):
    global people
    for k,v in people.items():
        if v.name == name and v.going:
            return True, k
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
    global announcements, people
    mode = people[user].mode
    if 'A' in mode:
        announcements.append(msg)
    pole = False
    if 'p' in mode:
        pole = True
        ending = currentPole.endPole(len(people))
    for k,v in people.items():
        if v.going and v.mode != 'r':
            if pole:
                if ending:
                    people[k].mode = 'h'
                else:
                    people[k].mode = 'p'
            if k == user:
                continue
            send(msg,k)
    return msg

def announceHistory(user):
    global announcements
    for msg in announcements:
        send(msg, user)
    if len(announcements) > 0:
        return "You should get the announcement's you've missed"
    return ""

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
        msg += '1,2,3,4,5,6,ect. to the amount of options or 1,2,3 to add only to those options (help prioritize your choices) or "none" for no choice\n'
        msg += 'If there is no list then only a yes or no is expected\n'
        msg += '"back" to start over questionnaire\n'
        msg += '"end" to leave if you changed you mind'
    elif 'v' in mode or 'q' in mode:
        msg += '"back" to not add this to sign up'
        if 'v' in mode:
            msg += '\n"end" to finish list of vote'
    elif 'p' in mode:
        if '1' in mode or '2' in mode:
            msg += '"back" to not send out this pole\n'
            msg += '"end" to finish list of options'
        else:
            msg += 'Your answer should just be the number of the option you choose\n'
            msg += '"back" cast no vote in the pole'
    elif 'P' in mode:
        msg += '"back" exit payment checklist mode'
    elif 'a' in mode:
        msg += '"back" stop adding number'
    elif 'A' in mode:
        msg += '"back" Exit announcement mode'
    elif 'm' in people[user].mode:
        msg += '"back" to stop messaging'
    elif people[user].going:
        if not people[user].paid and payment:
            msg += '"pay" to request Todd to check you off for paying everything. Send image proof to him directly\n'
        elif user == DAD:
            msg += '"pay" to check someone off for paying\n'
        msg += '"message" to begin message to someone\n'
        msg += '"status" to see people in the event'
        msg += ', your payment status ' if payment else ' '
        msg += 'and current results of all votes'
        msg += '. Type status and a name to see more specifics about them ("status zach")' if user == DAD else ""
        msg += '\n"add" to add someone to the group\n'
        if user == DAD or user == ADMIN:
            msg += '"announce" to send a message to everyone\n'
            msg += '"pole" to start a pole (e.g. dinner choices)\n'
        msg += '"end" to end the event for ' + ("everyone" if user == DAD else "yourself")
    return msg

def status(user, name):
    global people, Event, payment
    msg = ""
    if user == DAD or user == ADMIN:
        if name is not None:
            valid, number = getNumber(name)
            if valid:
                person = people[number]
                msg += name + ' is ' + '' if person.going else 'not ' + 'going\n'
                questions = [x.getText() for x in Event]
                for i in range(len(questions)):
                    msg += '\n' + questions[i] + ': ' + person.answers[i]
                return msg
            else:
                return "Name not found"

    if payment and user != DAD:
        msg += "You have " + "" if people[user].paid else " NOT " + "paid\n\n"

    msg += "Going:"
    for k,v in people.items():
        if people[k].going:
            msg += "\n" + v.name.title()

    if user == DAD or user == ADMIN:
        mylist = Event
    else:
        mylist = list(filter(lambda x: isinstance(x, Vote),Event))
    for event in mylist:
        msg += '\n\n' + event.getText()
        if isinstance(event, Vote):
            for i in range(len(event.options)):
                msg += '\n' + event.options[i] + ': ' + str(event.tally[i])
        elif isinstance(event, Question):
            msg += '\nYes: ' + str(event.yes) + "\nNo: " + str(event.no)
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

def announce(user):
    people[user].mode = 'A1'
    return "What would you like to message?"

def addVote(i):
    people[DAD].option = i
    people[DAD].mode = 'v1'
    if i > 0:
        return "Type now option " + str(i)
    else:
        return "Type now the theme of the selection"

def pole(i, user):
    people[user].option = i
    people[user].mode = 'pi1'
    if i > 0:
        return "Type now option " + str(i)
    else:
        return "What should the pole be about?"

def startOver(user):
    global people, Event
    answers = people[user].answers
    for i in range(len(answers)):
        if 'y' in answers[i]:
            Event[i].yes -= 1
        elif 'n' in answers[i]:
            Event[i].no -= 1
        else:
            Event[i].addTally(answers[i],True)

    people[user].option = 0
    people[user].answers = []
    return Event[people[user].option].text

def restart():
    global currentEvent, payment, people, Event, announcements
    currentEvent = False
    payment = False
    people = {DAD : Person('Todd', False, True)}
    Event = []
    announcements = []

def save():
    global currentEvent, payment, people, Event, announcements
    data = [currentEvent, payment, people, Event, announcements]
    with open("savefile.txt", 'w') as f:
        f.write(jsonpickle.encode(data))
    return "Saved"

def load():
    global currentEvent, payment, people, Event, announcements
    try:
        with open("savefile.txt", 'r') as f:
            data = jsonpickle.decode(f.readline())
        currentEvent = data[0]
        payment = data[1]
        people = data[2]
        Event = data[3]
        announcements = data[4]
        return "Loaded"
    except:
        return "Failed to load"

if __name__ == '__main__':
    app.run(debug=True)
