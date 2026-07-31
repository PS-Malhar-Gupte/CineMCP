"""
Observability module for the agent.

Provides structured logging and tracing capabilities (latency tracking).
Uses contextvars to maintain Request ID across async boundaries without
cluttering function signatures. Designed to easily drop-in OpenTelemetry later.
"""

import time
import json
import uuid
import contextvars
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Global context variable for the current request ID
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="system")
_spans_var: contextvars.ContextVar[list] = contextvars.ContextVar("spans", default=None)

def set_request_id(req_id: Optional[str] = None) -> str:
    """Sets a new request ID in the current context and returns it."""
    if not req_id:
        req_id = str(uuid.uuid4())
    _request_id_var.set(req_id)
    _spans_var.set([])
    return req_id

def get_request_id() -> str:
    """Gets the current request ID."""
    return _request_id_var.get()

def get_spans() -> list:
    """Gets the list of spans recorded for the current request."""
    spans = _spans_var.get(None)
    return spans if spans is not None else []


class MetricsLogger:
    """
    A simple tracing logger that mimics OpenTelemetry's start_as_current_span.
    Logs structured JSON with latency and metadata upon exiting the block.
    """
    
    @staticmethod
    @contextmanager
    def start_span(name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager to track execution time of a block of code.
        """
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000.0
            
            log_entry = {
                "event": "span_ended",
                "request_id": get_request_id(),
                "span_name": name,
                "duration_ms": round(duration_ms, 2)
            }
            if metadata:
                log_entry.update(metadata)
                
            # Store in contextvar
            spans = _spans_var.get(None)
            if spans is not None:
                spans.append(log_entry)
                
            # Log as structured JSON
            print(json.dumps(log_entry))
