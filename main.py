import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "mx0vgl8knwgL7bF14c"
API_SECRET = "921a17445d864768854f0d39a3667d38"
BASE_URL = "https://api.mexc.com"
symbol = "ETHUSDC"

def get_timestamp():
    return str(int(time.time() * 1000))

def get_headers(query_string):
    signature = hmac.new(
        bytes(API_SECRET, "utf-8"),
        bytes(query_string, "utf-8"),
        hashlib.sha256
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "ApiKey": API_KEY,
        "Request-Time": get_timestamp(),
        "Signature": signature
    }

def get_balance(asset):
    timestamp = get_timestamp()
    query_string = f"timestamp={timestamp}"
    headers = get_headers(query_string)
    url = f"{BASE_URL}/api/v3/account?{query_string}"
    response = requests.get(url, headers=headers)
    balances = response.json().get("balances", [])
    for b in balances:
        if b["asset"] == asset:
            return float(b["free"])
    return 0.0

def get_price(symbol):
    url = f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url)
    return response.json()["price"]

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    side = data.get("side")

    if side not in ["buy", "sell"]:
        return jsonify({"error": "Invalid side"}), 400

    usdt_balance = get_balance("USDC")
    if usdt_balance <= 0:
        return jsonify({"error": "No balance"}), 400

    price = float(get_price(symbol))
    limit_price = round(price - 0.01, 2) if side == "buy" else round(price + 0.01, 2)
    quantity = round(usdt_balance / price, 6)

    params = {
        "symbol": symbol,
        "side": side.upper(),
        "type": "LIMIT",
        "quantity": quantity,
        "price": str(limit_price),
        "timeInForce": "GTC",
        "timestamp": get_timestamp()
    }

    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    headers = get_headers(query_string)
    url = f"{BASE_URL}/api/v3/order"
    response = requests.post(url, headers=headers, params=params)
    return jsonify(response.json())

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)

