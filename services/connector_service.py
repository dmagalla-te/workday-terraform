import httpx
import time
import asyncio
from datetime import datetime
from services.logging_service import setup_api_calls_logger
from config.configuration import config

# Configurar el logger para las llamadas de API
logging = setup_api_calls_logger()


limits = httpx.Limits(max_keepalive_connections=100, max_connections=150, keepalive_expiry=50)
timeout = httpx.Timeout(27.7, read=None, pool=7.7)


##############NO Async###################################
class ConnectorSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        
        if cls._instance is None:
            
            limits = httpx.Limits(max_keepalive_connections=300, max_connections=1000, keepalive_expiry=100)
            timeout = httpx.Timeout(17.7, read=None, pool=7.7)
            cls._instance = httpx.Client(limits=limits, timeout=timeout)
        
        return cls._instance


super_http = ConnectorSingleton.get_instance()

def log_request(endpoint, status_code, roundtrip):

    """Log the request details including the time taken and status code."""
    
    logging.info(f"Status Code {status_code}: {endpoint} time: {roundtrip:.4f} seconds")


def handle_api_errors(response, endpoint):
    """Handle specific API error responses."""
    
    if response.status_code in {400, 401, 403, 404, 405}:
        
        error_message = f"Error {response.status_code} for {endpoint}: {response.text}"
        logging.error(error_message)
        
        return response.status_code, response.json(), True
    
    return None, None, False


def request_with_retry(method, url, **kwargs):

    """Generic request function with retry for rate limiting, timing, extra sleep time, and error handling."""
    start = time.time()
    response = super_http.request(method, url, **kwargs)
    roundtrip = time.time() - start

        # New rule: Check rate limit remaining and sleep if needed
    rate_limit_remaining = int(response.headers.get('x-organization-rate-limit-remaining', 240))
    reset_time =  (datetime.fromtimestamp(int(response.headers.get('x-organization-rate-limit-reset', 0))) - datetime.now()).total_seconds()
    
    if rate_limit_remaining <= 11 and reset_time >= 17:
        
        log_request(url, response.status_code, 5)  # Log this event
        time.sleep(5)  # Sleep for 7 seconds to relieve the API

    if response.status_code == 429:
        
        reset_timestamp = int(response.headers.get('x-organization-rate-limit-reset', 0))
        sleep_time = (datetime.fromtimestamp(reset_timestamp) - datetime.now()).total_seconds() + 1
        time.sleep(max(0, sleep_time))
        retry_start = time.time()
        response = super_http.request(method, url, **kwargs)
        roundtrip = time.time() - retry_start
    
    log_request(url, response.status_code, roundtrip)
    
    # Handle specific error codes
    status_code, error_response, has_error = handle_api_errors(response, url)
    
    if has_error:

        return status_code, error_response
    
    return response.status_code, response.json()


def get_data(headers, endp_url, params):
    
    status_code, response = request_with_retry('GET', endp_url, headers=headers, params=params)
    
    if isinstance(response, dict) or status_code in {200, 201}:
    
        return status_code, response
    
    else:
        # Handle non-JSON responses or unexpected outcomes
    
        return status_code, {"error": f"{response.text}"}


def post_data(headers, endp_url, payload):
    
    status_code, response = request_with_retry('POST', endp_url, headers=headers, data=payload)
    
    if isinstance(response, dict) or status_code in {200, 201}:
    
        return status_code, response
    
    else:
    
        # Handle non-JSON responses or unexpected outcomes
        return status_code, {"error": f"{response.text}"}



# ASYNC for Asyncio and not Asyncio corrutines.

#Async client not within multiple stupid corrutines
a_client = httpx.AsyncClient(limits=limits, timeout=timeout)
# Initialize the local logger
local_logger = setup_api_calls_logger()

async def a_log_request(endpoint, status_code, roundtrip):

    """Log the request details including the time taken and status code."""
    message = f"Status Code {status_code}: {endpoint} time: {roundtrip:.5f} seconds"
    loop = asyncio.get_running_loop()

    await loop.run_in_executor(None, local_logger.info, message)


async def a_handle_api_errors(response, endpoint):

    """Handle specific API error responses."""
    if response.status_code in {400, 401, 403, 404, 405}:

        error_message = f"Error {response.status_code} for {endpoint}: {response.text}"
        logging.error(error_message)
        
        return response.status_code, response.json(), True
    
    return None, None, False


async def a_request_with_retry(client, method, url, **kwargs):

    start = datetime.now()
    response = await client.request(method, url, **kwargs)
    roundtrip = (datetime.now() - start).total_seconds()

    rate_limit_remaining = int(response.headers.get('x-organization-rate-limit-remaining', 240))
    reset_time = (datetime.fromtimestamp(int(response.headers.get('x-organization-rate-limit-reset', 0))) - datetime.now()).total_seconds()
    
    if rate_limit_remaining <= 11 and reset_time >= 17:

        await a_log_request(url, response.status_code, 7)
        await asyncio.sleep(7)
    
    if response.status_code == 429:

        reset_timestamp = int(response.headers.get('x-organization-rate-limit-reset', 0))
        sleep_time = (datetime.fromtimestamp(reset_timestamp) - datetime.now()).total_seconds() + 1

        await a_log_request(url, response.status_code, sleep_time)
        await asyncio.sleep(max(0, sleep_time))
        
        retry_start = datetime.now()
        response = await client.request(method, url, **kwargs)
        roundtrip = (datetime.now() - retry_start).total_seconds()
    
    await a_log_request(url, response.status_code, roundtrip)
    
    status_code, error_response, has_error = await a_handle_api_errors(response, url)

    if has_error:

        return status_code, error_response
    
    return response.status_code, response.json()



async def aa_request_with_retry(method, url, **kwargs):
   
    """Generic request function with retry for rate limiting, timing, extra sleep time, and error handling."""
    start = datetime.now()
    response = await a_client.request(method, url, **kwargs)
    roundtrip = (datetime.now() - start).total_seconds()
    
    # New rule: Check rate limit remaining and sleep if needed
    rate_limit_remaining = int(response.headers.get('x-organization-rate-limit-remaining', 240))
    reset_time =  (datetime.fromtimestamp(int(response.headers.get('x-organization-rate-limit-reset', 5))) - datetime.now()).total_seconds()
    
    if rate_limit_remaining <= 25 and reset_time >= 10:
        
        await a_log_request(url, response.status_code, 5)  # Log this event
        await asyncio.sleep(5)  # Sleep for 7 seconds to relieve the API
    
    
    if response.status_code == 429:

        reset_timestamp = int(response.headers.get('x-organization-rate-limit-reset', 0))
        sleep_time = (datetime.fromtimestamp(reset_timestamp) - datetime.now()).total_seconds() + 1
        
        await a_log_request(url, response.status_code, sleep_time)
        await asyncio.sleep(max(0, sleep_time))
        
        retry_start = datetime.now()
        response = await a_client.request(method, url, **kwargs)
        roundtrip = (datetime.now() - retry_start).total_seconds()
    
    
    await a_log_request(url, response.status_code, roundtrip)
    
    # Handle specific error codes
    status_code, error_response, has_error = await a_handle_api_errors(response, url)
    
    if has_error:
        
        return status_code, error_response
    
    return response.status_code, response.json()


# Functions using a_client directly (no client passed)
async def aa_get_data(headers, endp_url, params):

    status_code, response = await aa_request_with_retry('GET', endp_url, headers=headers, params=params)

    if isinstance(response, dict) or status_code in {200, 201}:

        return status_code, response

    else:

        return status_code, {"error": f"{response.text}"}
    

async def aa_post_data(headers, endp_url, payload):
   
    status_code, response = await aa_request_with_retry('POST', endp_url, headers=headers, data=payload)
   
    if isinstance(response, dict) or status_code in {200, 201}:
   
        return status_code, response
   
    else:
   
        return status_code, {"error": response.text}


async def aa_put_data(headers, endp_url, payload):
    
    status_code, response = await aa_request_with_retry('PUT', endp_url, headers=headers, data=payload)
    
    if isinstance(response, dict) or status_code in {200, 201}:
    
        return status_code, response
    
    else:
    
        return status_code, {"error": response.text}



# Functions that require the client to be passed as an argument from the multuple corrutines de miercoles
async def a_get_data(headers, client, endp_url, params):
    
    status_code, response = await a_request_with_retry(client, 'GET', endp_url, headers=headers, params=params)
    
    if isinstance(response, dict) or status_code in {200, 201}:
    
        return status_code, response
    
    else:
    
        return status_code, {"error": response.text}


async def a_post_data(headers, endp_url, payload, client):
    
    status_code, response = await a_request_with_retry(client, 'POST', endp_url, headers=headers, data=payload)
    
    if isinstance(response, dict) or status_code in {200, 201}:
    
        return status_code, response
    
    else:
    
        return status_code, {"error": response.text}



async def a_put_data(headers, endp_url, payload, client):

    status_code, response = await a_request_with_retry(client, 'PUT', endp_url, headers=headers, data=payload)

    if isinstance(response, dict) or status_code in {200, 201}:

        return status_code, response

    else:

        return status_code, {"error": response.text}
