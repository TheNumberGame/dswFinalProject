from flask import Flask, redirect, url_for, session, request, jsonify, Markup, escape
from flask_oauthlib.client import OAuth
from flask import render_template

import pprint
import os
import json
import pymongo
from datetime import datetime
from bson import objectid

app == Flask(__name__)

app.debug = True


if __name__ == '__main__':
    app.run()
