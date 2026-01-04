import requests

def start_healing(bot_id):
    print("Healing started for:", bot_id)

    # Call AI engine module
    response = requests.post("http://ai-healing-engine:5001/heal", json={"botId": bot_id})
    print("Healing response:", response.json())
