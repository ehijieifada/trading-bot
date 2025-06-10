import time
from binance.client import Client
from binance.enums import *
from datetime import datetime
import os
import json

API_KEY = os.environ['API_KEY']
API_SECRET = os.environ['API_SECRET']

client = Client(API_KEY, API_SECRET)

def sync_time_offset():
    server_time = client.get_server_time()
    local_time = int(time.time() * 1000)
    offset = server_time['serverTime'] - local_time
    client.timestamp_offset = offset
    print(f"✅ Synced time offset: {offset} ms")

sync_time_offset()

triggered_coins = set()

token_precision = {
    'XRPUSDT': 1,
    'ADAUSDT': 0,
    'DOGEUSDT': 0,
    'SUIUSDT': 1,
    'LINKUSDT': 1,
    'TRXUSDT': 0,
    'PEPEUSDT': 0,
    'AVAXUSDT': 1,
    'DOTUSDT': 1,
    'LTCUSDT': 1,
}

def load_config():
    with open('config.json') as f:
        data = json.load(f)
        buy_triggers = {int(k): tuple(v) for k, v in data['buy_triggers'].items()}
        sell_trigger = int(data['sell_trigger'])
        return buy_triggers, sell_trigger

def get_btc_price():
    ticker = client.futures_symbol_ticker(symbol='BTCUSDT')
    return float(ticker['price'])

def open_short_position(symbol, usdt_amount):
    try:
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        precision = token_precision.get(symbol, 2)
        quantity = round(usdt_amount / price, precision)

        print(f'🔻 Shorting {symbol} | Qty: {quantity} | Price: {price}')
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL,  # Open short = SELL
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            positionSide='BOTH',
            recvWindow=10000,
            timestamp=int(time.time() * 1000 + client.timestamp_offset)
        )
        return order
    except Exception as e:
        print("❌ Short entry error:", e)

def close_short_position(symbol):
    try:
        positions = client.futures_account()['positions']
        for p in positions:
            if p['symbol'] == symbol:
                qty = float(p['positionAmt'])
                if qty < 0:  # short positions have negative qty
                    qty = round(abs(qty), 2)
                    print(f'✅ Closing short {symbol} | Qty: {qty}')
                    client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_BUY,  # Close short = BUY
                        type=ORDER_TYPE_MARKET,
                        quantity=qty,
                        positionSide='BOTH',
                        recvWindow=10000,
                        timestamp=int(time.time() * 1000 + client.timestamp_offset)
                    )
    except Exception as e:
        print("❌ Short close error:", e)

def run_bot():
    print("🚀 Bot started. Monitoring BTC/USDT price for SHORT positions...")
    while True:
        try:
            btc_price = get_btc_price()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] BTC/USDT Price: {btc_price}")

            buy_triggers, sell_trigger = load_config()

            for level, (coin, usdt_amount) in buy_triggers.items():
                if btc_price >= level and coin not in triggered_coins:
                    open_short_position(coin, usdt_amount)
                    triggered_coins.add(coin)

            if btc_price <= sell_trigger and triggered_coins:
                print(f"🎯 Close trigger hit at {btc_price}. Closing shorts for: {triggered_coins}")
                for coin in triggered_coins:
                    close_short_position(coin)
                print("✅ All positions closed. Exiting bot.")
                break

            time.sleep(3)

        except Exception as e:
            print("❌ Error in run loop:", e)
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
