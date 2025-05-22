from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse

from commands import (
    set_key, get, llen, rpush, lpop, lrange,
    keys, delete, flushdb, expire, ttl, chat
)

command_map = {
    "SET": set_key,
    "GET": get,
    "LLEN": llen,
    "RPUSH": rpush,
    "LPOP": lpop,
    "LRANGE": lrange,
    "KEYS": keys,
    "DEL": delete,
    "FLUSHDB": flushdb,
    "EXPIRE": expire,
    "TTL": ttl,
    "CHAT": chat
}

app = FastAPI()

@app.post("/", response_class=PlainTextResponse)
async def handle_command(request: Request):
    body_bytes = await request.body()
    command_str = body_bytes.decode("utf-8").strip()

    if not command_str:
        return "ERROR: Empty command."

    tokens = command_str.split()
    cmd = tokens[0].upper()

    handler = command_map.get(cmd)
    
    if not handler:
        return "ERROR: Unknown command."

    if cmd == "CHAT":
        # Processing CHAT command, outputing the LLM response and feeding it back 
        llm_command, validity = handler(tokens)
        if validity == False:
            return llm_command
        else:
            chat_tokens = llm_command.split()
            chat_cmd = chat_tokens[0].upper()
            chat_handler = command_map.get(chat_cmd)
            result = llm_command + "\n" + chat_handler(chat_tokens)
    else:
        # Run the other commands as usual
        try:
            result = handler(tokens)
        except Exception as e:
            result = f"ERROR: {str(e)}"

    return result
