from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post('/heal')
async def heal(data: dict):
    bot_id = data.get('botId')
    print('Mock heal called for', bot_id)
    return JSONResponse({'result': 'ok', 'botId': bot_id})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('mock_ai:app', host='0.0.0.0', port=5001, reload=False)
