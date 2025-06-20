import time
import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
from urllib.parse import urlencode

app = Flask(__name__)

# Deine echten API-Keys
api_key = 'mx0vgl8knwgL7bF14c'
api_secret = '921a17445d864768854f0d39a3667d38'

def get_usdc_balance():
    timestamp = int(time.time() * 1000)
    query_string = f"timestamp={timestamp}"
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    headers = {"X-MEXC-APIKEY": api_key}
    url = f"https://api.mexc.com/api/v3/account?{query_string}&signature={signature}"
    res = requests.get(url, headers=headers).json()
    for asset in res.get("balances", []):
        if asset["asset"] == "USDC":
            return float(asset["free"])
    return 0.0

def place_limit_order(symbol, side):
    balance = get_usdc_balance()
    if balance <= 0:
        return {"error": "No USDC balance"}

    price = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}").json()
    price = float(price["price"])
    limit_price = round(price * 0.995, 2) if side == "BUY" else round(price * 1.005, 2)
    quantity = round(balance / limit_price, 6)

    params = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": quantity,
        "price": limit_price,
        "timestamp": int(time.time() * 1000)
    }

    query_string = urlencode(params)
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    params["signature"] = signature

    headers = {
        "X-MEXC-APIKEY": api_key,
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post("https://api.mexc.com/api/v3/order", data=params, headers=headers)
    return response.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if "side" not in data:
        return jsonify({"error": "Missing side"}), 400
    symbol = "ETHUSDC"
    result = place_limit_order(symbol, data["side"].upper())
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)

