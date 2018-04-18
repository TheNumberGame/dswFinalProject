from flask import Flask, redirect, url_for, session, request, jsonify, Markup, escape
from flask_oauthlib.client import OAuth
from flask import render_template
from flask_socketio import SocketIO, emit
from threading import Lock

import pprint
import os
import json
import pymongo
import gridfs
from datetime import datetime
from bson.objectid import ObjectId


app = Flask(__name__)

#socketio = SocketIO(app, async_mode=None)


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
collection = usr['chat'] #This is contains all posts made
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
        data = user_info.find_one({'user_name': str(name)})
        print(data, name)
        profile_img = ''
        option = ''
        if not data == None and not data['profile_picture'] == '0':
            profile_img = Markup("<img src=\"/img/"+ str(data['profile_picture'])+"\" alt=\"picture\" class=\"proPicture\">")
        else:
            profile_img = Markup("<p>No profile picture</p>")        
        if 'user_data' in session and not data == None:
            if session['user_data']['login'] == name:
                option = Markup("<form action=\"/proPic\" enctype=\"multipart/form-data\" method=\"post\"><br><input name=\"file\" type=\"file\"><br><input type=\"submit\" value=\"submit\"></form>")
            elif name in user_info.find_one({'user_name': session['user_data']['login']})['friends']:
                option = Markup("<form action=\"/unFriend\" method=\"post\"><br><button type=\"submit\" name=\"unFriend\" value= \""+ name +"\">Delete Friend</button></form>")
            else:
                option = Markup("<form action=\"/addFriend\" method=\"post\"><br><button type=\"submit\" name=\"AddFriend\" value= \""+ name +"\">Add Friend</button></form>")
        return render_template('profile.html', profile_pic = profile_img, setting = option)

@app.route('/unFriend' methods=['POST'])
def unfriend():
    user_name = request.form['unFriend']
    user_client_friends = user_info.find_one({'user_name': session['user_data']['login']})['friends']
    user_client_friends.remove(user_name)
    user_info.find_one_and_update({'user_name': session['user_data']['login']}, {'$set': {'friends': user_client_friends}})
    return redirect('/profile/'+user_name)

@app.route('/addFriend' methods=['POST'])
def addFriend():
    user_name = request.form['AddFriend']
    user_client_friends = user_info.find_one({'user_name': session['user_data']['login']})['friends']
    user_client_friends.append(user_name)
    user_info.find_one_and_update({'user_name': session['user_data']['login']}, {'$set': {'friends': user_client_friends}})
    return redirect('/profile/'+user_name)

@app.route('/friends')
def friends():
        return render_template('friends.html')
       
@app.route('/posted', methods=['POST'])
def post():
    if 'file' in request.files and check_extension(request.files['file'].filename):
        fl = request.files['file']
        temp_file_id = fs.put(fl, filename=fl.filename)
    else:
        temp_file_id = None
        
    if not request.form['message'] == "" and not request.form['message'].isspace() or not temp_file_id == None:
        if not temp_file_id == None:
             data = { "_id": ObjectId(), "pic_id": temp_file_id, "name": session['user_data']['login'], "message": escape(request.form['message']), "date": str(datetime.now())}
        else:
            data = { "_id": ObjectId(), "pic_id": "0", "name": session['user_data']['login'], "message": escape(request.form['message']), "date": str(datetime.now())}         
    else:
        return render_template('home.html', message=posts_to_html("Invalid"))
        
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
               option += Markup("<br><button type=\"submit\" name=\"DeletePost\" value= \""+ str(data["_id"]) +"\">Delete Post</button>  <span style=\"color:green;\">Date Posted</span>: "+ str(data["date"]) +"</p>")
          else:
               option += Markup("<br><span style=\"color:green;\">Date Posted</span>: "+ data["date"] +"</p>")
     else:
          option += Markup("<br><span style=\"color:green;\">Date Posted</span>: "+ data["date"] +"</p>")
     return option
        
def posts_to_html(data = None):
     option = ""
     try:
          for i in data.sort('date', -1):
               option += single_post_to_html(i)
     except Exception as e:
          option += str(e)
     return option

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
    
    user_info.find_one_and_update({'user_name': session['user_data']['login']}, {'$set': {'profile_picture': str(temp_file_id)}})
    return redirect(url_for('profile'))


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
                user_info.insert({'user_name': session['user_data']['login'], 'last_login': str(datetime.now()), 'profile_picture': '0','profile_description': '0', 'friends': []})
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
