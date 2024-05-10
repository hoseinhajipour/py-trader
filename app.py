from flask import Flask, render_template, request
import MetaTrader5 as mt5

app = Flask(__name__)

# Connect to MetaTrader 5 terminal
mt5.initialize()

def get_account_balance():
    account_info = mt5.account_info()
    balance = account_info.balance
    return balance

def place_order(symbol, volume, order_type, price):
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
        "type_filling": mt5.ACCOUNT_TRADE_MODE_DEMO,
    }
    result = mt5.order_send(request_data)
    return result

def close_positions(symbol_to_close):
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
                return "Close order failed: {}".format(result.comment)
            else:
                return "Position {} closed successfully".format(position_id)
    else:
        return f"No positions found for symbol {symbol_to_close}"

@app.route('/')
def index():
    balance = get_account_balance()
    return render_template('index.html', balance=balance)

@app.route('/buy', methods=['POST'])
def buy():
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
        result = place_order(symbol_input, lot_size, mt5.ORDER_TYPE_BUY, symbol_info.ask)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            message = "Buy order failed: {}".format(result.comment)
        else:
            message = "Buy order placed successfully"
    balance = get_account_balance()
    return render_template('index.html', message=message, balance=balance)

@app.route('/sell', methods=['POST'])
def sell():
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
        result = place_order(symbol_input, lot_size, mt5.ORDER_TYPE_SELL, symbol_info.bid)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            message = "Sell order failed: {}".format(result.comment)
        else:
            message = "Sell order placed successfully"
    balance = get_account_balance()
    return render_template('index.html', message=message, balance=balance)

@app.route('/close', methods=['POST'])
def close():
    symbol_to_close = request.form['symbol']
    message = close_positions(symbol_to_close)
    balance = get_account_balance()
    return render_template('index.html', message=message, balance=balance)

@app.route('/metatrader-actions', methods=['POST'])
def metatrader_actions():
    action = request.form['action']
    if action == 'buy':
        return buy()
    elif action == 'sell':
        return sell()
    elif action == 'close':
        return close()
      
if __name__ == '__main__':
    app.run(debug=True)
