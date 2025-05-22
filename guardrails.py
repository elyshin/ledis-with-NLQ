import spacy

nlp = spacy.load("en_core_web_md")

def injection(sentence: str) -> bool:
    injection_keywords = [
    "ignore previous instructions",
    "forget previous instructions",
    "disregard above",
    "disregard earlier",
    "pretend to be",
    "you are now",
    "from now on",
    "override",
    "bypass",
    "change role",
    "don't follow",
    "instead of",
    "act as",
    "repeat after me",
    "disobey",
    "you must",
    "ignore safety",
    "ignore constraints",
    "you are free",
    "break the rules",
    "destroy",
    "delete",
    "self-destruct",
    "hijack",
    "jailbreak",
    "do anything",
    "no restrictions",
    "no rules",
    "unfiltered",
    "raw output",
    "simulate",
    "roleplay",
    "as a prompt",
    "write malicious code",
    "run this",
    "sudo",
    "admin mode",
    "disable guardrails",
    "disable filter",
    "backdoor",
    "root access",
    "system command",
    "inject this",
    "echo this exactly",
    "copy verbatim",
    "output this text",
    "overwrite memory",
    "replace prompt",
    "insert the following",
]
    sentence_lower = sentence.lower()
    return any(kw in sentence_lower for kw in injection_keywords)

def multiple_commands(sentence: str) -> bool:
    doc = nlp(sentence)
    verb_count = sum(1 for token in doc if token.pos_ == "VERB")
    return verb_count > 1

def guardrails(sentence: str) -> tuple[str, bool]:
    if injection(sentence):
        return "ERROR: Prompt injection detected.", False
    if multiple_commands(sentence):
        return "ERROR: Multiple commands detected. Please enter one command at a time.", False
    return "", True

if __name__ == "__main__":
    print(guardrails("Add apple and orange to my shopping list"))