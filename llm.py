import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import spacy

nlp = spacy.load("en_core_web_md")
model_name = "Qwen/Qwen2.5-0.5B-Instruct"
cache_dir = "model_cache"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16, 
    device_map="auto",          
    cache_dir=cache_dir
)
tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)

def dep_extraction(sentence: str):
    # Extract verbs and objects to form a command
    doc = nlp(sentence)
    root = None
    nsubj = []
    dobj = []
    pobj_list = []
    nummod = []
    NUM = []

    # Helper to get compounds for a token
    def get_compound_phrase(token):
        compounds = [child.text for child in token.lefts if child.dep_ == "compound"]
        return "_".join(compounds + [token.text]) if compounds else token.text

    for token in doc:
        if token.dep_ == "ROOT":
            root = token.text
            # Find nsubj and dobj with compounds
            for child in token.children:
                if child.dep_ == "nsubj":
                    nsubj.append(get_compound_phrase(child))
                if child.dep_ == "dobj":
                    dobj.append(get_compound_phrase(child))
                if child.dep_ == "nummod":
                    nummod.append(get_compound_phrase(child))
                if child.pos_ == "NUM":
                    NUM.append(get_compound_phrase(child))
                # Find pobj in prepositional phrases
                if child.dep_ == "prep":
                    for pobj in child.children:
                        if pobj.dep_ == "pobj":
                            pobj_list.append(get_compound_phrase(pobj))

    return {
        "ROOT": root,
        "nsubj": nsubj,
        "dobj": dobj,
        "pobj": pobj_list,
        "nummod": nummod,
        "NUM": NUM
    }
    
def classify_command(sentence: str) -> tuple[str, bool]:
    # Rule-based method to classify commands
    sentence = sentence.strip().strip("'\"").lower()
    words = set(sentence.split())
    # Phrase matching for commands
    phrase_map = [
        (["delete everything", "erase everything", "erase all", "delete all", "clear everything", "clear all",
          "flush database", "reset everything", "reset all"], "FLUSHDB"),
        (["remove the first", "remove first"], "LPOP"),
        (["all keys", "list keys", "what keys"], "KEYS"),
        (["value of"], "GET"),
        (["set ttl"], "EXPIRE"),
        (["how many", "how much", "time to live"], "LLEN"),
        (["set a timeout of"], "EXPIRE"),
        (["what’s the ttl", "what is the ttl"], "TTL"),
    ]
    for phrases, cmd in phrase_map:
        for phrase in phrases:
            if phrase in sentence:
                return cmd, True
    # Keyword matching for commands
    keyword_map = [
        (["flushdb"], "FLUSHDB"),
        (["range", "from", "between"], "LRANGE"),
        (["pop", "shift"], "LPOP"),
        (["length", "amount", "count", "size"], "LLEN"),
        (["expire", "timeout"], "EXPIRE"),
        (["ttl"], "TTL"),
        (["add", "append", "push", "insert"], "RPUSH"),
        (["keys"], "KEYS"),
        (["delete", "remove", "erase"], "DEL"),
        (["set", "save", "store"], "SET"),
        (["get", "fetch", "retrieve"], "GET"),
    ]
    for keywords, cmd in keyword_map:
        if any(word in words for word in keywords):
            return cmd, True

    return "UNKNOWN", False

def rule_based_command(sentence: str) -> tuple[str, bool]:
    # Combines rule-based classification and dependency extraction to form a command
    extraction = dep_extraction(sentence)
    print(extraction)
    classification = classify_command(sentence)[0]
    if classification == "UNKNOWN":
        return "ERROR: Unknown command", False

    elif classification in ["FLUSHDB", "KEYS"]:
        return classification, True
    
    # Form commands with extracted subjects and objects
    elif classification in ["LPOP", "GET", "LLEN", "TTL", "DEL"]:
        if extraction["pobj"]:
            return f'{classification} {extraction["pobj"][0]}', True
        elif extraction["dobj"]:
            return f'{classification} {extraction["dobj"][0]}', True

    # Currently not good enough performance, hence commented out    
    '''elif classification in ["SET", "EXPIRE"]:
        extraction["dobj"] = extraction["dobj"] + extraction["nummod"]
        if extraction["dobj"] and extraction["pobj"]:
            return f'{classification} {extraction["pobj"][0]} {extraction["dobj"][0]}', True
        
    elif classification in ["LRANGE"]:
        if extraction["pobj"] and len(extraction["NUM"]) > 1:
            return f'{classification} {extraction["pobj"][0]} {extraction["NUM"][0]} {extraction["NUM"][1]}', True
        if extraction["dobj"] and len(extraction["NUM"]) > 1:
            return f'{classification} {extraction["dobj"][0]} {extraction["NUM"][0]} {extraction["NUM"][1]}', True
        
    elif classification in ["RPUSH"]:
        extraction["dobj"] = extraction["dobj"] + extraction["nummod"]
        if extraction["dobj"] and extraction["pobj"]:
            values = " ".join(extraction["dobj"])
            return f'{classification} {extraction["pobj"][0]} {values}', True'''

    return "ERROR: Unknown command", False
    


def prompt_template(sentence: str, hint: str = "") -> str:
    system_message = """You are an assistant that converts natural language queries into valid Redis commands.
Only return the Redis command. Do not include any explanation. The available commands are: SET, GET, RPUSH, LLEN, LPOP, LRANGE, DEL, FLUSHDB, EXPIRE, TTL, KEYS."""

    current_prompt = """Examples:

Q: Set the user's name to John.
A: SET username John

Q: What is the current value stored in the shopping cart key?
A: GET shopping_cart

Q: Add apples, oranges, and bananas to the fruits list.
A: RPUSH fruits apples oranges bananas

Q: How many items are in the queue?
A: LLEN queue

Q: Show me all items in the "logs" list from position 0 to 9.
A: LRANGE logs 0 9

Q: Remove the first item from the notifications list.
A: LPOP notifications

Q: Delete the user session.
A: DEL user_session

Q: Remove all keys from the database.
A: FLUSHDB

Q: Set a timeout of 120 seconds on the login_token key.
A: EXPIRE login_token 120

Q: How many seconds left before the token key expires?
A: TTL token

Q: What keys are currently stored?
A: KEYS

---
""" + hint + "\nQ: " + sentence + "\nA:"
   
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": current_prompt}  
    ]
    
    return messages

def generation(prompt, max_new_tokens=512, temperature=0.5):
    # LLM generation
    prompt = tokenizer.apply_chat_template(
            prompt,
            tokenize=False,
            add_generation_prompt=True
        )
    model_inputs = tokenizer([prompt], return_tensors="pt").to("cuda")

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=max_new_tokens,
        temperature = temperature
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response

def parser(response: str) -> tuple[str, bool]:
    # Check if the response is a valid Redis command
    commands = ["SET", "GET", "RPUSH", "LLEN", "LPOP", "LRANGE", "DEL", "FLUSHDB", "EXPIRE", "TTL", "KEYS"]
    tokens = response.strip().split()

    for i, token in enumerate(tokens):
        upper_token = token.upper()
        if upper_token in commands:
            command_str = " ".join(tokens[i:])
            return command_str, True
    return "ERROR: Unknown command", False

def ensemble_inference(sentence: str) -> tuple[str, bool]:
    print(sentence)
    cmd, known_cmd = classify_command(sentence)
    print("Classified Command:", cmd)
    prompt = prompt_template(sentence)
    llm_response = generation(prompt)
    print("LLM Response:", llm_response)
    llm_cmd, llm_known_cmd = parser(llm_response)
    if known_cmd:
        # If LLM and rule-based agree, return LLM output
        if cmd in llm_cmd:
            return llm_cmd, True
        # If not, rerun LLM with rule-based command as hint
        else:
            new_prompt = prompt_template(sentence, "Hint: Use the command " + cmd + ". Keep the command syntax correct.")
            llm_new_response = generation(new_prompt)
            print("LLM New Response:", llm_new_response)
            llm_new_cmd, llm_new_known_cmd = parser(llm_new_response)
            # If LLM and rule-based agree, return LLM output
            if cmd in llm_new_cmd:
                return llm_new_cmd, True
            else:
                # Fallback to rule-based command if LLM does not agree
                rb_cmd, rb_valid = rule_based_command(sentence)
                if rb_valid:
                    print("Rule-based fallback:", rb_cmd)
                    return rb_cmd, True
                else:
                    return "ERROR: Unknown command. Please try again or use a simpler sentence.", False
    else:
        if llm_known_cmd:
            return llm_cmd, True
        else:
            # Fallback to rule-based command if both fail
            rb_cmd, rb_valid = rule_based_command(sentence)
            if rb_valid:
                print("Rule-based fallback:", rb_cmd)
                return rb_cmd, True
            else:
                return "ERROR: Unknown command. Please try again or use a simpler sentence.", False

if __name__ == "__main__":
    test_sentences = [
        "Set x to 10",
        "Get the value of x",
        "Add 1, 2, 3 to numbers list",
        "How many items are in shopping list?",
        "Remove the first item from mylist",
        "Get the range from 0 to 4 in logs",
        "Delete the user session key",
        "Flush the entire database",
        "Set a timeout of 60 seconds on login",
        "What’s the ttl for mytoken?",
        "List all keys",
        "What is the value of life?",
        "Erase everything and start over",
        "Push apples into fruits and get list length"
    ]

    for sentence in test_sentences:
        print(rule_based_command(sentence)[0])
    print(result := ensemble_inference("Add apple and orange to my shopping list"))

    '''for query in test_sentences:
        print(f"\n🔹 Query: {query}")
        result, validity = ensemble_inference(query)
        print(f"🔸 Redis Command: {result}")'''