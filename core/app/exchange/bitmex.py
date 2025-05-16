from ratelimit import limits, sleep_and_retry
import json, time, requests, logging
import bitmex

clients = {}
api_call_queue = []

def get_client(api_key, api_secret):
    key_pair = (api_key, api_secret)
    if key_pair not in clients:
        clients[key_pair] = bitmex.bitmex(test = False, api_key=api_key, api_secret=api_secret)
    return clients[key_pair]

def limit_wrapper(func):
    @sleep_and_retry
    @limits(calls=120, period=60)
    def wrapper(*args, **kwargs):
        # Add the function and arguments to the queue
        api_call_queue.append((func, args, kwargs))
        return process_queue()
    return wrapper

def process_queue():
    while api_call_queue:
        # Get the next function and arguments from the queue
        func, args, kwargs = api_call_queue.pop(0)
        try:
            api_key, api_secret = args[0], args[1]
            client = get_client(api_key, api_secret)
            return func(client, *args[2:], **kwargs)
        except Exception as e:
            return e

def unauthenticated_wrapper(func):
    @sleep_and_retry
    @limits(calls=30, period=60)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@limit_wrapper
def get_balance(client, currency):
    return client.User.User_getMargin(currency = currency).result()[0]



@limit_wrapper
def buy(client, pair, qty):
    result = client.Order.Order_new(symbol = pair, ordType = "Market", orderQty = qty).result()
    return result

    

@limit_wrapper
def sell(client, pair, qty):
    result = client.Order.Order_new(symbol = pair, ordType = "Market", orderQty = -1 * qty).result() 
    return result

    

@limit_wrapper
def close(client, pair):
    result = client.Order.Order_new(symbol = pair, execInst = 'Close').result()
    return result

    

@limit_wrapper
def leverage(client, pair, lev):
    result = client.Position.Position_updateLeverage(symbol = pair, leverage = lev).result()
    return result

    

@limit_wrapper
def isExit(client, pair):
    result = client.Position.Position_get(filter=json.dumps({"symbol": pair})).result()[0][0]['currentQty']
    return result

    

@limit_wrapper
def cancel_all(client, pair):
    result = client.Order.Order_cancelAll(symbol = pair).result()
    return result

    

@limit_wrapper
def set_take_profit(client, pair, qty, signal):
    result = client.Order.Order_new(symbol = pair, ordType = "MarketIfTouched", stopPx = signal, execInst = "MarkPrice", orderQty = qty).result()
    return result

    

@limit_wrapper
def set_stop_loss(client, pair, qty, signal):
    result = client.Order.Order_new(symbol = pair, ordType = "Stop", stopPx = signal, execInst = "MarkPrice", orderQty = qty).result()
    return result

    

@unauthenticated_wrapper
def get_data(size, pair, count):
    endpoint = 'https://www.bitmex.com/api/v1/trade/bucketed'
    params = {
        'partial': True,
        'binSize': size,
        'symbol': pair,
        'count': count,
        'reverse': True
    }
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        data = response.json()
        return data
    except Exception as e:
        return e

@unauthenticated_wrapper
def get_pair():
    endpoint = 'https://www.bitmex.com/api/v1/instrument/active'
    try:
        response = requests.get(endpoint, timeout=10)
        data = response.json()
        return data
    except Exception as e:
        return e

@unauthenticated_wrapper
def ask_price(pair):
    endpoint = 'https://www.bitmex.com/api/v1/instrument'
    params = {
        'symbol': pair
    }
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        data = response.json()
        return data[0]["askPrice"]
    except Exception as e:
        return e

@unauthenticated_wrapper
def tick_size(pair):
    endpoint = 'https://www.bitmex.com/api/v1/instrument'
    params = {
        'symbol': pair
    }
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        data = response.json()
        return data[0]["tickSize"]
    except Exception as e:
        return e
    
@unauthenticated_wrapper
def multiplier(pair):
    endpoint = 'https://www.bitmex.com/api/v1/instrument'
    params = {
        'symbol': pair
    }
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        data = response.json()
        return data[0]["multiplier"]
    except Exception as e:
        return e

@unauthenticated_wrapper
def instrument(pair):
    endpoint = 'https://www.bitmex.com/api/v1/instrument'
    params = {
        'symbol': pair
    }
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        data = response.json()
        return data
    except Exception as e:
        return e

