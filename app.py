import json
import os
import pandas as pd
import requests

from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from pprint import pprint
from decouple import config
from datetime import datetime
from dateutil import parser
from pybit import usdt_perpetual
from binance.um_futures import UMFutures
from binance.spot import Spot as BinanceSpot
from binance.error import ClientError, ServerError
from dydx3 import Client as dydxClient
from dydx3.constants import API_HOST_MAINNET
from dydx3.errors import DydxError
from web3 import Web3

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = config("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
HTTP_PROVIDER = config("HTTP_PROVIDER")

db = SQLAlchemy(app)

app.app_context().push()


class tvAlert(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    strategy = db.Column(db.String(100))
    ticker = db.Column(db.String(20))
    interval = db.Column(db.Integer)
    action = db.Column(db.String(10))
    chartTime = db.Column(db.DateTime)
    time = db.Column(db.DateTime)
    chartPrice = db.Column(db.Numeric(20, 10))
    price = db.Column(db.Numeric(20, 10))


db.create_all()

pd.options.display.float_format = "{:,.2f}".format  # type: ignore


@app.route("/bybitperp", methods=["POST"])
def bybitperp():

    data = json.loads(request.data)

    strategy = data["strategy"]
    ticker = data["ticker"]
    interval = (data["interval"],)
    action = data["action"]
    chartTime = parser.parse(data["time"])
    chartPrice = data["price"]

    bybit_session = usdt_perpetual.HTTP(endpoint="https://api.bybit.com")

    response = bybit_session.latest_information_for_symbol(symbol=ticker)

    ticker_data = response["result"][0]

    bid = ticker_data["bid_price"]
    ask = ticker_data["ask_price"]

    if action == "buy":
        price = ask
    else:
        price = bid

    time = datetime.now()

    alert = tvAlert(
        strategy=strategy,
        ticker=ticker,
        interval=interval,
        action=action,
        chartTime=chartTime,
        time=time,
        chartPrice=chartPrice,
        price=price,
    )

    db.session.add(alert)
    db.session.commit()

    return {"code": "success"}


@app.route("/dydx", methods=["POST"])
def dydx():

    try:
        data = json.loads(request.data)

        ticker = data["ticker"]
        strategy = data["strategy"]
        interval = (data["interval"],)
        action = data["action"]
        chartTime = parser.parse(data["time"])
        chartPrice = data["price"]

        client = dydxClient(
            host=API_HOST_MAINNET,
            web3=Web3(Web3.HTTPProvider(HTTP_PROVIDER)),  # type: ignore
        )

        response = client.public.get_orderbook(ticker)

        bid = response.data["bids"][0]["price"]
        ask = response.data["asks"][0]["price"]

        if action == "buy":
            price = ask
        else:
            price = bid

        time = datetime.now()

        alert = tvAlert(
            strategy=strategy,
            ticker=ticker,
            interval=interval,
            action=action,
            chartTime=chartTime,
            time=time,
            chartPrice=chartPrice,
            price=price,
        )

        db.session.add(alert)
        db.session.commit()

    except (DydxError) as e:
        return {"error": str(e)}  # type: ignore
    else:
        return {"code": "success"}


@app.route("/binanceperp", methods=["POST"])
def binanceperp():

    try:

        data = json.loads(request.data)

        strategy = data["strategy"]
        ticker = data["ticker"]
        interval = (data["interval"],)
        action = data["action"]
        chartTime = parser.parse(data["time"])
        chartPrice = data["price"]

        client = UMFutures()

        response = client.book_ticker(ticker)

        bid = response["bidPrice"]
        ask = response["askPrice"]

        if action == "buy":
            price = ask
        else:
            price = bid

        time = datetime.now()

        alert = tvAlert(
            strategy=strategy,
            ticker=ticker,
            interval=interval,
            action=action,
            chartTime=chartTime,
            time=time,
            chartPrice=chartPrice,
            price=price,
        )

        db.session.add(alert)
        db.session.commit()

    except (ClientError) as e:
        return {"error": str(e.error_message)}
    except (ServerError) as e:
        return {"error": str(e.message)}
    else:
        return {"code": "success"}


@app.route("/binancespot", methods=["POST"])
def binancespot():

    try:

        data = json.loads(request.data)

        strategy = data["strategy"]
        ticker = data["ticker"]
        interval = (data["interval"],)
        action = data["action"]
        chartTime = parser.parse(data["time"])
        chartPrice = data["price"]

        client = BinanceSpot()

        response = client.book_ticker(ticker)

        bid = response["bidPrice"]
        ask = response["askPrice"]

        if action == "buy":
            price = ask
        else:
            price = bid

        time = datetime.now()

        alert = tvAlert(
            strategy=strategy,
            ticker=ticker,
            interval=interval,
            action=action,
            chartTime=chartTime,
            time=time,
            chartPrice=chartPrice,
            price=price,
        )

        db.session.add(alert)
        db.session.commit()

    except (ClientError) as e:
        return {"error": str(e.error_message)}
    except (ServerError) as e:
        return {"error": str(e.message)}
    else:
        return {"code": "success"}


@app.route("/alertprice", methods=["POST"])
def alertprice():

    data = json.loads(request.data)

    strategy = data["strategy"]
    ticker = data["ticker"]
    interval = (data["interval"],)
    action = data["action"]
    chartTime = parser.parse(data["time"])
    chartPrice = data["price"]
    price = chartPrice
    time = datetime.now()

    alert = tvAlert(
        strategy=strategy,
        ticker=ticker,
        interval=interval,
        action=action,
        chartTime=chartTime,
        time=time,
        chartPrice=chartPrice,
        price=price,
    )

    db.session.add(alert)
    db.session.commit()

    return {"code": "success"}


@app.route("/trade", methods=["GET"])
def trade():

    leverage = int(request.args.get("leverage"))  # type: ignore
    risk = float(request.args.get("risk"))  # type: ignore
    startBalance = int(request.args.get("startBalance"))  # type: ignore
    fees = float(request.args.get("fees"))  # type: ignore
    strategyPar = request.args.get("strategy", None)
    tickerPar = request.args.get("ticker", None)

    if request.args.get("debug") == "True":
        debug = True
    else:
        debug = False

    resultDatas = []
    alertDatas = []

    strategies = []

    if strategyPar is not None:
        strategies.append(strategyPar)
    else:
        strategyRows = db.session.query(tvAlert.strategy).distinct().all()
        for strategyRow in strategyRows:
            strategy = strategyRow[0]
            strategies.append(strategy)

    for strategy in strategies:

        tickers = []

        if tickerPar is not None:
            tickers.append(tickerPar)
        else:
            tickerRows = (
                db.session.query(tvAlert.ticker)
                .filter(tvAlert.strategy == strategy)
                .distinct()
                .all()
            )
            for tickerRow in tickerRows:
                ticker = tickerRow[0]
                tickers.append(ticker)

        for ticker in tickers:

            intervals = []

            intervalRows = (
                db.session.query(tvAlert.interval)
                .filter(tvAlert.strategy == strategy, tvAlert.ticker == ticker)
                .distinct()
                .all()
            )
            for intervalRow in intervalRows:
                interval = intervalRow[0]
                intervals.append(interval)

            for interval in intervals:

                alerts = (
                    tvAlert.query.filter(
                        tvAlert.strategy == strategy,
                        tvAlert.ticker == ticker,
                        tvAlert.interval == interval,
                    )
                    .order_by(tvAlert.id)
                    .all()
                )

                rowCounter = 0
                lastAction = ""
                currBalance = startBalance
                lastBalance = 0
                noOfTrades = 0
                noOfTradesWon = 0
                noOfTradesLost = 0
                highestProfit = 0
                highestLoss = 0
                coinAmount = 0
                positionCost = 0
                alertTime = None
                startDateTime = None
                endDateTime = None

                for alert in alerts:

                    alertData = {}
                    closeFeesAmount = 0
                    closeCoinAmount = 0
                    closeReturn = 0
                    profit = 0
                    profitPercent = 0
                    buyBalance = 0
                    openFeesAmount = 0

                    rowCounter += 1

                    alertTime = alert.time
                    alertTicker = alert.ticker
                    alertInterval = alert.interval
                    alertAction = alert.action
                    alertPrice = float(alert.price)

                    if rowCounter == 1:
                        startDateTime = alertTime

                    if alertAction != lastAction:

                        if coinAmount > 0:

                            noOfTrades += 1

                            # Close Position -> Not for first alert

                            closeCoinAmount = coinAmount
                            closeFeesAmount = coinAmount * alertPrice * fees

                            if lastAction == "sell":
                                closeReturn = coinAmount * alertPrice + closeFeesAmount
                                profit = positionCost - closeReturn
                            if lastAction == "buy":
                                closeReturn = coinAmount * alertPrice - closeFeesAmount
                                profit = closeReturn - positionCost

                            currBalance = lastBalance + profit

                            profitPercent = (currBalance / lastBalance - 1) * 100

                            if profitPercent >= 0:
                                noOfTradesWon += 1
                            else:
                                noOfTradesLost += 1

                        # Open new position

                        if alertAction in ["buy", "sell"]:
                            buyBalance = currBalance * risk
                            openFeesAmount = buyBalance * leverage * fees
                            positionCost = buyBalance * leverage
                            if alertAction == "buy":
                                coinAmount = (
                                    positionCost - openFeesAmount
                                ) / alertPrice
                            if alertAction == "sell":
                                coinAmount = (
                                    positionCost + openFeesAmount
                                ) / alertPrice

                            lastBalance = currBalance
                            lastPrice = alertPrice
                        else:  # Position closed
                            coinAmount = 0

                        openCoinAmount = coinAmount

                    lastAction = alertAction

                    alertData["counter"] = rowCounter
                    alertData["strategy"] = strategy
                    alertData["ticker"] = alertTicker
                    alertData["interval"] = alertInterval
                    alertData["leverage"] = alertInterval
                    alertData["action"] = alertAction
                    alertData["price"] = alertPrice
                    alertData["fees"] = fees
                    alertData["closeFeesAmount"] = closeFeesAmount  # type: ignore
                    alertData["closeCoinAmount"] = closeCoinAmount  # type: ignore
                    alertData["closeReturn"] = closeReturn  # type: ignore
                    alertData["lastBalance"] = lastBalance  # type: ignore
                    alertData["currBalance"] = currBalance
                    alertData["profit"] = profit  # type: ignore
                    alertData["profitPercent"] = profitPercent  # type: ignore
                    alertData["buyBalance"] = buyBalance  # type: ignore
                    alertData["openFeesAmount"] = openFeesAmount  # type: ignore
                    alertData["openCoinAmount"] = openCoinAmount  # type: ignore
                    alertData["positionCost"] = positionCost  # type: ignore

                    alertDatas.append(alertData)

                profitPercent = (currBalance / startBalance - 1) * 100
                if noOfTrades > 0:
                    winRate = noOfTradesWon / noOfTrades
                else:
                    winRate = 0
                endDateTime = alertTime
                timeDiff = endDateTime - startDateTime  # type: ignore
                tradeHours = round(timeDiff.total_seconds() / 3600, 0)

                resultData = {}
                resultData["strategy"] = strategy
                resultData["ticker"] = ticker
                resultData["interval"] = interval
                resultData["leverage"] = leverage
                resultData["risk"] = risk
                resultData["endBalance"] = currBalance
                resultData["profit"] = profitPercent
                resultData["noOfTrades"] = noOfTrades
                resultData["noOfTradesWon"] = noOfTradesWon
                resultData["noOfTradesLost"] = noOfTradesLost
                resultData["winRate"] = winRate
                resultData["tradeHours"] = tradeHours

                resultDatas.append(resultData)

    df = pd.DataFrame(resultDatas)

    df.sort_values(["ticker", "profit"], inplace=True, ascending=False)
    df["interval"] = df["interval"].map("{:,.0f}".format)
    df["leverage"] = df["leverage"].map("{:,.0f}".format)
    df["noOfTrades"] = df["noOfTrades"].map("{:,.0f}".format)
    df["noOfTradesWon"] = df["noOfTradesWon"].map("{:,.0f}".format)
    df["noOfTradesLost"] = df["noOfTradesLost"].map("{:,.0f}".format)
    df["tradeHours"] = df["tradeHours"].map("{:,.0f}".format)

    df.rename(
        columns={
            "strategy": "Strategy",
            "ticker": "Ticker",
            "interval": "Interval min",
            "leverage": "Leverage",
            "risk": "Risk",
            "endBalance": "End balance",
            "profit": "Profit %",
            "noOfTrades": "No. of trades",
            "noOfTradesWon": "No. of trades won",
            "noOfTradesLost": "No. of trades lost",
            "winRate": "Win rate",
            "tradeHours": "Trading hours",
        },
        inplace=True,
    )

    af = pd.DataFrame(alertDatas)

    if debug:
        return render_template(
            "data.html", tables=[af.to_html(classes="data", header=True)]
        )
    else:
        return render_template(
            "data.html", tables=[df.to_html(classes="data", header=True)]
        )
