import requests

payload = {
    'botId': 'ui-bot-77-23',
    'error': 'APIFailure: 500 on /v1/data',
    'dom': '<div id="username">...</div>',
    'last_action': 'type(username)',
    'strategy': 'RunSelectorLocator',
    'priority': 'High'
}

resp = requests.post('http://localhost:8000/report_failure', json=payload, timeout=5)
print(resp.status_code)
print(resp.text)
