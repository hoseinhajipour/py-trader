from flask import Flask, render_template, request, jsonify
import MetaTrader5 as mt5
import json

app = Flask(__name__)

# Initialize MetaTrader 5 terminal
mt5.initialize()

# Create a dictionary to store MetaTrader accounts
meta_trader_accounts = {}

def get_account_balance(account_id):
    mt5.login(meta_trader_accounts[account_id]['login'], meta_trader_accounts[account_id]['password'])
    account_info = mt5.account_info()
    balance = account_info.balance
    mt5.shutdown()
    return balance

# Load MetaTrader accounts from local storage
try:
    with open('mt_accounts.json', 'r') as file:
        meta_trader_accounts = json.load(file)
        print(meta_trader_accounts)
        # Load balances for each account
        for account_id in meta_trader_accounts:
            print("account_id : "+account_id)
            balance = get_account_balance(account_id)
            print(balance)
            meta_trader_accounts[account_id]['balance'] = balance
except FileNotFoundError:
    pass

def save_meta_trader_accounts():
    with open('mt_accounts.json', 'w') as file:
        json.dump(meta_trader_accounts, file)



def place_order(account_id, symbol, volume, order_type, price):
    mt5.login(meta_trader_accounts[account_id]['login'], meta_trader_accounts[account_id]['password'])
    request_data = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": 10,
        "magic": 234000,
        "comment": "Order from API",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    result = mt5.order_send(request_data)
    mt5.shutdown()
    return result

def close_positions(account_id, symbol_to_close):
    mt5.login(meta_trader_accounts[account_id]['login'], meta_trader_accounts[account_id]['password'])
    positions = mt5.positions_get(symbol=symbol_to_close)
    if positions:
        for position in positions:
            position_id = position.ticket
            price = mt5.symbol_info_tick(symbol_to_close).bid
            deviation = 20
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol_to_close,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_SELL,
                "position": position_id,
                "price": price,
                "deviation": deviation,
                "magic": 234000,
                "comment": "Close order from API",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_FOK,
            }
            result = mt5.order_send(close_request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                mt5.shutdown()
                return "Close order failed: {}".format(result.comment)
            else:
                mt5.shutdown()
                return "Position {} closed successfully".format(position_id)
    else:
        mt5.shutdown()
        return f"No positions found for symbol {symbol_to_close}"

@app.route('/')
def index():
    return render_template('index02.html', meta_trader_accounts=meta_trader_accounts)

@app.route('/add_account', methods=['POST'])
def add_account():
    login = request.form['login']
    password = request.form['password']
    account_id = len(meta_trader_accounts) + 1
    meta_trader_accounts[account_id] = {'login': login, 'password': password}
    save_meta_trader_accounts()
    return jsonify(success=True)

@app.route('/buy', methods=['POST'])
def buy():
    account_id = int(request.form['account_id'])
    symbol_input = request.form['symbol']
    lot_size = float(request.form['lot_size'])
    symbol_info = mt5.symbol_info(symbol_input)
    if symbol_info is None:
        message = "Failed to get symbol information for {}".format(symbol_input)
    elif not symbol_info.visible:
        message = "Symbol {} is not visible, please check if it's available.".format(symbol_input)
    elif not symbol_info.bid or not symbol_info.ask:
        message = "Failed to get bid/ask prices for symbol {}".format(symbol_input)
    else:
        result = place_order(account_id, symbol_input, lot_size, mt5.ORDER_TYPE_BUY, symbol_info.ask)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            message = "Buy order failed: {}".format(result.comment)
        else:
            message = "Buy order placed successfully"
    balance = get_account_balance(account_id)
    return jsonify(message=message, balance=balance)

@app.route('/sell', methods=['POST'])
def sell():
    account_id = int(request.form['account_id'])
    symbol_input = request.form['symbol']
    lot_size = float(request.form['lot_size'])
    symbol_info = mt5.symbol_info(symbol_input)
    if symbol_info is None:
        message = "Failed to get symbol information for {}".format(symbol_input)
    elif not symbol_info.visible:
        message = "Symbol {} is not visible, please check if it's available.".format(symbol_input)
    elif not symbol_info.bid or not symbol_info.ask:
        message = "Failed to get bid/ask prices for symbol {}".format(symbol_input)
    else:
        result = place_order(account_id, symbol_input, lot_size, mt5.ORDER_TYPE_SELL, symbol_info.bid)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            message = "Sell order failed: {}".format(result.comment)
        else:
            message = "Sell order placed successfully"
    balance = get_account_balance(account_id)
    return jsonify(message=message, balance=balance)

@app.route('/close', methods=['POST'])
def close():
    account_id = int(request.form['account_id'])
    symbol_to_close = request.form['symbol']
    message = close_positions(account_id, symbol_to_close)
    balance = get_account_balance(account_id)
    return jsonify(message=message, balance=balance)

if __name__ == '__main__':
    app.run(debug=True)
