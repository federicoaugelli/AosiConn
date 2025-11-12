from dydx_v4_client.network import make_mainnet

#from ratelimit import limits, sleep_and_retry
#import json, time, requests
#
#clients = {}
#api_call_queue = []
#
#def get_client(api_key, api_secret):
#    key_pair = (api_key, api_secret)
#    if key_pair not in clients:
#        clients[key_pair] = bitmex.bitmex(test = False, api_key=api_key, api_secret=api_secret)
#    return clients[key_pair]
#
#def limit_wrapper(func):
#    @sleep_and_retry
#    @limits(calls=120, period=60)
#    def wrapper(*args, **kwargs):
#        # Add the function and arguments to the queue
#        api_call_queue.append((func, args, kwargs))
#        return process_queue()
#    return wrapper
#
#def process_queue():
#    while api_call_queue:
#        # Get the next function and arguments from the queue
#        func, args, kwargs = api_call_queue.pop(0)
#        try:
#            api_key, api_secret = args[0], args[1]
#            client = get_client(api_key, api_secret)
#            return func(client, *args[2:], **kwargs)
#        except Exception as e:
#            return e
#
#def unauthenticated_wrapper(func):
#    @sleep_and_retry
#    @limits(calls=30, period=60)
#    def wrapper(*args, **kwargs):
#        return func(*args, **kwargs)
#    return wrapper
#
#@limit_wrapper
#def get_balance(client, currency):
#
#@limit_wrapper
#def buy(client, pair, qty):
#
#@limit_wrapper
#def sell(client, pair, qty):
#
#@limit_wrapper
#def close(client, pair):
#
#@limit_wrapper
#def leverage(client, pair, lev):
#
#@limit_wrapper
#def isExit(client, pair):
#
#@limit_wrapper
#def cancel_all(client, pair):
#
#@limit_wrapper
#def set_take_profit(client, pair, qty, signal):
#
#@limit_wrapper
#def set_stop_loss(client, pair, qty, signal):
#
#@unauthenticated_wrapper
#def get_data(size, pair, count):
#
#@unauthenticated_wrapper
#def get_pair():
#
#@unauthenticated_wrapper
#def ask_price(pair):
#
#@unauthenticated_wrapper
#def tick_size(pair):
#    
#@unauthenticated_wrapper
#def multiplier(pair):
#
#@unauthenticated_wrapper
#def instrument(pair):
#
