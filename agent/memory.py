"""
Memory module for the agent.

Provides abstractions for caching agent responses to facilitate faster
repeated questions and user-specific memory. Supports a local memory
implementation with an extensible design for future Redis support.
"""

from abc import ABC, abstractmethod
from typing import Optional
import json
import os
import hashlib

class MemoryProvider(ABC):
    """
    Abstract base class for memory services.
    
    Any memory implementation (Local, Redis, etc.) must implement
    these methods to store and retrieve data.
    """
    
    @abstractmethod
    def get(self, user_id: str, key: str) -> Optional[str]:
        """Retrieve a cached value for a specific user."""
        pass
        
    @abstractmethod
    def set(self, user_id: str, key: str, value: str) -> None:
        """Store a value for a specific user."""
        pass
        
    def generate_key(self, query: str) -> str:
        """
        Helper method to generate a consistent key for a query.
        Uses SHA-256 to hash the query string.
        """
        # Normalize the query by converting to lowercase and stripping whitespace
        normalized_query = query.strip().lower()
        return hashlib.sha256(normalized_query.encode('utf-8')).hexdigest()


class LocalMemoryService(MemoryProvider):
    """
    Local implementation of MemoryProvider using a Python dictionary.
    Optionally persists to a local JSON file.
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        """
        Initialize the local memory service.
        
        Args:
            persist_path: Optional file path to load/save memory data.
                          If None, memory is entirely ephemeral.
        """
        self.persist_path = persist_path
        self._store: dict[str, dict[str, str]] = {}
        self._load()
        
    def _load(self) -> None:
        if self.persist_path and os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, 'r', encoding='utf-8') as f:
                    self._store = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load local memory from {self.persist_path}: {e}")
                self._store = {}
                
    def _save(self) -> None:
        if self.persist_path:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(os.path.abspath(self.persist_path)), exist_ok=True)
                with open(self.persist_path, 'w', encoding='utf-8') as f:
                    json.dump(self._store, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not save local memory to {self.persist_path}: {e}")

    def get(self, user_id: str, key: str) -> Optional[str]:
        """Retrieve a cached value for a specific user."""
        user_store = self._store.get(user_id, {})
        return user_store.get(key)
        
    def set(self, user_id: str, key: str, value: str) -> None:
        """Store a value for a specific user and optionally save to disk."""
        if user_id not in self._store:
            self._store[user_id] = {}
        self._store[user_id][key] = value
        self._save()
