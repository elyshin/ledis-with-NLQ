import time

db = {}
expiry = {}

def db_is_expired(key):
    return key in expiry and time.time() > expiry[key]

def db_rm_expired(key):
    if key in db:
        del db[key]
    if key in expiry:
        del expiry[key]

def db_set(key, value):
    db[key] = value
    expiry.pop(key, None)
    return "OK"

def db_get(key):
    if key not in db or db_is_expired(key):
        if db_is_expired(key):
            db_rm_expired(key)
        return "ERROR: Key not found"
    return db[key]

def db_expire(key, seconds):
    if key not in db:
        return "0"
    expiry[key] = time.time() + seconds
    return "1"

def db_ttl(key):
    if key not in db:
        return "ERROR: Key not found"
    if key not in expiry:
        return "-1"
    ttl = int(expiry[key] - time.time())
    if ttl < 0:
        db_rm_expired(key)
        return "ERROR: Key not found"
    return str(ttl)
