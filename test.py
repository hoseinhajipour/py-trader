import MetaTrader5 as mt5
import time

if not mt5.initialize(path="C:/Program Files/AMarkets - MetaTrader 5/terminal64.exe",login=6615926, server="AMarkets-Demo",password="yw*jZYY9"):
        print("initialize() failed, error code =",mt5.last_error())

if not mt5.initialize(path="C:/Program Files/IFC Markets MT5/terminal64.exe",login=789243, server="IFCMarkets-Demo",password="hMvG76gZh$"):
        print("initialize() failed, error code =",mt5.last_error())  
       
fusion_ticker = mt5.symbol_info_tick("ETHUSD")
exness_ticker = mt5.symbol_info_tick("ETHUSD")