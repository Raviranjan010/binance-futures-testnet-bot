from bot.client import BinanceFuturesClient

def place_order(client: BinanceFuturesClient, symbol: str, side: str, order_type: str, quantity: float, price: float = None, stop_price: float = None):
    """
    Builds the parameter payload and sends a POST request to place an order.
    
    :param client: An instance of BinanceFuturesClient.
    :param symbol: Trading pair (e.g., BTCUSDT).
    :param side: BUY or SELL.
    :param order_type: MARKET, LIMIT, or STOP (maps to Stop Loss Limit).
    :param quantity: Quantity to trade.
    :param price: Price for LIMIT and STOP orders.
    :param stop_price: Trigger price for STOP orders.
    :return: Dict response from the API.
    """
    params = {
        "symbol": symbol,
        "side": side,
        "quantity": str(quantity)
    }

    if order_type == "MARKET":
        params["type"] = "MARKET"
        
    elif order_type == "LIMIT":
        params["type"] = "LIMIT"
        params["price"] = str(price)
        params["timeInForce"] = "GTC"
        
    elif order_type == "STOP":
        # STOP is the Stop-Limit order type on USDS-M Futures.
        # Requires both stopPrice (trigger) and price (limit execution price).
        params["type"] = "STOP"
        params["price"] = str(price)
        params["stopPrice"] = str(stop_price)
        params["timeInForce"] = "GTC"
        
    else:
        raise ValueError(f"Unsupported order type: {order_type}")

    # Send a signed POST request to /fapi/v1/order
    return client._send_request(method="POST", endpoint="/fapi/v1/order", params=params, signed=True)
