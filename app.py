from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask_sqlalchemy import SQLAlchemy


# -----------------------------------
# -------------- FLASK --------------
# -----------------------------------

app = Flask(__name__)

app.secret_key = b'\x1c\xe1\xe7\x16Ja\xce\x889\x05\xcd\xcd'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://login:password@localhost/fkdatabase'
db = SQLAlchemy(app)

app.app_context().push()

admin_username = "login"
admin_passw = "passw"

# -------------------------------------
# --------------DATABASE---------------
# -------------------------------------

class Affiliate(db.Model):
    __table__ = db.Table('affiliate', db.metadata, autoload_with=db.engine)


    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

class PromoCode(db.Model):
    __table__ = db.Table('promocodes', db.metadata, autoload_with=db.engine)
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_promocode(cls, code):
        return cls.query.filter_by(code=code).first()

    def increament_promo(self):
        self.timesUsed += 1
        db.session.commit()

    @classmethod
    def check_promo(cls, code):
        promo = cls.get_promocode(code)
        if promo != None:
            promo.increament_promo()
            return promo.discount
        else:
            return False

    @classmethod
    def delete_promo(cls, promo_id):
        if cls.query.filter_by(id=promo_id).first() != None:
            db.session.delete(cls.query.filter_by(id=promo_id).first())
            db.session.commit()
        else:
            pass

    @classmethod
    def save_promocode(cls, code, discount):
        cls(code=code, discount=discount, timesUsed=0).save_to_db()

    @classmethod
    def get_promocodes(cls):
        return [{"id":i.id,"code":i.code,"discount":i.discount, "timesUsed":i.timesUsed} for i in cls.query.all()]


class Order(db.Model):
    __table__ = db.Table('orders', db.metadata, autoload_with=db.engine)
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def mark_as_done(cls, orderid):
        order = cls.query.filter_by(orderId=orderid).first()
        order.status = 'DONE'
        db.session.commit()

    @classmethod
    def save_order(cls, orderid, orderinfo, status, order_date):
        status = "DONE" if status else "NOT DONE"
        orderContent = json.dumps(orderinfo)
        if orderid.endswith("addServ"):
            orderinfo['ordername'] = orderinfo['ordername'].replace("EMAIL", "PAPER") if 'EMAIL' in orderinfo[
                'ordername'] else orderinfo['ordername'].replace("PAPER", "EMAIL")
        cls(orderId=orderid, orderContent=orderContent, status=status, order_date=order_date, email=orderinfo['email'], order_name=orderinfo['ordername']).save_to_db()

    @classmethod
    def get_orders(cls, done=None, email=None):
        if done == None and email == None:
            response = cls.query.order_by(cls.order_date.desc()).all()
        elif done == False and email == None:
            response = cls.query.filter_by(status="NOT DONE").order_by(cls.order_date.desc()).all()
        elif done == None and email != None:
            response = cls.query.filter_by(email=email).order_by(cls.order_date.desc()).all()
        elif done == False and email != None:
            response = cls.query.filter_by(status="NOT DONE").filter_by(email=email).order_by(cls.order_date.desc()).all()
        return [{"orderId": i.orderId, "orderContent": i.orderContent, "status": i.status, "order_date": i.order_date, "email": i.email,
                 "order_name": i.order_name} for i in response]

    @classmethod
    def get_order(cls, orderid):
        order = cls.query.filter_by(orderId=orderid).first()
        if order == None:
            return order
        else:
            return {"orderId": order.orderId, "orderContent": order.orderContent, "status": order.status, "order_date": order.order_date,
                    "email": order.email, "order_name": order.order_name}

class Item(db.Model):
    __table__ = db.Table('items', db.metadata, autoload_with=db.engine)
    best_items = ['BEST MOUSE', 'BEST Graphic Card', 'BEST COMPUTER']

    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def create_item(cls, requiredInfo, description, url, thumbnailUrl, itemName, type, price):
        if Question.questions_for_item(requiredInfo.split(',')) == None:
            raise Exception
        cls(requiredInfo=requiredInfo, description=description, url=url, thumbnailUrl=thumbnailUrl, itemName=itemName, type=type, price=price).save_to_db()

    @classmethod
    def delete_item(cls, itemid):
        if cls.query.filter_by(id=itemid).first() != None:
            db.session.delete(cls.query.filter_by(id=itemid).first())
            db.session.commit()
        else:
            raise Exception

    @classmethod
    def get_best_items(cls):
        return [{"thumbnailUrl": i.thumbnailUrl, "itemName": i.itemName, 'id': i.id, 'type': i.type} for i in cls.query.filter(cls.itemName.in_(cls.best_items)).all()]

    @classmethod
    def get_items(cls, item_type):
        if item_type == 'all':
            return [{"thumbnailUrl": i.thumbnailUrl, "itemName": i.itemName, 'id': i.id, 'type': i.type, 'url':i.url} for i in Item.query.all()]
        else:
            return [{"thumbnailUrl": i.thumbnailUrl, "itemName": i.itemName, 'id': i.id, 'type': i.type, "url":i.url} for i in
                    Item.query.filter_by(type=item_type)]
    @classmethod
    def get_item(cls, itemid):
        item = cls.query.filter_by(id=itemid).first()
        return {
            'id': item.id,
            "requiredInfo": zip(item.requiredInfo.split(","), Question.questions_for_item(item.requiredInfo.split(","))),
            'description': item.description,
            "url": item.url,
            'itemName': item.itemName,
            "type": item.type,
            "price": item.price
        }


class Question(db.Model):
    __table__ = db.Table('questions', db.metadata, autoload_with=db.engine)
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_question(cls, itemKey):
        question = cls.query.filter_by(itemKey=itemKey).first()
        if question == None:
            return question
        else:
            return question.itemQuestion

    @classmethod
    def questions_for_item(cls, keys: list):
        ret = []
        for i in keys:
            answer = cls.get_question(i)
            if answer == None:
                print(f"Doesnt exist - {i}")
                return
            ret.append(answer)
        return ret

    @classmethod
    def get_all_questions(cls):
        return [{"itemKey":i.itemKey, "itemQuestion":i.itemQuestion} for i in cls.query.all()]

    @classmethod
    def create_question(cls, itemKey, itemQuestion):
        if cls.query.filter_by(itemKey=itemKey).first() == None:
            cls(itemKey=itemKey, itemQuestion=itemQuestion).save_to_db()
        else:
            raise Exception
    @classmethod
    def delete_question(cls, itemKey):
        if cls.query.filter_by(itemKey=itemKey).first() != None:
            db.session.delete(cls.query.filter_by(itemKey=itemKey).first())
            db.session.commit()
        else:
            raise Exception

class Group(db.Model):
    __table__ = db.Table('fkgroups', db.metadata, autoload_with=db.engine)
    def save_to_db(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def get_groups(cls):
        return [name for name, in cls.query.with_entities(cls.groupName).all()]

    @classmethod
    def add_group(cls, group):
        if cls.query.filter_by(groupName=group).first() == None:
            cls(groupName=group).save_to_db()
        else:
            raise Exception

    @classmethod
    def delete_group(cls, group):
        if cls.query.filter_by(groupName=group).first() == None:
            raise Exception
        else:
            db.session.delete(cls.query.filter_by(groupName=group).first())
            db.session.commit()

# -----------------------------------------
# -------------- ADD PROGRAMS -------------
# -----------------------------------------

def get_date():
    current_datetime = datetime.now()

    formatted_date_time = current_datetime.strftime("%d.%m.%Y %H:%M")

    return formatted_date_time

def is_mobile():
    agent = request.headers.get('User-Agent').lower()
    if 'mobile' in agent or 'android' in agent or 'iphone' in agent:
        return True
    else:
        return False

def get_confirmation_message(recipient_email, ordername, orderid):
    with open("confirmation.html") as f:
        message = f.read()
    message = message.replace("{ordername}", ordername.upper()).replace('{orderid}', orderid)
    msg = MIMEMultipart()
    msg['To'] = recipient_email
    msg['From'] = "example@gmail.com"#email that will send a confirmation letter
    msg['Subject'] = "Thank you for the purchase!"
    msg.attach(MIMEText(message, 'html'))
    return msg

def confirmation(recipient_email, ordername, orderid):
    sender_email = "example@gmail.com"#email that will send a confirmation letter
    sender_password = "password123"#password of email that will send a confirmation letter
    message = get_confirmation_message(recipient_email, ordername, orderid)

    smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_server.starttls()
    smtp_server.login(sender_email, sender_password)

    smtp_server.sendmail(sender_email, recipient_email, message.as_string())
    smtp_server.quit()


# -----------------------------------
# ------------- ROUTING -------------
# -----------------------------------

@app.route('/')
def home():
    return render_template('mobile/home.html' if is_mobile() else 'home.html', products=Item.get_best_items())

@app.route('/store', methods=['GET', "POST"])
def store():
    if request.method == "GET":
        return render_template("mobile/store.html" if is_mobile() else "store.html", products=Item.get_items(item_type='all'), groups=Group.get_groups())
    elif request.method == "POST":
        button_pressed = request.form['buttons']
        return render_template("mobile/store.html" if is_mobile() else "store.html", products=Item.get_items(item_type=button_pressed), groups=Group.get_groups())

@app.route('/affiliate')
def affiliate():
    return render_template('mobile/affiliate.html' if is_mobile() else 'affiliate.html', products=Item.get_best_items())

@app.route('/contact')
def contact():
    return render_template('mobile/contact.html' if is_mobile() else 'contact.html', products=Item.get_best_items())

@app.route('/delivery')
def delivery():
    return render_template('mobile/delivery.html' if is_mobile() else 'delivery.html', products=Item.get_best_items())

@app.route('/reviews')
def reviews():
    return render_template('mobile/reviews.html' if is_mobile() else 'reviews.html', products=Item.get_best_items())

@app.route('/items/<itemid>')
def item(itemid):
    ItemInfo = Item.get_item(itemid)
    return render_template('mobile/product.html' if is_mobile() else 'product.html', item=ItemInfo, urls=ItemInfo['url'].split(','))

@app.route("/paid")
def check_paid():
    return render_template("mobile/paid.html" if is_mobile() else "paid.html")

@app.route("/checkout/<itemid>")
def iframe(itemid):
    itemInfo = Item.get_item(itemid)
    session['order_info'] = dict(request.args)
    return render_template('mobile/survey.html' if is_mobile() else 'survey.html', price=itemInfo['price'], type=itemInfo['type'], itemid=itemid)

@app.route('/checkout/end')
def checkout_end():
    return render_template('mobile/survey_end.html' if is_mobile() else 'survey_end.html')

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "GET":
        return render_template('admin/mobile/admin.html' if is_mobile() else 'admin/admin.html', wrong = "")
    elif request.method == "POST":
        session['username'] = request.form['username']
        session['password'] = request.form['password']
        if session['username'] == admin_username and session['password'] == admin_passw:
            return redirect(url_for("add_item"))
        else:
            return render_template('admin/mobile/admin.html' if is_mobile() else 'admin/admin.html', wrong = "Wrong password")

@app.route('/add_item', methods=["GET", "POST"])
def add_item():
    if request.method == 'GET':
        if session['username'] == admin_username and session['password'] == admin_passw:
            return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_1='', color="black", questions=Question.get_all_questions(), groups=Group.get_groups())
    elif request.method == "POST":
        if session['username'] == admin_username and session['password'] == admin_passw:
            if 'url' in request.form:
                try:
                    Item.create_item(requiredInfo=request.form['requiredInfo'],
                                      description=request.form['description'],
                                      url=request.form['url'],
                                      thumbnailUrl=request.form['thumbnailUrl'],
                                      itemName=request.form['itemName'],
                                      type = request.form['type'],
                                      price=request.form['price'])
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_1='The item was added succesfully', color="green", questions=Question.get_all_questions(), groups=Group.get_groups())
                except Exception:
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_1='The item was NOT added. Smth went wrong', color="red", questions=Question.get_all_questions(), groups=Group.get_groups())
            elif 'question_key' in request.form:
                try:
                    Question.create_question(request.form['question_key'], request.form['question'])
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_2='The question was added successfully!', color="green", questions=Question.get_all_questions(), groups=Group.get_groups())
                except Exception:
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_2='Smth went wrong(Most probably question with this key already exist)', color="red", questions=Question.get_all_questions(), groups=Group.get_groups())
            elif 'question_key_delete' in request.form:
                try:
                    Question.delete_question(request.form['question_key_delete'])
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_3='Successfully  deleted', color="green", questions=Question.get_all_questions(), groups=Group.get_groups())
                except Exception:
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_3='Smth went wrong(Most probably question with this key doesnt exist)', color="red", questions=Question.get_all_questions(), groups=Group.get_groups())
            elif 'add_group' in request.form:
                try:
                    Group.add_group(request.form['add_group'])
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_4='Successfully  added', color="green", questions=Question.get_all_questions(), groups=Group.get_groups())
                except Exception:
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_4='Smth went wrong(Most probably group with this key exist)', color="red", questions=Question.get_all_questions(), groups=Group.get_groups())
            elif 'delete_group' in request.form:
                try:
                    Group.delete_group(request.form['delete_group'])
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_5='Successfully  deleted', color="green", questions=Question.get_all_questions(), groups=Group.get_groups())
                except Exception:
                    return render_template('admin/mobile/add-item.html' if is_mobile() else 'admin/add-item.html', wrong_5='Smth went wrong(Most probably group with this key does not exist)', color="red", questions=Question.get_all_questions(), groups=Group.get_groups())

@app.route('/delete', methods=['GET', 'POST'])
def delete():
    if request.method == 'GET':
        if session['username'] == admin_username and session['password'] == admin_passw:
            items = Item.get_items(item_type="all")
            return render_template('admin/mobile/delete-item.html' if is_mobile() else 'admin/delete-item.html', products=items)
    elif request.method == 'POST':
        if session['username'] == admin_username and session['password'] == admin_passw:
            try:
                item_id = request.form['delete']
                Item.delete_item(item_id)
                items = Item.get_items(item_type="all")
                return render_template('admin/mobile/delete-item.html' if is_mobile() else 'admin/delete-item.html', products=items, color="green", wrong='Product has deleted successfully!')
            except Exception as e:
                print(e)
                items = Item.get_items(item_type="all")
                return render_template('admin/mobile/delete-item.html' if is_mobile() else 'admin/delete-item.html', products=items, color="red", wrong='Smth went wrong, product is not deleted')

@app.route("/orders", methods=['GET', "POST"])
def orders():
    if request.method == "GET":
        if session['username'] == admin_username and session['password'] == admin_passw:
            orders = Order.get_orders()
            return render_template('admin/mobile/orders.html' if is_mobile() else 'admin/orders.html', orders=orders)

    elif request.method == "POST":
        if session['username'] == admin_username and session['password'] == admin_passw:
            if "not-done" in request.form and request.form["search"] == '':
                orders = Order.get_orders(done=False)
            elif "not-done" in request.form and request.form["search"] != '':
                if Order.get_order(request.form['search']) == None:
                    orders = Order.get_orders(email=request.form["search"], done=False)
                else:
                    orders = [Order.get_order(request.form['search'])]
            elif request.form["search"] != '':
                if Order.get_order(request.form['search']) == None:
                    print('ALL/EMAIL')
                    orders = Order.get_orders(email=request.form["search"])
                else:
                    print('ALL/ID_2')
                    orders = [Order.get_order(request.form['search'])]
                    print(orders)
            elif request.form['search'] == "":
                print('ALL/NO EMAIL OR ID')
                orders = Order.get_orders()
            return render_template('admin/mobile/orders.html' if is_mobile() else 'admin/orders.html', orders=orders)

@app.route("/checkcheck")
def checkcheck():
    if session['username'] == admin_username and session['password'] == admin_passw:
        return render_template("CheckCheck/index.html")

@app.route("/orders/<orderid>", methods=['GET', "POST"])
def order(orderid):
    if request.method == "GET":
        if session['username'] == admin_username and session['password'] == admin_passw:
            orderinfo = Order.get_order(orderid)
            return render_template('admin/mobile/order.html' if is_mobile() else 'admin/order.html', orderinfo = orderinfo, add = json.loads(orderinfo['orderContent']), actionStatus='', color='black')
    elif request.method == 'POST':
        if session['username'] == admin_username and session['password'] == admin_passw:
            if request.form['buttons'] == 'mark-as-done':
                try:
                    Order.mark_as_done(orderid)
                    orderinfo = Order.get_order(orderid)
                    return render_template('admin/mobile/order.html' if is_mobile() else 'admin/order.html', orderinfo = orderinfo, add = json.loads(orderinfo['orderContent']), actionStatus="The action was completed!", color='green')
                except Exception:
                    orderinfo = Order.get_order(orderid)
                    return render_template('admin/mobile/order.html' if is_mobile() else 'admin/order.html', orderinfo = orderinfo, add = json.loads(orderinfo['orderContent']), actionStatus="Smth happened. The action was no completed", color='red')

            elif request.form['buttons'] == 'resend':
                orderinfo = Order.get_order(orderid)
                return render_template('admin/mobile/order.html' if is_mobile() else 'admin/order.html', orderinfo = orderinfo, add = json.loads(orderinfo['orderContent']), actionStatus="Smth happened. The action was not completed", color='red')

@app.route("/promocodes", methods=['GET', "POST"])
def promocodes():
    if request.method == "GET":
        if session['username'] == admin_username and session['password'] == admin_passw:
            return render_template("admin/promocodes.html", promocodes=PromoCode.get_promocodes())
    elif request.method == "POST":
        if session['username'] == admin_username and session['password'] == admin_passw:
            if 'delete' in request.form:
                PromoCode.delete_promo(request.form['delete'])
                return render_template("admin/promocodes.html", promocodes=PromoCode.get_promocodes())
            else:
                PromoCode.save_promocode(request.form['code'], request.form['discount'])
                return render_template("admin/promocodes.html", promocodes=PromoCode.get_promocodes())

if __name__=='__main__':
    app.run(host='0.0.0.0')