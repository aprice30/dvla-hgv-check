import time
from functools import wraps
from threading import Lock

def rate_limiter(calls_per_second):
    lock = Lock()
    min_interval = 1.0 / calls_per_second

    def decorator(func):
        last_call = [0.0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                elapsed = time.time() - last_call[0]
                wait_time = max(0, min_interval - elapsed)
                time.sleep(wait_time)
                result = func(*args, **kwargs)
                last_call[0] = time.time()
                return result

        return wrapper

    return decorator