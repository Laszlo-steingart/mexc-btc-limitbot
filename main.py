from flask import Flask, request
import time, hashlib, hmac, requests, json, os, sys
from datetime import datetime

app = Flask(__name__)

API_KEY = "mx0vgle6oc8ay5iiNK"
API_SECRET = "0f7ca5615bea483abfb971e11cee81ac"
BASE_URL = "https://api.mexc.com"
SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwB8vt8H6rBnFXvhaRnygxtpJu5uu-fafrSvlNcF3FwEUAr0efguEs4vQkBTK9s9-Gvuw/exec"
SYMBOL = "XRPUSDT"

def get_sign(query):
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def log_to_sheet(entry):
    entry["timestamp"] = datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S")
    try:
        requests.post(SHEET_WEBHOOK_URL, json=entry)
    except Exception as e:
        print("⚠️ Fehler beim Logging:", e)
        sys.stdout.flush()

def get_orderbook():
    r = requests.get(BASE_URL + "/api/v3/depth", params={"symbol": SYMBOL, "limit": 5}).json()
    bid = float(r["bids"][0][0])
    ask = float(r["asks"][0][0])
    return bid, ask

def get_balance(asset):
    ts = int(time.time() * 1000)
    query = f"timestamp={ts}"
    sig = get_sign(query)
    headers = {"X-MEXC-APIKEY": API_KEY}
    r = requests.get(f"{BASE_URL}/api/v3/account?{query}&signature={sig}", headers=headers)
    for i in r.json().get("balances", []):
        if i["asset"] == asset:
            return float(i["free"])
    return 0.0

def place_market_buy():
    usdt_balance = get_balance("USDT")
    if usdt_balance < 1.0:
        print("❌ Nicht genug USDT")
        sys.stdout.flush()
        return

    _, ask = get_orderbook()
    qty = round(usdt_balance / ask, 2)

    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL,
        "side": "BUY",
        "type": "MARKET",
        "quantity": qty,
        "recvWindow": 5000,
        "timestamp": ts
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    params["signature"] = get_sign(query)
    headers = {"X-MEXC-APIKEY": API_KEY}
    r = requests.post(BASE_URL + "/api/v3/order", params=params, headers=headers).json()
    print("📥 BUY MARKET Antwort:", r)
    sys.stdout.flush()

    if "fills" in r and len(r["fills"]) > 0:
        avg_price = sum(float(fill["price"]) * float(fill["qty"]) for fill in r["fills"]) / sum(float(fill["qty"]) for fill in r["fills"])
        log_to_sheet({
            "side": "BUY (Market)",
            "price": round(avg_price, 6),
            "quantity": qty
        })

def place_market_sell():
    xrp_balance = get_balance("XRP")
    if xrp_balance < 1.0:
        print("❌ Nicht genug XRP")
        sys.stdout.flush()
        return

    qty = round(xrp_balance, 2)

    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL,
        "side": "SELL",
        "type": "MARKET",
        "quantity": qty,
        "recvWindow": 5000,
        "timestamp": ts
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    params["signature"] = get_sign(query)
    headers = {"X-MEXC-APIKEY": API_KEY}
    r = requests.post(BASE_URL + "/api/v3/order", params=params, headers=headers).json()
    print("📤 SELL MARKET Antwort:", r)
    sys.stdout.flush()

    if "fills" in r and len(r["fills"]) > 0:
        avg_price = sum(float(fill["price"]) * float(fill["qty"]) for fill in r["fills"]) / sum(float(fill["qty"]) for fill in r["fills"])
        log_to_sheet({
            "side": "SELL (Market)",
            "price": round(avg_price, 6),
            "quantity": qty
        })

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "side" not in data:
        return {"error": "no signal"}, 400

    if data["side"].lower() == "buy":
        place_market_buy()
        return {"status": "buy executed"}, 200

    elif data["side"].lower() == "sell":
        place_market_sell()
        return {"status": "sell executed"}, 200

    return {"error": "invalid signal"}, 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

