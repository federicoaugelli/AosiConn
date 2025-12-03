import ccxt
import pandas as pd

class Exchange():
    def __init__(self, api_key, api_secret, symbol, timeframe='30m', limit=50, testnet=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.client = ccxt.hyperliquid({'walletAddress': api_key, 'privateKey': api_secret})
        if testnet:
            self.client.set_sandbox_mode(True)

    def get_balance(self):
        try:
            balance = self.client.fetch_balance()['USDC']
            return balance['total'], balance['used'], balance['free']
        except:
            return None

    def set_position_percentage(self, percentage, leverage=1):
        try:
            balance = self.get_balance()
            price = self.get_ticker()
            amount_usdc = balance * percentage / 100 * leverage
            return amount_usdc / float(price), price
        except:
            return None

    def buy(self, amount, price):
        try:
            return self.client.create_order(symbol=self.symbol, type='market', side='buy', amount=amount, price=price)
        except:
            return None

    def sell(self, amount, price):
        try:
            return self.client.create_order(symbol=self.symbol, type='market', side='sell', amount=amount, price=price)
        except:
            return None

    # TODO test
    def buy_percentage(self, percentage, leverage=1):
        try:
            balance = self.get_balance()
            price = self.get_ticker()
            amount_usdc = balance * percentage / 100 * leverage
            amount = amount_usdc / float(price)
            return self.client.create_order(symbol=self.symbol, type='market', side='buy', amount=amount, price=price), amount
        except:
            return None

    # TODO
    def sell_percentage(self, percentage, leverage=1):
        try:
            balance = self.get_balance()
            price = self.get_ticker()
            amount_usdc = balance * percentage / 100 * leverage
            amount = amount_usdc / float(price)
            return self.client.create_order(symbol=self.symbol, type='market', side='sell', amount=amount, price=price), amount
        except:
            return None

    def set_take_profit(self, side, amount, price):
        try:
            if side == 'long' or side == 1 or side == 'buy':
                return self.client.create_order(symbol=self.symbol, type='limit', side='sell', amount=amount, price=price)
            else:
                return self.client.create_order(symbol=self.symbol, type='limit', side='buy', amount=amount, price=price)
        except:
            return None

    def set_stop_loss(self, side, amount, price):
        try:
            if side == 'long' or side == 1 or side == 'buy':
                return self.client.create_order(symbol=self.symbol, type='stop', side='sell', amount=amount, price=price)
            else:
                return self.client.create_order(symbol=self.symbol, type='stop', side='buy', amount=amount, price=price)
        except:
            return None

    def set_margin_mode(self, mode="isolated", leverage=2):
        try:
            return self.client.set_margin_mode(mode, self.symbol, params={'leverage': leverage})
        except:
            return None

    def check_positions(self):
        try:
            return self.client.fetch_positions([self.symbol])
        except:
            return None

    # TODO test
    def check_open_positions(self):
        try:
            positions = self.client.check_positions()
            for position in positions:
                if position['contracts'] > 0:
                    return False
            return True
        except:
            return None

    def get_orders(self):
        try:
            return self.client.fetch_open_orders(self.symbol)
        except:
            return None

    def cancel_all_orders(self):
        try:
            orders = self.get_orders()
            for order in orders:
                self.client.cancel_order(order['id'], self.symbol)
            return 0
        except:
            return None

    def get_ticker(self):
        try:
            #return self.client.load_markets()[self.symbol]['info']['markPx']
            return self.client.fetch_tickers([self.symbol])[self.symbol]['info']['markPx']
        except:
            return None

    def get_decimals(self):
        try:
            return self.client.load_markets()[self.symbol]['info']['szDecimals']
        except:
            return None

    def get_max_leverage(self):
        try:
            return self.client.load_markets()[self.symbol]['info']['maxLeverage']
        except:
            return None

    def get_market(self):
        try:
            return self.client.load_markets()[self.symbol]
        except:
            return None

    def get_trades(self):
        try:
            return self.client.fetch_my_trades(self.symbol)
        except:
            return None

    def get_data(self):
        try:
            ohlcv = self.client.fetch_ohlcv(symbol=self.symbol, timeframe=self.timeframe, limit=self.limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            return df
        except Exception as e:
            return e
