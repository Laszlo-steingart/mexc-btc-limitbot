from flask import Flask, request
import time, hmac, hashlib, requests, sys, os, json

app = Flask(__name__)

API_KEY = 'mx0vgle6oc8ay5iiNK'
API_SECRET = '0f7ca5615bea483abfb971e11cee81ac'
BASE_URL = 'https://api.mexc.com'
SYMBOL = 'XRPUSDT'
TICK_SIZE = 0.0001
LIMIT_ORDER_FILE = "limit_order.json"

def get_sign(query):
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def get_headers():
    return {"X-MEXC-APIKEY": API_KEY}

def get_orderbook():
    r = requests.get(BASE_URL + "/api/v3/depth", params={"symbol": SYMBOL, "limit": 5}).json()
    bid = float(r["bids"][0][0])
    ask = float(r["asks"][0][0])
    return bid, ask

def get_balance(asset):
    ts = int(time.time() * 1000)
    query = f"timestamp={ts}&recvWindow=5000"
    sig = get_sign(query)
    url = f"{BASE_URL}/api/v3/account?{query}&signature={sig}"
    r = requests.get(url, headers=get_headers())
    print("DEBUG BALANCES RESPONSE:", r.json())
    sys.stdout.flush()
    for i in r.json().get("balances", []):
        if i["asset"] == asset:
            return float(i["free"])
    return 0.0

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def delete_json(path):
    if os.path.exists(path):
        os.remove(path)

def cancel_limit_order(order_id):
    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL,
        "orderId": order_id,
        "timestamp": ts,
        "recvWindow": 5000
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    params["signature"] = get_sign(query)
    r = requests.delete(BASE_URL + "/api/v3/order", params=params, headers=get_headers())
    print("LIMIT ORDER CANCELED:", r.json())
    sys.stdout.flush()

def place_limit_buy():
    bid, _ = get_orderbook()
    price = round(bid - 2 * TICK_SIZE, 6)
    qty = 3

    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL, "side": "BUY", "type": "LIMIT",
        "quantity": qty, "price": price, "timeInForce": "GTC",
        "recvWindow": 5000, "timestamp": ts
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    params["signature"] = get_sign(query)
    r = requests.post(BASE_URL + "/api/v3/order", params=params, headers=get_headers()).json()
    print("BUY RESPONSE:", r)
    sys.stdout.flush()

    if "orderId" in r:
        save_json(LIMIT_ORDER_FILE, {"orderId": r["orderId"]})

    return r

def place_market_sell():
    # Wenn offene BUY-Limit-Order existiert → canceln
    existing = load_json(LIMIT_ORDER_FILE)
    if "orderId" in existing:
        cancel_limit_order(existing["orderId"])
        delete_json(LIMIT_ORDER_FILE)

    qty = round(get_balance("XRP"), 1)
    if qty < 0.1:
        return {"error": "Not enough XRP to sell"}

    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL, "side": "SELL", "type": "MARKET",
        "quantity": qty, "recvWindow": 5000, "timestamp": ts
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    params["signature"] = get_sign(query)
    r = requests.post(BASE_URL + "/api/v3/order", params=params, headers=get_headers()).json()
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
    app.run(host='0.0.0.0', port=10000)

