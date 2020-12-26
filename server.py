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
import jinja2
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_formatting import *
import sys


#FireBase
cred = credentials.Certificate('firebasecert.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

credentials = ServiceAccountCredentials.from_json_keyfile_name("firebasecert.json", ['https://spreadsheets.google.com/feeds'])
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_url(storeconfig.spreadsheet_url)

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
app.static('/assets', './assets')

baserdict={"store_name":storeconfig.store_name,"store_title":storeconfig.store_title,"store_logo":storeconfig.store_logo,"store_description":storeconfig.store_description}

templateEnv = jinja2.Environment( loader=jinja2.FileSystemLoader('templates/'))

def init_spreadsheet():
    print("GET WORKSHEET")
    try:
        wsorders=spreadsheet.worksheet('Orders')
    except:
        wsorders=spreadsheet.add_worksheet(title="Orders", rows="1000", cols="11")
    try:
        wsproducts=spreadsheet.worksheet('Products')
    except:
        wsproducts=spreadsheet.add_worksheet(title="Products", rows="1000", cols="5")
    print("FORMAT COLOR-ORDERS")
    wsorders.format('A1:K1', {"backgroundColor": {
      "red": 0.8,
      "green": 1.0,
      "blue": 1.0
    },"horizontalAlignment": "CENTER",'textFormat': {'bold': True},"borders":{
        "top":
            {"style": "SOLID_MEDIUM"},
        "bottom":
            {"style": "SOLID_THICK"},
        "left":
            {"style": "SOLID_MEDIUM"},
        "right":
            {"style": "SOLID_MEDIUM"},
    }})
    print("FORMAT COLOR-PRODUCTS")
    wsproducts.format('A1:E1', {"backgroundColor": {
        "red": 1.0,
        "green": 1.0,
        "blue": 0.8
    }, "horizontalAlignment": "CENTER", 'textFormat': {'bold': True},"borders":{
        "top":
            {"style": "SOLID_MEDIUM"},
        "bottom":
            {"style": "SOLID_THICK"},
        "left":
            {"style": "SOLID_MEDIUM"},
        "right":
            {"style": "SOLID_MEDIUM"}
    }})
    orders_header=['주문일시', '주문고유번호', '상품명', '가격', '주소', '이름', '핸드폰번호', '로그인 방법','로그인 계정', '유저ID', '영주증주소']
    products_header=['상품명', '설명(개행<br>)', '이미지링크(543X543, Imgur)', '가격',"적용하려면 여기를 누르세요"]
    print("FORMAT WIDTHS-ORDERS")
    set_column_width(wsorders, "A", 170)
    set_column_width(wsorders, "B", 240)
    set_column_width(wsorders, "C", 140)
    set_column_width(wsorders, "D", 70)
    set_column_width(wsorders, "E", 450)
    set_column_width(wsorders, "F", 100)
    set_column_width(wsorders, "G", 100)
    set_column_width(wsorders, "H", 100)
    set_column_width(wsorders, "I", 140)
    set_column_width(wsorders, "J", 180)
    set_column_width(wsorders, "K", 180)
    print("FORMAT DATETIME-ORDERS")
    wsorders.format("A1:A1000",{
        "numberFormat":{
            "type": "DATE_TIME"
        }
    })
    print("FORMAT NUMTEXT-ORDERS")
    wsorders.format("G1:G1000",{
        "numberFormat":{
            "type": "TEXT"
        }
    })
    print("FORMAT ALIGNCENTER-ORDERS")
    wsorders.format("A1:K1000",{
        "horizontalAlignment":"CENTER"
    })
    print("FORMAT ALIGNCENTER-PRODUCTS")
    wsproducts.format("A1:E1000", {
        "horizontalAlignment": "CENTER"
    })
    print("FORMAT COLUMN-PRODUCTS")
    set_column_width(wsproducts, "A", 120)
    set_column_width(wsproducts, "B", 430)
    set_column_width(wsproducts, "C", 230)
    set_column_width(wsproducts, "D", 70)
    set_column_width(wsproducts, "E", 200)
    print("INPUT TEXTS-ORDERS")
    wsorders.update('A1:K1', [orders_header])
    print("INPUT TEXTS-PRODUCTS")
    wsproducts.update('A1:E1', [products_header])
    wsproducts.update('E2',"https://"+storeconfig.site_url+"/update")


try:
    opt=sys.argv[1]
    if opt == "init":
        init_spreadsheet()
        print("finish")
except:
    pass

wsorders=spreadsheet.worksheet('Orders')
wsproducts=spreadsheet.worksheet('Products')
@app.route('/')
async def login(request):
    return response.redirect(f"/login/{storeconfig.default_oauth_provider}")

@app.route('/shop')
#@jinja.template('index.html')
async def route_shop(request):
    products = a=db.collection(u"products").get()
    plist=[]
    for p in products:
        plist.append(p.to_dict())
    rdict=baserdict

    footer_icons = ""

    for i in storeconfig.footer_icons:
        icon = i['icon']
        url = i['url']
        footer_icon="""<li>
                <a
                  href="{url}"
                  class="icon style2 {icon}"
                  ></a
                >
              </li>""".format(url=url,icon=icon)
        footer_icons+=footer_icon


    footer_html="""
              <section>
            <h2 style="{style}">Links</h2>
            <ul class="icons">
                {footer_icons}
            </ul>
          </section>
    """.format(style=storeconfig.footer_style,footer_icons=footer_icons)
    if len(storeconfig.footer_icons) < 1:
        footer_html = ""
    rdict.update({"TossClientKey":storeconfig.TossClientKey,"firedata":storeconfig.firebase_web_cert,"plist":plist,"notice_site":storeconfig.notice_site,"modtool_url":storeconfig.spreadsheet_url,"title_style":storeconfig.title_style,"description_style":storeconfig.description_style,"footer_style":storeconfig.footer_style,"footer_html":footer_html})
    template = templateEnv.get_template('index.html')
    return response.html(template.render(rdict))

@app.route('/login')
async def route_login(request):
    rdict = baserdict
    rdict.update({"data": storeconfig.firebase_web_cert, "storeconfig": storeconfig})
    template = templateEnv.get_template('login.select.html')
    return response.html(template.render(rdict))

@app.route('/login/<oauth_provider>')
#@jinja.template('login.html')
async def route_login_given_provider(request,oauth_provider):
    if oauth_provider == "twitter":
        rdict=baserdict
        rdict.update({"data": storeconfig.firebase_web_cert,"storeconfig":storeconfig})
        template = templateEnv.get_template('login.html')
        return response.html(template.render(rdict))

    elif oauth_provider == "discord":
        try:
            OauthCode = request.args['code'][0]
            print(OauthCode)
            baseurl = "https://discord.com/api/oauth2/token"
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data = {
                'client_id': storeconfig.DiscordCilentID,
                'client_secret': storeconfig.DiscordSecret,
                'grant_type': 'authorization_code',
                'code': OauthCode,
                'redirect_uri': f"https://{storeconfig.site_url}/login/discord",
                'scope': 'identify email'
            }
            res = requests.post(baseurl, headers=headers, data=data)
            print(res.json())
            return response.redirect(
                f"https://{storeconfig.site_url}/tokenlogin?token={res.json()['access_token']}&provider=discord")
        except:
            discordOauthUrl = f"https://discord.com/api/oauth2/authorize?client_id={storeconfig.DiscordCilentID}&redirect_uri=https%3A%2F%2F{storeconfig.site_url}%2Flogin%2Fdiscord&response_type=code&scope=identify%20email"
            return response.redirect(discordOauthUrl)






@app.route("/tokenlogin",methods = ['GET','POST'])
async def route_tokenlogin(request):
    provider=request.args['provider'][0]

    if provider == "discord":
        data = request.args
        access_token=data['token'][0]
        url = 'https://discord.com/api/users/@me'
        res=requests.get(url, headers={"Authorization": f"Bearer {access_token}"}).json()
        id=res['id']
        ndata = {}
        ndata.update({"displayname": res['username']})
        ndata.update({"email": res['email']})
        ndata.update({"photoURL": f"https://cdn.discordapp.com/avatars/{id}/{res['avatar']}.png?size=64"})
        ndata.update({"token": f"{id}-{access_token}"})
        ndata.update({"usertag": res['username']+"#"+res['discriminator']})
    elif provider == "twitter.com":
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
    else:
        data = request.form

        userdata = mjson.loads(data['user'][0])[0]
        id=userdata['uid']
        ndata = {}
        ndata.update({"displayname": userdata['displayName']})
        ndata.update({"email": userdata['email']})
        ndata.update({"photoURL": f"{userdata['photoURL']}"})
        ndata.update({"token": f"{id}-{data['token'][0]}"})
        ndata.update({"usertag": userdata['displayName']})
    ndata.update({"OauthProvider":provider.split(".")[0]})
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
                modtool = False
                if int(id) in storeconfig.moderator_ids:
                    modtool=True
                return json({"code":"0","nickname":doc['displayname'],"photoURL":doc['photoURL'],'usertag':doc['usertag'],"OauthProvider":doc['OauthProvider'],"modtool":modtool})
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

    doc_ref = db.collection(u"products").document(f"{prodcode}")
    doc = doc_ref.get()
    doc = doc.to_dict()
    prodname=doc['name']
    price=doc['price']

    doc_ref = db.collection(u"users").document(f"{id}")
    doc = doc_ref.get()
    doc = doc.to_dict()
    displayname = doc['displayname']
    usertag = doc['usertag']
    OauthProvider = doc['OauthProvider']



    d={"address":finaladdress,"id":id,"prodcode":prodcode,"prodname":prodname,"price":price,"paid":False,"phonenum":phonenum, "displayname":displayname, "name":realname, "usertag":usertag, "OauthProvider":OauthProvider}
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
            try:
                apiheader = {"X-Naver-Client-Id": storeconfig.naver_api_client_id,
                             "X-Naver-Client-Secret": storeconfig.naver_api_secret}
                res = requests.get("https://openapi.naver.com/v1/util/shorturl", headers=apiheader,
                                   params={"url": receiptUrl})
                receiptUrl = res.json()['result']['url']
            except:
                pass
            d.update({"paid":True,"receiptUrl":receiptUrl,"didsms":False})
            doc_ref.set(d)
            doc_ref = db.collection(u"paid_orders").document(f"{orderid}")
            doc_ref.set(d)
            spreadsheet_time=datetime.datetime.now().timestamp() / 86400 + 365 * 70 + 19 + 9 / 24
            wsorders.append_row([spreadsheet_time,orderid,d['prodname'],d['price'],d['address'],d['name'],d['phonenum'],d['OauthProvider'],d['usertag'],d['id'],receiptUrl])
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
#@jinja.template('success.html')
async def success(request):
    rdict = baserdict
    try:
        data=request.args
        orderid=data['orderid'][0]
        doc_ref = db.collection(u"orders").document(f"{orderid}")
        doc = doc_ref.get()
        d = doc.to_dict()
        if d['paid'] == False:
            rdict.update({"text": "주문이 완료되지 않았습니다."})
            template = templateEnv.get_template('success.html')
            return response.html(template.render(rdict))
    except Exception as e:
        rdict.update({"text": "올바르지 않은 접근입니다."})
        template = templateEnv.get_template('success.html')
        return response.html(template.render(rdict))
    st=f"결제계정: {d['usertag']}\n주문번호: {orderid}\n주문상품: {d['prodname']}\n가격: KRW {d['price']}\n배송: {d['address']}\n"
    rdict.update({"text": f"결제계정: {d['usertag']}<br>주문번호: {orderid}<br>주문상품: {d['prodname']}<br>가격: KRW {d['price']}<br>배송: {d['address']}<br> 해당 내용을 주문시 적은 핸드폰으로 발송하였습니다!<br>주문해 주셔서 감사합니다!"})

    params['to'] = d['phonenum']
    receipturl=d["receiptUrl"]

    params['text'] = f'[{storeconfig.store_name}] 주문이 완료되었습니다!\n{st}영수증: {receipturl}\n'
    try:
        if not d['didsms']:
            cool.send(params)
            d.update({"didsms": True})
            doc_ref.set(d)
    except CoolsmsException as e:
        pass
    template = templateEnv.get_template('success.html')
    return response.html(template.render(rdict))

@app.route("/update")
async def update_products(request):
    plist=wsproducts.get_all_values()
    plist.pop(0)
    alldoc = db.collection("products").get()
    for doc in alldoc:
        doc = db.collection("products").document(doc.id)
        doc.delete()
    for i in range(len(plist)):
        doc=db.collection("products").document(f"{i+1}")
        product_dict={"name":plist[i][0],"content":plist[i][1],"imgsrc":plist[i][2],"price":plist[i][3]}
        doc.set(product_dict)
    return response.redirect("/shop")


@app.route('/test', methods = ['POST',"GET","DELETE"])
async def testroute(request):
    a=request.json
    print(a)

    return json({"json":a})



if __name__ == "__main__":
    ssl_context ={"cert":"./cert/fullchain.pem",'key': "./cert/privkey.pem"}
    app.run(host='0.0.0.0',port=storeconfig.site_port,ssl=ssl_context,debug=True)
