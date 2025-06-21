import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "mx0vgl8knwgL7bF14c"
API_SECRET = "921a17445d864768854f0d39a3667d38"
BASE_URL = "https://api.mexc.com"
SYMBOL = "SOLUSDT"

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(params, secret):
    query_string = '&'.join([f"{key}={value}" for key, value in 
sorted(params.items())])
    signature = hmac.new(secret.encode('utf-8'), 
query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_balance(asset):
    path = "/api/v3/account"
    timestamp = get_timestamp()
    params = {"timestamp": timestamp}
    params["signature"] = sign_request(params, API_SECRET)
    headers = {"X-MEXC-APIKEY": API_KEY}
    response = requests.get(BASE_URL + path, headers=headers, 
params=params)
    balances = response.json().get("balances", [])
    for b in balances:
        if b["asset"] == asset:
            return float(b["free"])
    return 0.0

def place_order(symbol, side, quantity):
    path = "/api/v3/order"
    timestamp = get_timestamp()
    params = {
        "symbol": symbol,
        "side": side.upper(),
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": quantity,
        "price": get_limit_price(symbol, side),
        "timestamp": timestamp
    }
    params["signature"] = sign_request(params, API_SECRET)
    headers = {"X-MEXC-APIKEY": API_KEY}
    return requests.post(BASE_URL + path, headers=headers, 
params=params).json()

def get_limit_price(symbol, side):
    depth = requests.get(f"{BASE_URL}/api/v3/depth", params={"symbol": 
symbol, "limit": 5}).json()
    if side.lower() == "buy":
        return str(round(float(depth["asks"][0][0]) - 0.001, 4))
    else:
        return str(round(float(depth["bids"][0][0]) + 0.001, 4))

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    side = data.get("side")
    usdt_balance = get_balance("USDT")
    if usdt_balance <= 0:
        return jsonify({"error": "No USDT balance"}), 400

    price = float(get_limit_price(SYMBOL, side))
    quantity = round(usdt_balance / price, 3)
    result = place_order(SYMBOL, side, quantity)
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)

