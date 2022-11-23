import json
import os

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
# from pprint import pprint
from dotenv import load_dotenv
from datetime import datetime
from dateutil import parser
from pybit import usdt_perpetual

app = Flask(__name__)

load_dotenv()

bybit_session = usdt_perpetual.HTTP(
    endpoint="https://api.bybit.com"
)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Alert(db.Model):                              # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    strategy = db.Column(db.String(100))
    ticker = db.Column(db.String(20))
    interval = db.Column(db.Integer)
    action = db.Column(db.String(10))
    chartTime = db.Column(db.DateTime)
    time = db.Column(db.DateTime)
    chartPrice = db.Column(db.Numeric(20,10))
    price = db.Column(db.Numeric(20,10))    

db.create_all()

@ app.route('/webhook', methods=['POST'])
def webhook():

    data = json.loads(request.data)

    strategy = data["strategy"]
    ticker = data["ticker"]
    interval = data["interval"],
    action = data["action"]    
    chartTime = parser.parse(data["time"])
    chartPrice = data["price"]
    
    response = bybit_session.latest_information_for_symbol(
        symbol=ticker
    )

    ticker_data = response["result"][0]    

    bid = ticker_data["bid_price"]
    ask = ticker_data["ask_price"]
    
    if action == 'buy':
        price = ask
    else:
        price = bid
    
    time = datetime.now()
    
    alert = Alert(  strategy=strategy, 
                    ticker=ticker, 
                    interval=interval, 
                    action=action, 
                    chartTime=chartTime, 
                    time=time, 
                    chartPrice=chartPrice, 
                    price=price)
    
    db.session.add(alert)
    db.session.commit()

    return {
        "code": "success"
    }


@ app.route('/alerts')
def alertsStatus():    

    return {
        "alerts": "alerts"
    }
    
