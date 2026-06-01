import re

class ValidationError(Exception):
    """Exception raised when CLI inputs fail validation."""
    pass

def validate_symbol(symbol: str) -> str:
    """Validates and formats the symbol (e.g. BTCUSDT)."""
    if not symbol:
        raise ValidationError("Symbol is required.")
    
    clean_symbol = symbol.strip().upper()
    # Binance symbols are alphanumeric. Typically USDT-M futures end with USDT (e.g., BTCUSDT).
    if not re.match(r"^[A-Z0-9]{3,15}$", clean_symbol):
        raise ValidationError(
            f"Invalid symbol format '{symbol}'. Symbol must be alphanumeric uppercase (e.g. BTCUSDT)."
        )
    return clean_symbol

def validate_side(side: str) -> str:
    """Validates and formats the order side (BUY or SELL)."""
    if not side:
        raise ValidationError("Order side is required.")
    
    clean_side = side.strip().upper()
    if clean_side not in ("BUY", "SELL"):
        raise ValidationError(
            f"Invalid side '{side}'. Must be either 'BUY' or 'SELL'."
        )
    return clean_side

def validate_order_type(order_type: str) -> str:
    """Validates and formats the order type (MARKET, LIMIT, or STOP)."""
    if not order_type:
        raise ValidationError("Order type is required.")
    
    clean_type = order_type.strip().upper()
    if clean_type not in ("MARKET", "LIMIT", "STOP"):
        raise ValidationError(
            f"Invalid order type '{order_type}'. Supported types are 'MARKET', 'LIMIT', and 'STOP' (Stop-Limit)."
        )
    return clean_type

def validate_quantity(quantity) -> float:
    """Validates and converts quantity to a positive float."""
    if quantity is None or quantity == "":
        raise ValidationError("Quantity is required.")
    
    try:
        val = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Quantity '{quantity}' must be a numeric value.")
    
    if val <= 0:
        raise ValidationError(f"Quantity must be a positive number. Got {val}.")
    
    return val

def validate_price(price) -> float:
    """Validates and converts price to a positive float."""
    if price is None or price == "":
        raise ValidationError("Price is required for LIMIT and STOP orders.")
    
    try:
        val = float(price)
    except (ValueError, TypeError):
        raise ValidationError(f"Price '{price}' must be a numeric value.")
    
    if val <= 0:
        raise ValidationError(f"Price must be a positive number. Got {val}.")
    
    return val

def validate_stop_price(stop_price) -> float:
    """Validates and converts stop price to a positive float."""
    if stop_price is None or stop_price == "":
        raise ValidationError("Stop price is required for STOP (Stop-Limit) orders.")
    
    try:
        val = float(stop_price)
    except (ValueError, TypeError):
        raise ValidationError(f"Stop price '{stop_price}' must be a numeric value.")
    
    if val <= 0:
        raise ValidationError(f"Stop price must be a positive number. Got {val}.")
    
    return val

def validate_inputs(symbol: str, side: str, order_type: str, quantity, price=None, stop_price=None):
    """
    Consolidated helper to validate all inputs.
    Returns a dictionary of cleaned/formatted values.
    """
    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_quantity = validate_quantity(quantity)
    
    clean_price = None
    clean_stop_price = None
    
    if clean_type in ("LIMIT", "STOP"):
        clean_price = validate_price(price)
        
    if clean_type == "STOP":
        clean_stop_price = validate_stop_price(stop_price)
        
    return {
        "symbol": clean_symbol,
        "side": clean_side,
        "type": clean_type,
        "quantity": clean_quantity,
        "price": clean_price,
        "stop_price": clean_stop_price
    }
