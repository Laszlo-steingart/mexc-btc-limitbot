import os
import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = "mx0vgl8knwgL7bF14c"
API_SECRET = "921a17445d864768854f0d39a3667d38"

BASE_URL = "https://api.mexc.com"
SYMBOL = "ETHUSDC"

def get_server_time():
    return str(int(time.time() * 1000))

def sign(params, secret):
    query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_account_info():
    timestamp = get_server_time()
    params = {
        "timestamp": timestamp
    }
    signature = sign(params, API_SECRET)
    headers = {
        "X-MEXC-APIKEY": API_KEY
    }
    url = f"{BASE_URL}/api/v3/account?timestamp={timestamp}&signature={signature}"
    response = requests.get(url, headers=headers)
    return response.json()

def place_limit_order(side, quantity, price):
    timestamp = get_server_time()
    params = {
        "symbol": SYMBOL,
        "side": side.upper(),
        "type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "timeInForce": "GTC",
        "timestamp": timestamp
    }
    signature = sign(params, API_SECRET)
    headers = {
        "X-MEXC-APIKEY": API_KEY
    }
    url = f"{BASE_URL}/api/v3/order"
    response = requests.post(url, headers=headers, params={**params, "signature": signature})
    return response.json()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    side = data.get("side")
    if side not in ["buy", "sell"]:
        return jsonify({"error": "Invalid side"}), 400

    account_info = get_account_info()
    usdc_balance = float(next((item for item in account_info["balances"] if item["asset"] == "USDC"), {"free": 0})["free"])
    if usdc_balance <= 0:
        return jsonify({"error": "No balance"}), 400

    price_data = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={"symbol": SYMBOL}).json()
    current_price = float(price_data["price"])
    quantity = round(usdc_balance / current_price, 6)

    order = place_limit_order(side, quantity, current_price)
    return jsonify(order)

if __name__ == '__main__':
    app.run(debug=True, port=10000, host='0.0.0.0')

