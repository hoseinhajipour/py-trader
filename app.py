from flask import Flask, render_template, request, jsonify
import MetaTrader5 as mt5
import time
import json

app = Flask(__name__)



# Create a dictionary to store MetaTrader accounts
meta_trader_accounts = {}

def get_account_balance(account_id):
    if not  mt5.initialize(path= meta_trader_accounts[account_id]['path'], login=int(meta_trader_accounts[account_id]['login']) , server=meta_trader_accounts[account_id]['server'], password=meta_trader_accounts[account_id]['password']):
        print("initialize() failed, error code =",mt5.last_error())
    print(meta_trader_accounts[account_id])
    #mt5.login(meta_trader_accounts[account_id]['login'], meta_trader_accounts[account_id]['password'],meta_trader_accounts[account_id]['server'])
    account_info = mt5.account_info()
    balance = 0
    if account_info :
        print("account_info x : ",account_info)
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
            balance = get_account_balance(account_id)
            meta_trader_accounts[account_id]['balance'] = balance
except FileNotFoundError:
    pass

def save_meta_trader_accounts():
    with open('mt_accounts.json', 'w') as file:
        json.dump(meta_trader_accounts, file)



def place_order(account_id, symbol, volume, order_type, price,type_filling):
    print("Start place_order \n")
    
    if not mt5.initialize(path=meta_trader_accounts[account_id]['path'], login=int(meta_trader_accounts[account_id]['login']), server=meta_trader_accounts[account_id]['server'], password=meta_trader_accounts[account_id]['password']):
        print("initialize() failed, error code =", mt5.last_error())
        return "Initialize failed"
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        mt5.shutdown()
        return f"Failed to get symbol information for {symbol}"
    
    deviation = 10  # Define deviation according to your strategy or requirements
    request_data = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": deviation,
        "magic": 234000,
        "comment": "Order from API",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": type_filling,  # Updated type_filling parameter
    }
    result = mt5.order_send(request_data)
    print(result)
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
    return render_template('index.html', meta_trader_accounts=meta_trader_accounts)

@app.route('/add_account', methods=['POST'])
def add_account():
    login = request.form['login']
    password = request.form['password']
    server = request.form['server']
    path = request.form['path']
    
    # Extract symbol names and lot percentages from form data
    symbol_lot_percentages = {}
    symbols = ['XAUUSD', 'Nasdaq', 'Dow_Jones', 'Oil', 'EURUSD']
    for symbol in symbols:
        symbol_lot_percentages[symbol] = {
            'symbol': request.form.get(f"{symbol}_symbol"),
            'lot_percent': float(request.form.get(f"{symbol}_lot_percent"))
        }
    
    # Store account details and symbol lot percentages
    account_id = len(meta_trader_accounts) + 1
    meta_trader_accounts[account_id] = {
        'login': login,
        'password': password,
        'server': server,
        'path': path,
        'symbol_lot_percentages': symbol_lot_percentages
    }
    
    # Save updated meta_trader_accounts dictionary to JSON file
    save_meta_trader_accounts()
    

    try:
        with open('mt_accounts.json', 'r') as file:
            meta_trader_accounts = json.load(file)
            print(meta_trader_accounts)
            # Load balances for each account
            for account_id in meta_trader_accounts:
                balance = get_account_balance(account_id)
                meta_trader_accounts[account_id]['balance'] = balance
    except FileNotFoundError:
        pass

    return jsonify(success=True)

@app.route('/buy', methods=['POST'])
def buy():
    account_id = int(request.form['account_id'])
    symbol_input = request.form['symbol']
    lot_size = float(request.form['lot_size'])
    
    # Retrieve symbol and lot percent from account's data
    symbol_lot_percentages = meta_trader_accounts[account_id]['symbol_lot_percentages']
    
    # Check if the symbol exists in the account's data
    if symbol_input in symbol_lot_percentages:
        symbol_info = mt5.symbol_info(symbol_input)
        if symbol_info is None:
            message = f"Failed to get symbol information for {symbol_input}"
        elif not symbol_info.visible:
            message = f"Symbol {symbol_input} is not visible, please check if it's available."
        elif not symbol_info.bid or not symbol_info.ask:
            message = f"Failed to get bid/ask prices for symbol {symbol_input}"
        else:
            # Calculate lot size based on lot percentage from account data
            lot_percent = symbol_lot_percentages[symbol_input]['lot_percent']
            calculated_lot_size = lot_size * lot_percent / 100.0
            
            result = place_order(account_id, symbol_input, calculated_lot_size, mt5.ORDER_TYPE_BUY, symbol_info.ask, mt5.ORDER_FILLING_FOK)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                message = f"Buy order failed: {result.comment}"
            else:
                message = "Buy order placed successfully"
    else:
        message = f"Symbol {symbol_input} not found in account's symbol lot percentages"
    
    balance = get_account_balance(account_id)
    return jsonify(message=message, balance=balance)

@app.route('/sell', methods=['POST'])
def sell():
    account_id = int(request.form['account_id'])
    symbol_input = request.form['symbol']
    lot_size = float(request.form['lot_size'])
    
    # Retrieve symbol and lot percent from account's data
    symbol_lot_percentages = meta_trader_accounts[account_id]['symbol_lot_percentages']
    
    # Check if the symbol exists in the account's data
    if symbol_input in symbol_lot_percentages:
        symbol_info = mt5.symbol_info(symbol_input)
        if symbol_info is None:
            message = f"Failed to get symbol information for {symbol_input}"
        elif not symbol_info.visible:
            message = f"Symbol {symbol_input} is not visible, please check if it's available."
        elif not symbol_info.bid or not symbol_info.ask:
            message = f"Failed to get bid/ask prices for symbol {symbol_input}"
        else:
            # Calculate lot size based on lot percentage from account data
            lot_percent = symbol_lot_percentages[symbol_input]['lot_percent']
            calculated_lot_size = lot_size * lot_percent / 100.0
            
            result = place_order(account_id, symbol_input, calculated_lot_size, mt5.ORDER_TYPE_SELL, symbol_info.bid, mt5.ORDER_FILLING_FOK)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                message = f"Sell order failed: {result.comment}"
            else:
                message = "Sell order placed successfully"
    else:
        message = f"Symbol {symbol_input} not found in account's symbol lot percentages"
    
    balance = get_account_balance(account_id)
    return jsonify(message=message, balance=balance)

@app.route('/close', methods=['POST'])
def close():
    account_id = int(request.form['account_id'])
    symbol_to_close = request.form['symbol']
    
    # Retrieve symbol and lot percent from account's data
    symbol_lot_percentages = meta_trader_accounts[account_id]['symbol_lot_percentages']
    
    # Check if the symbol exists in the account's data
    if symbol_to_close in symbol_lot_percentages:
        message = close_positions(account_id, symbol_to_close)
    else:
        message = f"Symbol {symbol_to_close} not found in account's symbol lot percentages"
    
    balance = get_account_balance(account_id)
    return jsonify(message=message, balance=balance)


@app.route('/remove_account', methods=['POST'])
def remove_account():
    select_account_id = request.form['account_id']
    for account_id in meta_trader_accounts:
        if(account_id == select_account_id):
            del meta_trader_accounts[account_id]
            save_meta_trader_accounts()
            return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True)
