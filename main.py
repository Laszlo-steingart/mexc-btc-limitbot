from flask import Flask, request, jsonify
import hmac, hashlib, time, requests

app = Flask(__name__)

API_KEY = "mx0vgl8knwgL7bF14c"
API_SECRET = "921a17445d864768854f0d39a3667d38"
SYMBOL = "ETHUSDC"

BASE_URL = "https://api.mexc.com"

def sign_request(params):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return query_string + f"&signature={signature}"

def get_available_usdc_balance():
    timestamp = int(time.time() * 1000)
    query = f"timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    headers = {"X-MEXC-APIKEY": API_KEY}
    url = f"{BASE_URL}/api/v3/account?{query}&signature={signature}"
    res = requests.get(url, headers=headers)
    balances = res.json().get("balances", [])
    for asset in balances:
        if asset["asset"] == "USDC":
            return float(asset["free"])
    return 0.0

def place_limit_buy(symbol, quantity, price):
    timestamp = int(time.time() * 1000)
    params = {
        "symbol": symbol,
        "side": "BUY",
        "type": "LIMIT",
        "timeInForce": "GTC",
        "quantity": quantity,
        "price": price,
        "timestamp": timestamp
    }
    signed = sign_request(params)
    headers = {"X-MEXC-APIKEY": API_KEY}
    url = f"{BASE_URL}/api/v3/order?{signed}"
    return requests.post(url, headers=headers)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or data.get("side") != "buy":
        return jsonify({"error": "Invalid payload"}), 400

    try:
        ticker = requests.get(f"{BASE_URL}/api/v3/ticker/bookTicker?symbol={SYMBOL}").json()
        ask_price = float(ticker["askPrice"])
        limit_price = round(ask_price * 0.998, 2)

        usdc_balance = get_available_usdc_balance()
        if usdc_balance < 5:
            return jsonify({"error": "Not enough balance"}), 400

        quantity = round(usdc_balance / limit_price, 5)
        res = place_limit_buy(SYMBOL, quantity, limit_price)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return 'MEXC Webhook Bot Active'

