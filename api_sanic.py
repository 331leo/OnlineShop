import datetime
import random
import aiofiles

import hcskr
import jwt
import openpyxl
import json as mjson
from sanic import Sanic
from sanic import response
from sanic.response import json
from sanic.response import redirect
from sdk.api.message import Message
from sdk.exceptions import CoolsmsException
import subprocess
import pickle
import pytz
import storeconfig
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from sanic_session import Session
from sanic_jinja2 import SanicJinja2
import requests


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
    return {"data":storeconfig.firebase_web_cert}


@app.route("/tokenlogin",methods = ['POST'])
async def route_tokenlogin(request):

    data = request.form
    userdata = mjson.loads(data['user'][0])[0]
    id=userdata['uid']
    ndata={}
    ndata.update({"token":data['token'][0]})
    ndata.update({"secret":data['secret'][0]})
    ndata.update({"displayname":userdata['displayName']})
    ndata.update({"photoURL": userdata['photoURL']})
    ndata.update({"email":userdata['email']})
    ndata.update({"updatetime":datetime.datetime.utcnow()})
    print(id)
    print(ndata)
    dbdoc = db.collection(f"users").document(f"{id}")
    dbdoc.set(ndata)
    return response.redirect(f"/shop?token={ndata['token']}")

@app.route("/verifytoken",methods = ['POST'])
async def route_verify_token(request):
    data = request.form
    token = data['token'][0]
    id = token.split("-")[0]

    timeout = 2000
    doc_ref = db.collection(u"users").document(f"{id}")
    try:
        doc = doc_ref.get()
        doc = doc.to_dict()
        token_time=doc['updatetime']
        now=datetime.datetime.utcnow()
        now=now.replace(tzinfo=pytz.UTC)
        td=now-token_time
        print(td.seconds)
        if td.seconds<2000:
            if doc['token'] == token:
                return json({"code":"0","nickname":doc['displayname'],"photoURL":doc['photoURL']})
            else:
                return json({"code": "3"})
        else:
            return json({"code":"1"})
    except Exception as e:
        print(f'{e}')
        return json({"code":"2"})


@app.route('/buying',methods = ['POST'])
async def buying(request):
    data = request.form
    id=data['userid'][0]
    prodcode = data['prodcode'][0]


    postalcode = data['postalcode'][0]
    address = data['address'][0]
    building = data['building'][0]
    detail = data['detail'][0]
    finaladdress=f"{address} {detail} ({building}), {postalcode}"

    now = datetime.datetime.utcnow()
    now = now.replace(tzinfo=pytz.UTC)
    day=str(now)[2:19].replace("-","").replace(" ","").replace(":","")
    order_num=f"{id}_{day}"

    doc_ref = db.collection(u"product").document(f"{prodcode}")
    doc = doc_ref.get()
    doc = doc.to_dict()
    prodname=doc['name']
    price=doc['price']


    d={"address":finaladdress,"id":id,"prodcode":prodcode,"prodname":prodname,"price":price,"paid":False}
    dbdoc = db.collection(f"orders").document(f"{order_num}")
    dbdoc.set(d)
    d.update({"order_num":order_num})
    return response.json(d)

@app.route('/payproceed',methods = ['POST',"GET"])
async def payproceed(request):
    data=request.args
    paymentkey=data['paymentKey'][0]
    orderid=data['orderId'][0]
    amount=data['amount'][0]

    doc_ref = db.collection(u"orders").document(f"{orderid}")
    doc = doc_ref.get()
    doc = doc.to_dict()
    price=doc['price']
    if amount == str(price):
        headers={'Authorization':storeconfig.TossBasicAuthKey,'Content-Type': 'application/json'}
        data={"orderId":orderid,"amount":price}
        res = requests.post(f"https://api.tosspayments.com/v1/payments/{paymentkey}",headers=headers,json=data)
        if res.status_code == requests.codes.ok:
            receipt=res.json()
            doc_ref = db.collection(u"receipts").document(f"{orderid}")
            doc_ref.set(receipt)
            doc_ref = db.collection(u"orders").document(f"{orderid}")
            doc = doc_ref.get()
            d = doc.to_dict()
            d.update({"paid":True})
            doc_ref.set(d)
            return redirect("/success")
        else:
            return json(res.json())
        print(res)
        print(res.json())
    else:
        return json({"ERROR":"가격 임의 변경"})

@app.route('/success')
@jinja.template('login.html')
async def success(request):
    return {}
@app.route('/payfail')
async def payfail(request):
    return json({"ERROR":"알수없는에러, 문의바랍니다."})





@app.route('/test', methods = ['POST',"GET"])
async def testroute(request):
    return response.text(request.ip)

@app.route('/ip', methods = ['POST',"GET"])
async def iproute(request):
    return response.text(request.ip)



if __name__ == "__main__":
    ssl_context ={"cert":"./cert/fullchain.pem",'key': "./cert/privkey.pem"}
    app.run(host='0.0.0.0',port=443,ssl=ssl_context,debug=True)