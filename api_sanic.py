import datetime
import random
import aiofiles

import hcskr
import jwt
import openpyxl

from sanic import Sanic
from sanic import response
from sanic.response import json
from sanic.response import redirect
from sdk.api.message import Message
from sdk.exceptions import CoolsmsException
import subprocess
import pickle
import storeconfig
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from sanic_session import Session
from sanic_jinja2 import SanicJinja2



#FireBase
cred = credentials.Certificate('firebasecert.json')
firebase_admin.initialize_app(cred)

db = firestore.client()



#sms
api_key = storeconfig.coolsms_api_key
api_secret = storeconfig.coolsms_api_secret
params = dict()
params['type'] = 'sms'  # Message type ( sms, lms, mms, ata )
params['from'] = storeconfig.coolsms_api_number  # Sender number
cool = Message(api_key, api_secret)

#Sanic
app = Sanic (__name__)
app.config['JSON_AS_ASCII'] = False
Session(app)
jinja = SanicJinja2(app)
app.static('/assets', './assets')


@app.route('/')
async def login(request):
    return response.redirect("/login")

@app.route('/shop')
@jinja.template('index.html')
async def route_shop(request):
    orderid=""
    amout=""
    ordername=""
    customername=""
    return {"TossClientKey":storeconfig.TossClientKey,"orderid":orderid,"amount":amout,"ordername":ordername,"customername":customername}

@app.route('/login')
@jinja.template('login.html')
async def route_login(request):
    return

@app.route("/tokenlogin")
async def route_saveuser(request):
    pass
@app.route('/saveadd',methods = ['POST'])
async def address(request):
    data = request.form
    id=data['userid'][0]
    postalcode = data['postalcode'][0]
    address = data['address'][0]
    building = data['building'][0]
    detail = data['detail'][0]
    d = {id:{"address":f"{address} {detail} ({building}), {postalcode}","didpay":False},"code":"OK"}
    return response.json(d)

@app.route('/payproceed')
async def payproceed(request):
    pass
@app.route('/payfail')
async def payfail(request):
    pass





@app.route('/test', methods = ['POST',"GET"])
async def testroute(request):
    return response.text(request.ip)

@app.route('/ip', methods = ['POST',"GET"])
async def iproute(request):
    return response.text(request.ip)



if __name__ == "__main__":
    ssl_context ={"cert":"./cert/fullchain.pem",'key': "./cert/privkey.pem"}
    app.run(host='0.0.0.0',port=443,ssl=ssl_context,debug=True)