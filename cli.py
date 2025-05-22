import readline
import requests

def send_command(command):
    url = "http://localhost:8000/"
    try:
        response = requests.post(url, data=command)
        print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set editing-mode vi")

    while True:
        line = input("> ")
        if line.strip().lower() in ("exit", "quit"):
            break
        if line.strip() == "":
            continue
        send_command(line.strip())


