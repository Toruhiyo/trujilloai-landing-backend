import json
import logging
import asyncio
from typing import Any, Optional, Callable
import websockets
from fastapi import WebSocket
from websockets.exceptions import ConnectionClosed
from src.utils.metaclasses import DynamicSingleton
from src.wrappers.elevenlabs.toolbox import get_signed_url

logger = logging.getLogger(__name__)


class ElevenLabsWebsocketMiddleware(metaclass=DynamicSingleton):

    # Public:
    @property
    def client_id(self) -> str | None:
        return self.__client_id

    @property
    def is_client_connected(self) -> bool:
        return self.__is_client_connected

    @property
    def is_elevenlabs_connected(self) -> bool:
        return self.__is_elevenlabs_connected

    @property
    def agent_id(self) -> str:
        return self.__agent_id

    @property
    def voice_id(self) -> Optional[str]:
        return self.__voice_id

    def __init__(self, agent_id: str, api_key: str, voice_id: Optional[str] = None):
        self.__agent_id = agent_id
        self.__api_key = api_key
        self.__voice_id = voice_id
        self.__elevenlabs_connection = None
        self.__client_connection = None
        self.__is_elevenlabs_connected = False
        self.__is_client_connected = False
        self.__client_id = None
        self.__forward_tasks = []
        self.__shutdown_event = asyncio.Event()

    async def setup_connections(
        self, client_websocket: WebSocket, debug: bool = False
    ) -> str:
        # Accept the client connection
        await client_websocket.accept()
        self.__client_connection = client_websocket
        self.__is_client_connected = True
        self.__client_id = f"{id(client_websocket)}"

        # Connect to ElevenLabs
        await self.__connect_to_elevenlabs(debug)

        # Send connected event to client
        await self.__send_connected_event()

        # Return the client ID for reference
        return self.__client_id

    async def start_forwarding(self):
        if not (self.__is_client_connected and self.__is_elevenlabs_connected):
            raise ConnectionError(
                "Both client and ElevenLabs connections must be established"
            )

        # Clear any existing tasks
        self.__forward_tasks = []
        self.__shutdown_event.clear()

        # Create tasks for forwarding in both directions
        client_to_elevenlabs = asyncio.create_task(
            self.__forward_client_to_elevenlabs()
        )
        elevenlabs_to_client = asyncio.create_task(
            self.__forward_elevenlabs_to_client()
        )

        # Store tasks
        self.__forward_tasks = [client_to_elevenlabs, elevenlabs_to_client]

        # Wait for either task to complete - when one connection fails, we stop both
        try:
            done, pending = await asyncio.wait(
                self.__forward_tasks, return_when=asyncio.FIRST_COMPLETED
            )

            # Check for exceptions in completed tasks
            for task in done:
                if task.exception():
                    logger.warning(
                        f"Forwarding task failed with exception: {task.exception()}"
                    )

        except asyncio.CancelledError:
            logger.info("Forwarding was cancelled")
        finally:
            # Ensure both tasks are properly cleaned up
            for task in self.__forward_tasks:
                if not task.done():
                    task.cancel()

            # Wait briefly for tasks to complete
            await asyncio.gather(*self.__forward_tasks, return_exceptions=True)

            # Ensure connections are closed
            await self.close_all_connections()

    async def close_all_connections(self):
        # Trigger shutdown event
        self.__shutdown_event.set()

        # Close ElevenLabs connection
        await self.__close_elevenlabs_connection()

        # Close client connection
        await self.__close_client_connection("Service shutting down")

        # Wait for forwarding tasks to complete
        if self.__forward_tasks:
            await asyncio.wait(self.__forward_tasks, timeout=2)

    # Private:
    async def __send_connected_event(self):
        if self.__is_client_connected and self.__client_connection:
            from src.app.voicechat.enums import WebSocketEventType

            await self.__client_connection.send_json(
                {
                    "type": WebSocketEventType.CONNECTED,
                    "data": {"status": "connected", "client_id": self.__client_id},
                }
            )
            logger.info(f"Sent connected event to client: {self.__client_id}")

    async def __connect_to_elevenlabs(self, debug: bool = False) -> None:
        query_params = [f"agent_id={self.__agent_id}"]
        if self.__voice_id:
            query_params.append(f"voice_id={self.__voice_id}")
        if debug:
            query_params.append("debug=true")

        connection_url = f"{self.__get_signed_url()}?{'&'.join(query_params)}"

        try:
            self.__elevenlabs_connection = await websockets.connect(connection_url)
            self.__is_elevenlabs_connected = True
            logger.info("Connected to ElevenLabs websocket API")
        except Exception as e:
            logger.error(f"Failed to connect to ElevenLabs: {str(e)}")
            # Close client connection if ElevenLabs connection fails
            await self.__close_client_connection("Failed to connect to ElevenLabs")
            raise

    async def __forward_client_to_elevenlabs(
        self, on_event: Optional[Callable[[str, Any], None]] = None
    ):
        try:
            while (
                not self.__shutdown_event.is_set()
                and self.__is_client_connected
                and self.__is_elevenlabs_connected
            ):
                # Receive message from client with a timeout to check connection status periodically
                try:
                    if self.__client_connection:
                        client_message = await asyncio.wait_for(
                            self.__client_connection.receive_json(), timeout=1.0
                        )
                    else:
                        logger.warning("Cannot forward to client: connection is closed")
                        break
                except asyncio.TimeoutError:
                    # Just check if connections are still valid and continue
                    if not (
                        self.__is_client_connected and self.__is_elevenlabs_connected
                    ):
                        break
                    continue

                # Skip forwarding if ElevenLabs connection is closed
                if not self.__is_elevenlabs_connected:
                    logger.warning("Cannot forward to ElevenLabs: connection is closed")
                    break

                # Call the event handler if provided
                if on_event:
                    on_event("client_to_elevenlabs", client_message)

                # Forward to ElevenLabs
                if self.__elevenlabs_connection:
                    await self.__elevenlabs_connection.send(json.dumps(client_message))
                else:
                    logger.warning("Cannot forward to ElevenLabs: connection is closed")

        except websockets.exceptions.ConnectionClosed as e:
            # Normal closure, don't treat as error
            logger.info(f"Client connection closed with code {e.code}")
            self.__is_client_connected = False

            # Don't try to close ElevenLabs if it's already closed
            if self.__is_elevenlabs_connected:
                await self.__close_elevenlabs_connection()
        except Exception as e:
            logger.error(f"Error forwarding client to ElevenLabs: {str(e)}")

            # Don't try to close ElevenLabs if it's already closed
            if self.__is_elevenlabs_connected:
                await self.__close_elevenlabs_connection()
        finally:
            # Make sure client is marked as disconnected
            self.__is_client_connected = False

    async def __forward_elevenlabs_to_client(
        self, on_event: Optional[Callable[[str, Any], None]] = None
    ):
        try:
            while (
                not self.__shutdown_event.is_set()
                and self.__is_elevenlabs_connected
                and self.__is_client_connected
            ):
                # Receive message from ElevenLabs
                if self.__elevenlabs_connection is None:
                    logger.warning("Cannot receive from ElevenLabs: connection is None")
                    break

                data = await self.__elevenlabs_connection.recv()
                elevenlabs_message = json.loads(data)

                # Skip forwarding if client connection is closed
                if not self.__is_client_connected:
                    logger.warning("Cannot forward to client: connection is closed")
                    break

                # Call the event handler if provided
                if on_event:
                    on_event("elevenlabs_to_client", elevenlabs_message)

                # Forward to client
                if self.__client_connection:
                    await self.__client_connection.send_json(elevenlabs_message)
                else:
                    logger.warning("Cannot forward to client: connection is closed")

        except ConnectionClosed as e:
            logger.info(
                f"ElevenLabs connection closed. Code: {e.code}. Reason: {e.reason}"
            )
            self.__is_elevenlabs_connected = False
            # Close client connection if ElevenLabs connection closes
            await self.__close_client_connection("ElevenLabs connection closed")
        except Exception as e:
            logger.error(f"Error forwarding ElevenLabs to client: {str(e)}")
            # Close client connection on error
            await self.__close_client_connection(
                f"Error in ElevenLabs communication: {str(e)}"
            )

    async def __close_client_connection(self, reason: str):
        if self.__is_client_connected and self.__client_connection:
            try:
                from src.app.voicechat.enums import WebSocketEventType

                # Send error message before closing
                await self.__client_connection.send_json(
                    {
                        "type": WebSocketEventType.ERROR,
                        "data": {"error": reason, "code": "connection_closed"},
                    }
                )
                await self.__client_connection.close(code=1000, reason=reason)
                logger.info(f"Closed client connection: {reason}")
            except Exception as e:
                logger.error(f"Error closing client connection: {e}")
            finally:
                self.__is_client_connected = False

    async def __close_elevenlabs_connection(self):
        if self.__is_elevenlabs_connected and self.__elevenlabs_connection:
            try:
                await self.__elevenlabs_connection.close()
                logger.info("Closed ElevenLabs connection")
            except Exception as e:
                logger.error(f"Error closing ElevenLabs connection: {e}")
            finally:
                self.__is_elevenlabs_connected = False

    def __get_signed_url(self):
        return get_signed_url(self.__api_key, self.__agent_id)
