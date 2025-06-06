import time
from binance.client import Client
from binance.enums import *
from datetime import datetime

import os

API_KEY = os.environ['API_KEY']
API_SECRET = os.environ['API_SECRET']

# --- Initialize client and sync timestamp ---
client = Client(API_KEY, API_SECRET)

def sync_time_offset():
    server_time = client.get_server_time()
    local_time = int(time.time() * 1000)
    offset = server_time['serverTime'] - local_time
    client.timestamp_offset = offset
    print(f"✅ Synced time offset: {offset} ms")

sync_time_offset()

# --- Trigger levels ---
buy_triggers = {
    101680: ('XRPUSDT', 6),
    100679: ('ADAUSDT', 6),
    100677: ('DOGEUSDT', 6),
}
sell_trigger = 104685

# Track which coins have been bought
triggered_coins = set()

def get_btc_price():
    ticker = client.futures_symbol_ticker(symbol='BTCUSDT')
    return float(ticker['price'])

# Define token precision for quantity
token_precision = {
    'XRPUSDT': 1,
    'ADAUSDT': 0,  # whole number only (e.g., 74)
    'DOGEUSDT': 0,  # whole number only (e.g., 264)
}

def market_buy(symbol, usdt_amount):
    try:
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        precision = token_precision.get(symbol, 2)
        quantity = round(usdt_amount / price, precision)

        print(f'🟢 Buying {symbol} | Qty: {quantity} | Price: {price}')
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
            positionSide='BOTH',
            recvWindow=10000,
            timestamp=int(time.time() * 1000 + client.timestamp_offset)
        )
        return order
    except Exception as e:
        print("❌ Buy order error:", e)

def market_sell(symbol):
    try:
        positions = client.futures_account()['positions']
        for p in positions:
            if p['symbol'] == symbol:
                qty = float(p['positionAmt'])
                if qty > 0:
                    qty = round(qty, 2)
                    print(f'🔴 Selling {symbol} | Qty: {qty}')
                    client.futures_create_order(
                        symbol=symbol,
                        side=SIDE_SELL,
                        type=ORDER_TYPE_MARKET,
                        quantity=qty,
                        positionSide='BOTH',
                        recvWindow=10000,
                        timestamp=int(time.time() * 1000 + client.timestamp_offset)
                    )
    except Exception as e:
        print("❌ Sell order error:", e)

def run_bot():
    print("🚀 Bot started. Monitoring BTC/USDT price...")
    while True:
        try:
            btc_price = get_btc_price()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] BTC/USDT Price: {btc_price}")

            # Buy logic
            for level, (coin, usdt_amount) in buy_triggers.items():
                if btc_price <= level and coin not in triggered_coins:
                    market_buy(coin, usdt_amount)
                    triggered_coins.add(coin)

            # Sell logic
            if btc_price >= sell_trigger and triggered_coins:
                print(f"🎯 Sell trigger hit at {btc_price}. Closing positions for: {triggered_coins}")
                for coin in triggered_coins:
                    market_sell(coin)
                print("✅ All positions closed. Exiting bot.")
                break

            time.sleep(3)

        except Exception as e:
            print("❌ Error in run loop:", e)
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
