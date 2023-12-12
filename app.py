import os, random, jsonpickle, re
from dotenv import load_dotenv

from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, redirect, url_for, render_template, session

# from twilio.rest import Client
# from twilio.http.http_client import TwilioHttpClient
# from twilio.twiml.messaging_response import MessagingResponse

import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

project_folder = os.path.expanduser('~/mysite')
load_dotenv(os.path.join(project_folder, '.env'))

app = Flask(__name__, static_url_path='/static/')

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://zmarshall:'
app.config['SQLALCHEMY_DATABASE_URI'] += os.getenv("PASSWORD")
app.config['SQLALCHEMY_DATABASE_URI'] += '@zmarshall.mysql.pythonanywhere-services.com/zmarshall$planner'
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_POOL_RECYCLE'] = 280

# TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
# TWILIO_NUM = os.getenv("TWILIO_NUM")
# proxy_client = TwilioHttpClient(proxy={'http': os.environ['http_proxy'], 'https': os.environ['https_proxy']})
# twilio_api = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, http_client=proxy_client)

db = SQLAlchemy(app)

class Contacts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    number = db.Column(db.String(15), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=True)
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
        if dad: self.mode = "s"
        self.buffer = ""
        self.lastResponse = ""
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
        except: return False
    def endpoll(self, users):
        if users == self.count: return self.findWinner()
        first = 0
        second = 0
        for tick in self.tally:
            if tick > first:
                second = first
                first = tick
            elif tick > second:
                second = tick
        if (first-second) > (users - self.count): return self.findWinner()
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
        self.notPlaying = []
    def broadcast(self):
        msg = "Here are the teams: \n"
        for team in self.teams: msg += ','.join([x.title() for x in team]) + '\n'
        broadcast(None, msg)
    def bestball(self):
        currentGame = load('currentGame')
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
        currentGame = load('currentGame')
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
        currentGame = load('currentGame')
        i = currentGame.tees.index(tees)
        while self.handicaps[i][0] == 0: i += 1
        return i
    def setTeams(self,msg):
        people = load('people')
        self.teams = []
        if msg == 'random':
            temp = []
            for v in people.values():
                if v.name not in self.notPlaying:
                    temp.append(v.name)
            if len(temp) < 6: return False
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
        currentGame = load('currentGame')
        def format(v):
            val = v.split(',')
            if len(val) == 1: return v
            ret = ''
            dash = 0
            prev = val[0]
            for i in range(1,len(val)):
                if int(prev) == int(val[i])-1:
                    dash += 1
                    if dash == 2: ret = ret[:-1] + '-'
                else: dash = 0
                if dash < 2: ret += prev + ','
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
                elif v[i] == val: cancel = True
            if not cancel:
                if name in skinCount: skinCount[name] += ',' + str(i+1)
                else: skinCount[name] = str(i+1)
        if not skinCount: return 'No skins'
        for k,v in skinCount.items(): msg += '\n' + k.title() + ': ' + format(v)
        return msg
    def standings(self):
        people = load('people')
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
    def getText(self): return self.text
    def getTheme(self): return self.text
    def setText(self): return
class Vote:
    def __init__(self):
        self.text = ""
        self.theme = ""
        self.options = []
        self.tally = []
    def addTally(self,msg,negate=False):
        val = 1
        if negate: val = -1
        votes = msg.split(',')
        for i in range(len(votes)):
            self.tally[i] += int(votes[i]) * val
    def getText(self):
        msg = self.theme + ':'
        i = 0
        for option in self.options:
            i+=1
            msg += '\n' + str(i) + '. ' + option
        return msg
    def getTheme(self):return self.theme
    def setText(self):
        self.theme = self.options.pop(0)
        msg = self.theme
        for i in range(len(self.options)):
            msg += '\n' + str(i+1) + ". " + self.options[i]
        self.text = msg

DAD = os.getenv("DAD_NUM")
ADMIN = os.getenv("ADMIN_NUM")
FAIL = 'Unrecognized command. Look below to see command options'
ROUTE = 'http://zmarshall.pythonanywhere.com/'

@app.route('/help/<code>', methods=['GET', 'POST'])
def helpRoute(code):
    people = load('people')
    for user,peep in people.items():
        if peep.buffer == code:
            return help(user).replace('\n','<br>')
    return "I can't help you unfortunately. Please request a new link"
@app.route('/score', methods=['GET', 'POST'])
def score():
    currentGame, people = load('currentGame'), load('people')
    if currentGame is None: return "Sorry. It seems there is no game active :("
    if request.method == 'POST':
        name = request.form['name'].lower().strip()
        tee = request.form['tees']
        handicap = courseHandicap(float(request.form['handicap']),tee)
        holes = []
        for i in range(currentGame.holeCount):
            holes.append(int(request.form[('hole' + str(i))]))
        if getNumber(name)[0] and name not in currentGame.notPlaying:
            if dataEntered(handicap,holes,tee,name):
                msg = "Success :). Thanks " + name.title() + ". Your total today was "
                msg += str(people[getNumber(name)[1]].lastScore) + " and Net " + str(int(sum(currentGame.scores[name])))
                if currentGame.scores == peopleGoing():
                    broadcast(None, currentGame.standings())
                    currentGame = None
                    save('currentGame', currentGame)
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
    currentGame, safetyPlug, people = load('currentGame'), load('safetyPlug'), load('people')
    holeCount = currentGame.holeCount
    net = []
    i = currentGame.selectHandicaps(tees)
    additive = handicap // holeCount
    extra = handicap % holeCount
    for hole in range(holeCount):
        netScore = holes[hole] - additive - (extra >= currentGame.handicaps[i][hole])
        if currentGame.pars[hole] + 2 < netScore: netScore = currentGame.pars[hole] + 2
        net.append(netScore)
    currentGame.scores[name] = net
    save('currentGame',currentGame)
    differential = sum(net) - sum(currentGame.pars)
    if -10 < differential or safetyPlug:
        people[getNumber(name)[1]].lastScore = int(sum(net)) + handicap
        save('people', people)
        return True
    return False
def courseHandicap(handicap,tees):
    currentGame = load('currentGame')
    i = currentGame.tees.index(tees)
    plus = False
    if handicap < 0:
        plus = True
        handicap = -handicap
    val = round((handicap * currentGame.slopes[i])/113 + currentGame.rating[i] - sum(currentGame.pars))
    if currentGame.holeCount == 9: val /= 2
    return -val if plus else val
@app.route('/signup/<code>', methods=['GET', 'POST'])
def signupRoute(code):
    people, Events, texting = load('people'), load('Events'), load('texting')
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
            elif request.form.get(str(count)):
                msg = 'yes'
                event.yes += 1
            else:
                msg = 'no'
                event.no += 1
            people[user].answers.append(msg)
        save('people', people)
        save('Events', Events)
        clean(user)
        return 'All signed in!<br>' + announceHistory().replace('\n','<br>')
    else:
        for user,peep in people.items():
            if peep.buffer == code:
                questions = []
                for event in Events:
                    if isinstance(event, Vote):
                        temp = event.options[:]
                        temp.insert(0,event.theme)
                        questions.append(temp)
                    else: questions.append(event.text)
                return render_template("signup.html",user=user,questions=questions)
        return "I can't help you unfortunately. Please request a new link"
@app.route('/answers/<code>', methods=['GET', 'POST'])
def statusRoute(code):
    people = load('people')
    for user,peep in people.items():
        if peep.buffer == code:
            return answers().replace('\n','<br>')
    return "I can't help you unfortunately"
@app.route('/terminal', methods=['GET', 'POST'])
def terminal():
    if 'verified' in session and session['verified'] and 'user' in session and session['user']:
        user = getNumber(session['user'])[1]
        people = load('people')
        if user not in people: return "Looks like you haven't been invited yet :("
        if session['name'] == 'admin': newMessage = ''
        else: newMessage = 'Last message: ' + people[user].lastResponse if people[user].lastResponse else ""
        if request.method == 'POST' and 'msg' in request.form:
            newMessage = decode(user, str(request.form['msg']))
            people = load('people')
            if session['name'] != 'admin':
                people[user].lastResponse = newMessage
                save('people',people)
        mode = load('people')[user].mode
        box = False
        if mode: box = mode[0] in ['w','m','I','A','q']
        if 'q' in mode and '1' not in mode: box = False
        link = ROUTE in newMessage
        return render_template('terminal.html', newMessage=newMessage.split('\n'), user=session['name'], commands=help(user).split('\n')[1:],box=box,link=link)
    if request.method == 'POST':
        name = session['name']
        if str(request.form['code']) == session['code']:
            session['verified'] = True
            session['user'] = name
            return render_template('terminal.html', newMessage=[""], commands=help(getNumber(name)[1]).split('\n')[1:],box=False,link=False)
        else: return "Wrong code. Please go to last page and get new code"
    return "Error. Please try the link from your email again"
# @app.route('/text', methods=['GET', 'POST'])
# def text():
#     people = load('people')
#     if request.method != 'POST': redirect(url_for('score'))
#     incoming_msg = request.form['Body']
#     incoming_number = request.form['From']
#     if incoming_number in people or incoming_number == ADMIN:
#         try:
#             resp = MessagingResponse()
#             msg = resp.message()
#             msg.body(decode(incoming_number, incoming_msg))
#             return str(resp)
#         except Exception as e: send(ADMIN, str(e))
#     return ':3'
@app.route('/verify/<name>', methods=['GET', 'POST'])
def verify(name):
    if not load('loaded'): loadState('current')
    else: restart()
    name = name.lower().replace('%20',' ')
    if 'verified' in session and session['verified']: return redirect(url_for('terminal'))
    code = getCode()
    user = getNumber(name)[1] if name != 'admin' else ADMIN
    if user == "": return "Looks like this user wasn't invited. Reach out to Todd if this is a mistake"
    session['code'] = code
    if sendEmail(user,"Your verification code is: "+code,'verify'):
        session['name'] = name
        return redirect(url_for('verifySent'))
    return "This user doesn't have their email set up"
@app.route('/verify', methods=['GET', 'POST'])
def verifySent():
    if 'verified' in session and session['verified']: redirect(url_for('terminal'))
    if 'name' in session and session['name']: return render_template('verify.html', user=session['name'])
    return "Something went wrong. Re-launch the link from you email"

def addAll():
    people, Welcome = load('people'), load('Welcome')
    peeps = Contacts.query.all()
    msg = "Added:"
    for peep in peeps:
        if peep.number not in people:
            msg += '\n' + peep.name.title()
            people[peep.number] = Person(peep.name)
            send(peep.number, Welcome)
    save('people', people)
    return msg
def addCourse():
    newCourse, safetyPlug = load('newCourse'), load('safetyPlug')
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
    people, Welcome = load('people'), load('Welcome')
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
            if send(number, Welcome):
                people[number] = Person(name)
                save('people', people)
            else:
                people[user].mode = 'E2'
                save('people', people)
                return "Please add their email now"
        else: msg = "They are already signed up for the event"
    clean(user)
    return msg
def addItinerary(user):
    people = load('people')
    people[user].mode = 'I1'
    save('people', people)
    return "What should be the itinerary?"
def addList(peepList):
    people, Welcome = load('people'), load('Welcome')
    peeps = Contacts.query.all()
    for peep in peeps:
        if peep in peepList:
            people[peep.number] = Person(peep.name)
            send(peep.number, Welcome)
    return "Added"
def addQuestion():
    people = load('people')
    people[DAD].mode = 'q2'
    save('people', people)
    return "Type now your yes or no question"
def addStepOne(user, msg):
    if len(msg) > 40: return "Name is to long please retype it. Try again"
    elif ',' in msg: return "No commas allowed in name. Try again"
    people = load('people')
    if user == DAD and msg == "all":
        people[DAD].mode = 'a4'
        save('people', people)
        return "Add everyone that's in the database?\n" + listUsers()
    if user in [DAD,ADMIN] and msg == "list":
        people[DAD].mode = 'a5'
        people[DAD].buffer = listUsers()
        save('people', people)
        return listUsers()
    people[user].buffer = msg
    if Contacts.query.filter_by(name=msg).first() is None:
        people[user].mode = 'a2'
        save('people', people)
        return "What's their number?"
    num = Contacts.query.filter_by(name=msg).first().number
    people[user].mode = 'a3'
    save('people', people)
    return "This name is already in the database. Add number ending in " + num[-4:]
def addEmailStepOne(user, msg):
    if len(msg) > 40: return "Name is to long please retype it. Try again"
    elif ',' in msg: return "No commas allowed in name. Try again"
    if Contacts.query.filter_by(name=msg).first() is None: return "Name not in database. I can only add emails to existing contacts"
    people = load('people')
    people[user].buffer = msg + ','
    people[user].mode = 'E2'
    save('people', people)
    return "Found them. What is their email?"
def addVote(i):
    people = load('people')
    people[DAD].option = i
    people[DAD].mode = 'v1'
    save('people', people)
    if i > 0: return "Type now option " + str(i)
    return "Type now the theme of the selection"
def announce(user):
    people = load('people')
    people[user].mode = 'A1'
    save('people', people)
    return "What would you like to message?"
def announceHistory():
    announcements = load('announcements')
    finalMSG = "Announcements:"
    for msg in announcements: finalMSG += '\n\n' + msg
    if announcements: return finalMSG
    return ""
def answers():
    people, finalized, payment, Events = load('people'), load('finalized'), load('payment'), load('Events')
    msg = 'People going:\n'
    for person in people.values():
        if person.answers or (person.going and finalized) or person == people[DAD] or (person.going and not Events):
            msg += person.name.title() + '\n'
    if Events:
        msg += "\nPeople interested:\n"
        for person in people.values():
            if person.going and not (person.answers or finalized) and person != people[DAD]:
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
        msg += event.getTheme()
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
                questions = [x.getTheme() for x in Events]
                for i in range(len(questions)):
                    msg += '\n' + questions[i] + ': ' + person.answers[i]
            elif person.going and Events: msg += person.name.title() + " hasn't filled out the sheet"
            elif Events: msg += person.name.title() + " hasn't yet responded"
            msg += '\n\n'
    return msg
def broadcast(user, msg):
    announcements, people, currentPoll = load('announcements'), load('people'), load('currentPoll')
    poll = False
    if user:
        mode = people[user].mode
        if 'A' in mode: announcements.append(msg)
        if 'p' in mode:
            poll = True
            ending = currentPoll.endpoll(peopleGoing())
    for k,v in people.items():
        if v.going and v.mode != 'r':
            if poll:
                if ending: people[k].mode = 'h'
                else: people[k].mode = 'p'
            send(k, msg)
    save('announcements',announcements), save('people',people), save('currentPoll',currentPoll)
    return msg
def checkCourse(msg):
    course = Courses.query.filter_by(name=msg).first()
    if course:
        currentGame = Game(course.name, course.pars, course.tees, course.slopes, course.ratings, course.handicaps)
        save('currentGame',currentGame)
        return True
    return False
def checkPerson(user, msg):
    people = load('people')
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
    save('people',people)
    return msg
def clean(user):
    currentPoll, people, Events = load('currentPoll'), load('people'), load('Events')
    mode = people[user].mode
    if 'p' in mode:
        if 'i' in mode:
            if '2' in mode:
                people[user].mode = 'p'
                currentPoll.setText()
                save('currentPoll',currentPoll), save('people',people)
                return
            currentPoll = None
        else:
            currentPoll.count += 1
        save('currentPoll',currentPoll)
    if 'q' in mode or 'v' in mode:
        people[DAD].mode = 's'
        people[DAD].option = 0
        save('people', people)
        if '2' in mode: Events[-1].setText()
        else:
            Events.pop(-1)
            send(DAD, "Removed")
        save('Events', Events)
        return 'Ok'
    if 'w' in mode:
        people[DAD].mode = 's'
    elif 's' in mode:
        people[DAD].mode = 'h'
        save('people',people)
        saveState('current')
        return "Event set. Now you can add everyone to the event"
    elif people[user].going:
        people[user].mode = 'h'
    people[user].buffer = ""
    save('people', people)
    saveState('current')
    return 'Ok'
def decode(user, oMsg):
    currentEvent, safetyPlug, payment, finalized, texting, people,\
    Events, announcements, currentPoll, currentGame, Schedule, Welcome, newCourse = \
        load('currentEvent'),load('safetyPlug'),load('payment'),load('finalized'),\
        load('texting'),load('people'),load('Events'),load('announcements'),load('currentPoll'),\
        load('currentGame'),load('Schedule'),load('Welcome'),load('newCourse')
    msg = oMsg.lower().strip()
    try: mode = people[user].mode
    except:
        if user == ADMIN: mode = 'h'
        else: return "Not Invited :("
    if user == ADMIN:
        if msg == 'save': return saveState('savefile')
        elif msg == 'load': return loadState('savefile')
        elif msg == "add self" and ADMIN not in people:
            people[ADMIN] = Person("zach m")
            save('people', people)
            return clean(user)
        elif msg == 'texting':
            texting = not texting
            save('texting', texting)
            if not texting: return sendEmail(ADMIN,"Emailing now set for event")
            else: return "texting now enabled"
    if len(msg) < 1: return FAIL
    if people[user].starting:
        if 'y' == msg[0]:
            people[user].going = True
            people[user].starting = False
            save('people', people)
            if Events and not finalized:
                people[user].mode = 'r'
                code = getCode()
                people[user].buffer = code
                save('people', people)
                return "Here is your link to sign up:" + ROUTE+'signup/' + code
            clean(user)
            return 'Welcome. Type "?" to see your options\n' + announceHistory()
        elif not people[user].rejected:
            if 'n' == msg[0]:
                people[user].rejected = True
                save('people', people)
                saveState('current')
                return "Just reply 'y' if you change your mind"
            return "Only expecting 'y' or 'n'"
    if not people[user].going: return ""
    if msg == "?":
        if 'h' in mode or 's' in mode:
            if texting:
                code = getCode()
                people[user].buffer = code
                save('people', people)
                return ROUTE + "help/" + code
            else: return help(user)
        return help(user)
    if msg == 'back':
        if currentEvent or mode[0] in ['q','v','w']: return clean(user)
        currentEvent = True
        save('currentEvent',currentEvent)
        return "Typing back again will finalize the event. Make sure you're ready"
    if 'a' in mode:
        if '1' in mode: return addStepOne(user, msg)
        elif '4' in mode or '6' in mode:
            if 'y' == msg[0]:
                clean(user)
                if '4' in mode: return addAll()
                else: addList(people[user].buffer)
            elif 'n' == msg[0]: return clean(user)
        elif '5' in mode:
            temp = people[user].buffer.split('\n')
            people[user].buffer = filter(lambda x: listCheck(x.split('.')[0],msg), temp)
            people[user].mode = 'a6'
            save('people',people)
            if people[user].buffer:
                msg = "Add these people?\n"
                for person in people[user].buffer: msg += '\n' + person
                return msg
            clean(user)
            return "Bad input"
        if 'y' == msg[0] or '2' in mode:
            if '2' in mode:
                num = ''.join(list(filter(lambda x: x.isdigit(), msg.removeprefix('+1'))))
                if len(num) != 10: return "Phone number must be exactly 10 numbers"
                people[user].buffer += ',+1' + num
            else: people[user].buffer += ',' + Contacts.query.filter_by(name=people[user].buffer).first().number
            save('people', people)
            return addNum(user)
        elif 'n' == msg[0]:
            clean(user)
            return "Maybe add last name and try again"
        return "Only expecting 'y' or 'n'"
    elif 'A' in mode:
        if '1' in mode:
            people[user].buffer = "Announcement: " + oMsg
            people[user].mode = 'A2'
            save('people', people)
            return "Announce this?\n" + oMsg
        if 'y' == msg[0]:
            broadcast(user, people[user].buffer)
            clean(user)
            return "Messages Sent"
        elif 'n' == msg[0]: return announce(user)
        return "Only expecting 'y' or 'n'"
    elif 'e' in mode:
        if 'y' in msg:
            if user == DAD or user == ADMIN:
                if '1' in mode:
                    people[user].mode = 'e2'
                    save('people', people)
                    return "Double checking again because everything will be gone"
                msg = "The event has been ended. Thank you for participating!"
                broadcast(user,msg)
                restart()
                return "Ok then. Deleting..."
            people[user].going = False
            people[user].starting = True
            people[user].rejected = True
            save('people', people)
            startOver(user)
            saveState('current')
            return "Just reply 'y' if you change your mind"
        clean(user)
        return 'Ok'
    elif 'E' in mode:
        if '1' in mode: return addEmailStepOne(user, msg)
        if '2' in mode:
            regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
            if re.fullmatch(regex, msg):
                name = people[user].buffer.split(',')[0]
                contact = Contacts.query.filter_by(name=name).first()
                if contact:
                    contact.email = msg
                    db.session.commit()
                    clean(user)
                    if user in people: return "Email updated"
                    else:
                        people[user] = Person(name)
                        save('people', people)
                        sendEmail(user,Welcome)
                        return "All set. Sent email to " + msg
                else: return "This person is not in the database (You should NOT be able to get to this message. Please contact admin)"
            else: return "Not a valid email, please try again.\nIf you are sure you have typed it correctly please reach out to admin"
    elif 'g' in mode: return startGame(user, msg)
    elif 'h' in mode:
        people[user].buffer = ""
        save('people', people)
        if "add" in msg:
            if msg == "add":
                people[user].mode = 'a1'
                save('people', people)
                return "Who would you like to add?"
            try:
                name = msg.split(' ',1)[1]
                return addStepOne(user, name)
            except: return FAIL
        elif 'email' in msg:
            if msg == "email":
                people[user].mode = 'E1'
                save('people',people)
                return "Who would you like to add?"
            try:
                name = msg.split(' ',1)[1]
                return addEmailStepOne(user, name)
            except: return FAIL
        elif msg == "end":
            people[user].mode = 'e1'
            save('people', people)
            return "Are you sure you want to" + (" end " if (user == DAD or user == ADMIN) else " leave ") + "this event??"
        elif "message" in msg or "msg" in msg:
            people[user].mode = 'm1'
            save('people', people)
            if msg == 'message' or msg == 'msg': return "Who would you like to message?"
            try:
                name = msg.split(' ',1)[1]
                return checkPerson(user, name)
            except:
                clean(user)
                return FAIL
        elif msg == "pay" and payment: return pay(user)
        elif "schedule" in msg:
            if msg == "schedule": return Schedule
            elif (user == DAD or user == ADMIN) and msg == "set schedule": return addItinerary(user)
        elif msg == "status":
            if user == DAD or user == ADMIN:
                code = getCode()
                people[user].buffer = code
                save('people', people)
                return ROUTE + "answers/" + code
            return status(user)
        elif (user == DAD or user == ADMIN) and currentEvent:
            if msg == "announce": return announce(user)
            elif currentGame and "minus" in msg:
                try:
                    for name in msg.split()[1].split(','):
                        if not getNumber(name)[0]:
                            return name.title() + " not found"
                    currentGame.notPlaying.extends(msg.split()[1].split(','))
                    return "Removed " + " ".join(msg.split()[1].split(','))
                except: return FAIL
            elif msg == 'finalize': return finalize()
            elif "kick" in msg:
                if msg == "kick":
                    people[user].mode = 'k1'
                    save('people', people)
                    return "Who would you like to remove?"
                try:
                    name = msg.split(' ',1)[1]
                    return kickStepOne(user, name)
                except: return FAIL
            elif msg == 'new course':
                people[user].mode = 'n1'
                save('people', people)
                msg = "What is the name of the course?"
                return msg
            elif "play" in msg:
                if msg == 'play':
                    if currentGame:
                        broadcast(user, "Game ended")
                        currentGame = None
                        save('currentGame', currentGame)
                    people[user].mode = 'g'
                    save('people', people)
                    return "What course?"
                try:
                    msg = msg.split(' ',1)[1]
                    return startGame(user, msg)
                except: return FAIL
            elif msg == "poll":
                people[user].mode = 'p'
                save('people',people)
                if currentPoll is not None:
                    currentPoll.findWinner()
                    msg = broadcast(user, currentPoll.winner)
                    currentPoll = None
                    save('currentPoll',currentPoll)
                    clean(user)
                    return msg
                currentPoll = Poll()
                save('currentPoll',currentPoll)
                return poll(user, 0)
            elif msg == "pullsafetyplug":
                safetyPlug = not safetyPlug
                save('safetyPlug',safetyPlug)
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
                except: return FAIL
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
            save('people',people)
            return "This is what will be seen:\n " + oMsg
        if 'y' == msg[0]:
            Schedule = people[user].buffer
            save('Schedule',Schedule)
            clean(user)
            return "Itinerary set"
        elif 'n' == msg[0]: return addItinerary(user)
        return "Only expecting 'y' or 'n'"
    elif 'k' in mode:
        if '1' in mode: return kickStepOne(user, msg)
        if '2' in mode:
            if 'y' == msg[0]:
                peep = getNumber(people[user].buffer)[1]
                send(peep, "You have been removed from the group. Text Todd directly if you want back in")
                if not finalized: startOver(peep)
                del people[peep]
                save('people',people)
                clean(user)
                return "Removed them from the event"
            elif 'n' == msg[0]: return clean(user)
            return "Only expecting 'y' or 'n'"
    elif 'm' in mode:
        if '1' in mode: return checkPerson(user, msg)
        send(people[user].buffer, (people[user].name.title() + " says:\n" + msg))
        clean(user)
        return "Message sent"
    elif 'n' in mode:
        if '1' in mode:
            newCourse['n'] = msg
            people[user].mode = 'n2'
            save('newCourse', newCourse)
            save('people', people)
            return newCourse['n'] + " will be the name. What are the tee options?"
        elif '2' in mode:
            try: newCourse['t'] = [x.strip().lower() for x in msg.split(',')]
            except: return "Text must be comma separated"
            people[user].mode = 'n3'
            save('newCourse', newCourse)
            save('people', people)
            return " ".join(newCourse['t']) + " will be the tees. What are the tee respective slopes?"
        elif '3' in mode:
            try: newCourse['s'] = [int(x.strip().lower()) for x in msg.split(',')]
            except: return "Text must be comma separated numbers"
            people[user].mode = 'n4'
            save('newCourse', newCourse)
            save('people', people)
            return " ".join([str(x) for x in newCourse['s']]) + " will be the slopes. What are the tee respective ratings?"
        elif '4' in mode:
            try: newCourse['r'] = [float(x.strip().lower()) for x in msg.split(',')]
            except: return "Text must be comma separated numbers"
            people[user].mode = 'n5'
            save('newCourse', newCourse)
            save('people', people)
            return " ".join([str(x) for x in newCourse['r']]) + " will be the ratings. What are the tee respective hole handicaps?"
        elif '5' in mode:
            try: newCourse['h'] = [[int(x.strip().lower()) for x in holes.split(',')] for holes in msg.split(';')]
            except: return "Text must be comma separated holes and semi-colon separated sets"
            people[user].mode = 'n6'
            save('newCourse', newCourse)
            save('people', people)
            return msg.replace(';',' ') + " will be the hole handicaps. What are the tee respective pars?"
        elif '6' in mode:
            try: newCourse['p'] = [int(x.strip().lower()) for x in msg.split(',')]
            except: return "Text must be comma separated numbers"
            people[user].mode = 'n7'
            save('newCourse', newCourse)
            save('people', people)
            return " ".join([str(x) for x in newCourse['p']]) + " will be the pars. Are the course specs correct?"
        elif '7' in mode:
            if 'y' == msg[0]:
                clean(user)
                return addCourse()
            else: return 'Either send "yes" to confirm or "back" to quit out and try again'
    elif 'p' in mode:
        if currentPoll is None:
            people[user].mode = 'h'
            save('people', people)
            return decode(user, oMsg)
        if 'i' in mode:
            if msg == 'end':
                people[user].mode = 'pi2'
                save('people', people)
                clean(user)
                return "Poll is now running. Cast your vote too\n" + broadcast(user, currentPoll.text)
            i = people[user].option
            currentPoll.options.append(oMsg)
            currentPoll.tally.append(0)
            save('currentPoll',currentPoll)
            return poll(user, i + 1)
        if currentPoll.addTally(msg):
            msg = "Your vote has been cast"
            if currentPoll.endpoll(peopleGoing()):
                msg = broadcast(user, currentPoll.winner)
                currentPoll = None
                save('currentPoll',currentPoll)
            people[user].mode = 'h'
            save('people', people)
            return msg
        return 'Not valid. "?" for help'
    elif 'P' in mode:
        present, num = getNumber(msg)
        clean(DAD)
        if present:
            people[num].paid = not people[num].paid
            save('people',people)
            return msg.title() + " has been marked as " + ("" if people[num].paid else "not") + "paid"
        return 'Name not found in group. Type "status" to see all who are present'
    elif 'q' in mode:
        if '1' in mode:
            people[DAD].mode = 'q2'
            people[DAD].buffer = oMsg
            save('people', people)
            return "Are you sure that you want to ask:\n" + oMsg
        if 'y' == msg[0]:
            Events[-1].text = people[DAD].buffer
            save('Events', Events)
            clean(DAD)
            return "Question now in sign up"
        elif 'n' == msg[0]: return addQuestion()
        return "Only expecting 'y' or 'n'"
    elif 'r' in mode:
        if msg == "end":
            clean(user)
            people[user].going = False
            people[user].starting = True
            people[user].rejected = True
            save('people', people)
            return "Just reply 'y' if you change your mind"
        elif msg == "link":
            code = getCode()
            people[user].buffer = code
            save('people', people)
            return ROUTE+'signup/' + code
    elif 's' in mode:
        currentEvent = False
        save('currentEvent',currentEvent)
        if msg == "question":
            Events.append(Question())
            save('Events',Events)
            people[DAD].mode = 'q1'
            save('people', people)
            return "Type now your yes or no question"
        elif msg == "vote":
            Events.append(Vote())
            save('Events',Events)
            return addVote(0)
        elif msg == "pay":
            payment = not payment
            msg = 'Now party members'
            msg += ' ' if payment else " don't "
            msg += 'need to keep track of payment'
            save('payment',payment)
            return msg
        elif msg == "end":
            restart()
            return "You now have a clean slate"
        elif msg == "status": return showQuestions()
        elif msg == "welcome":
            people[DAD].mode = 'w'
            save('people',people)
            return 'What do you want the welcome message to be?'
    elif 'v' in mode:
        if msg == 'end':
            people[DAD].mode = 'v2'
            save('people',people)
            clean(DAD)
            return "Vote set for sign up"
        i = people[DAD].option
        Events[-1].options.append(oMsg)
        Events[-1].tally.append(0)
        save('Events',Events)
        return addVote(i+1)
    elif 'w' in mode:
        Welcome = oMsg
        save('Welcome',Welcome)
        clean(DAD)
        return 'Welcome message is set'
    return FAIL
def finalize():
    people = load('people')
    peeps = ''
    msg = "The event is now finalized so you can't join anymore. Sorry you couldn't make it."
    msg += " You'll need to text Todd directly if you want back in now"
    for k,v in dict(people).items():
        if not v.going:
            send(k,msg)
            peeps += '\n' + v.name.title()
            del people[k]
            save('people',people)
    if peeps: return 'Removed: ' + peeps
    return 'No one removed'
def getCode():
    people = load('people')
    while True:
        code = random.randint(1000000,9999999)
        for peep in people.values():
            if peep.buffer == code: break
        else: break
    return str(code)
def getNumber(name):
    if name == 'admin': return True, ADMIN
    people = load('people')
    for k,v in people.items():
        if v.name == name: return v.going, k
    return False, ""
def help(user):
    people, payment, currentGame = load('people'), load('payment'), load('currentGame')
    if user == ADMIN and ADMIN not in people: mode = 'z'
    else: mode = people[user].mode
    msg = ""
    if mode in ['a3','a4','a6','A2','I2','k2','q2']:
        msg = '"y" or "n" is expected here'
    msg += '"?": shows available commands. Commands are NOT case sensitive.\n'
    if 'a' in mode:
        msg += '\n"back": to no longer add a number.'
    elif 'A' in mode: msg += '\n"back": to no longer make an announcement.'
    elif 'h' in mode:
        if currentGame: msg += '\n"link": to get a new link to enter scores.\n'
        if payment:
            if not people[user].paid:
                msg += '\n"pay": to request Todd to check you off for paying everything. Send image proof to him directly.\n'
            elif user == DAD:
                msg += '\n"pay": to check someone off for paying.\n'
        msg += '\n"message" or "msg": to begin messaging to someone on the going list.'
        msg += ' Add a name for a shortcut-> "Msg todd". Use the "status" command to see all the names.\n'
        msg += '\n"add": to add someone to the group. Add a name for a shortcut-> "Add todd".\n'
        msg += '\n"status": to see people in the event'
        msg += ', current answers to all questions' if user == DAD else ''
        msg += ' and your payment status. ' if payment else '. '
        msg += '\n"schedule": to see what is posted to the schedule.\n'
        if user == DAD or user == ADMIN:
            msg += '\n------ ADMIN EXCLUSIVE -------'
            msg += '\n"set schedule": to set and reset the schedule. This is a place to house tee times or' \
                   ' something of the sort. Could hold any information you want though.\n'
            msg += '\n"add all": to add all numbers in database.\n'
            msg += '\n"add list": to add selections of numbers from database.\n'
            msg += '\n"announce": to send a message to everyone. ' \
                   'These will also be sent to members that arrive after you send the announcement\n'
            msg += '\n"poll": to start a poll or end one early.'
            msg += '\n"waiting": to get a list of people that have yet to vote in a poll if there is one.\n'
            msg += '\n"kick": to remove a player from the event. Add a name for a shortcut-> "Kick zach".\n'
            msg += '\n"finalize": will kick all the people that are not planning on going to the event\n'
            msg += '\n"email": to add an email address to an existing contact\n'
            if currentGame:
                msg += '\n"teams <teams>": to make the teams. Must either be manually entered: Teams zach,todd;dana,jim\n'
                msg += '(Notice how each team is separated by a ";" and each player is separated by ",")\n'
                msg += 'Or, if there\'s at least 6 players: Teams random\n'
                msg += 'Teams can be recreated each time if needed\n'
                msg += '"minus": to have a list of players that you aren\'t expecting to receive a score from: Minus zach\n'
            else: msg += '\n"play" to start playing a golf course. Add the name for a shortcut-> "Play Dos Rios"\n'
            msg += '\n------ ADMIN EXCLUSIVE -------'
        else: msg += '\n'
        msg += '\n"end": to end the event for ' + ("everyone" if user == DAD else "yourself")
    elif 'I' in mode: msg += '\n"back": to no longer make changes the schedule page.'
    elif 'k' in mode: msg += '\n"back": stop kicking mode.'
    elif 'm' in mode: msg += '\n"back": to stop messaging.'
    elif 'n' in mode: msg += '\n"back": to stop adding course.'
    elif 'p' in mode:
        if '1' in mode or '2' in mode:
            msg += '\n"back": to not send out this poll\n'
            msg += '\n"end": to finish list of options'
        else:
            msg += '\nYour answer should just be the number of the option you chose\n'
            msg += '\n"back": cast no vote in the poll'
    elif 'P' in mode: msg += '\n"back": exit payment checklist mode'
    elif 'q' in mode or 'v' in mode:
        msg += '\n"back": to not add this to sign up'
        if 'v' in mode: msg += '\n\n"end": to finish list of vote'
    elif 'r' in mode:
        msg += '\n"link": to send yourself the link again\n'
        msg += '\n"end": if you change your mind and don\'t want to sign up'
    elif 's' in mode:
        msg += '\n"question": to add a yes or no question when signing up\n'
        msg += '\n"vote": to add a vote when signing up\n'
        msg += '\n"pay": change whether or not you are expecting payment from everyone\n'
        msg += '\n"status": to see what questions have been added to the event so far\n'
        msg += '\n"welcome": to update the welcoming message that invites people to your trip\n'
        msg += '\n"back": to end sign up and start adding people\n'
        msg += '\n"end": to restart the questionnaire'
    elif 'w' in mode:
        msg += '\n"back": exit set welcome\n'
    elif 'e' in mode:
        msg += '\n"y": to confirm\n'
        msg += '\n"n": to continue with event\n'
    elif 'E' in mode:
        msg += '\n"back": exit setting email\n'
    elif 'z' in mode:
        msg += '\n"save": saveState'
        msg += '\n"load": loadState'
        msg += '\n"add self": add Zach to group'
        msg += '\n"texting": switch to texting mode'
        msg += '\n"back": clean user'
    elif mode == "":
        msg += '\n"y": will let you sign up for the event. Don\'t worry, you can always back out whenever you need'
        msg += '\n"n": will mark you as not interested. If you say no now you will still be able to sign up later if you change your mind'
    return msg
def kickStepOne(user, msg):
    people = load('people')
    people[user].buffer = msg
    save('people',people)
    for val in people.values():
        if msg == val.name:
            people[user].mode = 'k2'
            save('people',people)
            return "Remove " + msg.title() + '?'
    else:
        clean(user)
        return "Name not in event"
def listCheck(num,testSet):
    try:
        for selection in [x.strip() for x in testSet.split(',')]:
            if ('-' in selection and int(selection.split('-')[0]) <= int(num) <= int(selection.split('-')[-1])) \
                    or num == selection: return True
    except: pass
    return False
def listUsers():
    people = load('people')
    peeps = Contacts.query.all()
    msg = "Not yet invited:"
    i = 0
    for peep in peeps:
        if peep.number not in people:
            i += 1
            msg += '\n' + str(i) + '. ' + peep.name.title()
    return msg
def load(name):
    try:
        with open("globals/" + name + ".txt", 'r') as f:
            return jsonpickle.decode(f.readline())
    except: return None
def loadState(name):
    try:
        with open(name + ".txt", 'r') as f:
            data = jsonpickle.decode(f.readline())
    except: return "Failed to load"
    save('currentEvent', data[0])
    save('safetyPlug', data[1])
    save('payment', data[2])
    save('finalized', data[3])
    save('texting', data[4])
    save('people', data[5])
    save('Events', data[6])
    save('announcements', data[7])
    save('currentPoll', data[8])
    save('currentGame', data[9])
    save('Schedule', data[10])
    save('Welcome', data[11])
    save('newCourse', data[12])
    save('loaded', data[13])
    return "Loaded"
def pay(user):
    people = load('people')
    if user == DAD:
        people[DAD].mode = 'P'
        save('people',people)
        return "Who would you like to check off as paid?"
    send(DAD, people[user].name.title() + ' says they have paid. Type "pay" to check someone off for paying')
    return "Request sent. Send Todd a screenshot or image of your payment just in case he's drunk :)"
def peopleGoing():
    people = load('people')
    count = 0
    for v in people.values():
        if v.going: count += 1
    return count
def poll(user, i):
    people = load('people')
    people[user].option = i
    people[user].mode = 'pi1'
    save('people',people)
    if i > 0: return "Type now option " + str(i)
    return "What should the poll be about?"
def restart():
    currentEvent, safetyPlug, payment, finalized, texting, loaded = False, False, False, False, False, False
    people = {DAD: Person('todd m', False, True)}
    Events, announcements = [], []
    currentPoll, currentGame = None, None
    Schedule = "No schedule set yet"
    Welcome = "Send 'y' if interested in joining Todd's trip"
    newCourse = {'n':'', 't':[], 'p':[], 'h':[], 's':[], 'r':[]}

    save('currentEvent', currentEvent)
    save('safetyPlug', safetyPlug)
    save('payment', payment)
    save('finalized', finalized)
    save('texting', texting)
    save('loaded', loaded)
    save('people', people)
    save('Events', Events)
    save('announcements', announcements)
    save('currentPoll', currentPoll)
    save('currentGame', currentGame)
    save('Schedule', Schedule)
    save('Welcome', Welcome)
    save('newCourse', newCourse)
    saveState("current")
def save(name,data):
    with open("globals/" + name + ".txt", 'w') as f: f.write(jsonpickle.encode(data))
    return True
def saveState(name):
    data = [load('currentEvent')
            ,load('safetyPlug')
            ,load('payment')
            ,load('finalized')
            ,load('texting')
            ,load('people')
            ,load('Events')
            ,load('announcements')
            ,load('currentPoll')
            ,load('currentGame')
            ,load('Schedule')
            ,load('Welcome')
            ,load('newCourse')
            ,load('loaded')]
    with open(name + ".txt", 'w') as f:
        f.write(jsonpickle.encode(data))
    return "Saved"
def send(user, msg):
    texting = load('texting')
    try:
        if texting: return False # twilio_api.messages.create(body=msg, from_=TWILIO_NUM, to=user)
        else: return sendEmail(user,msg)
    except: return False
def sendEmail(user, msg, template='email'):
    smtp_server = "smtp.outlook.com"
    port = 587
    sender = "ToddTrips@outlook.com"
    contact = Contacts.query.filter_by(number=user).first()
    if contact:
        name = contact.name
        receiver = contact.email
        if not receiver: return False
        context = ssl.create_default_context()
        try:
            server = smtplib.SMTP(smtp_server, port)
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender, os.getenv("PASSWORD"))
            message = MIMEMultipart('alternative')
            message['From'] = sender
            message['To'] = receiver
            subject = 'Mesquite 2024' if template == 'email' else 'Verification Code'
            message['Subject'] = subject
            if template == 'email':
                msg = email_template.format(msg=msg.replace('\n','<br>').replace('\r','<br>'),name=name,route=ROUTE)
            elif template == 'verify':
                msg = verify_template.format(msg=msg.replace('\n','<br>').replace('\r','<br>'),route=ROUTE)
            message.attach(MIMEText(msg,'html'))
            server.sendmail(sender, receiver, message.as_string())
        except Exception as e:
            print('\n\n\n',"Email error:",e,'\n\n\n')
            return False
        finally: server.quit()
    else: return False
    return True
def showQuestions():
    Events, Welcome = load('Events'), load('Welcome')
    msg = "Welcome: " + Welcome + '\n'
    for event in Events: msg += event.getText() + '\n'
    return msg
def startGame(user, msg):
    clean(user)
    if checkCourse(msg):
        msg = "Game started. Good luck!"
        return broadcast(user, msg)
    return "Course not found"
def startOver(user):
    people, Events = load('people'), load('Events')
    answers = people[user].answers
    for i in range(len(answers)):
        if 'y' in answers[i]: Events[i].yes -= 1
        elif 'n' in answers[i]: Events[i].no -= 1
        else: Events[i].addTally(answers[i], True)
    people[user].option = 0
    people[user].answers = []
    save('people',people)
    save('Events',Events)
    saveState("current")
    return
def status(user):
    people, payment = load('people'), load('payment')
    msg = ""
    if payment: msg += "You have " + ("" if people[user].paid else " NOT ") + "paid\n\n"
    msg += "Going:"
    for k,v in people.items():
        if people[k].answers or k == DAD: msg += "\n" + v.name.title()
    return msg

email_template="""<body style="text-align:center">
<h4>{msg}</h4>
----------------
<p>Go here to start interacting with the app: <a href="{route}verify/{name}">{route}verify/{name}</a><p>
<p style="color:gray">This route will verify you are who you are first then you'll have full access for a while until your session expires<p>
<p style="color:gray">Contact Zach if there are any errors or troubles so we can get them fixed!<p>
</body>"""
verify_template="""<body>
<h4>{msg}</h4>
<enter it here: <a href="{route}/verify">{route}/verify</a>
</body>"""

if __name__ == '__main__':
    if load('loaded'): loadState('current')
    else: restart()
    app.run()

# Legend
# a = add person
# A = announce
# e = end
# E = add email
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
