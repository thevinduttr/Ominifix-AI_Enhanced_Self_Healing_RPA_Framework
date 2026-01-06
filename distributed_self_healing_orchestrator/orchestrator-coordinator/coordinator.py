import requests

def start_healing(bot_id):
    print("Healing started for:", bot_id)

    # Call AI engine module
    # Use compose service name for DNS resolution inside the network
    response = requests.post("http://ai_healing_engine:5001/heal", json={"botId": bot_id})
    print("Healing response:", response.json())
