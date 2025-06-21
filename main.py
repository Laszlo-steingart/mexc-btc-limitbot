import os
import hmac
import hashlib
import time
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Fixe API Keys (manuell eingefügt, nicht aus ENV)
API_KEY = "mx0vgl8knwgL7bF14c"
API_SECRET = "921a17445d864768854f0d39a3667d38"

symbol = "SOLUSDT"

def get_server_time():
    return int(time.time() * 1000)

def sign_request(params):
    query_string = '&'.join([f"{k}={params[k]}" for k in sorted(params)])
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"{query_string}&signature={signature}"

def get_available_balance(asset):
    url = "https://api.mexc.com/api/v3/account"
    timestamp = get_server_time()
    query = {
        "timestamp": timestamp
    }
    signed_query = sign_request(query)
    headers = {"X-MEXC-APIKEY": API_KEY}
    response = requests.get(f"{url}?{signed_query}", headers=headers)
    balances = response.json().get("balances", [])
    for b in balances:
        if b["asset"] == asset:
            return float(b["free"])
    return 0.0

def place_limit_buy_order(symbol, price, quantity):
    url = "https://api.mexc.com/api/v3/order"
    timestamp = get_server_time()
    params = {
        "symbol": symbol,
        "side": "BUY",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": quantity,
        "price": price,
        "timestamp": timestamp
    }
    signed_query = sign_request(params)
    headers = {"X-MEXC-APIKEY": API_KEY}
    response = requests.post(url, headers=headers, data=signed_query)
    return response.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if data["side"] == "buy":
        usdt_balance = get_available_balance("USDT")
        ticker = requests.get(f"https://api.mexc.com/api/v3/ticker/bookTicker?symbol={symbol}").json()
        ask_price = float(ticker["askPrice"])
        price = round(ask_price - 0.002, 4)
        quantity = round(usdt_balance / price, 3)
        response = place_limit_buy_order(symbol, price, quantity)
        return jsonify(response)
    return jsonify({"status": "ignored"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)

