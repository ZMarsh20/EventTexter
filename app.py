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
        self.paid = dad
        self.rejected = False
        self.name = name.lower()
        self.starting = starting
        self.going = dad
        self.answers = []
class Poll:
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
    def endpoll(self, users):
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
            self.winner = "After a coinflip, " + random.choice(winners) + " wins the poll!"
            return True
        self.winner = winners[0] + " wins the poll!"
        return True
    def getText(self):
        return self.theme
    def setText(self):
        self.theme = self.options.pop(0)
        msg = self.theme
        for i in range(len(self.options)):
            msg += '\n' + str(i+1) + ". " + self.options[i]
        self.text = "New Poll!\n" + msg
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
        self.holeCount = len(self.pars)
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
                for i in range(currentGame.holeCount):
                    bestball.append(min([self.scores[x][i] for x in team]))
                msg += ','.join([x.title() for x in team]) + ': ' + str(int(sum(bestball))) + '\n'
        bestball = []
        for i in range(currentGame.holeCount):
            bestball.append(min([x[i] for x in self.scores.values()]))
        msg += "Everyone: " + str(sum(bestball)) + '\n\n'
        return msg
    def pinkball(self):
        msg = ""
        if self.teams:
            msg += "Pink Ball:\n"
            for team in self.teams:
                pinkball = []
                for i in range(currentGame.holeCount):
                    score = self.scores[team[(i%len(team))]][i]
                    pinkball.append(score)
                msg += ','.join([x.title() for x in team]) + ': ' + str(int(sum(pinkball))) + '\n'
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
                if case % 4 != 0 and not team:
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
        for i in range(currentGame.holeCount):
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
        if not skinCount:
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
        msg += '\n'
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
    def setText(self):
        return
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
        votes = msg.split(',')
        for i in range(len(votes)):
            self.tally[i] += int(votes[i]) * val
    def getText(self):
        return self.theme
    def setText(self):
        self.theme = self.options.pop(0)
        msg = self.theme
        for i in range(len(self.options)):
            msg += '\n' + str(i+1) + ". " + self.options[i]
        self.text = msg

DAD = os.getenv("DAD_NUM")
ADMIN = os.getenv("ADMIN_NUM")
FAIL = 'Unrecognized command. Type "?" to see command options'
ROUTE = 'http://zmarshall.pythonanywhere.com/'
currentEvent, safetyPlug, payment, loaded, finalized = False, False, False, False, False
people = {DAD:Person('todd m', False, True)}
newCourse = {'n':'', 't':[], 'p':[], 'h':[], 's':[], 'r':[]}
Events, announcements = [], []
currentPoll, currentGame = None, None
Schedule = "No schedule set yet"
Welcome = "Hey it's Todd here! I am Todd's birthday gift created by his incredibly gifted son. I am a texting program here to " \
          "invite you to his latest shenanigans and keep things organized for him. This is the first run of this app" \
          " so constructive criticism is encouraged. Say yes to join :)"

@app.route('/help/<code>', methods=['GET', 'POST'])
def helpRoute(code):
    global people
    for user,peep in people.items():
        if peep.buffer == code:
            return help(user).replace('\n','<br>')
    return "I can't help you unfortunately. Please request a new link"
@app.route('/score', methods=['GET', 'POST'])
def score():
    global currentGame
    if currentGame is None:
        return "Sorry. It seems there is no game active :("
    if request.method == 'POST':
        name = request.form['name'].lower().strip()
        tee = request.form['tees']
        handicap = courseHandicap(float(request.form['handicap']),tee)
        holes = []
        for i in range(currentGame.holeCount):
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
    holeCount = currentGame.holeCount
    net = []
    i = currentGame.selectHandicaps(tees)
    additive = handicap // holeCount
    extra = handicap % holeCount
    for hole in range(holeCount):
        netScore = holes[hole] - additive - (extra >= currentGame.handicaps[i][hole])
        if currentGame.pars[hole] + 2 < netScore:
            netScore = currentGame.pars[hole] + 2
        net.append(netScore)
    currentGame.scores[name] = net
    differential = sum(net) - sum(currentGame.pars)
    if -10 < differential or safetyPlug:
        people[getNumber(name)[1]].lastScore = int(sum(net)) + handicap
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
    if currentGame.holeCount == 9:
        val /= 2
    return -val if plus else val
@app.route('/signup/<code>', methods=['GET', 'POST'])
def signupRoute(code):
    global people, Events
    if request.method == 'POST' and code == '0':
        user = request.form['user']
        count = 0
        for event in Events:
            count += 1
            if isinstance(event, Vote):
                msg = ""
                for i in range(len(event.options)):
                    msg += request.form[str(count)+'[' + str(i) + ']'] + ','
                msg = msg[:-1]
                event.addTally(msg)
            else:
                if request.form.get(str(count)):
                    msg = 'yes'
                    event.yes += 1
                else:
                    msg = 'no'
                    event.no += 1
            people[user].answers.append(msg)
        clean(user)
        return 'All signed in! "?" for options. ' + announceHistory(user)
    else:
        for user,peep in people.items():
            if peep.buffer == code:
                questions = []
                for event in Events:
                    if isinstance(event, Vote):
                        temp = event.options[:]
                        temp.insert(0,event.theme)
                        questions.append(temp)
                    else:
                        questions.append(event.text)
                return render_template("signup.html",user=user,questions=questions)
        return "I can't help you unfortunately. Please request a new link"
@app.route('/answers/<code>', methods=['GET', 'POST'])
def statusRoute(code):
    global people
    for user,peep in people.items():
        if peep.buffer == code:
            return answers().replace('\n','<br>')
    return "I can't help you unfortunately"

@app.route('/text', methods=['GET', 'POST'])
def text():
    global loaded
    if request.method != 'POST':
        redirect(url_for('score'))
    incoming_msg = request.form['Body']
    incoming_number = request.form['From']
    if not loaded:
        load('current')
        loaded = True
    if incoming_number in people or incoming_number == ADMIN:
        try:
            resp = MessagingResponse()
            msg = resp.message()
            msg.body(decode(incoming_number, incoming_msg))
            return str(resp)
        except Exception as e:
            send(ADMIN, str(e))
    return ':3'
def addAll():
    global people
    peeps = Contacts.query.all()
    msg = "Added:"
    for peep in peeps:
        if peep.number not in people:
            msg += '\n' + peep.name.title()
            people[peep.number] = Person(peep.name)
            send(peep.number, Welcome)
    return msg
def addCourse():
    global newCourse, safetyPlug
    if checkCourse(newCourse['n']):
        return "Name already in database"
    if max(newCourse['p']) > 5 + safetyPlug or min(newCourse['p']) < 3:
        return "Pars don't make sense"
    handicaps = []
    for i in range(len(newCourse['h'])):
        handicaps.append(",".join([str(x) for x in newCourse['h'][i]]))
        if newCourse['h'][i] != [0] and (max(newCourse['h'][i]) > 18 or min(newCourse['h'][i]) < 1):
            return "Handicaps don't make sense"
    if max(newCourse['r']) > 90 or min(newCourse['r']) < 50:
        return "Ratings don't make sense"
    if max(newCourse['s']) > 155 or min(newCourse['s']) < 55:
        return "Slopes don't make sense"
    if not len(newCourse['t']) == len(newCourse['s']) == len(newCourse['r']) == len(newCourse['h']):
        return "All entries should have same length"
    if len(newCourse['p']) != len(newCourse['h'][i]):
        return "handicaps and pars don't match"
    course = Courses(name=newCourse['n'],
                     tees=",".join(newCourse['t']),
                     slopes=",".join([str(x) for x in newCourse['s']]),
                     ratings=",".join([str(x) for x in newCourse['r']]),
                     pars=",".join([str(x) for x in newCourse['p']]),
                     handicaps=";".join(handicaps))
    db.session.add(course)
    db.session.commit()
    return "Course successfully added"
def addNum(user):
    msg = "Got it"
    if user != DAD and user != ADMIN:
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
            msg = "They are already signed up for the event"
    clean(user)
    return msg
def addItinerary(user):
    people[user].mode = 'I1'
    return "What should be the itinerary?"
def addQuestion():
    people[DAD].mode = 'q1'
    return "Type now your yes or no question"
def addStepOne(user, msg):
    global people
    if len(msg) > 40:
        return "Name is to long please retype it. Try again"
    elif ',' in msg:
        return "No commas allowed in name. Try again"
    if user == DAD and msg == "all":
        people[DAD].mode = 'a4'
        return "Add everyone that's in the database?"
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
    if announcements:
        return "You should get the announcement's you've missed"
    return ""
def answers():
    global people
    msg = 'People going:\n'
    for person in people.values():
        if person.answers or person == people[DAD]:
            msg += person.name.title() + '\n'
    msg += "\nPeople interested:\n"
    for person in people.values():
        if person.going and not person.answers and person != people[DAD]:
            msg += person.name.title() + '\n'
    msg += '\nPeople unresponsive:\n'
    for person in people.values():
        if person.starting and not person.rejected:
            msg += person.name.title() + '\n'
    msg += '\nPeople declined:\n'
    for person in people.values():
        if person.rejected:
            msg += person.name.title() + '\n'
    msg += '\n'
    for event in Events:
        msg += event.getText()
        if isinstance(event, Vote):
            for i in range(len(event.options)):
                msg += '\n' + event.options[i] + ': ' + str(event.tally[i])
        elif isinstance(event, Question):
            msg += '\nYes: ' + str(event.yes) + "\nNo: " + str(event.no)
        msg += '\n\n'
    for person in people.values():
        if person != people[DAD]:
            if person.rejected:
                msg += person.name.title() + " doesn't want to go or can't go"
            elif person.answers:
                msg += person.name.title() + ' would like to go\n'
                if payment:
                    msg += 'Has ' + ('' if person.paid else 'not ') + 'paid'
                questions = [x.getText() for x in Events]
                for i in range(len(questions)):
                    msg += '\n' + questions[i] + ': ' + person.answers[i]
            elif person.going:
                msg += person.name.title() + " hasn't filled out the sheet"
            else:
                msg += person.name.title() + " hasn't yet responded"
            msg += '\n\n'
    return msg
def broadcast(user, msg):
    global announcements, people
    poll = False
    if user:
        mode = people[user].mode
        if 'A' in mode:
            announcements.append(msg)
        if 'p' in mode:
            poll = True
            ending = currentPoll.endpoll(peopleGoing())
    for k,v in people.items():
        if k != user and v.going and v.mode != 'r':
            if poll:
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
    global people
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
        people[user].mode = 'h'
        msg = 'Didn\'t find that name in the group. "status" will show you all names in group'
    return msg
def clean(user):
    global currentPoll, people
    mode = people[user].mode
    if 'p' in mode:
        if 'i' in mode:
            if '2' in mode:
                people[user].mode = 'p'
                currentPoll.setText()
                return
            currentPoll = None
        else:
            currentPoll.count += 1
    if 'q' in mode or 'v' in mode:
        people[DAD].mode = 's'
        people[DAD].option = 0
        if '2' in mode:
            Events[-1].setText()
        else:
            Events.pop(-1)
            send(DAD, "Removed")
    elif 's' in mode:
        people[DAD].mode = 'h'
        save('current')
        return "Event set. Now you can add everyone to the event"
    elif people[user].going:
        people[user].mode = 'h'
    people[user].buffer = ""
    save('current')
    return 'Ok'
def decode(user, oMsg):
    global currentEvent, payment, people, Events, announcements, currentPoll, currentGame, safetyPlug, Schedule, newCourse
    msg = oMsg.lower().strip()
    try:
        mode = people[user].mode
    except:
        if user == ADMIN:
            mode = 'h'
        else:
            return "Not Invited :("

    if user == ADMIN:
        if msg == 'save':
            return save('savefile')
        elif msg == 'load':
            return load('savefile')
        elif msg == "add self" and ADMIN not in people:
            people[ADMIN] = Person("zach")
            return clean(user)
    if len(msg) < 1:
        return FAIL
    if people[user].starting:
        if 'y' == msg[0]:
            people[user].going = True
            people[user].starting = False
            if Events and not finalized:
                people[user].mode = 'r'
                code = getCode()
                people[user].buffer = code
                send(user,(ROUTE+'signup/' + code))
                return "Welcome! You should have a link to the sign in sheet now"
            clean(user)
            return 'Welcome. Type "?" to see your options' + announceHistory(user)
        elif not people[user].rejected:
            if 'n' == msg[0]:
                people[user].rejected = True
                save('current')
                return "Just reply 'y' if you change your mind"
            return "Only expecting 'yes' or 'no'"
    if not people[user].going:
        return ""
    if msg == "?":
        if 'h' in mode or 's' in mode:
            code = getCode()
            people[user].buffer = code
            return ROUTE + "help/" + code
        return help(user)
    if msg == 'back':
        if currentEvent:
            return clean(user)
        currentEvent = True
        return "Typing back again will finalize the event. Make sure you're ready"
    if 'a' in mode:
        if '1' in mode:
            return addStepOne(user, msg)
        elif '4' in mode:
            if 'y' == msg[0]:
                clean(DAD)
                return addAll()
            elif 'n' == msg[0]:
                clean(DAD)
                return "Ok"
        if 'y' == msg[0] or '2' in mode:
            if '2' in mode:
                num = ''.join(list(filter(lambda x: x.isdigit(), msg.removeprefix('+1'))))
                if len(num) != 10:
                    return "Phone number must be exactly 10 numbers"
                people[user].buffer += ',+1' + num
            else:
                people[user].buffer += ',' + Contacts.query.filter_by(name=people[user].buffer).first().number
            return addNum(user)
        elif 'n' == msg[0]:
            clean(user)
            return "Maybe add last name and try again"
        return "Only expecting 'yes' or 'no'"
    elif 'A' in mode:
        if '1' in mode:
            people[user].buffer = "Announcement: " + oMsg
            people[user].mode = 'A2'
            return "Announce this?\n" + oMsg
        if 'y' == msg[0]:
            broadcast(user, people[user].buffer)
            clean(user)
            return "Messages Sent"
        elif 'n' == msg[0]:
            return announce(user)
        return "Only expecting 'yes' or 'no'"
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
            people[user].rejected = True
            startOver(user)
            save('current')
            return "Just reply 'y' if you change your mind"
        clean(user)
        return 'Ok'
    elif 'g' in mode:
        return startGame(user, msg)
    elif 'h' in mode:
        people[user].buffer = ""
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
                return checkPerson(user, name)
            except:
                clean(user)
                return FAIL
        elif msg == "pay" and payment:
            return pay(user)
        elif "schedule" in msg:
            if msg == "schedule":
                return Schedule
            elif (user == DAD or user == ADMIN) and msg == "set schedule":
                return addItinerary(user)
        elif msg == "status":
            if user == DAD or user == ADMIN:
                code = getCode()
                people[user].buffer = code
                return ROUTE + "answers/" + code
            return status(user)
        elif (user == DAD or user == ADMIN) and currentEvent:
            if msg == "announce":
                return announce(user)
            elif msg == 'finalize':
                return finalize()
            elif "kick" in msg:
                if msg == "kick":
                    people[user].mode = 'k1'
                    return "Who would you like to remove?"
                try:
                    name = msg.split(' ',1)[1]
                    return kickStepOne(user, name)
                except:
                    return FAIL
            elif msg == 'new course':
                people[user].mode = 'n1'
                msg = "What is the name of the course?"
                return msg
            elif "play" in msg:
                if msg == 'play':
                    people[user].mode = 'g'
                    return "What course?"
                try:
                    msg = msg.split(' ',1)[1]
                    return startGame(user, msg)
                except:
                    return FAIL
            elif msg == "poll":
                people[user].mode = 'p'
                if currentPoll is not None:
                    currentPoll.findWinner()
                    msg = broadcast(user, currentPoll.winner)
                    currentPoll = None
                    clean(user)
                    return msg
                currentPoll = Poll()
                return poll(user, 0)
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
            elif msg == "waiting" and currentPoll:
                msg = "Waiting on:"
                for peep in people.values():
                    if 'p' in peep.mode:
                        msg += '\n' + peep.name.title()
                return msg
    elif 'I' in mode:
        if '1' in mode:
            people[user].mode = 'I2'
            people[user].buffer = oMsg
            return "This is what will be seen:\n " + oMsg
        if 'y' == msg[0]:
            Schedule = people[user].buffer
            clean(user)
            return "Itinerary set"
        elif 'n' == msg[0]:
            return addItinerary(user)
        return "Only expecting 'yes' or 'no'"
    elif 'k' in mode:
        if '1' in mode:
            return kickStepOne(user, msg)
        if '2' in mode:
            if 'y' == msg[0]:
                peep = getNumber(people[user].buffer)[1]
                send(peep, "You have been removed from the group. Text Todd directly if you want back in")
                startOver(peep)
                del people[peep]
                clean(user)
                return "Removed them from the event"
            elif 'n' == msg[0]:
                return clean(user)
            return "Only expecting 'yes' or 'no'"
    elif 'm' in mode:
        if '1' in mode:
            return checkPerson(user, msg)
        send(people[user].buffer, (people[user].name.title() + " says:\n" + msg))
        clean(user)
        return "Message sent"
    elif 'n' in mode:
        if '1' in mode:
            newCourse['n'] = msg
            people[user].mode = 'n2'
            return newCourse['n'] + " will be the name. What are the tee options?"
        elif '2' in mode:
            try:
                newCourse['t'] = [x.strip().lower() for x in msg.split(',')]
            except:
                return "Text must be comma separated"
            people[user].mode = 'n3'
            return " ".join(newCourse['t']) + " will be the tees. What are the tee respective slopes?"
        elif '3' in mode:
            try:
                newCourse['s'] = [int(x.strip().lower()) for x in msg.split(',')]
            except:
                return "Text must be comma separated numbers"
            people[user].mode = 'n4'
            return " ".join([str(x) for x in newCourse['s']]) + " will be the slopes. What are the tee respective ratings?"
        elif '4' in mode:
            try:
                newCourse['r'] = [float(x.strip().lower()) for x in msg.split(',')]
            except:
                return "Text must be comma separated numbers"
            people[user].mode = 'n5'
            return " ".join([str(x) for x in newCourse['r']]) + " will be the ratings. What are the tee respective hole handicaps?"
        elif '5' in mode:
            try:
                newCourse['h'] = [[int(x.strip().lower()) for x in holes.split(',')] for holes in msg.split(';')]
            except:
                return "Text must be comma separated holes and semi-colon separated sets"
            people[user].mode = 'n6'
            return msg.replace(';',' ') + " will be the hole handicaps. What are the tee respective pars?"
        elif '6' in mode:
            try:
                newCourse['p'] = [int(x.strip().lower()) for x in msg.split(',')]
            except:
                return "Text must be comma separated numbers"
            people[user].mode = 'n7'
            return " ".join([str(x) for x in newCourse['p']]) + " will be the pars. Are the course specs correct?"
        elif '7' in mode:
            if 'y' == msg[0]:
                clean(user)
                return addCourse()
            else:
                return 'Either send "yes" to confirm or "back" to quit out and try again'
    elif 'p' in mode:
        if currentPoll is None:
            people[user].mode = 'h'
            return decode(user, oMsg)
        if 'i' in mode:
            if msg == 'end':
                people[user].mode = 'pi2'
                clean(user)
                return "Poll is now running. Cast your vote too\n" + broadcast(user, currentPoll.text)
            i = people[user].option
            currentPoll.options.append(oMsg)
            currentPoll.tally.append(0)
            return poll(user, i + 1)
        if currentPoll.addTally(msg):
            msg = "Your vote has been cast"
            if currentPoll.endpoll(peopleGoing()):
                msg = broadcast(user, currentPoll.winner)
                currentPoll = None
            people[user].mode = 'h'
            return msg
        return 'Not valid. "?" for help'
    elif 'P' in mode:
        present, num = getNumber(msg)
        clean(DAD)
        if present:
            people[num].paid = not people[num].paid
            return msg.title() + " has been marked as " + ("" if people[num].paid else "not") + "paid"
        return 'Name not found in group. Type "status" to see all who are present'
    elif 'q' in mode:
        if '1' in mode:
            people[DAD].mode = 'q3'
            people[DAD].buffer = oMsg
            return "Are you sure that you want to ask:\n" + oMsg
        if 'y' == msg[0]:
            Events[-1].text = people[DAD].buffer
            people[DAD].mode = 'q2'
            clean(DAD)
            return "Question now in sign up"
        elif 'n' == msg[0]:
            return addQuestion()
        return "Only expecting 'yes' or 'no'"
    elif 'r' in mode:
        if msg == "end":
            clean(user)
            people[user].going = False
            people[user].starting = True
            people[user].rejected = True
            return "Just reply 'y' if you change your mind"
        elif msg == "link":
            code = getCode()
            people[user].buffer = code
            return ROUTE+'signup/' + code
    elif 's' in mode:
        if msg == "question":
            Events.append(Question())
            return addQuestion()
        elif msg == "vote":
            Events.append(Vote())
            return addVote(0)
        elif msg == "pay":
            payment = not payment
            msg = 'Now party members'
            msg += ' ' if payment else " don't "
            msg += 'need to keep track of payment'
            return msg
        elif msg == "end":
            restart()
            return "You now have a clean slate"
        elif msg == 'status':
            return showQuestions()
    elif 'v' in mode:
        if msg == 'end':
            people[DAD].mode = 'v2'
            clean(DAD)
            return "Vote set for sign up"
        i = people[DAD].option
        Events[-1].options.append(oMsg)
        Events[-1].tally.append(0)
        return addVote(i+1)
    return FAIL
def finalize():
    global people
    peeps = ''
    msg = "The event is now finalized so you can't join anymore. Sorry you couldn't make it."
    msg += " You'll need to text Todd directly if you want back in now"
    for k,v in dict(people).items():
        if not v.going:
            send(k,msg)
            peeps += '\n' + v.name.title()
            del people[k]
    if peeps:
        return 'Removed: ' + peeps
    return 'No one removed'
def getCode():
    global people
    while True:
        code = random.randint(1000000,9999999)
        for peep in people.values():
            if peep.buffer == code:
                break
        else:
            break
    return str(code)
def getNumber(name):
    global people
    for k,v in people.items():
        if v.name == name:
            return v.going, k
    return False, ""
def help(user):
    mode = people[user].mode
    msg = '"?" shows available commands. Commands are NOT case sensitive.\n'
    if 'a' in mode:
        msg += '\n"back" to no longer add a number.'
    elif 'A' in mode:
        msg += '\n"back" to no longer make an announcement.'
    elif 'h' in mode:
        if currentGame:
            msg += '\n"link" to get a new link to enter scores.\n'
        if payment:
            if not people[user].paid:
                msg += '\n"pay" to request Todd to check you off for paying everything. Send image proof to him directly.\n'
            elif user == DAD:
                msg += '\n"pay" to check someone off for paying.\n'
        msg += '\n"message" or "msg" to begin messaging to someone on the going list.'
        msg += ' Add a name for a shortcut: "Msg todd". Type status to see name list.\n'
        msg += '\n"add" to add someone to the group. Add a name for a shortcut: "Add todd".\n'
        msg += '\n"schedule" to see what is posted to the schedule.\n'
        msg += '\n"status" to see people in the event'
        msg += ', current answers to all questions' if user == DAD else ''
        msg += ' and your payment status. ' if payment else '. '
        if user == DAD or user == ADMIN:
            msg += '\n"announce" to send a message to everyone. ' \
                   'These will also be sent to members that arrive after you send the announcement\n'
            msg += '\n"poll" to start a poll or end one early.'
            msg += '\n"waiting" to get a list of people that have yet to vote in a poll if there is one.\n'
            msg += '\n"set schedule" to set and reset the schedule. This is a place to house tee times or' \
                   ' something of the sort. Could hold any information you want though.\n'
            msg += '\n"kick" to remove a player from the event. Add a name for a shortcut: "Kick zach".\n'
            msg += '\n"finalize" will kick all the people that are not planning on going to the event\n'
            if currentGame:
                msg += '\n"teams <teams>" to make the teams. Must either be manually entered: Teams zach,todd;dana,jim\n'
                msg += '(Notice how each team is separated by a ";" and each player is separated by ",")\n'
                msg += 'Or, if there\'s at least 6 players: Teams random\n'
                msg += 'Teams can be recreated each time if needed\n'
            else:
                msg += '\n"play" to start playing a golf course. Add the name for a shortcut: "Play Dos Rios"\n'
        else:
            msg += '\n'
        msg += '\n"end" to end the event for ' + ("everyone" if user == DAD else "yourself")
    elif 'I' in mode:
        msg += '\n"back" to no longer make changes the schedule page.'
    elif 'k' in mode:
        msg += '\n"back" stop kicking mode.'
    elif 'm' in mode:
        msg += '\n"back" to stop messaging.'
    elif 'n' in mode:
        msg += '\n"back" to stop adding course.'
    elif 'p' in mode:
        if '1' in mode or '2' in mode:
            msg += '\n"back" to not send out this poll\n'
            msg += '\n"end" to finish list of options'
        else:
            msg += '\nYour answer should just be the number of the option you choose\n'
            msg += '\n"back" cast no vote in the poll'
    elif 'P' in mode:
        msg += '\n"back" exit payment checklist mode'
    elif 'q' in mode or 'v' in mode:
        msg += '\n"back" to not add this to sign up'
        if 'v' in mode:
            msg += '\n\n"end" to finish list of vote'
    elif 'r' in mode:
        msg += '\n"link" to send yourself the link again\n'
        msg += '\n"end" if you change your mind and don\'t want to sign up'
    elif 's' in mode:
        msg += '\n"question" to add a yes or no question when signing up\n'
        msg += '\n"vote" to add a vote when signing up\n'
        msg += '\n"pay" change whether or not you are expecting payment from everyone\n'
        msg += '\n"status" to see what questions have been added to the event so far\n'
        msg += '\n"back" to end sign up and start adding people\n'
        msg += '\n"end" to restart the questionnaire'
    return msg
def kickStepOne(user, msg):
    global people
    people[user].buffer = msg
    for val in people.values():
        if msg == val.name:
            people[user].mode = 'k2'
            return "Remove " + msg.title() + '?'
    else:
        clean(user)
        return "Name not in event"
def load(s):
    global currentEvent, payment, people, Events, announcements, Schedule, finalized
    try:
        with open(s + ".txt", 'r') as f:
            data = jsonpickle.decode(f.readline())
        currentEvent = data[0]
        payment = data[1]
        people = dict(sorted(data[2].items(),key=lambda x: x[1].name))
        Events = data[3]
        announcements = data[4]
        Schedule = data[5]
        finalized = data[6]
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
def poll(user, i):
    people[user].option = i
    people[user].mode = 'pi1'
    if i > 0:
        return "Type now option " + str(i)
    return "What should the poll be about?"
def restart():
    global currentEvent, payment, people, Events, announcements, currentPoll, currentGame
    currentEvent = False
    payment = False
    people = {DAD : Person('Todd', False, True)}
    Events = []
    announcements = []
    currentPoll = None
    currentGame = None
def save(s):
    global currentEvent, payment, people, Events, announcements, Schedule, finalized
    data = [currentEvent, payment, people, Events, announcements, Schedule, finalized]
    with open(s + ".txt", 'w') as f:
        f.write(jsonpickle.encode(data))
    return "Saved"
def send(user, msg):
    try:
        return twilio_api.messages.create(body=msg, from_=TWILIO_NUM, to=user)
    except:
        return False
def showQuestions():
    global Events
    msg = ""
    for event in Events:
        msg += event.getText() + '\n'
    return msg
def startGame(user, msg):
    clean(user)
    if checkCourse(msg):
        msg = "Game started. Enter game information at " + ROUTE + "score \nGood luck!"
        return broadcast(user, msg)
    return "Course not found"
def startOver(user):
    global people, Events
    answers = people[user].answers
    for i in range(len(answers)):
        if 'y' in answers[i]:
            Events[i].yes -= 1
        elif 'n' in answers[i]:
            Events[i].no -= 1
        else:
            Events[i].addTally(answers[i], True)
    people[user].option = 0
    people[user].answers = []
    save("current")
    return
def status(user):
    global people, Events, payment
    msg = ""
    if payment:
        msg += "You have " + ("" if people[user].paid else " NOT ") + "paid\n\n"
    msg += "Going:"
    for k,v in people.items():
        if people[k].answers or k == DAD:
            msg += "\n" + v.name.title()
    return msg

if __name__ == '__main__':
    app.run()

# Legend
# a = add person
# A = announce
# e = end
# g = golf game
# h = home
# I = itinerary
# m = message
# n = new course adding
# p = poll mode
# pi = poll initiate
# P = pay mode
# q = question
# r = ramp up
# s = start
# v = vote set up or vote
