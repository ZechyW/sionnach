"""
Handles the low-level server/client interface
- Reads raw client input into the input queue
- Sends raw client output from the output queue

Higher-level functionality is handled by the Character class
"""
import asyncio


class Server:
    def __init__(self):
        self.server = asyncio.start_server(self.handle_echo, "127.0.0.1", 8888)

        print(f"Serving on port 8888.")

        self.server = asyncio.get_event_loop().create_task(self.server)

    async def handle_echo(self, reader, writer):
        data = await reader.read(100)
        message = data.decode()
        address = writer.get_extra_info("peername")

        print(f"Received {message!r} from {address!r}")

        print(f"Send: {message!r}")
        writer.write(data)
        await writer.drain()

        print("Close the connection")
        writer.close()


class Client:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.remote_ip = writer.get_extra_info("peername")

        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()

        self.kill_switch = asyncio.Future()
