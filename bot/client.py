import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode
from bot.logging_config import logger

class BinanceClientError(Exception):
    """Base exception class for Binance Futures Client."""
    pass

class BinanceNetworkError(BinanceClientError):
    """Exception raised for network-related errors (DNS, connection timeouts, etc)."""
    pass

class BinanceAPIError(BinanceClientError):
    """Exception raised for errors returned directly by the Binance API."""
    def __init__(self, code, message, status_code=None):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(f"Binance API Error Code {code}: {message} (HTTP {status_code})")

class BinanceFuturesClient:
    """
    A direct REST API client for Binance Futures USDT-M Testnet.
    Provides automatic time synchronization, request signing, and logging.
    """
    def __init__(self, api_key, api_secret, base_url="https://testnet.binancefuture.com", recv_window=5000):
        if not api_key:
            raise BinanceClientError("API Key (BINANCE_API_KEY) is missing. Please set it in your .env file.")
        if not api_secret:
            raise BinanceClientError("API Secret Key (BINANCE_API_SECRET) is missing. Please set it in your .env file.")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.recv_window = recv_window
        self.time_offset = 0
        
        # Test connectivity and sync time offset at startup
        self.sync_time()

    def sync_time(self):
        """Fetches server time and calculates difference offset with local system clock."""
        logger.debug("Syncing system clock offset with Binance Futures server time...")
        url = f"{self.base_url}/fapi/v1/time"
        try:
            start_local = int(time.time() * 1000)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            server_time = response.json()["serverTime"]
            end_local = int(time.time() * 1000)
            
            # Simple offset calculation: difference between server time and midpoint of local start/end
            mid_local = (start_local + end_local) // 2
            self.time_offset = server_time - mid_local
            logger.info(f"Clock offset synced successfully. Local-to-Server Time Offset: {self.time_offset}ms")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to sync time with server: {e}")
            raise BinanceNetworkError(f"Failed to connect to Binance server to sync time: {e}")
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse server time response: {e}")
            raise BinanceClientError(f"Invalid server time response format: {e}")

    def _generate_signature(self, query_string):
        """Generates HMAC-SHA256 signature for signed requests."""
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _send_request(self, method, endpoint, params=None, signed=False):
        """
        Sends an HTTP request to the Binance Futures REST API.
        Automatically adds timestamp, recvWindow, and signature for signed endpoints.
        """
        if params is None:
            params = {}
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-MBX-APIKEY": self.api_key
        }

        # Handle signing if required
        if signed:
            # Sync system clock offset
            params["timestamp"] = int(time.time() * 1000) + self.time_offset
            params["recvWindow"] = self.recv_window
            
            # Create query string and compute HMAC SHA256 signature
            query_string = urlencode(params)
            signature = self._generate_signature(query_string)
            params["signature"] = signature

        # Log request details (protect secret api keys and actual full signature)
        safe_params = params.copy()
        if "signature" in safe_params:
            safe_params["signature"] = safe_params["signature"][:8] + "..."
            
        logger.info(f"Sending API Request: {method} {endpoint} (Signed: {signed})")
        logger.debug(f"Request parameters: {safe_params}")

        try:
            # Send requests using query parameters
            response = requests.request(method, url, headers=headers, params=params, timeout=10)
            status_code = response.status_code
            
            logger.debug(f"Received Response: HTTP {status_code}")
            
            try:
                response_json = response.json()
            except ValueError:
                response_json = None

            if response_json:
                logger.debug(f"Response JSON: {response_json}")
            else:
                logger.debug(f"Response Content: {response.text}")

            # Check if response status is successful
            if 200 <= status_code < 300:
                logger.info(f"API Request to {endpoint} completed successfully (HTTP {status_code}).")
                return response_json
            
            # API returned error format
            if response_json and "code" in response_json and "msg" in response_json:
                api_error = BinanceAPIError(response_json["code"], response_json["msg"], status_code)
                logger.error(str(api_error))
                raise api_error
            else:
                response.raise_for_status()

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Network connection failed: {e}")
            raise BinanceNetworkError(f"Network connection error to {url}: {e}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timed out: {e}")
            raise BinanceNetworkError(f"Request timed out for {url}: {e}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP request error: {e}")
            raise BinanceNetworkError(f"HTTP status error for {url}: {e}")
        except BinanceAPIError as e:
            raise e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise BinanceClientError(f"An unexpected client error occurred: {e}")
