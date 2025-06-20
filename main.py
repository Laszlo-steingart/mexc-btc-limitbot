from flask import Flask, request, jsonify
import requests
import time
import hmac
import hashlib

app = Flask(__name__)

API_KEY = 'mx0vgl8knwgL7bF14c'
API_SECRET = '921a17445d864768854f0d39a3667d38'

BASE_URL = 'https://api.mexc.com'
SYMBOL = 'SOLUSDT'

def get_headers(query_string):
    timestamp = str(int(time.time() * 1000))
    signature = hmac.new(
        API_SECRET.encode(),
        (query_string + "&timestamp=" + timestamp).encode(),
        hashlib.sha256
    ).hexdigest()
    return {
        'Content-Type': 'application/json',
        'ApiKey': API_KEY
    }, signature, timestamp

def get_price():
    url = f'{BASE_URL}/api/v3/ticker/price?symbol={SYMBOL}'
    response = requests.get(url)
    return float(response.json()['price'])

def get_balance(asset):
    url = f'{BASE_URL}/api/v3/account'
    query_string = f'recvWindow=5000'
    headers, signature, timestamp = get_headers(query_string)
    query = f'{query_string}&timestamp={timestamp}&signature={signature}'
    response = requests.get(f'{url}?{query}', headers=headers)
    balances = response.json()['balances']
    for b in balances:
        if b['asset'] == asset:
            return float(b['free'])
    return 0

def place_limit_order(side):
    balance = get_balance('USDT')
    if balance < 1:
        return {'error': 'Insufficient balance'}

    current_price = get_price()
    limit_price = round(current_price - 0.002, 3)
    qty = round(balance / limit_price, 2)

    url = f'{BASE_URL}/api/v3/order'
    query_string = f'symbol={SYMBOL}&side={side.upper()}&type=LIMIT&timeInForce=GTC&quantity={qty}&price={limit_price}&recvWindow=5000'
    headers, signature, timestamp = get_headers(query_string)
    query = f'{query_string}&timestamp={timestamp}&signature={signature}'
    response = requests.post(f'{url}?{query}', headers=headers)
    return response.json()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    side = data.get('side')
    if side not in ['buy', 'sell']:
        return jsonify({'error': 'Invalid side'}), 400
    result = place_limit_order(side)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=10000)

