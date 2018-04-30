from flask import Flask, redirect, url_for, session, request, jsonify, Markup, escape
from flask_oauthlib.client import OAuth
from flask import render_template

import pprint
import os
import json
import pymongo
import gridfs
from datetime import datetime, timezone, timedelta
from bson.objectid import ObjectId


app = Flask(__name__)


app.debug = True

oauth = OAuth(app)
app.secret_key = os.environ['SECRET_KEY']

url = 'mongodb://{}:{}@{}:{}/{}'.format(
        os.environ["MONGO_USERNAME"],
        os.environ["MONGO_PASSWORD"],
        os.environ["MONGO_HOST"],
        os.environ["MONGO_PORT"],
        os.environ["MONGO_DBNAME"])
clt = pymongo.MongoClient(url)
usr = clt[os.environ["MONGO_DBNAME"]]
collection = usr['chat'] #This is contains all posts made to main feed
reply = usr['reply'] #contains the replys to chat
user_info = usr['user_data'] #contains user data
fs = gridfs.GridFS(usr, 'pictures') #This contains the pictures

github = oauth.remote_app(
    'github', consumer_key=os.environ['GITHUB_CLIENTID'], 
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],
    request_token_params={'scope': 'user:email'}, 
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' 
)

VALID_EXTENSIONS = ['jpeg', 'png', 'jpg', 'PNG']
PST = timezone(timedelta(hours=-7), name='PST')

@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/login')
def login():   
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='https'))

@app.route('/')
def home():
        return render_template('home.html', posts=posts_to_html(collection.find()))

@app.route('/profile/<name>')
def profile(name = None):
        feed = ''
        data = user_info.find_one({'user_name': str(name)})
        profile_img = ''
        option = ''
        profile_bio = ''
        if not data == None and not data['profile_picture'] == '0':
            profile_img = Markup("<img src=\"/img/"+ str(data['profile_picture'])+"\" alt=\"picture\" class=\"proPicture\">")
        else:
            profile_img = Markup("<p>No profile picture</p>")      
        
        if not data == None and not data['profile_description'] == '0':
            profile_bio = Markup("<p>"+ data['profile_description'] +"</p>")
        else:
            profile_bio = Markup("<p>No Profile Bio</p>")
           
        if 'user_data' in session and not data == None:
            for i in collection.find().sort('date', -1):
                if i['name'] == name:
                    feed += single_post_to_html(i)
            if session['user_data']['login'] == name:
                profile_bio += Markup("<br><form action=\"/bio\" method=\"post\"><textarea name=\"Bio\" style=\"width:100%; height:100px;\"></textarea><input type=\"submit\" value=\"Change Bio\"></form>")
                option = Markup("<form action=\"/proPic\" enctype=\"multipart/form-data\" method=\"post\"><br><input name=\"file\" type=\"file\"><br><input type=\"submit\" value=\"Change Profile Picture\"></form>")
            elif name in user_info.find_one({'user_name': session['user_data']['login']})['following']:
                option = Markup("<form action=\"/unFriend\" method=\"post\"><br><button type=\"submit\" name=\"unFriend\" value= \""+ name +"\">UnFollow</button></form>")
            else:
                option = Markup("<form action=\"/addFriend\" method=\"post\"><br><button type=\"submit\" name=\"AddFriend\" value= \""+ name +"\">Follow</button></form>")
        return render_template('profile.html', profile_pic = profile_img,name = name, setting = option, description = profile_bio, posts = feed)

@app.route('/bio', methods=['POST'])
def profile_description():
    mes = request.form['Bio']
    if not mes == "" and not mes.isspace():
        user_info.find_one_and_update({'user_name': session['user_data']['login']}, {'$set': {'profile_description': mes}})
    return redirect('/profile/'+session['user_data']['login'])

@app.route('/unFriend', methods=['POST'])
def unfriend():
    user_name = request.form['unFriend']
    user_client_friends = user_info.find_one({'user_name': session['user_data']['login']})['following']
    user_client_friends.remove(user_name)
    user_info.find_one_and_update({'user_name': session['user_data']['login']}, {'$set': {'following': user_client_friends}})
    user_client_friends = user_info.find_one({'user_name': user_name})['followers']
    user_client_friends.remove(session['user_data']['login'])
    user_info.find_one_and_update({'user_name': user_name}, {'$set': {'followers': user_client_friends}})
    return redirect('/profile/'+user_name)

@app.route('/addFriend', methods=['POST'])
def addFriend():
    user_name = request.form['AddFriend']
    user_client_friends = user_info.find_one({'user_name': session['user_data']['login']})['following']
    user_client_friends.append(user_name)
    user_info.find_one_and_update({'user_name': session['user_data']['login']}, {'$set': {'following': user_client_friends}})
    user_client_friends = user_info.find_one({'user_name': user_name})['followers']
    user_client_friends.append(session['user_data']['login'])
    user_info.find_one_and_update({'user_name': user_name}, {'$set': {'followers': user_client_friends}})
    return redirect('/profile/'+user_name)

@app.route('/friends')
def friends():
        data = user_info.find_one({'user_name': session['user_data']['login']})
        feed = ""
        option = Markup("<ul>")
        for i in data['following']:
            option += Markup("<li><a href=\"/profile/"+ i +"\">"+ i +"</a></li>")
        option += Markup("</ul>")
        for i in collection.find().sort('date', -1):
            if i['name'] in data['following']:
                feed += single_post_to_html(i)
        return render_template('friends.html', Following = option, posts = feed)

@app.route('/follower')
def follower():
     data = user_info.find_one({'user_name': session['user_data']['login']})
     option = Markup("<ul>")
     for i in data['followers']:
         option += Markup("<li><a href=\"/profile/"+ i +"\">"+ i +"</a></li>")
     option += Markup("</ul>")
     return render_template('follower.html', follow = option)

@app.route('/posted', methods=['POST'])
def post():
    if 'file' in request.files and check_extension(request.files['file'].filename):
        fl = request.files['file']
        temp_file_id = fs.put(fl, filename=fl.filename)
    else:
        temp_file_id = None
     
    message = request.form['message']
    
    if not message == "" and not message.isspace() and len(message) < 251 or not temp_file_id == None:
        if not temp_file_id == None:
             data = { "_id": ObjectId(), "pic_id": temp_file_id, "name": session['user_data']['login'], "message": escape(message), "date": str(datetime.now()), "replys": []}
        else:
            data = { "_id": ObjectId(), "pic_id": "0", "name": session['user_data']['login'], "message": escape(message), "date": str(datetime.now())}         
    else:
        if len(message) > 251:
            return render_template('home.html', message=posts_to_html("Must be less than 251 characters."))
        elif message == "" and message.isspace() or temp_file_id == None:
            return render_template('home.html', message=posts_to_html("There is no text or picture."))
        else:
            return render_template('home.html', message=posts_to_html("Unknown Error."))
        
    collection.insert(data)
    
    return redirect(url_for("home"))

def check_extension(ext):
     if ext.split(".")[1] in VALID_EXTENSIONS:
        return True
     return False
        
def single_post_to_html(data = None):
     option = Markup("<p class=\"mes\" ><span style=\"color:blue;\"><a href=\"/profile/"+ str(data['name']) +"\">" + data["name"] + "</a></span>: ")
     if not data['pic_id'] == '0':
          option += Markup("<img src=\"/img/"+ str(data['pic_id'])+"\" alt=\"picture\" class=\"imgPost\">"+ data["message"])
     else:
          option += data['message']
     if 'user_data' in session:
          if data['name'] == session['user_data']['login']:
               option += Markup("<br><button type=\"submit\" name=\"DeletePost\" form=\"deleteForm\" value= \""+ str(data["_id"]) +"\">Delete Post</button>  <span style=\"color:green;\">Date Posted</span>: "+ date_of_post(data["date"]) +"</p>")
          else:
               option += Markup("<br><button class=\"toTextBox\" type=\"button\" name=\"ReplyPost\" value= \""+ str(data["_id"]) +"\">Reply</button><span style=\"color:green;\">Date Posted</span>: "+ date_of_post(data["date"]) +"</p>")
     else:
          option += Markup("<br><span style=\"color:green;\">Date Posted</span>: "+ date_of_post(data["date"]) +"</p>")
     return option
        
def posts_to_html(data = None):
     option = ""
     try:
          for i in data.sort('date', -1):
               option += single_post_to_html(i)
     except:
          option += data
     return option

def date_of_post(date = None):
     temp_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
     today_date = datetime.now()
     if temp_date.day == today_date.day and temp_date.month == today_date.month and temp_date.year == today_date.year:
          if today_date.hour-temp_date.hour == 0:
               if today_date.minute-temp_date.minute == 0:
                    return 'Just Now.'
               return str(today_date.minute-temp_date.minute) +' minutes ago.'
          return str(today_date.hour-temp_date.hour)+' hours ago.'
     else:
          temp_date = temp_date.astimezone(PST)
          return str(temp_date.year)+'-'+str(temp_date.month)+'-'+str(temp_date.day)

@app.route('/reply', methods=['POST'])
def reply_to_post():
    if 'file' in request.files and check_extension(request.files['file'].filename):
        fl = request.files['file']
        temp_file_id = fs.put(fl, filename=fl.filename)
    else:
        temp_file_id = None
    
    main_post = request.form['MainPost']
    message = request.form['ReplyPost']
    
    if not message == "" and not message.isspace() and len(message) < 251 or not temp_file_id == None:
        if not temp_file_id == None:
             data = { "_id": ObjectId(), "pic_id": temp_file_id, "name": session['user_data']['login'], "message": escape(message), "date": str(datetime.now()), "replys": []}
        else:
            data = { "_id": ObjectId(), "pic_id": "0", "name": session['user_data']['login'], "message": escape(message), "date": str(datetime.now())}         
    else:
        if len(message) > 251:
            return render_template('home.html', message=posts_to_html("Must be less than 251 characters."))
        elif message == "" and message.isspace() or temp_file_id == None:
            return render_template('home.html', message=posts_to_html("There is no text or picture."))
        else:
            return render_template('home.html', message=posts_to_html("Unknown Error."))
    
    temp_reply = collection.find_one({"_id": ObjectId(main_post)})['replys']
    temp_reply.append(data['_id'])
    collection.find_one_and_update({"_id": ObjectId(main_post)}, {'$set': {"replys": temp_reply}})    
    reply.insert(data)
    return redirect(url_for("home"))

@app.route('/searchPerson')        
def search_person():
     name = request.args['search']
     if user_info.find_one({'user_name': name}) == None:
          return redirect('/')
     return redirect('/profile/'+name)

@app.route('/b', methods=['POST'])
def delPost():
    doc_id = request.form['DeletePost']
    
    db_doc = collection.find_one_and_delete({'_id': ObjectId(doc_id)})
    if not db_doc['pic_id'] == '0':
         fs.delete({'_id': ObjectId(db_doc['pic_id'])})
   
    return redirect(url_for("home"))


@app.route("/img/<filename>")
def post_img(filename = None):
     image = fs.find_one({'_id': ObjectId(filename)})
     return image.read()

@app.route("/proPic", methods=['POST'])
def update_profile_pic():
    if 'file' in request.files and check_extension(request.files['file'].filename):
        fl = request.files['file']
        temp_file_id = fs.put(fl, filename=fl.filename)
    else:
        temp_file_id = '0'
    if user_info.find_one({'user_name': session['user_data']['login']})['profile_picture'] == '0':
        user_info.update_one({'user_name': session['user_data']['login']}, {'$set': {'profile_picture': str(temp_file_id)}})
    return redirect('/profile/'+session['user_data']['login'])


@app.route('/logout')
def logout():
    session.clear()
    return render_template('home.html', message='You were logged out')


@app.route('/login/authorized')
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        message = 'Access denied: reason=' + request.args['error'] + ' error=' + request.args['error_description'] + ' full=' + pprint.pformat(request.args)      
    else:
        try:
            session['github_token'] = (resp['access_token'], '')
            session['user_data']=github.get('user').data
            if user_info.find_one({'user_name': session['user_data']['login']}) == None:
                user_info.insert({'user_name': session['user_data']['login'], 'last_login': str(datetime.now()), 'profile_picture': '0','profile_description': '0', 'following': [], 'followers': []})
            message='You were successfully logged in as ' + session['user_data']['login']
        except Exception as inst:
            session.clear()
            print(inst)
            message='Unable to login, please try again.  '
    return render_template('home.html', message=message, posts=posts_to_html(collection.find()))

@github.tokengetter
def get_github_oath_token():
     return session.get('github_token')

if __name__ == '__main__':
    app.run()
