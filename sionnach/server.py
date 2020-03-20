"""
Handles the low-level server/client interface
- Reads raw client input into the input queue
- Sends raw client output from the output queue

Higher-level functionality is handled by the Character class
"""
import asyncio
from asyncio import CancelledError, FIRST_COMPLETED, StreamReader, StreamWriter

from sionnach import config, log

logger = log.logger(__name__)


class Server:
    def __init__(self, register_client, deregister_client):
        # The main controller passes in a handler for upstream client
        # registration
        self.register_client = register_client
        self.deregister_client = deregister_client

        self.server = None
        self.clients = []

    async def start_server(self):
        self.server = await asyncio.start_server(
            self.handle_new_client, "127.0.0.1", config.port
        )

        logger.info(f"Serving on port {config.port}.")

    async def handle_new_client(self, reader, writer):
        client = Client(reader, writer)
        self.clients.append(client)
        self.register_client(client)
        await client.communicate_until_closed()
        self.deregister_client(client)


class Client:
    def __init__(self, reader: StreamReader, writer: StreamWriter):
        self.reader = reader
        self.writer = writer
        self.remote_ip = writer.get_extra_info("peername")[0]

        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()

        # When a value is set on this Future, the client is set to be dropped...
        self.kill_switch = asyncio.get_running_loop().create_future()
        # Which will trigger resolution on this Future.
        self.closed = asyncio.get_running_loop().create_future()

    async def communicate_until_closed(self):
        """
        Start up the sub-tasks:
        - Read input from the client (in complete lines)
        - Send output to the client
        - Watch out for a kill order from above
        :return:
        """
        logger.debug(f"({self.remote_ip}) New client.")

        receive_task = asyncio.create_task(self._receive_to_queue())
        send_task = asyncio.create_task(self._send_from_queue())

        comm_tasks = {
            receive_task,
            send_task,
            self.kill_switch,
        }
        done, pending = await asyncio.wait(comm_tasks, return_when=FIRST_COMPLETED)

        logger.debug(f"({self.remote_ip}) Cleaning up client...")

        for task in pending:
            # The kill switch is a simple future that does not need to be cleaned up
            if task is self.kill_switch:
                continue

            if not task.cancelled():
                task.cancel()

            await task

        await self._close_socket()

        logger.debug(f"({self.remote_ip}) Client dropped.")
        self.closed.set_result(True)

    async def close(self):
        """
        Synchronous method that drops the client as soon as possible.
        Does not have to be awaited, unless we explicitly want to do something after
        the client is fully dropped.
        :return:
        """
        self.kill_switch.set_result(True)
        return await self.closed

    def send(self, msg):
        """
        Synchronous method that sends a given message to this client as soon as
        possible.
        :param msg:
        :return:
        """
        self.output_queue.put_nowait(msg)

    async def async_receive(self):
        """
        Read something from the client's input queue, blocking until successful
        :return:
        """
        return await self.input_queue.get()

    def set_password_mode(self, mode):
        """
        Send IAC WILL/WON'T ECHO based on the mode param.
        If True, send WILL ECHO so that the client stops local echo (but we don't
        actually send remote echoes either, so that passwords are not revealed)
        :param mode:
        :return:
        """
        if mode:
            self.output_queue.put_nowait(bytes([IAC, WILL, ECHO]))
        else:
            self.output_queue.put_nowait(bytes([IAC, WONT, ECHO]))

    # ---------------------------
    # Private helpers
    async def _receive_to_queue(self):
        """
        Read complete lines of input from the client socket into its input queue
        :return:
        """
        try:
            msg = await self.reader.readline()

            # Watch for telnet commands
            while len(msg) > 0 and msg[0] == IAC:
                # Just strip them for now
                msg = msg[3:]

            # "If the EOF was received and the internal buffer is empty,
            # return an empty bytes object."
            if msg == b"":
                logger.debug(f"({self.remote_ip}) Client closed socket.")
                return

            msg = msg.decode().strip()[0 : config.max_input_length]
            logger.debug(f"({self.remote_ip}) [RECV] {msg}")

            # Register as next available input from client
            await self.input_queue.put(msg)

            return await self._receive_to_queue()

        except CancelledError:
            logger.debug(f"({self.remote_ip}) Receiver cancelled.")

    async def _send_from_queue(self):
        """
        Send messages to the client from its output queue
        :return:
        """
        # Lazily get queued messages and send them
        try:
            msg = await self.output_queue.get()
            await self._send_msg(msg)

            return await self._send_from_queue()

        except CancelledError:
            await self.output_queue.put("Server closed connection.  Goodbye.")

            # Flush any remaining messages immediately
            while self.output_queue.qsize() > 0:
                msg = self.output_queue.get_nowait()
                await self._send_msg(msg)

            logger.debug(f"({self.remote_ip}) Sender cancelled.")

    async def _send_msg(self, msg):
        """
        Low level function to perform the actual stream write for sending
        messages to clients
        :param msg:
        :return:
        """
        # Prepare debug preview
        msg_preview = msg[0 : config.output_preview_length]

        # Some things should only be done on actual strings, not raw bytestrings
        # (i.e., telnet commands)
        if isinstance(msg, str):
            msg_preview = msg_preview.replace("\n", "\\n").replace("\r", "\\r")

            if len(msg) > config.output_preview_length:
                msg_preview += "..."

            # Always end with a newline for the client
            if msg[-2:] != "\r\n":
                msg = f"{msg}\r\n"

            # Encode string to bytes
            msg = msg.encode()

        # Perform actual write (message in raw bytes)
        self.writer.write(msg)
        await self.writer.drain()
        logger.debug(f"({self.remote_ip}) [SEND] {msg_preview}")

    async def _close_socket(self):
        """
        Gracefully kick the client
        :return:
        """
        # Goodbye
        self.writer.close()
        await self.writer.wait_closed()


# --[ Telnet Commands ]---------------------------------------------------------
# (Adapted from https://github.com/quixadhal/PykuMUD)
SE = 240  # End of subnegotiation parameters
NOP = 241  # No operation
DATMK = 242  # Data stream portion of a sync.
BREAK = 243  # NVT Character BRK
IP = 244  # Interrupt Process
AO = 245  # Abort Output
AYT = 246  # Are you there
EC = 247  # Erase Character
EL = 248  # Erase Line
GA = 249  # The Go Ahead Signal
SB = 250  # Sub-option to follow
WILL = 251  # Will; request or confirm option begin
WONT = 252  # Wont; deny option request
DO = 253  # Do = Request or confirm remote option
DONT = 254  # Don't = Demand or confirm option halt
IAC = 255  # Interpret as Command
SEND = 1  # Sub-process negotiation SEND command
IS = 0  # Sub-process negotiation IS command

# --[ Telnet Options ]----------------------------------------------------------
BINARY = 0  # Transmit Binary
ECHO = 1  # Echo characters back to sender
RECON = 2  # Reconnection
SGA = 3  # Suppress Go-Ahead
TTYPE = 24  # Terminal Type
NAWS = 31  # Negotiate About Window Size
LINEMO = 34  # Line Mode
