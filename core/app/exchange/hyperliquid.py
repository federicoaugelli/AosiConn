import ccxt
import pandas as pd
import logging
import requests
from typing import Optional, Tuple, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Exchange:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        symbol: str,
        timeframe: str = "30m",
        limit: int = 50,
        testnet: bool = False,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        # Ensure proper symbol format for Hyperliquid (e.g., "BTC/USDC:USDC")
        if "/" not in symbol:
            symbol = f"{symbol}/USDC:USDC"
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        private_key = api_secret.strip()
        if private_key.lower().startswith("0x"):
            private_key = private_key[2:]
        self.client = ccxt.hyperliquid(
            {"walletAddress": api_key.strip(), "privateKey": private_key}
        )
        if testnet:
            self.client.set_sandbox_mode(True)
        # WORKAROUND: ccxt v4.5.18 crashes in fetch_spot_markets() on mainnet
        # AND testnet because some universe entries reference out-of-bounds
        # token indices, causing None + '/' + str to raise TypeError. This
        # breaks load_markets() and every method that depends on it.
        # Fix: pre-load only swap (perp) markets, skipping the broken spot path.
        # This is harmless since we only trade perps (USDC:USDC settle format).
        swap_markets = self.client.fetch_swap_markets({})
        self.client.markets = {m["symbol"]: m for m in swap_markets}
        self.client.markets_by_id = {m["id"]: m for m in swap_markets}
        self.client.markets_loaded = True
        logger.info(f"Hyperliquid exchange initialized with symbol: {self.symbol}")
        decimals = self.get_decimals()
        self.decimals = int(decimals) if decimals is not None else 0

    def _handle_error(self, operation: str, error: Exception) -> None:
        """Centralized error handling with logging"""
        logger.error(f"Error in {operation} for {self.symbol}: {str(error)}")

    def _fetch_spot_balance(self) -> Optional[float]:
        """Fetch USDC spot balance available for trading from Hyperliquid REST API.
        
        On unified accounts, Hyperliquid pools spot + perp into a single
        collateral pool.  ccxt's fetch_balance() only returns the perp side,
        missing the spot USDC that can be used as margin.
        """
        try:
            base_url = (
                "https://api.hyperliquid-testnet.xyz/info"
                if self.testnet
                else "https://api.hyperliquid.xyz/info"
            )
            payload = {"type": "spotClearinghouseState", "user": self.api_key}
            r = requests.post(base_url, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            for b in data.get("balances", []):
                if b.get("coin") == "USDC":
                    total = float(b.get("total", 0) or 0)
                    hold = float(b.get("hold", 0) or 0)
                    available = max(0.0, total - hold)
                    if available > 0:
                        logger.debug(
                            f"Spot USDC: total={total:.2f} hold={hold:.2f} "
                            f"available={available:.2f}"
                        )
                    return available
            return 0.0
        except Exception:
            return 0.0

    def get_balance(self) -> Optional[Tuple[float, float, float]]:
        """Returns (total, used, free) USDC balance (spot + perp merged)."""
        try:
            balance = self.client.fetch_balance()["USDC"]
            perp_total = float(balance.get("total", 0) or 0)
            perp_used = float(balance.get("used", 0) or 0)
            perp_free = float(balance.get("free", 0) or 0)

            spot_avail = self._fetch_spot_balance()

            total = perp_total + spot_avail
            free = perp_free + spot_avail
            used = perp_used

            logger.debug(
                f"Balance (merged): total={total:.2f} used={used:.2f} "
                f"free={free:.2f} (perp={perp_total:.2f}/{perp_used:.2f}/{perp_free:.2f} "
                f"+ spot_avail={spot_avail:.2f})"
            )
            return total, used, free
        except Exception as e:
            self._handle_error("get_balance", e)
            return None

    def set_position_percentage(
        self, percentage: float, leverage: int = 1
    ) -> Optional[Tuple[float, float]]:
        """Calculate position size based on percentage of balance"""
        try:
            balance_result = self.get_balance()
            if not balance_result:
                return None
            balance = balance_result[0]  # total balance
            price = self.get_ticker()
            if not price:
                return None
            amount_usdc = balance * percentage / 100 * leverage
            return amount_usdc / float(price), price
        except Exception as e:
            self._handle_error("set_position_percentage", e)
            return None

    def buy(self, amount: float, price: float) -> Optional[Dict[str, Any]]:
        """Execute buy order"""
        try:
            return self.client.create_order(
                symbol=self.symbol,
                type="market",
                side="buy",
                amount=amount,
                price=price,
            )
        except Exception as e:
            self._handle_error("buy", e)
            return None

    def sell(self, amount: float, price: float) -> Optional[Dict[str, Any]]:
        """Execute sell order"""
        try:
            return self.client.create_order(
                symbol=self.symbol,
                type="market",
                side="sell",
                amount=amount,
                price=price,
            )
        except Exception as e:
            self._handle_error("sell", e)
            return None

    def buy_percentage(
        self, percentage: float, leverage: int = 1
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """Buy with percentage of balance using a market order."""
        try:
            balance_result = self.get_balance()
            if not balance_result:
                return None
            balance = balance_result[0]
            price = self.get_ticker()
            if not price:
                return None
            amount_usdc = balance * percentage / 100 * leverage
            amount = round(amount_usdc / float(price), self.decimals)
            params = {"slippage": "0.01"}
            order = self.client.create_order(
                symbol=self.symbol,
                type="market",
                side="buy",
                amount=float(amount),
                price=float(price),
                params=params,
            )
            return order, amount
        except Exception as e:
            self._handle_error("buy_percentage", e)
            return None

    def sell_percentage(
        self, percentage: float, leverage: int = 1
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """Sell with percentage of balance using a market order."""
        try:
            balance_result = self.get_balance()
            if not balance_result:
                return None
            balance = balance_result[0]
            price = self.get_ticker()
            if not price:
                return None
            amount_usdc = balance * percentage / 100 * leverage
            amount = amount_usdc / float(price)
            amount = round(amount, self.decimals)
            params = {"slippage": "0.01"}
            order = self.client.create_order(
                symbol=self.symbol,
                type="market",
                side="sell",
                amount=float(amount),
                price=float(price),
                params=params,
            )
            return order, amount
        except Exception as e:
            self._handle_error("sell_percentage", e)
            return None

    def set_take_profit(
        self, side: str, amount: float, price: float
    ) -> Optional[Dict[str, Any]]:
        """Set a reduce-only take-profit trigger order."""
        try:
            order_side = "sell" if side in ["long", "1", "buy"] else "buy"
            params = {"reduceOnly": True, "takeProfitPrice": float(price)}
            return self.client.create_order(
                symbol=self.symbol,
                type="limit",
                side=order_side,
                amount=round(amount, self.decimals),
                price=float(price),
                params=params,
            )
        except Exception as e:
            self._handle_error("set_take_profit", e)
            return None

    def set_stop_loss(
        self, side: str, amount: float, price: float
    ) -> Optional[Dict[str, Any]]:
        """Set a reduce-only stop-loss trigger order."""
        try:
            order_side = "sell" if side in ["long", "1", "buy"] else "buy"
            params = {"reduceOnly": True, "stopLossPrice": float(price)}
            return self.client.create_order(
                symbol=self.symbol,
                type="market",
                side=order_side,
                amount=round(amount, self.decimals),
                price=float(price),
                params=params,
            )
        except Exception as e:
            self._handle_error("set_stop_loss", e)
            return None

    def set_margin_mode(
        self, mode: str = "isolated", leverage: int = 2
    ) -> Optional[Dict[str, Any]]:
        """Set margin mode and leverage"""
        try:
            return self.client.set_margin_mode(
                mode, self.symbol, params={"leverage": leverage}
            )
        except Exception as e:
            self._handle_error("set_margin_mode", e)
            return None

    def check_positions(self) -> Optional[list]:
        """Fetch all positions for the symbol"""
        try:
            return self.client.fetch_positions([self.symbol])
        except Exception as e:
            self._handle_error("check_positions", e)
            return None

    def check_open_positions(self) -> Optional[bool]:
        """Check if there are any open positions"""
        try:
            positions = self.check_positions()
            if positions is None:
                return None
            for position in positions:
                contracts = float(position.get("contracts", 0))
                if contracts != 0:
                    return True
            return False
        except Exception as e:
            self._handle_error("check_open_positions", e)
            return None

    def get_orders(self) -> Optional[list]:
        """Fetch open orders"""
        try:
            return self.client.fetch_open_orders(self.symbol)
        except Exception as e:
            self._handle_error("get_orders", e)
            return None

    def cancel_all_orders(self) -> int:
        """Cancel all open orders. Returns number of cancelled orders or -1 on error"""
        try:
            orders = self.get_orders()
            if orders is None:
                return -1
            for order in orders:
                self.client.cancel_order(order["id"], self.symbol)
            return len(orders)
        except Exception as e:
            self._handle_error("cancel_all_orders", e)
            return -1

    def get_ticker(self) -> Optional[float]:
        """Get current mark price"""
        try:
            params = {"type": "swap"}
            ticker = self.client.fetch_tickers([self.symbol], params=params)
            if self.symbol not in ticker:
                logger.error(f"Symbol {self.symbol} not found in ticker response.")
                return None
            return float(ticker[self.symbol]["info"]["markPx"])
        except Exception as e:
            self._handle_error("get_ticker", e)
            return None

    def get_decimals(self) -> Optional[int]:
        """Get size decimals for the symbol"""
        try:
            markets = self.client.load_markets()
            return markets[self.symbol]["info"]["szDecimals"]
        except Exception as e:
            self._handle_error("get_decimals", e)
            return None

    def get_max_leverage(self) -> Optional[int]:
        """Get maximum leverage for the symbol"""
        try:
            markets = self.client.load_markets()
            return markets[self.symbol]["info"]["maxLeverage"]
        except Exception as e:
            self._handle_error("get_max_leverage", e)
            return None

    def get_market(self) -> Optional[Dict[str, Any]]:
        """Get market info for the symbol"""
        try:
            markets = self.client.load_markets()
            return markets[self.symbol]
        except Exception as e:
            self._handle_error("get_market", e)
            return None

    def get_trades(self) -> Optional[list]:
        """Fetch my trades for the symbol"""
        try:
            return self.client.fetch_my_trades(self.symbol)
        except Exception as e:
            self._handle_error("get_trades", e)
            return None

    def get_data(self) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data as DataFrame"""
        try:
            ohlcv = self.client.fetch_ohlcv(
                symbol=self.symbol, timeframe=self.timeframe, limit=self.limit
            )
            df = pd.DataFrame(
                ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("datetime", inplace=True)
            return df
        except Exception as e:
            self._handle_error("get_data", e)
            return None
