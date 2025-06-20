import hmac
import time
import hashlib
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "mx0vgl8knwgL7bF14c"
API_SECRET = "921a17445d864768854f0d39a3667d38"
BASE_URL = "https://api.mexc.com"
SYMBOL = "XRPUSDT"

def get_headers():
    return {
        "X-MEXC-APIKEY": API_KEY
    }

def sign_params(params):
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_balance():
    path = "/api/v3/account"
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp}
    params["signature"] = sign_params(params)
    r = requests.get(BASE_URL + path, headers=get_headers(), params=params)
    assets = r.json().get("balances", [])
    usdt_balance = next((a for a in assets if a["asset"] == "USDT"), {"free": "0"})["free"]
    return float(usdt_balance)

def get_price():
    path = f"/api/v3/ticker/price"
    r = requests.get(BASE_URL + path, params={"symbol": SYMBOL})
    return float(r.json()["price"])

def place_order(side):
    balance = get_balance()
    price = get_price()
    qty = round(balance / price, 1)  # XRP often allows 1 decimal

    path = "/api/v3/order"
    timestamp = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL,
        "side": side.upper(),
        "type": "MARKET",
        "quantity": qty,
        "timestamp": timestamp
    }
    params["signature"] = sign_params(params)
    r = requests.post(BASE_URL + path, headers=get_headers(), params=params)
    return r.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    side = data.get("side")
    if side not in ["buy", "sell"]:
        return jsonify({"error": "Invalid side"}), 400
    result = place_order(side)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)

