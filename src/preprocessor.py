"""preprocessor.py — Data ingestion and text normalization for conversation analysis"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass

# --- types ---
@dataclass
class Message:
    sender: str
    text: str
    ts_unix: int
    role: str
    turn_index: int

# --- constants ---
HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
WHITESPACE_PATTERN = re.compile(r'\s+')

# --- core functions ---
def normalize_text(text: str) -> str:
    """Strip HTML, collapse whitespace, lowercase. Input: str. Output: str."""
    text = HTML_TAG_PATTERN.sub('', text)
    text = WHITESPACE_PATTERN.sub(' ', text)
    return text.strip().lower()

def parse_conversation(raw: List[Dict[str, Any]]) -> List[Message]:
    """Parse raw messages into typed Message objects. Input: list[dict]. Output: list[Message]."""
    messages = []
    if not raw:
        return messages
        
    initiator = raw[0].get("sender", "")
    
    for i, msg in enumerate(raw):
        sender = msg.get("sender", "")
        # Basic ts_unix parsing or fallback (assuming caller provides string or int timestamps)
        raw_ts = msg.get("timestamp", 0)
        try:
            ts_unix = int(raw_ts) if not isinstance(raw_ts, str) else int(float(raw_ts))
        except ValueError:
            ts_unix = 0
            
        role = "initiator" if sender == initiator else "receiver"
        
        messages.append(Message(
            sender=sender,
            text=normalize_text(msg.get("text", "")),
            ts_unix=ts_unix,
            role=role,
            turn_index=i
        ))
        
    return messages

if __name__ == "__main__":
    # smoke test
    raw_data = [
        {"sender": "Alice", "text": "Hello  <br> world! ", "timestamp": "1672531200"},
        {"sender": "Bob", "text": "  Hi there! ", "timestamp": "1672531260"}
    ]
    msgs = parse_conversation(raw_data)
    for m in msgs:
        print(m)
    assert len(msgs) == 2
    assert msgs[0].role == "initiator"
    assert msgs[1].role == "receiver"
    assert msgs[0].text == "hello world!"
    print("Smoke test passed.")
