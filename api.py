from flask import Flask, render_template, url_for, request, g, session, redirect
from flask_mail import Mail, Message
from flask_mongoalchemy import MongoAlchemy
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

'''Setting up MongoDB and MailServer'''

app = Flask(__name__) 
app.config['SECRET_KEY'] = 'firstkey'
app.config['DEBUG'] = True
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

''' Assing here your values'''

app.config['MONGOALCHEMY_DATABASE'] = '' 
app.config['MONGOALCHEMY_CONNECTION_STRING'] = ''
app.config['MAIL_SERVER'] = ''
youremail = app.config['MAIL_USERNAME'] = '' 
app.config['MAIL_PASSWORD'] = ''

db = MongoAlchemy(app)
mail = Mail(app)
key = URLSafeTimedSerializer('secondkey')

'''Users document'''

class Users(db.Document): 
    users_id = db.ObjectId()
    username = db.StringField()
    password = db.StringField()
    e_mail = db.StringField()
    usertype = db.StringField()
    c_state = db.StringField()
    
'''Requests document'''  
 
class Requests(db.Document):
    requests_id = db.ObjectId()
    user_name = db.StringField()
    first_name = db.StringField()
    last_name = db.StringField()
    age = db.StringField()
    city = db.StringField()
    email = db.StringField()
    phone_number = db.StringField()
    job = db.StringField()
    state = db.StringField()

'''index route, is the main page, closes user session and renders index.html'''

@app.route('/')
def index():
    session.pop('username', None)
    return render_template('index.html')

'''login route, checks user input and query it to find a match. if result true and
 mail is confirmed, we assign input name to session then he gets redirect to a url base on his usertype'''
 
@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        session.pop('username', None)
        name = str(request.form['username'])
        code = str(request.form['password'])
        login_user = Users.query.filter(Users.username == name, Users.password == code)
        result = login_user.first()

        if result:
            if result.c_state == 'confirmed':
                session['username'] = request.form['username']
                if 'username' in session:
                    rights = Users.query.filter(Users.username == session['username'])
                    result = rights.first()
                    if result.usertype == 'simple':
                        return redirect(url_for('simple'))
                    elif result.usertype == 'advance':
                        return redirect(url_for('advance'))
                else:
                    return render_template('login.html')
            else:
                return render_template('confirm_email_form.html')
        else:
            return render_template('login.html', error = 'Invalid credentials')
    else:
        return render_template('login.html')

'''register route, checks user input and query it to find a match.
if result false and fields meet the requirements, a user is created base on the inputs, with simple rights.
Also a url with a unique confirmation code is send to the inputed email'''

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        email = str(request.form['email'])        
        name = str(request.form['username'])
        code = str(request.form['password'])
        c_code = str(request.form['c_password'])
        existing_user = Users.query.filter(Users.username == name)
        result = existing_user.first()
        existing_mail = Users.query.filter(Users.e_mail == email)
        result2 = existing_mail.first()
        
        if result is None:
            if len(email) >= 4:
                if result2 is None:
                    if len(name) >= 4:
                        if len(code) >= 6 and len(c_code) >= 6:
                            if code == c_code:
                                state = 'not confirmed'
                                group = Users(username = name, password = code, usertype = 'simple', e_mail = email, c_state = state) 
                                db.session.add(group)
                                token = key.dumps(email, salt='confirm-mail')
                                msg = Message(subject = 'Confirm Email', sender = youremail, recipients = [email])
                                link = url_for('confirm_email', token = token, _external = True)
                                msg.body = 'Your link is {}'.format(link)
                                mail.send(msg)
                                session['username'] = request.form['username']
                                return redirect(url_for('login'))
                            else:
                                return render_template('register.html', error = 'Password and confirm password do not match')
                        else:
                            return render_template('register.html', error = 'Password must be at least 6 characters')
                    else:
                        return render_template('register.html', error = 'Username must be at least 4 characters')
                else:
                    return render_template('register.html', error = 'That email already exists')
            else:
                return render_template('register.html', error = 'Not a valid email')
        else:
            return render_template('register.html', error = 'That username already exists!')
    else:
        return render_template('register.html')

'''confirm_email_form route, called if user forgets to confirm his email.
base on his input, an email is send with a confirmation link''' 
     
@app.route('/confirm_email_form', methods=['POST', 'GET'])
def confirm_email_form():
    if request.method == 'POST':
        email = request.form['email']     
        token = key.dumps(email, salt='confirm-mail')
        msg = Message(subject = 'Confirm Email', sender = youremail, recipients = [email])
        link = url_for('confirm_email', token = token, _external = True)
        msg.body = 'Your link is {}'.format(link)
        mail.send(msg)
        return render_template('login.html')
    else:
        return render_template('confirm_email_form.html')

'''confirm_email route, decodes the confirmation url.
base on the decoded email a query is called and the c_state field on its document is changed to confirmed''' 
  
@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = key.loads(token, salt='confirm-mail', max_age = 180)
    except SignatureExpired:    
        return '<h1>The token is expired!</h1>'
    existing_user = Users.query.filter(Users.e_mail == email)
    result = existing_user.first()
    result.c_state = 'confirmed'
    result.save() 
    return redirect(url_for('login'))

'''logout route, if called closes user session and calls login route''' 

@app.route('/logout')
def logout(): 
    session.pop('username', None)
    return redirect(url_for('login'))

'''before_request route, called before any other route and 
used for assigning session name to g.user. then its route can get session value''' 

@app.before_request
def before_request():
    g.user = None
    if 'username' in session:
        g.user = session['username']

'''simple route, if user logs in and usertype is simple gets redirected here''' 

@app.route('/simple')
def simple():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'simple':
            return render_template('simplemenu.html')
        else:
            return redirect(url_for('login'))
    return render_template('login.html')

'''advance route, if user logs in and usertype is advance gets redirected here''' 

@app.route('/advance')
def advance():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'advance':
            return render_template('advancemenu.html')
        else:
            return redirect(url_for('login'))
    return render_template('login.html')

'''deleteuser route, its called only by advance user, to delete a user base on inputed username.
user admin password can not be deleted''' 
        
@app.route('/deleteuser',  methods = ['POST'])
def deleteuser():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'advance':
            name = request.form['username']
            existing_user = Users.query.filter(Users.username == name)
            result = existing_user.first()
            if result:
                if result.username != session['username'] and result.username != 'admin':
                    result.remove()
            return redirect(url_for('users'))
        else:
            return render_template('login.html')
    return render_template('login.html')

'''deleterequest route, its called only by advance user, to delete a request base on inputed username''' 
        
@app.route('/deleterequest',  methods = ['POST'])
def deleterequest():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'advance':
            name = request.form['username']
            existing_request = Requests.query.filter(Requests.user_name == name)
            result = existing_request.first()
            if result:
                result.remove()
            return redirect(url_for('requests')) 
        else:
            return render_template('login.html')
    return render_template('login.html')

'''deletemyrequest route, its called only by simple user, to delete his request''' 
        
@app.route('/deletemyrequest')
def deletemyrequest():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'simple':    
            name = session['username']
            existing_request = Requests.query.filter(Requests.user_name == name)
            result = existing_request.first()
            if result:
                result.remove()
            return redirect(url_for('myrequests'))
        else:
            return render_template('login.html')
    return render_template('login.html')

'''myrequests route, its called only by simple user, to query his request''' 

@app.route('/myrequests') 
def myrequests():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'simple':
            result = []
            q = Requests.query.filter(Requests.user_name == session['username'])
            for i in q:
                result.append((
                        '\nSubmitted By User: ' + i.user_name +
                        '\nFirst Name: '+ i.first_name +
                        '\nLast Name: '+ i.last_name +
                        '\nBirthday: '+ i.age +
                        '\nCity: '+ i.city +
                        '\nEmail: '+ i.email +
                        '\nPhone Number: '+ i.phone_number +
                        '\nRequested Positions: '+ i.job +
                        '\nRequest State: '+ i.state + '\n'))
            return render_template('myrequests.html', result = '\n'.join(result))
        else:
            return render_template('login.html')
    return render_template('login.html')

'''requeststate route, its called only by advance user, to approve a request or disapprove it
by changing its request state field. input for changing request state is the name of the user who submited it''' 

@app.route('/requeststate',  methods = ['POST'])
def requeststate():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'advance':
            name = request.form['username2']
            existing_request = Requests.query.filter(Requests.user_name == name)
            result2 = existing_request.first()
            if result2:
                if request.form.get('Approve') == 'Approve':
                    result2.state = 'Approved'
                    result2.save()
                    msg = Message(subject = 'Request Approval - Company',
                                  sender = youremail,
                                  recipients = [result2.email],
                                  body = 'Congratulations, your request has been approved.\nWe will contact you by your phone within 3 days\nin order to inform of arranging a personal meeting,\nThank you for your time.')
                    mail.send(msg)
                elif request.form.get('Disapprove') == 'Disapprove':
                    result2.state = 'Disapproved'
                    result2.save()
                    msg = Message(subject = 'Request Disapproval - Company',
                                  sender = youremail,
                                  recipients = [result2.email],
                                  body = 'We are sorry to inform you that your request has been disapproved.\nThank you for your time.')
                    mail.send(msg)
                return redirect(url_for('requests'))
            else:
                return render_template('requests.html')
        else:
            return render_template('login.html')
    return render_template('login.html')

'''requests route, its called only by advance user, to query all requests''' 

@app.route('/requests') 
def requests():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'advance':
            result = []
            q = Requests.query.all()
            for i in q:
                result.append((
                        '\nSubmitted By User: ' + i.user_name +
                        '\nFirst Name: '+ i.first_name +
                        '\nLast Name: '+ i.last_name +
                        '\nBirthday: '+ i.age +
                        '\nCity: '+ i.city +
                        '\nEmail: '+ i.email +
                        '\nPhone Number: '+ i.phone_number +
                        '\nRequested Positions: '+ i.job +
                        '\nRequest State: '+ i.state))
            return render_template('requests.html', result = '\n'.join(result))
        else:
            return render_template('login.html')
    return render_template('login.html')

'''changerights route , its called only by advance user, to change a users rights. if his usertype is advance then
 base on his input he can change user rights. user's admin usertype can not be changed''' 
 
@app.route('/changerights', methods = ['POST'])
def changerights():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'advance':
            name = request.form['username2']
            existing_user = Users.query.filter(Users.username == name)
            result = existing_user.first()
            if result:
                if result.username != 'admin':
                    if result.username != session['username']:
                        if result.usertype == 'simple':
                            result.usertype = 'advance'
                            result.save()
                        elif result.usertype == 'advance':
                            result.usertype = 'simple'
                            result.save() 
                    return redirect(url_for('users'))
                else:
                    return redirect(url_for('users'))                    
            else:
                return redirect(url_for('users'))
        else:
            return render_template('login.html')
    return render_template('login.html')

'''accountinfo route, its called to change user password. a query base on session name is called,
 if result true and new inputed password meets the requirements, password is updated and a mail is send to the user to inform him
 of the change. user's admin password can not be changed''' 
 
@app.route('/accountinfo', methods=['POST', 'GET'])
def accountinfo():
    if g.user and g.user != 'admin':
        if request.method == 'POST':
            code = str(request.form['password'])
            user = Users.query.filter(Users.username == session['username'])
            result = user.first()
        
            if result:
                    if len(code) >= 6:
                        result.password = code
                        result.save()
                        msg = Message(subject = 'Password Changed',
                                      sender = youremail,
                                      recipients = [result.e_mail],
                                      body = 'Your password has been changed')
                        mail.send(msg)
                        return redirect(url_for('login'))
                    else:
                        return render_template('accountinfo.html')
            else:
                return render_template('accountinfo.html')
        else:
            return render_template('accountinfo.html')
    return render_template('login.html')

'''users route, its called only by advance user, to get a list of the users inserted in the database''' 

@app.route('/users') 
def users():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'advance':
            result = []
            q = Users.query.all()
            for i in q:
                result.append('\nUser: ' + i.username +'\nRights: '+ i.usertype)
            return render_template('users.html', result = '\n'.join(result))
        else:
            return render_template('login.html')
    return render_template('login.html')

'''addrequest route, its called only by simple user, to add a request, if the fields meet the requirements and
 user does not already have a request added''' 
 
@app.route('/addrequest', methods=['GET', 'POST'])
def addrequest():
    if g.user:
        rights = Users.query.filter(Users.username == g.user)
        result = rights.first()
        if result.usertype == 'simple':
            if request.method == 'POST':
                username = session['username']
                first_name = request.form['name']
                last_name = request.form['surname']
                age = request.form['age'] 
                city = request.form['city'] 
                email = request.form['email']
                phone_number = request.form['phone_number']
                job1 = request.form['field1']
                job2 = request.form['field2']
                job3 = request.form['field3']
                job4 = request.form['field4']
                state = 'Not Reviewed'
                jobs_input = [job1, job2, job3, job4]
                jobs_filter = []
                for i in jobs_input:
                    if i not in jobs_filter and i != 'None':
                        jobs_filter.append(i)
                    jobs_final = str(jobs_filter)

                existing_user = Requests.query.filter(Requests.user_name == username)
                result = existing_user.first()
        
                if result is None:
                    if len(first_name) >= 1 and len(last_name) >= 1 and len(age) >= 1 and len(city) >= 1 and len(email) >= 1 and len(phone_number) >= 1 and jobs_final != None:
                        group = Requests(
                                user_name = username,
                                first_name = first_name,
                                last_name = last_name,
                                age = age,
                                city = city,
                                email = email,
                                phone_number = phone_number,
                                job = jobs_final,
                                state = state)
                        db.session.add(group)
                        return redirect(url_for('myrequests'))
                    else:
                        return render_template('addrequest.html')
                else:
                    return render_template('addrequest.html')
            else:
                return render_template('addrequest.html')
        else:
            return render_template('login.html')  
    return render_template('login.html')

'''contact route, if called closes user session and renders contact.html'''
    
@app.route('/contact', methods=['POST', 'GET'])
def contact():
    session.pop('username', None)
    return render_template('contact.html')

'''about route, if called closes user session and renders about.html'''

@app.route('/about')
def about():
    session.pop('username', None)
    return render_template('about.html')

if __name__ == '__main__':
    app.run(debug=True)
    #app.run(host='0.0.0.0', port=80) #here we will put the host ip and an open port when we upload the api