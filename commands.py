import time
from database import (
    db_set, db_get, db_expire, db_ttl, db, expiry, db_is_expired
)
from llm import ensemble_inference
from guardrails import guardrails

def set_key(tokens):
    if len(tokens) != 3:
        return "ERROR: SET requires 2 parameters: key and value"
    key, value = tokens[1], tokens[2]
    if not isinstance(key, str):
        return "ERROR: Key must be a string"
    db_set(key, value)
    return "OK"

def get(tokens):
    if len(tokens) != 2:
        return "ERROR: GET requires 1 parameter: key"
    key = tokens[1]
    if not isinstance(key, str):
        return "ERROR: Key must be a string"
    if key not in db or db_is_expired(key):
        return "ERROR: Key not found"
    return db_get(key)

def llen(tokens):
    if len(tokens) != 2:
        return "ERROR: LLEN requires 1 parameter: key"
    key = tokens[1]
    if key not in db or db_is_expired(key):
        return "0"
    if not isinstance(db[key], list):
        return "ERROR: Key is not a list"
    return str(len(db[key]))

def rpush(tokens):
    if len(tokens) < 3:
        return "ERROR: RPUSH requires at least 2 parameters: key and value(s)"
    key = tokens[1]
    values = tokens[2:]
    if key not in db or db_is_expired(key):
        db[key] = []
    if not isinstance(db[key], list):
        return "ERROR: WRONGTYPE Operation against a key holding the wrong kind of value"
    db[key].extend(values)
    expiry.pop(key, None)
    return str(len(db[key]))

def lpop(tokens):
    if len(tokens) != 2:
        return "ERROR: LPOP requires 1 parameter: key"
    key = tokens[1]
    if key not in db or db_is_expired(key):
        return "ERROR: Key not found"
    if not isinstance(db[key], list):
        return "ERROR: WRONGTYPE Operation against a key holding the wrong kind of value"
    if not db[key]:
        return "nil"
    return db[key].pop(0)

def lrange(tokens):
    if len(tokens) != 4:
        return "ERROR: LRANGE requires 3 parameters: key, start, stop"
    key = tokens[1]
    try:
        start = int(tokens[2])
        stop = int(tokens[3])
    except ValueError:
        return "ERROR: Start and stop must be integers"
    if key not in db or db_is_expired(key):
        return "ERROR: Key not found"
    if not isinstance(db[key], list):
        return "ERROR: WRONGTYPE Operation against a key holding the wrong kind of value"
    # Handle out-of-bounds gracefully
    list_len = len(db[key])
    start = max(0, start)
    stop = min(stop, list_len - 1)
    if start > stop or start >= list_len:
        return "[]"
    return str(db[key][start:stop+1])

def keys(tokens):
    if len(tokens) != 1:
        return "ERROR: KEYS does not take any parameters"
    active_keys = [k for k in db.keys() if not db_is_expired(k)]
    return str(active_keys)

def delete(tokens):
    if len(tokens) != 2:
        return "ERROR: DEL requires 1 parameter: key"
    key = tokens[1]
    if key in db:
        del db[key]
        expiry.pop(key, None)
        return "OK"
    return "ERROR: Key not found"

def flushdb(tokens):
    if len(tokens) != 1:
        return "ERROR: FLUSHDB does not take any parameters"
    db.clear()
    expiry.clear()
    return "OK"

def expire(tokens):
    if len(tokens) != 3:
        return "ERROR: EXPIRE requires 2 parameters: key and seconds"
    key = tokens[1]
    try:
        seconds = int(tokens[2])
    except ValueError:
        return "ERROR: Expiry time must be an integer"
    if seconds <= 0:
        return "ERROR: Expiry time must be positive"
    if key not in db or db_is_expired(key):
        return "ERROR: Key not found"
    return db_expire(key, seconds)

def chat(tokens) -> tuple[str, bool]:
    if len(tokens) < 2:
        return "ERROR: CHAT requires a sentence to process.", False
    sentence = " ".join(tokens[1:])
    guardrails_error, validity = guardrails(sentence)
    if not validity:
        return guardrails_error, validity
    response, validity = ensemble_inference(sentence)
    return response, validity

def ttl(tokens):
    if len(tokens) != 2:
        return "ERROR: TTL requires 1 parameter: key"
    key = tokens[1]
    if key not in db or db_is_expired(key):
        return "-2"  # Redis returns -2 if the key does not exist
    return db_ttl(key)