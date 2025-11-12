import ccxt

exchange = ccxt.hyperliquid({'account_address': 'YOUR_WALLET_PUBLIC_ADDRESS', 'secret_key': 'YOUR_PRIVATE_KEY',})

balance = exchange.fetch_balance()
print(balance)


