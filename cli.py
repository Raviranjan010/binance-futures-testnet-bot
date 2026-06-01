import os
import sys
import argparse
from dotenv import load_dotenv

from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError, BinanceClientError
from bot.validators import validate_inputs, ValidationError
from bot.orders import place_order

# Try importing rich, fall back to basic print if not available
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, Confirm
    CONSOLE_AVAILABLE = True
except ImportError:
    CONSOLE_AVAILABLE = False

# Initialize console
console = Console() if CONSOLE_AVAILABLE else None

def print_banner():
    if CONSOLE_AVAILABLE:
        console.print(Panel.fit(
            "[bold cyan]🤖 Binance Futures Testnet Trading Bot 🤖[/bold cyan]\n"
            "[dim]A clean, structured CLI bot for placing USDT-M futures orders[/dim]",
            border_style="cyan"
        ))
    else:
        print("=" * 50)
        print("🤖 Binance Futures Testnet Trading Bot 🤖")
        print("=" * 50)

def print_error(message: str):
    if CONSOLE_AVAILABLE:
        console.print(f"[bold red]Error:[/bold red] {message}")
    else:
        print(f"Error: {message}")

def print_success(message: str):
    if CONSOLE_AVAILABLE:
        console.print(f"[bold green]Success:[/bold green] {message}")
    else:
        print(f"Success: {message}")

def run_interactive():
    print_banner()
    
    if CONSOLE_AVAILABLE:
        console.print("[yellow]Starting Interactive Order Placement Menu...[/yellow]\n")
        
        # 1. Symbol
        while True:
            symbol = Prompt.ask("[bold]Enter Symbol[/bold] (e.g., BTCUSDT, ETHUSDT)", default="BTCUSDT").strip().upper()
            try:
                from bot.validators import validate_symbol
                symbol = validate_symbol(symbol)
                break
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
        
        # 2. Side
        side_choice = Prompt.ask(
            "[bold]Select Side[/bold]", 
            choices=["BUY", "SELL"], 
            default="BUY"
        )
        side = side_choice
        
        # 3. Order Type
        type_choice = Prompt.ask(
            "[bold]Select Order Type[/bold]",
            choices=["MARKET", "LIMIT", "STOP"],
            default="MARKET"
        )
        order_type = type_choice
        
        # 4. Quantity
        while True:
            qty_input = Prompt.ask("[bold]Enter Quantity[/bold] (e.g., 0.001)")
            try:
                from bot.validators import validate_quantity
                quantity = validate_quantity(qty_input)
                break
            except ValidationError as e:
                console.print(f"[red]{e}[/red]")
                
        # 5. Price (only for LIMIT/STOP)
        price = None
        if order_type in ("LIMIT", "STOP"):
            while True:
                price_input = Prompt.ask(f"[bold]Enter Limit Price[/bold]")
                try:
                    from bot.validators import validate_price
                    price = validate_price(price_input)
                    break
                except ValidationError as e:
                    console.print(f"[red]{e}[/red]")
                    
        # 6. Stop Price (only for STOP)
        stop_price = None
        if order_type == "STOP":
            while True:
                stop_input = Prompt.ask("[bold]Enter Trigger/Stop Price[/bold]")
                try:
                    from bot.validators import validate_stop_price
                    stop_price = validate_stop_price(stop_input)
                    break
                except ValidationError as e:
                    console.print(f"[red]{e}[/red]")
                    
        return {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price,
            "stop_price": stop_price
        }
    else:
        # Fallback raw inputs if rich not installed
        symbol = input("Enter Symbol (default BTCUSDT): ").strip().upper() or "BTCUSDT"
        side = input("Enter Side (BUY/SELL): ").strip().upper()
        order_type = input("Enter Order Type (MARKET/LIMIT/STOP): ").strip().upper()
        quantity = input("Enter Quantity: ").strip()
        price = input("Enter Price (if LIMIT or STOP): ").strip() if order_type in ("LIMIT", "STOP") else None
        stop_price = input("Enter Stop Price (if STOP): ").strip() if order_type == "STOP" else None
        
        return {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "price": price,
            "stop_price": stop_price
        }

def display_summary(inputs: dict):
    if CONSOLE_AVAILABLE:
        table = Table(title="Order Request Summary", title_style="bold magenta", box=None)
        table.add_column("Parameter", style="cyan", justify="right")
        table.add_column("Value", style="white")
        
        table.add_row("Symbol", inputs["symbol"])
        side_color = "green" if inputs["side"] == "BUY" else "red"
        table.add_row("Side", f"[{side_color}]{inputs['side']}[/{side_color}]")
        table.add_row("Order Type", inputs["type"])
        table.add_row("Quantity", str(inputs["quantity"]))
        
        if inputs["price"] is not None:
            table.add_row("Limit Price", str(inputs["price"]))
        if inputs["stop_price"] is not None:
            table.add_row("Stop/Trigger Price", str(inputs["stop_price"]))
            
        console.print(Panel(table, border_style="magenta", expand=False))
    else:
        print("\n--- Order Request Summary ---")
        for k, v in inputs.items():
            if v is not None:
                print(f"{k.replace('_', ' ').title()}: {v}")
        print("-----------------------------\n")

def display_response(res: dict):
    if CONSOLE_AVAILABLE:
        table = Table(title="Order Execution Details", title_style="bold green", show_header=True, header_style="bold green")
        table.add_column("Field", style="cyan")
        table.add_column("Response Value", style="white")
        
        table.add_row("Order ID", str(res.get("orderId")))
        table.add_row("Client Order ID", str(res.get("clientOrderId")))
        table.add_row("Symbol", str(res.get("symbol")))
        
        side = str(res.get("side"))
        side_color = "green" if side == "BUY" else "red"
        table.add_row("Side", f"[{side_color}]{side}[/{side_color}]")
        table.add_row("Type", str(res.get("type")))
        
        status = str(res.get("status"))
        status_color = "green" if status in ("FILLED", "NEW") else "yellow"
        table.add_row("Status", f"[{status_color}]{status}[/{status_color}]")
        
        table.add_row("Executed Qty", str(res.get("executedQty", "0.0")))
        table.add_row("Original Qty", str(res.get("origQty", "0.0")))
        
        price = res.get("price")
        avg_price = res.get("avgPrice")
        
        table.add_row("Limit Price Set", str(price) if float(price or 0) > 0 else "N/A")
        table.add_row("Average Exec Price", str(avg_price) if float(avg_price or 0) > 0 else "Pending")
        
        if "stopPrice" in res and float(res.get("stopPrice", 0)) > 0:
            table.add_row("Trigger Stop Price", str(res.get("stopPrice")))
            
        console.print(Panel(table, border_style="green", expand=False))
    else:
        print("\n--- Order Response Details ---")
        for k in ["orderId", "status", "symbol", "side", "type", "executedQty", "origQty", "price", "avgPrice", "stopPrice"]:
            if k in res:
                print(f"{k}: {res[k]}")
        print("------------------------------\n")

def main():
    # Load configuration
    load_dotenv()
    
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    base_url = os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com")
    recv_window = int(os.getenv("BINANCE_RECV_WINDOW", "5000"))

    # Argument Parser
    parser = argparse.ArgumentParser(description="Binance Futures Testnet Trading Bot (USDT-M)")
    parser.add_argument("--symbol", help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", choices=["BUY", "SELL", "buy", "sell"], help="Order side: BUY or SELL")
    parser.add_argument("--type", choices=["MARKET", "LIMIT", "STOP", "market", "limit", "stop"], help="Order type: MARKET, LIMIT, or STOP (Stop-Limit)")
    parser.add_argument("--quantity", help="Order quantity (e.g. 0.001)")
    parser.add_argument("--price", help="Limit execution price (required for LIMIT and STOP)")
    parser.add_argument("--stop-price", help="Trigger price (required for STOP)")
    parser.add_argument("-i", "--interactive", action="store_true", help="Force interactive prompt mode")
    
    args = parser.parse_args()

    # Determine if we run in interactive mode:
    # If explicitly passed -i OR if no key arguments are provided, use interactive mode
    is_interactive = args.interactive or not (args.symbol or args.side or args.type or args.quantity)

    try:
        if is_interactive:
            inputs = run_interactive()
        else:
            # Parse and validate CLI args
            raw_inputs = {
                "symbol": args.symbol,
                "side": args.side,
                "type": args.type,
                "quantity": args.quantity,
                "price": args.price,
                "stop_price": args.stop_price
            }
            # Clean and validate using validators
            inputs = validate_inputs(
                symbol=raw_inputs["symbol"],
                side=raw_inputs["side"],
                order_type=raw_inputs["type"],
                quantity=raw_inputs["quantity"],
                price=raw_inputs["price"],
                stop_price=raw_inputs["stop_price"]
            )
            
        # Display the parsed details before sending
        display_summary(inputs)
        
        # Confirm before placing order in interactive mode
        if is_interactive and CONSOLE_AVAILABLE:
            confirm = Confirm.ask("Do you want to send this order to Binance Futures Testnet?", default=True)
            if not confirm:
                console.print("[yellow]Order aborted by user.[/yellow]")
                sys.exit(0)

        # Check API key presence before connecting
        if not api_key or not api_secret:
            raise BinanceClientError(
                "Missing Binance API Credentials.\n"
                "Please configure BINANCE_API_KEY and BINANCE_API_SECRET in your .env file."
            )

        # Initialize Client
        if CONSOLE_AVAILABLE:
            with console.status("[bold green]Connecting to Binance Futures Testnet..."):
                client = BinanceFuturesClient(api_key, api_secret, base_url, recv_window)
        else:
            print("Connecting to Binance Futures Testnet...")
            client = BinanceFuturesClient(api_key, api_secret, base_url, recv_window)

        # Place Order
        if CONSOLE_AVAILABLE:
            with console.status("[bold green]Sending order request..."):
                res = place_order(
                    client=client,
                    symbol=inputs["symbol"],
                    side=inputs["side"],
                    order_type=inputs["type"],
                    quantity=inputs["quantity"],
                    price=inputs["price"],
                    stop_price=inputs["stop_price"]
                )
        else:
            print("Sending order request...")
            res = place_order(
                client=client,
                symbol=inputs["symbol"],
                side=inputs["side"],
                order_type=inputs["type"],
                quantity=inputs["quantity"],
                price=inputs["price"],
                stop_price=inputs["stop_price"]
            )

        # Display Response
        print_success("Order placed successfully!")
        display_response(res)

    except ValidationError as e:
        print_error(f"Input Validation Failure: {e}")
        sys.exit(1)
    except BinanceAPIError as e:
        print_error(f"Binance API Execution Failure: {e}")
        sys.exit(2)
    except BinanceNetworkError as e:
        print_error(f"Network Failure: {e}")
        sys.exit(3)
    except BinanceClientError as e:
        print_error(f"Client Initialization Failure: {e}")
        sys.exit(4)
    except KeyboardInterrupt:
        if CONSOLE_AVAILABLE:
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        else:
            print("\nOperation cancelled by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
