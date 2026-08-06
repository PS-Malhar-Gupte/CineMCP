"""
Manages the conversation state and history across multiple turns.
Provides bounded history tracking to prevent context window explosion.
"""

from typing import List, Dict

class ConversationState:
    def __init__(self, max_turns: int):
        """
        Initialize the conversation state.
        
        Args:
            max_turns: The maximum number of interaction pairs (user + assistant) to retain.
        """
        self.max_turns = max_turns
        self.history: List[Dict[str, str]] = []

    def load(self, history: List[Dict[str, str]]) -> None:
        """
        Replace the current history with previously-stored turns (e.g. from
        a conversation store), applying the same truncation rule as
        add_turn so a long stored history can't bypass max_turns.
        """
        max_messages = self.max_turns * 2
        self.history = list(history)[-max_messages:] if history else []

    def add_turn(self, user_msg: str, assistant_msg: str) -> None:
        """
        Append a completed interaction turn to the history.
        Truncates the history if it exceeds the maximum allowed turns.
        """
        self.history.append({"role": "user", "content": user_msg})
        self.history.append({"role": "assistant", "content": assistant_msg})
        
        max_messages = self.max_turns * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

    def get_history(self) -> List[Dict[str, str]]:
        """
        Retrieve a copy of the current conversation history.
        """
        return list(self.history)
