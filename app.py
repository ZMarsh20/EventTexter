import os
import random
import jsonpickle
from dotenv import load_dotenv

from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, redirect, url_for, render_template

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

class Contacts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    number = db.Column(db.String(15), unique=True, nullable=False)
class Courses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40))
    slopes = db.Column(db.String(40))
    ratings = db.Column(db.String(40))
    tees = db.Column(db.String(80))
    handicaps = db.Column(db.String(350))
    pars = db.Column(db.String(35))

class Person:
    def __init__(self,name,starting=True,dad=False):
        self.mode = ""
        if dad:
            self.mode = "s"
        self.buffer = ""
        self.option = 0
        self.lastScore = 0
        self.paid = False
        self.limitOutput = False
        self.name = name
        self.starting = starting
        self.going = dad
        self.answers = []
class Pole:
    def __init__(self):
        self.text = ""
        self.theme = ""
        self.winner = ""
        self.count = 0
        self.options = []
        self.tally = []
    def addTally(self,msg):
        try:
            if 0 < int(msg) <= len(self.options):
                self.count += 1
                self.tally[int(msg)-1] += 1
                return True
            return False
        except:
            return False
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
    def findWinner(self):
        winners = []
        for i in range(len(self.options)):
            if self.tally[i] == max(self.tally):
                winners.append(self.options[i])
        if len(winners) > 1:
            self.winner = "After a coinflip, " + random.choice(winners) + " wins the pole!"
            return True
        self.winner = winners[0] + " wins the pole!"
        return True
    def getText(self):
        return self.theme
    def setText(self):
        self.theme = self.options.pop(0)
        msg = self.theme
        for i in range(len(self.options)):
            msg += '\n' + str(i+1) + ". " + self.options[i]
        self.text = msg
class Game:
    def __init__(self, name, pars, tees, slopes, rating, handicaps):
        self.name = name
        self.pars = [int(i) for i in pars.split(',')]
        self.tees = tees.split(',')
        self.slopes = [int(i) for i in slopes.split(',')]
        self.rating = [float(i) for i in rating.split(',')]
        self.handicaps = handicaps.split(';')
        for _ in range(len(self.handicaps)):
            self.handicaps.append([int(x) for x in (self.handicaps.pop(0)).split(',')])
        self.scores = {}
        self.teams = []
    def broadcast(self):
        msg = "Here are the teams: \n"
        for team in self.teams:
            msg += ','.join([x.title() for x in team]) + '\n'
        broadcast(None, msg)
    def bestball(self):
        msg = "Best Ball:\n"
        if self.teams:
            for team in self.teams:
                bestball = []
                for i in range(18):
                    bestball.append(min([x[i] for x in team]))
            msg += ','.join([x.title() for x in team]) + ': ' + str(sum(bestball)) + '\n'
        bestball = []
        for i in range(18):
            bestball.append(min([x[i] for x in self.scores.values()]))
        msg += "Everyone: " + str(sum(bestball)) + '\n\n'
        return msg
    def pinkball(self):
        msg = ""
        if self.teams:
            msg += "Pink Ball:\n"
            for team in self.teams:
                pinkball = []
                for i in range(18):
                    score = self.scores[team[(i%len(team))]][i]
                    pinkball.append(score)
                msg += ','.join([x.title() for x in team]) + ': ' + str(sum(pinkball)) + '\n'
            msg += '\n'
        return msg
    def selectHandicaps(self, tees):
        i = currentGame.tees.index(tees)
        while self.handicaps[i][0] == 0:
            i += 1
        return i
    def setTeams(self,msg):
        global people
        self.teams = []
        if msg == 'random':
            temp = []
            for v in people.values():
                temp.append(v.name)
            if len(temp) < 6:
                return False
            random.shuffle(temp)
            case = len(temp) % 4
            group = 0
            team = []
            for name in temp:
                if case % 4 != 0 and team is None:
                    group += 1
                    case += 1
                team.append(name)
                group += 1
                if group == 4:
                    group = 0
                    self.teams.append(team)
                    team = []
            return True
        try:
            self.teams = msg.split(';')
            for _ in range(len(self.teams)):
                self.teams.append((self.teams.pop(0)).split(','))
            for team in self.teams:
                if len(team) < 2 or len(team) > 4:
                    self.teams = []
                    return False
            return True
        except:
            self.teams = []
            return False
    def skins(self):
        def format(v):
            val = v.split(',')
            if len(val) == 1:
                return v
            ret = ''
            dash = 0
            prev = val[0]
            for i in range(1,len(val)):
                if int(prev) == int(val[i])-1:
                    dash += 1
                    if dash == 2:
                        ret = ret[:-1] + '-'
                else:
                    dash = 0
                if dash < 2:
                    ret += prev + ','
                prev = val[i]
            return ret + val[i]
        msg = 'Skins:'
        skinCount = {}
        for i in range(18):
            name = ""
            val = 10
            cancel = False
            for k,v in self.scores.items():
                if v[i] < val:
                    name = k
                    val = v[i]
                    cancel = False
                elif v[i] == val:
                    cancel = True
            if not cancel:
                if name in skinCount:
                    skinCount[name] += ',' + str(i+1)
                else:
                    skinCount[name] = str(i+1)
        if skinCount is None:
            return 'No skins'
        for k,v in skinCount.items():
            msg += '\n' + k.title() + ': ' + format(v)
        return msg
    def standings(self):
        global people
        msg = "Scores:\n"
        for k,v in self.scores.items():
            val = int(sum(v))
            msg += k.title() + ": " + str(people[getNumber(k)[1]].lastScore) + ' for ' + str(val) + '\n'
        msg += self.pinkball()
        msg += self.bestball()
        msg += self.skins()
        return msg
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
    def addTally(self,msg,negate=False):
        val = 1
        if negate:
            val = -1
        if msg == 'none':
            return True
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
    def setText(self):
        self.theme = self.options.pop(0)
        msg = self.theme
        for i in range(len(self.options)):
            msg += '\n' + str(i+1) + ". " + self.options[i]
        self.text = msg

#DAD = os.getenv("DAD_NUM")
DAD = os.getenv("ADMIN_NUM")
ADMIN = os.getenv("ADMIN_NUM")
FAIL = 'Unrecognized response. Type "?" to see command options'
currentEvent = False
safetyPlug = False
payment = False
people = {DAD:Person('todd', False, True)}
Event = []
announcements = []
currentPole = None
currentGame = None
Welcome = "Hi there! I am Todd's birthday gift created by his incredibly gifted son. I am a chat bot here to " \
          "invite you to his latest shenanigans and keep things organized for him. Say yes to join :)"

@app.route('/', methods=['GET', 'POST'])
def score():
    global currentGame
    if currentGame is None:
        return "Sorry. It seems there is no game active :("
    if request.method == 'POST':
        name = request.form['name'].lower().strip()
        handicap = float(request.form['handicap'])
        tee = request.form['tees']
        holes = []
        for i in range(18):
            holes.append(int(request.form[('hole' + str(i))]))
        if getNumber(name)[0]:
            if dataEntered(handicap,holes,tee,name):
                msg = "Success :). Thanks " + name.title() + ". Your total today was "
                msg += str(people[getNumber(name)[1]].lastScore) + " and Net " + str(int(sum(currentGame.scores[name])))
                if len(currentGame.scores) == peopleGoing():
                    broadcast(None, currentGame.standings())
                    currentGame = None
                return msg
            msg = "That score is not realistic for the entered handicap. Round not entered. "
            msg += "If the score is accurate, ask admin to override before retrying"
            return msg
        return render_template("scores.html", courseName=currentGame.name.title(),
                                            tees=currentGame.tees,
                                            holes=holes,
                                            handicap=handicap,
                                            pars=currentGame.pars,
                                            nameFail=True)
    return render_template("scores.html", courseName=currentGame.name.title(),
                                        tees=currentGame.tees,
                                        holes=None,
                                        handicap=None,
                                        pars=currentGame.pars,
                                        nameFail=False)
def dataEntered(handicap,holes,tees,name):
    global currentGame, safetyPlug
    net = []
    i = currentGame.selectHandicaps(tees)
    additive = handicap // 18
    extra = handicap % 18
    for hole in range(18):
        netScore = holes[hole] - additive - (extra >= currentGame.handicaps[i][hole])
        if currentGame.pars[hole] + 2 < netScore:
            netScore = currentGame.pars[hole] + 2
        net.append(netScore)
    currentGame.scores[name] = net
    differential = sum(net) - courseHandicap(handicap,tees) - sum(currentGame.pars)
    if -10 < differential or safetyPlug:
        people[getNumber(name)[1]].lastScore = int(sum(net)) + courseHandicap(handicap,tees)
        return True
    return False
def courseHandicap(handicap,tees):
    global currentGame
    i = currentGame.tees.index(tees)
    plus = False
    if handicap < 0:
        plus = True
        handicap = -handicap
    val = round((handicap * currentGame.slopes[i])/113 + currentGame.rating[i] - sum(currentGame.pars))
    return -val if plus else val

@app.route('/text', methods=['GET', 'POST'])
def text():
    if request.method != 'POST':
        redirect(url_for('score'))
    incoming_msg = request.form['Body']
    incoming_number = request.form['From']
    resp = MessagingResponse()
    msg = resp.message()
    if incoming_number in people or incoming_number == ADMIN:
        msg.body(decode(incoming_number, incoming_msg))
    return str(resp)
def addNum(user):
    msg = "Got it"
    if user != DAD:
        send(DAD, "Please add " + people[user].buffer.title() + " - " + people[user].name.title())
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
            send(number, Welcome)
        else:
            return "They are already signed up for the event"
    clean(user)
    return msg
def addQuestion():
    people[DAD].mode = 'q1'
    return "Type now your yes or no question"
def addStepOne(user, msg):
    if len(msg) > 40:
        return "Name is to long please retype it. Try again"
    if ',' in msg:
        return "No commas allowed in name. Try again"
    people[user].buffer = msg
    if Contacts.query.filter_by(name=msg).first() is None:
        people[user].mode = 'a2'
        return "What's their number?"
    num = Contacts.query.filter_by(name=msg).first().number
    people[user].mode = 'a3'
    return "This name is already in the database. Add number ending in " + num[-4:]
def addVote(i):
    people[DAD].option = i
    people[DAD].mode = 'v1'
    if i > 0:
        return "Type now option " + str(i)
    return "Type now the theme of the selection"
def announce(user):
    people[user].mode = 'A1'
    return "What would you like to message?"
def announceHistory(user):
    global announcements
    for msg in announcements:
        send(user, msg)
    if len(announcements) > 0:
        return "You should get the announcement's you've missed"
    return ""
def broadcast(user, msg):
    global announcements, people
    pole = False
    if user:
        mode = people[user].mode
        if 'A' in mode:
            announcements.append(msg)
        if 'p' in mode:
            pole = True
            ending = currentPole.endPole(peopleGoing())
    for k,v in people.items():
        if k != user and v.going and v.mode != 'r':
            if pole:
                if ending:
                    people[k].mode = 'h'
                else:
                    people[k].mode = 'p'
            send(k, msg)
    return msg
def checkCourse(msg):
    global currentGame
    course = Courses.query.filter_by(name=msg).first()
    if course:
        currentGame = Game(course.name, course.pars, course.tees, course.slopes, course.ratings, course.handicaps)
        return True
    return False
def checkPerson(user, msg):
    mode = people[user].mode
    for k,v in people.items():
        if msg in v.name:
            if 'm' in mode:
                people[user].mode = 'm2'
                msg = "What would you like to send to " + v.name.title() + "?"
                people[user].buffer = k
            elif 'p' in mode:
                v.mode = 'p2'
                msg = "You want to check off " + v.name.title() + " for paying?"
            break
    else:
        msg = 'Didn\'t find that name in the group. "status" will show you all names in group'
    return msg
def clean(user):
    global currentPole
    mode = people[user].mode
    if 'p' in mode:
        if 'i' in mode:
            if '2' in mode:
                people[user].mode = 'p'
                currentPole.setText()
                return
            currentPole = None
        else:
            currentPole.count += 1
    if 'q' in mode or 'v' in mode:
        people[DAD].mode = 's'
        people[DAD].option = 0
        if 'v2' in mode:
            Event[-1].setText()
        else:
            Event.pop(-1)
            send(DAD, "Removed")
    elif 's' in mode:
        people[DAD].mode = 'h'
        return "Event set. Now you can add everyone to the event"
    elif people[user].going:
        people[user].mode = 'h'
    people[user].buffer = ""
def decode(user, oMsg):
    global currentEvent, payment, people, Event, announcements, currentPole, currentGame, safetyPlug
    msg = oMsg.lower().strip()
    mode = people[user].mode
    if len(msg) < 1:
        return FAIL
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
            people[user].mode = 'h'
            return 'Welcome. Type "?" to see your options' + announceHistory()
        elif not people[user].limitOutput:
            if 'n' == msg[0]:
                people[user].limitOutput = True
                return "Just reply 'y' if you change your mind"
            return "Only expecting 'y' or 'n'"
    if not people[user].going:
        return ""
    if msg == "?":
        return help(user)
    if msg == 'back':
        if 'r' in mode:
            return startOver(user)
        elif currentEvent or 's' not in mode:
            return clean(user)
        currentEvent = True
        return "Typing back again will finalize the event. Make sure you're ready"
    if 'a' in mode:
        if '1' in mode:
            return addStepOne(user, msg)
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
        return "Only expecting 'y' or 'n'"
    elif 'A' in mode:
        if '1' in mode:
            people[user].buffer = "Announcement: " + oMsg
            people[user].mode = 'A2'
            return "Announce this? " + oMsg
        if 'y' == msg[0]:
            broadcast(user, people[user].buffer)
            clean(user)
            return "Messages Sent"
        elif 'n' == msg[0]:
            return announce(user)
        return "Only expecting 'y' or 'n'"
    elif 'e' in mode:
        if 'y' in msg:
            if user == DAD or user == ADMIN:
                if '1' in mode:
                    people[user].mode = 'e2'
                    return "Double checking again because everything will be gone"
                restart()
                return "Ok then. Deleting..."
            people[user].going = False
            people[user].starting = True
            startOver(user)
            return "Just reply 'y' if you change your mind"
        clean(user)
        return 'Ok'
    elif 'g' in mode:
        return startGame(user, msg)
    elif 'h' in mode:
        if "add" in msg:
            if msg == "add":
                people[user].mode = 'a1'
                return "Who would you like to add?"
            try:
                name = msg.split(' ',1)[1]
                return addStepOne(user, name)
            except:
                return FAIL
        elif msg == "end":
            people[user].mode = 'e1'
            return "Are you sure you want to" + (" end " if user == DAD else " leave ") + "this event??"
        elif "message" in msg or "msg" in msg:
            people[user].mode = 'm1'
            if msg == 'message' or msg == 'msg':
                return "Who would you like to message?"
            try:
                name = msg.split(' ',1)[1]
                return checkPerson(name, user)
            except:
                clean(user)
                return FAIL
        elif msg == "pay" and payment:
            return pay(user)
        elif "status" in msg:
            if msg == "status":
                return status(user, None)
            elif user == DAD:
                try:
                    name = msg.split(' ',1)[1]
                    return status(user,name)
                except:
                    return FAIL
        elif user == DAD or user == ADMIN:
            if currentEvent:
                if msg == "announce":
                    return announce(user)
                elif "play" in msg:
                    if msg == 'play':
                        people[user].mode = 'g'
                        return "What course?"
                    try:
                        msg = msg.split(' ',1)[1]
                        return startGame(user, msg)
                    except:
                        return FAIL
                elif msg == "pole":
                    currentPole = Pole()
                    return pole(user, 0)
                elif msg == "pullsafetyplug":
                    safetyPlug = not safetyPlug
                    return "un" if safetyPlug else "" + "plugged"
                elif "teams" in msg and currentGame:
                    try:
                        teams = msg.split(' ',1)[1].split(';')
                        if teams[0] != 'random':
                            for team in teams:
                                for t in team.split(','):
                                    if not getNumber(t)[0]:
                                        return t + " is not found"
                        if currentGame.setTeams(msg.split(' ',1)[1]):
                            currentGame.broadcast()
                            return "Teams set"
                        return "Team setup unsuccessful"
                    except:
                        return FAIL

    elif 'm' in mode:
        if '1' in mode:
            return checkPerson(msg, user)
        send(people[user].buffer, (people[user].name.title() + " says:\n" + msg))
        clean(user)
        return "Message sent"
    elif 'p' in mode:
        if 'i' in mode:
            if msg == 'end':
                people[user].mode = 'pi2'
                clean(user)
                return "Pole is now running. Cast your vote too\n" + broadcast(user, currentPole.text)
            i = people[user].option
            currentPole.options.append(people[user].buffer)
            currentPole.tally.append(0)
            return pole(user, i + 1)
        if currentPole.addTally(msg):
            msg = "Your vote has been cast"
            if currentPole.endPole(peopleGoing()):
                msg = broadcast(user, currentPole.winner)
                currentPole = None
            return msg
        return 'Not valid. "?" for help'
    elif 'P' in mode:
        present, num = getNumber(msg)
        people[DAD].mode = 'h'
        if present:
            people[num].paid = not people[num].paid
            return msg.title() + " has been marked as " + ("" if people[num].paid else "not") + "paid"
        return 'Name not found in group. Type "status" to see all who are present'
    elif 'q' in mode:
        if '1' in mode:
            people[DAD].mode = 'q2'
            people[DAD].buffer = oMsg
            return "Are you sure that you want to ask: " + oMsg
        if 'y' == msg[0]:
            people[DAD].mode = 's'
            Event[-1].text = people[DAD].buffer
            people[DAD].buffer = ''
            return "Question now in sign up"
        elif 'n' == msg[0]:
            return addQuestion()
        return "Only expecting 'y' or 'n'"
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
            return "Only expecting 'y' or 'n'"
        people[user].answers.append(msg)
        people[user].option += 1
        if i+1 >= len(Event):
            clean(user)
            return 'Thank you. Type "?" for your options\n' + announceHistory(user)
        msg = Event[people[user].option].text
        return "Answer locked in. Next question:\n" + msg
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
    elif 'v' in mode:
        if msg == 'end':
            clean(DAD)
            return "Vote set for sign up"
        i = people[DAD].option
        Event[-1].options.append(oMsg)
        Event[-1].tally.append(0)
        return addVote(i+1)
    return FAIL
def getNumber(name):
    global people
    for k,v in people.items():
        if v.name == name and v.going:
            return True, k
    return False, ""
def help(user):
    mode = people[user].mode
    msg = '"?" shows available commands\n'
    if 'a' in mode:
        msg += '"back" stop adding number'
    elif 'A' in mode:
        msg += '"back" Exit announcement mode'
    elif 'h' in mode:
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
    elif 'm' in people[user].mode:
        msg += '"back" to stop messaging'
    elif 'p' in mode:
        if '1' in mode or '2' in mode:
            msg += '"back" to not send out this pole\n'
            msg += '"end" to finish list of options'
        else:
            msg += 'Your answer should just be the number of the option you choose\n'
            msg += '"back" cast no vote in the pole'
    elif 'P' in mode:
        msg += '"back" exit payment checklist mode'
    elif 'q' in mode or 'v' in mode:
        msg += '"back" to not add this to sign up'
        if 'v' in mode:
            msg += '\n"end" to finish list of vote'
    elif 'r' in mode:
        msg += 'If there is a list with numbers then expected replies are as follows:\n'
        msg += '1,2,3,4,5,6,ect. to the amount of options or 1,2,3 to add only to those options (help prioritize your choices) or "none" for no choice\n'
        msg += 'If there is no list then only a yes or no is expected\n'
        msg += '"back" to start over questionnaire\n'
        msg += '"end" to leave if you changed you mind'
    elif 's' in mode:
        msg += '"question" to add a yes or no question when signing up\n'
        msg += '"vote" to add a vote when signing up\n'
        msg += '"pay" change whether or not you are expecting payment\n'
        msg += '"back" to end sign up and start adding people\n'
        msg += '"end" to restart'
    return msg
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
def pay(user):
    if user == DAD:
        people[DAD].mode = 'P'
        return "Who would you like to check off as paid?"
    send(DAD, people[user].name.title() + ' says they have paid. Type "pay" to check someone off for paying')
    return "Request sent. Send Todd a screenshot or image of your payment just in case he's drunk :)"
def peopleGoing():
    global people
    count = 0
    for v in people.values():
        if v.going:
            count += 1
    return count
def pole(user, i):
    people[user].option = i
    people[user].mode = 'pi1'
    if i > 0:
        return "Type now option " + str(i)
    return "What should the pole be about?"
def restart():
    global currentEvent, payment, people, Event, announcements, currentPole, currentGame
    currentEvent = False
    payment = False
    people = {DAD : Person('Todd', False, True)}
    Event = []
    announcements = []
    currentPole = None
    currentGame = None
def save():
    global currentEvent, payment, people, Event, announcements
    data = [currentEvent, payment, people, Event, announcements]
    with open("savefile.txt", 'w') as f:
        f.write(jsonpickle.encode(data))
    return "Saved"
def send(user, msg):
    return twilio_api.messages.create(body=msg, from_=TWILIO_NUM, to=user)
def startGame(user, msg):
    clean(user)
    if checkCourse(msg):
        msg = "Game started. Enter game information at http://zmarshall.pythonanywhere.com/. Good luck!"
        return broadcast(user, msg)
    return "Course not found"
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
def status(user, name):
    global people, Event, payment
    msg = ""
    if user == DAD or user == ADMIN:
        if name:
            valid, number = getNumber(name)
            if valid:
                person = people[number]
                msg += name + ' is ' + '' if person.going else 'not ' + 'going\n'
                questions = [x.getText() for x in Event]
                for i in range(len(questions)):
                    msg += '\n' + questions[i] + ': ' + person.answers[i]
                return msg
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

if __name__ == '__main__':
    app.run()

# Legend
# a = add person
# A = announce
# e = end
# g = golf game
# h = home
# m = message
# p = pole mode
# pi = pole initiate
# P = pay mode
# q = question
# r = ramp up
# s = start
# v = vote set up or vote
