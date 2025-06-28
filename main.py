from flask import Flask, request
import time, hmac, hashlib, requests

app = Flask(__name__)

API_KEY = 'mx0vgI8knwgL7bF14c'
API_SECRET = '921a17445d864768854f0d39a3667d38'
SYMBOL = 'XRPUSDT'
TICK_SIZE = 0.0001
BASE_URL = 'https://api.mexc.com'

def sign(params):
    query = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    sig = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    return f"{query}&signature={sig}"

def get_headers():
    return {"X-MEXC-APIKEY": API_KEY}

def get_best_price():
    res = requests.get(f"{BASE_URL}/api/v3/depth", params={"symbol": SYMBOL, "limit": 5}).json()
    best_bid = float(res['bids'][0][0])
    best_ask = float(res['asks'][0][0])
    return best_bid, best_ask

def get_balance(asset):
    timestamp = int(time.time() * 1000)
    params = {"timestamp": timestamp}
    url = f"{BASE_URL}/api/v3/account?" + sign(params)
    res = requests.get(url, headers=get_headers()).json()
    for b in res.get("balances", []):
        if b["asset"] == asset:
            return float(b["free"])
    return 0.0

def place_limit_order(side):
    best_bid, best_ask = get_best_price()
    timestamp = int(time.time() * 1000)

    if side == "buy":
        price = round(best_bid - 2 * TICK_SIZE, 6)
        usdt_balance = get_balance("USDT")
        qty = round(usdt_balance / price, 1)
    else:
        price = round(best_ask + 2 * TICK_SIZE, 6)
        qty = round(get_balance("XRP"), 1)

    params = {
        "symbol": SYMBOL,
        "side": side.upper(),
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": qty,
        "price": price,
        "timestamp": timestamp
    }

    url = f"{BASE_URL}/api/v3/order?" + sign(params)
    return requests.post(url, headers=get_headers()).json()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data or 'side' not in data:
        return {"error": "missing 'side'"}, 400
    side = data['side'].lower()
    if side not in ['buy', 'sell']:
        return {"error": "invalid side"}, 400
    return place_limit_order(side)

if __name__ == '__main__':
    app.run(debug=False)

