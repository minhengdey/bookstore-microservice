import httpx
import time
import logging
import hmac
import hashlib
import os
import json
import redis
from .middleware import get_request_id

logger = logging.getLogger(__name__)

class CircuitState:
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

redis_host = os.environ.get("REDIS_HOST", "redis")
redis_port = int(os.environ.get("REDIS_PORT", 6379))
try:
    cb_redis = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True)
except Exception:
    cb_redis = None

class InternalClient:
    def __init__(self, timeout=2.0, max_retries=2):
        self.timeout = timeout
        self.max_retries = max_retries
        self.service_name = os.environ.get("SERVICE_NAME", "unknown_service")
        self.internal_token = os.environ.get("INTERNAL_TOKEN", "internal-dev-token")
        self.signing_secret = os.environ.get("INTERNAL_SIGNING_SECRET", "internal-signing-secret")
        
        # Circuit Breaker thresholds
        self.fail_threshold = 3
        self.reset_timeout = 15

    def _generate_signature(self, timestamp: str, body: str) -> str:
        return hmac.new(
            self.signing_secret.encode("utf-8"),
            f"{timestamp}.{body}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _get_headers(self, request_body: str = "") -> dict:
        request_id = get_request_id() or "unknown-req-id"
        timestamp = str(int(time.time()))
        signature = self._generate_signature(timestamp, request_body)
        return {
            "X-Request-ID": request_id,
            "X-Trace-ID": request_id, # Distributed tracing alias
            "X-Service-Name": self.service_name,
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "X-Internal-Token": self.internal_token,
            "Content-Type": "application/json"
        }

    def _get_host(self, url: str) -> str:
        from urllib.parse import urlparse
        return urlparse(url).netloc

    def _check_circuit(self, host: str):
        if not cb_redis:
            return {"status": CircuitState.CLOSED, "failures": 0, "last_failure_time": 0}
            
        key = f"circuit:{host}"
        data = cb_redis.get(key)
        if data:
            state = json.loads(data)
        else:
            state = {"status": CircuitState.CLOSED, "failures": 0, "last_failure_time": 0}
            
        if state["status"] == CircuitState.OPEN:
            if time.time() - state["last_failure_time"] > self.reset_timeout:
                state["status"] = CircuitState.HALF_OPEN
                cb_redis.set(key, json.dumps(state), ex=60)
            else:
                raise Exception(f"Circuit Breaker OPEN for host {host}")
        return state

    def _save_circuit(self, host: str, state: dict):
        if cb_redis:
            cb_redis.set(f"circuit:{host}", json.dumps(state), ex=3600)

    def _record_success(self, host: str, state: dict):
        if state.get("status") != CircuitState.CLOSED or state.get("failures", 0) > 0:
            state["status"] = CircuitState.CLOSED
            state["failures"] = 0
            self._save_circuit(host, state)

    def _record_failure(self, host: str, state: dict):
        state["failures"] = state.get("failures", 0) + 1
        state["last_failure_time"] = time.time()
        if state["status"] == CircuitState.HALF_OPEN or state["failures"] >= self.fail_threshold:
            state["status"] = CircuitState.OPEN
        self._save_circuit(host, state)

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        host = self._get_host(url)
        cb_state = self._check_circuit(host)
        
        request_body = ""
        if "json" in kwargs:
            import json
            request_body = json.dumps(kwargs["json"], separators=(",", ":"), sort_keys=True)
            kwargs["data"] = request_body
            kwargs.pop("json", None)
        elif "content" in kwargs:
            request_body = kwargs["content"] if isinstance(kwargs["content"], str) else kwargs["content"].decode()

        headers = kwargs.pop("headers", {})
        headers.update(self._get_headers(request_body))
        
        attempt = 0
        backoff = 0.5
        
        with httpx.Client(timeout=self.timeout) as client:
            while attempt <= self.max_retries:
                start_time = time.time()
                try:
                    response = client.request(method, url, headers=headers, **kwargs)
                    latency = int((time.time() - start_time) * 1000)
                    
                    log_extra = {
                        "target_service": host,
                        "endpoint": url,
                        "status_code": response.status_code,
                        "latency_ms": latency,
                        "span": f"{self.service_name}->{host}"
                    }
                    logger.info(f"InternalClient: {method} {url}", extra=log_extra)
                    
                    if 500 <= response.status_code < 600:
                        raise httpx.HTTPStatusError(
                            f"Server error {response.status_code}", 
                            request=response.request, 
                            response=response
                        )
                        
                    self._record_success(host, cb_state)
                    return response
                    
                except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as e:
                    self._record_failure(host, cb_state)
                    attempt += 1
                    
                    if attempt > self.max_retries:
                        logger.error(f"InternalClient: {method} {url} failed after {self.max_retries} retries", extra={"target_service": host, "reason": str(e), "span": f"{self.service_name}->{host}"})
                        raise e
                        
                    logger.warning(f"InternalClient: {method} {url} failed ({str(e)}), retrying in {backoff}s...", extra={"target_service": host, "span": f"{self.service_name}->{host}"})
                    time.sleep(backoff)
                    backoff *= 2

    def get(self, url: str, **kwargs) -> httpx.Response: return self.request("GET", url, **kwargs)
    def post(self, url: str, **kwargs) -> httpx.Response: return self.request("POST", url, **kwargs)
    def put(self, url: str, **kwargs) -> httpx.Response: return self.request("PUT", url, **kwargs)
    def delete(self, url: str, **kwargs) -> httpx.Response: return self.request("DELETE", url, **kwargs)
