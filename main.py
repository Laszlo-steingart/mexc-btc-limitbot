from flask import Flask, request
import time, hmac, hashlib, requests, sys

app = Flask(__name__)

API_KEY = 'mx0vgL8knwgL7bF14c'
API_SECRET = '921a17445d864768854f0d39a3667d38'
BASE_URL = 'https://api.mexc.com'
SYMBOL = 'XRPUSDT'
TICK_SIZE = 0.0001

def get_sign(query):
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def get_orderbook():
    r = requests.get(BASE_URL + "/api/v3/depth", params={"symbol": SYMBOL, "limit": 5}).json()
    bid = float(r["bids"][0][0])
    ask = float(r["asks"][0][0])
    return bid, ask

def get_balance(asset):
    ts = int(time.time() * 1000)
    query = f"timestamp={ts}&recvWindow=5000"
    sig = get_sign(query)
    headers = {"X-MEXC-APIKEY": API_KEY}
    r = requests.get(f"{BASE_URL}/api/v3/account?{query}&signature={sig}", headers=headers)
    for i in r.json().get("balances", []):
        if i["asset"] == asset:
            return float(i["free"])
    return 0.0

def place_limit_buy():
    bid, _ = get_orderbook()
    price = round(bid - 2 * TICK_SIZE, 6)
    usdt = get_balance("USDT")
    qty = round(usdt / price, 1)

    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL, "side": "BUY", "type": "LIMIT",
        "quantity": qty, "price": price, "timeInForce": "GTC",
        "recvWindow": 5000, "timestamp": ts
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    params["signature"] = get_sign(query)
    headers = {"X-MEXC-APIKEY": API_KEY}
    r = requests.post(BASE_URL + "/api/v3/order", params=params, headers=headers).json()
    print("BUY RESPONSE:", r)
    sys.stdout.flush()
    return r

def place_market_sell():
    qty = round(get_balance("XRP"), 1)
    if qty < 1:
        return {"error": "Not enough XRP to sell"}

    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL, "side": "SELL", "type": "MARKET",
        "quantity": qty, "recvWindow": 5000, "timestamp": ts
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    params["signature"] = get_sign(query)
    headers = {"X-MEXC-APIKEY": API_KEY}
    r = requests.post(BASE_URL + "/api/v3/order", params=params, headers=headers).json()
    print("SELL RESPONSE:", r)
    sys.stdout.flush()
    return r

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "side" not in data:
        return {"error": "Missing 'side'"}, 400

    if data["side"].lower() == "buy":
        return place_limit_buy()

    if data["side"].lower() == "sell":
        return place_market_sell()

    return {"error": "Invalid side"}, 400

if __name__ == '__main__':
    app.run(debug=False)

