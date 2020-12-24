import datetime
import openpyxl
import json as mjson
from sanic import Sanic
from sanic import response
from sanic.response import json
from sanic.response import redirect
from sdk.api.message import Message
from sdk.exceptions import CoolsmsException
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
params['type'] = 'lms'
params['from'] = storeconfig.coolsms_api_number  # Sender number
cool = Message(api_key, api_secret)

#Sanic
app = Sanic (__name__)
app.config['JSON_AS_ASCII'] = False
Session(app)
jinja = SanicJinja2(app)
app.static('/assets', './assets')

baserdict={"store_name":storeconfig.store_name,"store_title":storeconfig.store_title,"store_logo":storeconfig.store_logo,"store_description":storeconfig.store_description}


@app.route('/')
async def login(request):
    return response.redirect(f"/login/{storeconfig.default_oauth_provider}")

@app.route('/shop')
@jinja.template('index.html')
async def route_shop(request):
    products = a=db.collection(u"product").get()
    plist=[]
    for p in products:
        plist.append(p.to_dict())
    rdict=baserdict
    rdict.update({"TossClientKey":storeconfig.TossClientKey,"firedata":storeconfig.firebase_web_cert,"plist":plist,"notice_site":storeconfig.notice_site})
    return rdict

@app.route('/login')
async def route_login(request):
    a = '"/twitter"'
    b = '"/discord"'
    return response.html(f"<button onclick='window.location.href = window.location + {a}'>twitter login</button><br><button onclick='window.location.href=window.location + {b}'>discord login</button>")

@app.route('/login/twitter')
@jinja.template('login.twitter.html')
async def route_login_twitter(request):
    rdict=baserdict
    rdict.update({"data": storeconfig.firebase_web_cert})
    return rdict

@app.route('/login/discord')
async def route_login_discord(request):
    try:
        OauthCode = request.args['code'][0]
        print(OauthCode)
        baseurl="https://discord.com/api/oauth2/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': storeconfig.DiscordCilentID,
            'client_secret': storeconfig.DiscordSecret,
            'grant_type': 'authorization_code',
            'code': OauthCode,
            'redirect_uri': f"https://{storeconfig.site_url}/login/discord",
            'scope': 'identify email'
        }
        res=requests.post(baseurl,headers=headers,data=data)
        print(res.json())
        return response.redirect(f"https://{storeconfig.site_url}/tokenlogin?token={res.json()['access_token']}&provider=discord")
    except:
        discordOauthUrl=f"https://discord.com/api/oauth2/authorize?client_id={storeconfig.DiscordCilentID}&redirect_uri=https%3A%2F%2F{storeconfig.site_url}%2Flogin%2Fdiscord&response_type=code&scope=identify%20email"
        return response.redirect(discordOauthUrl)





@app.route("/tokenlogin",methods = ['GET','POST'])
async def route_tokenlogin(request):
    provider=request.args['provider'][0]
    if provider == "twitter":
        data = request.form
        userdata = mjson.loads(data['user'][0])[0]
        id=userdata['uid']
        usertag = requests.get(f"https://api.twitter.com/2/users/{id}", headers={"Authorization": storeconfig.TwitterApiKey}).json()['data']['username']
        ndata = {}

        ndata.update({"usertag": "@" + usertag})

        ndata.update({"token":data['token'][0]})
        ndata.update({"secret":data['secret'][0]})
        ndata.update({"displayname":userdata['displayName']})
        ndata.update({"photoURL": userdata['photoURL']})
        ndata.update({"email":userdata['email']})

    if provider == "discord":
        data = request.args
        access_token=data['token'][0]
        url = 'https://discord.com/api/users/@me'
        res=requests.get(url, headers={"Authorization": f"Bearer {access_token}"}).json()
        id=res['id']
        ndata = {}
        ndata.update({"displayname": res['username']})
        ndata.update({"email": res['email']})
        ndata.update({"photoURL": f"https://cdn.discordapp.com/avatars/{id}/{res['avatar']}.png?size=48"})
        ndata.update({"token": f"{id}-{access_token}"})
        ndata.update({"usertag": res['username']+"#"+res['discriminator']})
    ndata.update({"OauthProvider":provider})
    ndata.update({"updatetime": datetime.datetime.utcnow()})
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
                return json({"code":"0","nickname":doc['displayname'],"photoURL":doc['photoURL'],'usertag':doc['usertag'],"OauthProvider":doc['OauthProvider']})
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

    phonenum=data['phonenum'][0]
    postalcode = data['postalcode'][0]
    address = data['address'][0]
    building = data['building'][0]
    detail = data['detail'][0]
    realname = data['realname'][0]
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

    doc_ref = db.collection(u"users").document(f"{id}")
    doc = doc_ref.get()
    doc = doc.to_dict()
    displayname = doc['displayname']
    usertag = doc['usertag']



    d={"address":finaladdress,"id":id,"prodcode":prodcode,"prodname":prodname,"price":price,"paid":False,"phonenum":phonenum, "displayname":displayname, "name":realname, "usertag":usertag}
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
            receiptUrl=""
            try:
                receiptUrl=receipt['card']['receiptUrl']
            except:
                pass
            doc_ref = db.collection(u"receipts").document(f"{orderid}")
            doc_ref.set(receipt)
            doc_ref = db.collection(u"orders").document(f"{orderid}")
            doc = doc_ref.get()
            d = doc.to_dict()
            d.update({"paid":True,"receiptUrl":receiptUrl,"didsms":False})
            doc_ref.set(d)
            doc_ref = db.collection(u"paid_orders").document(f"{orderid}")
            doc_ref.set(d)
            return redirect(f"/success?orderid={orderid}")
        else:
            return json(res.json())
        print(res)
        print(res.json())
    else:
        return json({"ERROR":"가격 임의 변경"})


@app.route('/payfail')
async def payfail(request):
    return json({"ERROR":"알수없는에러, 문의바랍니다."})

@app.route('/success')
@jinja.template('success.html')
async def success(request):
    try:
        data=request.args
        orderid=data['orderid'][0]
        doc_ref = db.collection(u"orders").document(f"{orderid}")
        doc = doc_ref.get()
        d = doc.to_dict()
        rdict=baserdict
        if d['paid'] == False:
            rdict.update({"text": "주문이 완료되지 않았습니다."})
            return rdict
    except Exception as e:
        rdict.update({"text": "올바르지 않은 접근입니다."})
        return rdict
    st=f"결제계정: {d['usertag']}\n주문번호: {orderid}\n주문상품: {d['prodname']}\n가격: KRW {d['price']}\n배송: {d['address']}\n"
    rdict.update({"text": f"결제계정: {d['usertag']}<br>주문번호: {orderid}<br>주문상품: {d['prodname']}<br>가격: KRW {d['price']}<br>배송: {d['address']}<br> 해당 내용을 주문시 적은 핸드폰으로 발송하였습니다!<br>주문해 주셔서 감사합니다!"})

    params['to'] = d['phonenum']
    receipturl=d["receiptUrl"]
    apiheader = {"X-Naver-Client-Id": storeconfig.naver_api_client_id,"X-Naver-Client-Secret": storeconfig.naver_api_secret}
    res=requests.get("https://openapi.naver.com/v1/util/shorturl",headers=apiheader,params={"url":receipturl})
    shortUrl=res.json()['result']['url']
    params['text'] = f'[{storeconfig.store_name}] 주문이 완료되었습니다!\n{st}영수증: {shortUrl}\n'
    try:
        if not d['didsms']:
            cool.send(params)
            d.update({"didsms": True})
            doc_ref.set(d)
    except CoolsmsException as e:
        return rdict
    return rdict

@app.route('/view', methods = ['POST',"GET"])
async def testroute(request):
    return response.redirect("https://docs.google.com/spreadsheets/d/1bGP3Hp8nRn3H7uv3hCaAYbJb85fqnR_Ueni6fhSssJU/edit?usp=sharing")

@app.route('/ip', methods = ['POST',"GET"])
async def iproute(request):
    return response.text(request.ip)



if __name__ == "__main__":
    ssl_context ={"cert":"./cert/fullchain.pem",'key': "./cert/privkey.pem"}
    app.run(host='0.0.0.0',port=storeconfig.site_port,ssl=ssl_context,debug=True)
