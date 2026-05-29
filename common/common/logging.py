import json
import logging
from datetime import datetime, timezone
import os

SERVICE_NAME = os.environ.get("SERVICE_NAME", "unknown_service")

class JSONFormatter(logging.Formatter):
    def format(self, record):
        from common.middleware import get_request_id
        
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service_name": getattr(record, "service_name", SERVICE_NAME),
            "trace_id": getattr(record, "request_id", get_request_id()),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        # Extract additional metrics from extra={}
        for key in ["latency_ms", "status_code", "target_service", "reason", "order_id", "endpoint", "span"]:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
                
        return json.dumps(log_data)
