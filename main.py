from datetime import datetime
import time, hashlib, hmac, requests, json, os
from flask import Flask, request

app = Flask(__name__)

# Konfiguration
API_KEY = "mx0vgle6oc8ay5iiNK"
API_SECRET = "0f7ca5615bea483abfb971e11cee81ac"
BASE_URL = "https://api.mexc.com"
SYMBOL = "XRPUSDT"
SHEET_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwB8vt8H6rBnFXvhaRnygxtpJu5uu-fafrSvlNcF3FwEUAr0efguEs4vQkBTK9s9-Gvuw/exec"
STATE_FILE = "position_state.json"
PNL_FILE = "cumulative_pnl.json"

def get_sign(query):
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f)

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return default

def get_orderbook():
    r = requests.get(BASE_URL + "/api/v3/depth", params={"symbol": SYMBOL, "limit": 5}).json()
    bid = float(r["bids"][0][0])
    return round(bid, 6)

def place_limit_buy():
    price = get_orderbook()
    qty = 3  # Festgelegt auf 3 XRP

    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL, "side": "BUY", "type": "LIMIT",
        "quantity": qty, "price": price,
        "timeInForce": "GTC", "timestamp": ts, "recvWindow": 5000
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    sig = get_sign(query)
    params["signature"] = sig
    headers = {"X-MEXC-APIKEY": API_KEY}
    r = requests.post(BASE_URL + "/api/v3/order", params=params, headers=headers).json()

    if "orderId" in r:
        state = {"entry_price": price, "quantity": qty}
        save_json(STATE_FILE, state)
        requests.post(SHEET_WEBHOOK_URL, json={
            "side": "BUY (Entry)", "price": price, "quantity": qty
        })
        return {"status": "BUY gesetzt", "response": r}
    else:
        return {"error": "BUY fehlgeschlagen", "response": r}

def place_market_sell():
    state = load_json(STATE_FILE, {})
    if not state.get("entry_price"):
        return {"error": "Kein aktiver BUY"}

    qty = state.get("quantity", 0)
    if qty == 0:
        return {"error": "Menge 0"}

    ts = int(time.time() * 1000)
    params = {
        "symbol": SYMBOL, "side": "SELL", "type": "MARKET",
        "quantity": qty, "timestamp": ts, "recvWindow": 5000
    }
    query = '&'.join([f"{k}={v}" for k, v in params.items()])
    sig = get_sign(query)
    params["signature"] = sig
    headers = {"X-MEXC-APIKEY": API_KEY}
    r = requests.post(BASE_URL + "/api/v3/order", params=params, headers=headers).json()

    if "fills" in r:
        total_cost = sum(float(fill["price"]) * float(fill["qty"]) for fill in r["fills"])
        total_qty = sum(float(fill["qty"]) for fill in r["fills"])
        avg_price = total_cost / total_qty if total_qty else 0.0
    else:
        avg_price = get_orderbook()

    pnl = (avg_price - state["entry_price"]) * qty
    cum_pnl = load_json(PNL_FILE, 0.0) + pnl
    save_json(PNL_FILE, cum_pnl)
    save_json(STATE_FILE, {"entry_price": None, "quantity": None})

    requests.post(SHEET_WEBHOOK_URL, json={
        "side": "SELL (Close)", "price": round(avg_price, 6),
        "quantity": qty
    })

    return {
        "status": "SELL abgeschlossen",
        "avg_price": avg_price,
        "pnl": pnl,
        "cum_pnl": cum_pnl
    }

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "side" not in data:
        return {"error": "Kein Signal"}, 400

    side = data["side"].lower()
    if side == "buy":
        return place_limit_buy()
    elif side == "sell":
        return place_market_sell()
    else:
        return {"error": "Ungültiger side-Wert"}, 400


