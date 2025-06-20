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

SYMBOL = "BTCUSDT"

def get_balance():
    timestamp = int(time.time() * 1000)
    query = f"timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = { "X-MEXC-APIKEY": API_KEY }
    url = f"{BASE_URL}/api/v3/account?{query}&signature={signature}"
    r = requests.get(url, headers=headers)
    assets = r.json().get("balances", [])
    usdt = next((a for a in assets if a["asset"] == "USDT"), None)
    return float(usdt["free"]) if usdt else 0

def get_price():
    url = f"{BASE_URL}/api/v3/ticker/price?symbol={SYMBOL}"
    r = requests.get(url)
    return float(r.json()["price"])

def place_order(side):
    balance = get_balance()
    price = get_price()
    qty = round(balance / price, 6)
    if qty <= 0:
        return {"error": "Not enough USDT balance"}, 400

    timestamp = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL,
        "side": side.upper(),
        "type": "MARKET",
        "quantity": qty,
        "timestamp": timestamp
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature
    headers = { "X-MEXC-APIKEY": API_KEY }

    r = requests.post(f"{BASE_URL}/api/v3/order", headers=headers, params=params)
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

