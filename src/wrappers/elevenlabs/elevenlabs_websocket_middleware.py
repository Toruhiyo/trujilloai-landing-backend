import json
import logging
import asyncio
from typing import Any, Optional, Callable, TypeVar
import websockets
from fastapi import WebSocket
from websockets.exceptions import ConnectionClosed
from src.utils.metaclasses import DynamicSingleton
from src.wrappers.elevenlabs.errors import ToolCallMissingParametersError
from src.wrappers.elevenlabs.toolbox import format_message_for_logging, get_signed_url

logger = logging.getLogger(__name__)

# Type for the event matcher function
T = TypeVar("T")
EventMatcherType = Callable[[dict[str, Any]], bool]


# Decorator factories
def client_event(event_match: EventMatcherType) -> Callable[[Callable], Callable]:

    def decorator(func):
        # Mark this function for later registration
        func.is_client_handler = True
        func.event_matcher = event_match
        return func

    return decorator


def server_event(event_match: EventMatcherType) -> Callable[[Callable], Callable]:

    def decorator(func):
        # Mark this function for later registration
        func.is_server_handler = True
        func.event_matcher = event_match
        return func

    return decorator


def client_tool_call(tool_name: str, required_parameters: Optional[list[str]] = None):

    def event_matcher(message: dict[str, Any]) -> bool:
        # First check if it's a client_tool_call message
        if message.get("type") != "client_tool_call":
            return False

        # Then check if the tool_name matches
        tool_call_data = message.get("client_tool_call", {})
        if tool_call_data.get("tool_name") != tool_name:
            return False

        # Check for required parameters if specified
        if required_parameters:
            parameters = tool_call_data.get("parameters", {})
            missing_parameters = [
                param for param in required_parameters if param not in parameters
            ]
            if missing_parameters:
                raise ToolCallMissingParametersError(tool_name, missing_parameters)

        return True

    return server_event(event_matcher)


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

        # Event handling attributes
        self.__client_event_handlers: list[Callable] = []
        self.__server_event_handlers: list[Callable] = []
        self.__register_event_handlers()

        # Message filtering attributes (true = forward message, false = don't forward)
        self._client_to_elevenlabs_filters: list[Callable[[dict[str, Any]], bool]] = []
        self._elevenlabs_to_client_filters: list[Callable[[dict[str, Any]], bool]] = []

        self._register_additional_filters()

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

        # Create tasks for forwarding in both directions with event handling
        client_to_elevenlabs = asyncio.create_task(
            self.__forward_client_to_elevenlabs_with_handlers()
        )
        elevenlabs_to_client = asyncio.create_task(
            self.__forward_elevenlabs_to_client_with_handlers()
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

    async def send_message_to_client(self, message: dict):
        if self.__client_connection:
            logger.debug(
                f"Sending message to client: {format_message_for_logging(message)}"
            )
            await self.__client_connection.send_json(message)
        else:
            logger.warning("Cannot forward to client: connection is closed")

    async def send_message_to_elevenlabs(self, message: dict):
        if self.__elevenlabs_connection:
            logger.debug(
                f"Sending message to ElevenLabs: {format_message_for_logging(message)}"
            )
            await self.__elevenlabs_connection.send(json.dumps(message))
        else:
            logger.warning("Cannot forward to ElevenLabs: connection is closed")

    def add_client_to_elevenlabs_filter(
        self, filter_func: Callable[[dict[str, Any]], bool]
    ):
        self._client_to_elevenlabs_filters.append(filter_func)

    def add_elevenlabs_to_client_filter(
        self, filter_func: Callable[[dict[str, Any]], bool]
    ):
        self._elevenlabs_to_client_filters.append(filter_func)

    # Protected:
    def _register_additional_filters(self):
        # Check if child classes have defined additional filters
        if hasattr(self, "_additional_client_to_elevenlabs_filters"):
            additional_filters: list[Callable[[dict[str, Any]], bool]] = (
                self._additional_client_to_elevenlabs_filters  # type: ignore
            )
            self._client_to_elevenlabs_filters.extend(additional_filters)

        if hasattr(self, "_additional_elevenlabs_to_client_filters"):
            additional_filters: list[Callable[[dict[str, Any]], bool]] = (
                self._additional_elevenlabs_to_client_filters  # type: ignore
            )
            self._elevenlabs_to_client_filters.extend(additional_filters)

    def __register_event_handlers(self):
        for attr_name in dir(self):
            if attr_name.startswith("__"):
                continue

            attr = getattr(self, attr_name)
            if callable(attr):
                # Register client event handlers
                if hasattr(attr, "is_client_handler") and getattr(
                    attr, "is_client_handler"
                ):
                    self.__client_event_handlers.append(attr)
                    logger.info(f"Registered client event handler: {attr_name}")

                # Register server event handlers
                if hasattr(attr, "is_server_handler") and getattr(
                    attr, "is_server_handler"
                ):
                    self.__server_event_handlers.append(attr)
                    logger.info(f"Registered server event handler: {attr_name}")

    def __should_forward_to_elevenlabs(self, message: dict[str, Any]) -> bool:
        # If no filters, forward by default
        if not self._client_to_elevenlabs_filters:
            return True

        # Check all filters - all must return True for the message to be forwarded
        for filter_func in self._client_to_elevenlabs_filters:
            try:
                if filter_func(message):
                    logger.debug(
                        f"Message filtered, not forwarding to ElevenLabs: "
                        f"{format_message_for_logging(message)}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error in filter function: {e}")
                # In case of error, be conservative and forward the message
                continue

        return True

    def __should_forward_to_client(self, message: dict[str, Any]) -> bool:
        # If no filters, forward by default
        if not self._elevenlabs_to_client_filters:
            return True

        # Check all filters - all must return True for the message to be forwarded
        for filter_func in self._elevenlabs_to_client_filters:
            try:
                if filter_func(message):
                    logger.debug(
                        f"Message filtered, not forwarding to client: "
                        f"{format_message_for_logging(message)}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error in filter function: {e}")
                # In case of error, be conservative and forward the message
                continue

        return True

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

    async def __forward_client_to_elevenlabs_with_handlers(
        self, on_event: Optional[Callable[[str, Any], None]] = None
    ):
        try:
            while (
                not self.__shutdown_event.is_set()
                and self.__is_client_connected
                and self.__is_elevenlabs_connected
                and self.__client_connection is not None
            ):
                # Receive message from client with a timeout
                try:
                    client_message = await asyncio.wait_for(
                        self.__client_connection.receive_json(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    # Just check if connections are still valid and continue
                    if not (
                        self.__is_client_connected and self.__is_elevenlabs_connected
                    ):
                        break
                    continue

                # Process the message with client event handlers
                await self.__process_client_message(client_message)

                # Call the event handler if provided
                if on_event:
                    on_event("client_to_elevenlabs", client_message)

                # Skip forwarding if ElevenLabs connection is closed
                if not self.__is_elevenlabs_connected:
                    logger.warning("Cannot forward to ElevenLabs: connection is closed")
                    break

                # Check if message should be forwarded based on filters
                if self.__should_forward_to_elevenlabs(client_message):
                    # Forward to ElevenLabs
                    await self.send_message_to_elevenlabs(client_message)
                else:
                    logger.info(
                        f"Message filtered out from forwarding to ElevenLabs: "
                        f"{format_message_for_logging(client_message)}"
                    )

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

    async def __forward_elevenlabs_to_client_with_handlers(
        self, on_event: Optional[Callable[[str, Any], None]] = None
    ):
        try:
            while (
                not self.__shutdown_event.is_set()
                and self.__is_elevenlabs_connected
                and self.__is_client_connected
                and self.__elevenlabs_connection is not None
            ):
                # Receive message from ElevenLabs
                data = await self.__elevenlabs_connection.recv()
                elevenlabs_message = json.loads(data)

                # Process the message with server event handlers
                await self.__process_server_message(elevenlabs_message)

                # Call the event handler if provided
                if on_event:
                    on_event("elevenlabs_to_client", elevenlabs_message)

                # Skip forwarding if client connection is closed
                if not self.__is_client_connected:
                    logger.warning("Cannot forward to client: connection is closed")
                    break

                # Check if message should be forwarded based on filters
                if self.__should_forward_to_client(elevenlabs_message):
                    # Forward to client
                    await self.send_message_to_client(elevenlabs_message)
                else:
                    logger.info(
                        f"Message filtered out from forwarding to client: "
                        f"{format_message_for_logging(elevenlabs_message)}"
                    )

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

    async def __process_client_message(self, message: dict[str, Any]):
        try:
            # Go through all registered client event handlers
            for handler in self.__client_event_handlers:
                # Check if this handler should process this message
                event_matcher = getattr(handler, "event_matcher", None)
                if event_matcher is None:
                    continue

                try:
                    if event_matcher(message):
                        # Run the handler
                        handler(message)
                except Exception as matcher_error:
                    # If the matcher fails (e.g., due to missing keys), just skip this handler
                    logger.debug(f"Event matcher failed: {matcher_error}")
                    continue
        except Exception as e:
            logger.error(f"Error processing client message: {e}")

    async def __process_server_message(self, message: dict[str, Any]):
        try:
            # Go through all registered server event handlers
            for handler in self.__server_event_handlers:
                # Check if this handler should process this message
                event_matcher = getattr(handler, "event_matcher", None)
                if event_matcher is None:
                    continue

                try:
                    if event_matcher(message):
                        # Run the handler
                        await handler(message)
                except ToolCallMissingParametersError as e:
                    logger.error(f"Tool call missing parameters: {e}")
                    continue
                except Exception as matcher_error:
                    # If the matcher fails (e.g., due to missing keys), just skip this handler
                    logger.debug(f"Event matcher failed: {matcher_error}")
                    continue
        except Exception as e:
            logger.error(f"Error processing server message: {e}")

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
