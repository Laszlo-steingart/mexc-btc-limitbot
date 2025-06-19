from flask import Flask, request, jsonify
import requests
import time
import hmac
import hashlib

app = Flask(__name__)

# Feste API-Keys direkt im Code (nicht empfohlen für Produktion)
API_KEY = "mx0vglDYMDpju8DKxc"
API_SECRET = "40a163d25d1642bb85f4dd181a63fa00"

BASE_URL = "https://api.mexc.com"
SYMBOL = "XRPUSDT"
TICK_SIZE = 0.0001  # XRP Tickgröße prüfen und ggf. anpassen

def sign(params):
    query = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    return signature

def get_server_time():
    r = requests.get(BASE_URL + "/api/v3/time")
    return r.json()["serverTime"]

def get_price():
    r = requests.get(BASE_URL + f"/api/v3/ticker/price", params={"symbol": SYMBOL})
    return float(r.json()["price"])

def place_limit_order(price):
    url = BASE_URL + "/api/v3/order"
    timestamp = get_server_time()
    params = {
        "symbol": SYMBOL,
        "side": "BUY",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": "20",  # Beispielgröße für XRP
        "price": f"{price:.4f}",
        "timestamp": timestamp
    }
    params["signature"] = sign(params)
    headers = { "X-MEXC-APIKEY": API_KEY }

    r = requests.post(url, params=params, headers=headers)
    print("ORDER PARAMS:", params)
    print("RESPONSE:", r.status_code, r.text)
    return r.json()

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if data.get("side") == "buy":
        current_price = get_price()
        limit_price = round(current_price - 2 * TICK_SIZE, 4)
        response = place_limit_order(limit_price)
        return jsonify(response)
    elif data.get("side") == "close":
        return jsonify({"message": "Close signal received (logic not implemented)"})
    return jsonify({"error": "Invalid data"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)

