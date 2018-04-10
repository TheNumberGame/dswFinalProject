from flask import Flask, redirect, url_for, session, request, jsonify, Markup, escape
from flask_oauthlib.client import OAuth
from flask import render_template

import pprint
import os
import json
import pymongo
import gridfs
from datetime import datetime
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
collection = usr['chat']

fs = gridfs.GridFS(usr, 'pictures')

github = oauth.remote_app(
    'github', consumer_key=os.environ['GITHUB_CLIENTID'], #your web app's "username" for github's OAuth
    consumer_secret=os.environ['GITHUB_CLIENT_SECRET'],#your web app's "password" for github's OAuth
    request_token_params={'scope': 'user:email'}, #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',  
    authorize_url='https://github.com/login/oauth/authorize' #URL for github's OAuth login
)

VALID_EXTENSIONS = ['jpeg', 'png']

@app.context_processor
def inject_logged_in():
    return {"logged_in":('github_token' in session)}

@app.route('/login')
def login():   
    return github.authorize(callback=url_for('authorized', _external=True, _scheme='https')) #callback URL must match the pre-configured callback URL

@app.route('/')
def home():
        return render_template('home.html', message=posts_to_html(collection.find()))

@app.route('/posted', methods=['POST'])
def post():
    if 'file' in request.files and check_extension(request.files['file']):
        fl = request.files['file']
        temp_file_id = fs.put(fl, filename=fl.filename)
    else:
        temp_file_id = None
        
    if not request.form['message'] == "" and not request.form['message'].isspace():
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
     return False:
        

def posts_to_html(data = None):
     option = ""
     try:
          session['user_data']
          try:
               for i in data.sort([("date", -1)]):
                    if not i['pic_id'] == "0":
                         option += Markup("<img src=\"/img/"+ fs.get(i['pic_id']).filename+"\" alt=\"picture\" height=\"50\" width=\"50\">")
                    option += Markup("<p class=\"mes\" ><span style=\"color:blue;\">" + i["name"] + "</span>: " + i["message"]) 
                    if i['name'] == session['user_data']['login']:
                         option += Markup("<br><button type=\"submit\" name=\"DeletePost\" value= \""+ str(i["_id"]) +"\">Delete Post</button>  <span style=\"color:green;\">Date Posted</span>: "+ str(i["date"]) +"</p>")
                    else:
                         option += Markup("<br><span style=\"color:green;\">Date Posted</span>: "+ str(i["date"]) +"</p>")
          except:
               return option
     except:
          try:
               for i in data.sort([("date", -1)]):
                    option += Markup("<p class=\"mes\" ><span style=\"color:blue;\">" + i["name"] + "</span>: " + i["message"]+"<br><span style=\"color:green;\">Date Posted</span>: "+ str(i["date"]) +"</p>") 
          except:
               return data
     return option


@app.route('/b', methods=['POST'])
def delPost():
    docId = request.form['DeletePost']
    
    collection.delete_one({'_id': ObjectId(docId)})
   
    return redirect(url_for("home"))


@app.route("/img/<filename>")
def post_img(filename):
     image = fs.get_latest_version(filename=filename)
     response.content_type = 'image/'+ filename.split('.')[1]
     return image


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
            session['github_token'] = (resp['access_token'], '') #save the token to prove that the user logged in
            session['user_data']=github.get('user').data
            message='You were successfully logged in as ' + session['user_data']['login']
        except Exception as inst:
            session.clear()
            print(inst)
            message='Unable to login, please try again.  '
    return render_template('home.html', message=message)

@github.tokengetter
def get_github_oath_token():
     return session.get('github_token')

if __name__ == '__main__':
    app.run()
