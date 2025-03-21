import json
import logging
import asyncio
import traceback
from typing import Any, Optional, Callable
import websockets
from fastapi import WebSocket
from websockets.exceptions import ConnectionClosed
from src.utils.metaclasses import DynamicSingleton
from src.wrappers.elevenlabs.toolbox import get_signed_url

logger = logging.getLogger(__name__)


class ElevenLabsWebsocketMiddleware(metaclass=DynamicSingleton):
    """
    Middleware for handling websocket connections with ElevenLabs Conversational AI API.
    Acts as a bidirectional proxy between front-end clients and ElevenLabs websocket service.
    """

    def __init__(self, agent_id: str, api_key: str, voice_id: Optional[str] = None):
        self.agent_id = agent_id
        self.api_key = api_key
        self.voice_id = voice_id
        self.elevenlabs_connection = None
        self.client_connection = None
        self.is_elevenlabs_connected = False
        self.is_client_connected = False
        self.client_id = None
        self._forward_tasks = []
        self._shutdown_event = asyncio.Event()

    async def setup_connections(
        self, client_websocket: WebSocket, debug: bool = False
    ) -> str:
        """
        Setup connections for both client and ElevenLabs

        Args:
            client_websocket: The client's WebSocket connection
            debug: Enable debug mode for ElevenLabs

        Returns:
            client_id: The ID assigned to the client
        """
        # Accept the client connection if not already accepted
        # Check if the connection is already accepted to avoid errors
        if not getattr(client_websocket, "_accepted", False):
            try:
                await client_websocket.accept()
                logger.info("Accepted WebSocket connection in middleware")
            except RuntimeError as e:
                if "already accepted" not in str(e).lower():
                    # If the error is not about already being accepted, re-raise
                    raise
                logger.info("WebSocket connection was already accepted")

        self.client_connection = client_websocket
        self.is_client_connected = True
        self.client_id = f"{id(client_websocket)}"

        # Connect to ElevenLabs
        await self._connect_to_elevenlabs(debug)

        # Send connected event to client
        await self._send_connected_event()

        # Return the client ID for reference
        return self.client_id

    async def _send_connected_event(self):
        """Send a connected event to the client"""
        if self.is_client_connected and self.client_connection:
            from src.app.voicechat.enums import WebSocketEventType

            await self.client_connection.send_json(
                {
                    "type": WebSocketEventType.CONNECTED,
                    "data": {"status": "connected", "client_id": self.client_id},
                }
            )
            logger.info(f"Sent connected event to client: {self.client_id}")

    async def _connect_to_elevenlabs(self, debug: bool = False) -> None:
        """Establish connection to ElevenLabs websocket"""
        query_params = [f"agent_id={self.agent_id}"]
        if self.voice_id:
            query_params.append(f"voice_id={self.voice_id}")
        if debug:
            query_params.append("debug=true")

        try:
            # Get the signed URL and log it (partially redacted for security)
            signed_url = self.__get_signed_url()
            if signed_url:
                # Redact most of the URL for security but show part of it for debugging
                redacted_url = (
                    f"{signed_url[:20]}...{signed_url[-20:]}"
                    if len(signed_url) > 40
                    else "URL too short to redact safely"
                )
                logger.info(f"Got signed URL from ElevenLabs: {redacted_url}")
            else:
                logger.error("Failed to get signed URL from ElevenLabs: URL is None")
                raise Exception("Failed to get signed URL from ElevenLabs")

            connection_url = f"{signed_url}?{'&'.join(query_params)}"
            logger.info(
                f"Attempting to connect to ElevenLabs with params: {query_params}"
            )

            # Add a timeout to the websocket connection to avoid hanging
            self.elevenlabs_connection = await asyncio.wait_for(
                websockets.connect(connection_url), timeout=10.0  # 10 second timeout
            )
            self.is_elevenlabs_connected = True
            logger.info("Connected to ElevenLabs websocket API")
        except Exception as e:
            stack_trace = traceback.format_exc()
            error_msg = f"Failed to connect to ElevenLabs: {str(e)}\n{stack_trace}"
            logger.error(error_msg)
            # Close client connection if ElevenLabs connection fails
            await self._close_client_connection("Failed to connect to ElevenLabs")
            raise

    async def start_forwarding(self):
        """Start forwarding messages between client and ElevenLabs"""
        if not (self.is_client_connected and self.is_elevenlabs_connected):
            raise ConnectionError(
                "Both client and ElevenLabs connections must be established"
            )

        # Clear any existing tasks
        self._forward_tasks = []
        self._shutdown_event.clear()

        # Create tasks for forwarding in both directions
        client_to_elevenlabs = asyncio.create_task(self._forward_client_to_elevenlabs())
        elevenlabs_to_client = asyncio.create_task(self._forward_elevenlabs_to_client())

        # Store tasks
        self._forward_tasks = [client_to_elevenlabs, elevenlabs_to_client]

        # Wait for either task to complete - when one connection fails, we stop both
        try:
            done, pending = await asyncio.wait(
                self._forward_tasks, return_when=asyncio.FIRST_COMPLETED
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
            for task in self._forward_tasks:
                if not task.done():
                    task.cancel()

            # Wait briefly for tasks to complete
            await asyncio.gather(*self._forward_tasks, return_exceptions=True)

            # Ensure connections are closed
            await self.close_all_connections()

    async def _forward_client_to_elevenlabs(
        self, on_event: Optional[Callable[[str, Any], None]] = None
    ):
        """Forward messages from client to ElevenLabs"""
        try:
            while (
                not self._shutdown_event.is_set()
                and self.is_client_connected
                and self.is_elevenlabs_connected
            ):
                # Receive message from client with a timeout to check connection status periodically
                try:
                    if self.client_connection:
                        client_message = await asyncio.wait_for(
                            self.client_connection.receive_json(), timeout=1.0
                        )
                    else:
                        logger.warning("Cannot forward to client: connection is closed")
                        break
                except asyncio.TimeoutError:
                    # Just check if connections are still valid and continue
                    if not (self.is_client_connected and self.is_elevenlabs_connected):
                        break
                    continue

                # Skip forwarding if ElevenLabs connection is closed
                if not self.is_elevenlabs_connected:
                    logger.warning("Cannot forward to ElevenLabs: connection is closed")
                    break

                # Call the event handler if provided
                if on_event:
                    on_event("client_to_elevenlabs", client_message)

                # Forward to ElevenLabs
                if self.elevenlabs_connection:
                    await self.elevenlabs_connection.send(json.dumps(client_message))
                else:
                    logger.warning("Cannot forward to ElevenLabs: connection is closed")

        except websockets.exceptions.ConnectionClosed as e:
            # Normal closure, don't treat as error
            logger.info(f"Client connection closed with code {e.code}")
            self.is_client_connected = False

            # Don't try to close ElevenLabs if it's already closed
            if self.is_elevenlabs_connected:
                await self._close_elevenlabs_connection()
        except Exception as e:
            logger.error(f"Error forwarding client to ElevenLabs: {str(e)}")

            # Don't try to close ElevenLabs if it's already closed
            if self.is_elevenlabs_connected:
                await self._close_elevenlabs_connection()
        finally:
            # Make sure client is marked as disconnected
            self.is_client_connected = False

    async def _forward_elevenlabs_to_client(
        self, on_event: Optional[Callable[[str, Any], None]] = None
    ):
        """Forward messages from ElevenLabs to client"""
        try:
            while (
                not self._shutdown_event.is_set()
                and self.is_elevenlabs_connected
                and self.is_client_connected
            ):
                # Receive message from ElevenLabs
                if self.elevenlabs_connection is None:
                    logger.warning("Cannot receive from ElevenLabs: connection is None")
                    break

                data = await self.elevenlabs_connection.recv()
                elevenlabs_message = json.loads(data)

                # Skip forwarding if client connection is closed
                if not self.is_client_connected:
                    logger.warning("Cannot forward to client: connection is closed")
                    break

                # Call the event handler if provided
                if on_event:
                    on_event("elevenlabs_to_client", elevenlabs_message)

                # Forward to client
                if self.client_connection:
                    await self.client_connection.send_json(elevenlabs_message)
                else:
                    logger.warning("Cannot forward to client: connection is closed")

        except ConnectionClosed as e:
            logger.info(
                f"ElevenLabs connection closed. Code: {e.code}. Reason: {e.reason}"
            )
            self.is_elevenlabs_connected = False
            # Close client connection if ElevenLabs connection closes
            await self._close_client_connection("ElevenLabs connection closed")
        except Exception as e:
            logger.error(f"Error forwarding ElevenLabs to client: {str(e)}")
            # Close client connection on error
            await self._close_client_connection(
                f"Error in ElevenLabs communication: {str(e)}"
            )

    async def _close_client_connection(self, reason: str):
        """Close the client WebSocket connection with error message"""
        if self.is_client_connected and self.client_connection:
            try:
                from src.app.voicechat.enums import WebSocketEventType

                # Send error message before closing
                await self.client_connection.send_json(
                    {
                        "type": WebSocketEventType.ERROR,
                        "data": {"error": reason, "code": "connection_closed"},
                    }
                )
                await self.client_connection.close(code=1000, reason=reason)
                logger.info(f"Closed client connection: {reason}")
            except Exception as e:
                logger.error(f"Error closing client connection: {e}")
            finally:
                self.is_client_connected = False

    async def _close_elevenlabs_connection(self):
        """Close the ElevenLabs WebSocket connection"""
        if self.is_elevenlabs_connected and self.elevenlabs_connection:
            try:
                await self.elevenlabs_connection.close()
                logger.info("Closed ElevenLabs connection")
            except Exception as e:
                logger.error(f"Error closing ElevenLabs connection: {e}")
            finally:
                self.is_elevenlabs_connected = False

    async def close_all_connections(self):
        """Close both client and ElevenLabs connections"""
        # Trigger shutdown event
        self._shutdown_event.set()

        # Close ElevenLabs connection
        await self._close_elevenlabs_connection()

        # Close client connection
        await self._close_client_connection("Service shutting down")

        # Wait for forwarding tasks to complete
        if self._forward_tasks:
            await asyncio.wait(self._forward_tasks, timeout=2)

    # Private methods:
    def __get_signed_url(self):
        try:
            url = get_signed_url(self.api_key, self.agent_id)
            return url
        except Exception as e:
            stack_trace = traceback.format_exc()
            logger.error(f"Error getting signed URL: {str(e)}\n{stack_trace}")
            return None
