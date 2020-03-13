"""
Handles the low-level server/client interface
- Reads raw client input into the input queue
- Sends raw client output from the output queue

Higher-level functionality is handled by the Character class
"""
import asyncio
from asyncio import CancelledError, FIRST_COMPLETED

from sionnach import log, config

logger = log.logger(__name__)


class Server:
    def __init__(self, register_client, deregister_client):
        # The main controller passes in a handler for upstream client registration
        self.register_client = register_client
        self.deregister_client = deregister_client

        self.clients = []

        self.server = asyncio.start_server(
            self.handle_new_client, "127.0.0.1", config.port
        )

        logger.info(f"Serving on port {config.port}.")

        self.server = asyncio.get_event_loop().create_task(self.server)

    async def handle_new_client(self, reader, writer):
        client = Client(reader, writer)
        self.clients.append(client)
        self.register_client(client)
        await client.communicate_until_closed()


class Client:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer
        self.remote_ip = writer.get_extra_info("peername")[0]

        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()

        self.kill_switch = asyncio.Future()

    async def communicate_until_closed(self):
        """
        Start up the sub-tasks:
        - Read input from the client (in complete lines)
        - Send output to the client
        - Watch out for a kill order from above
        :return:
        """
        logger.debug(f"({self.remote_ip}) New client.")

        comm_tasks = {
            asyncio.create_task(self._receive_to_queue()),
            asyncio.create_task(self._send_from_queue()),
        }
        done, pending = await asyncio.wait(comm_tasks, return_when=FIRST_COMPLETED)

        logger.debug(f"({self.remote_ip}) Cleaning up client.")

        # async def handle_echo(self, reader, writer):
        #     data = await reader.read(100)
        #     message = data.decode()
        #     address = writer.get_extra_info("peername")
        #
        #     print(f"Received {message!r} from {address!r}")
        #
        #     print(f"Send: {message!r}")
        #     writer.write(data)
        #     await writer.drain()
        #
        #     print("Close the connection")
        #     writer.close()

    async def _receive_to_queue(self):
        """
        Read complete lines of input from the client socket into its input queue
        :return:
        """
        try:
            msg = await self.reader.readline()

            # "If the EOF was received and the internal buffer is empty,
            # return an empty bytes object."
            if msg == b"":
                logger.debug(f"({self.remote_ip}) Client closed socket.")
                return

            logger.debug(f"({self.remote_ip}) [RECV] {msg}")

            await self.input_queue.put(msg)

            return asyncio.create_task(self._receive_to_queue())

        except CancelledError:
            logger.debug(f"({self.remote_ip}) Cancelling receiver...")

    async def _send_from_queue(self):
        try:
            msg = await self.output_queue.get()
            self.writer.write(msg.encode())
            await self.writer.drain()

        except CancelledError:
            logger.debug(f"({self.remote_ip}) Cancelling sender...")
