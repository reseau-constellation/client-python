import sys

import trio
from trio_websocket import serve_websocket, ConnectionClosed


async def echo_server(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            réponse = traiter_message(message)
            await ws.send_message(réponse)
        except ConnectionClosed:
            break


port = sys.argv[2]


async def main():
    await serve_websocket(echo_server, '127.0.0.1', port=int(port), ssl_context=None)


trio.run(main)
