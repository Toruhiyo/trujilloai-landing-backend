from typing import Optional
from src.message_typification.message_typifier import MessageTypifier
from src.app.entities.messages.dtos import MessageDTO
from openai.types.beta.threads.message import Message
from openai.types.beta.threads.text_content_block import TextContentBlock

from src.wrappers.azure.openai.session import AzureOpenAiSession


def typify_message(
    raw_message: Message,
    client: Optional[AzureOpenAiSession] = None,
    shall_remove_citation_marks: bool = False,
    shall_remove_markdown: bool = False,
) -> MessageDTO:
    client = client or AzureOpenAiSession()
    message_typifier = MessageTypifier(client=client)
    return message_typifier.compute(
        raw_message,
        shall_remove_citation_marks=shall_remove_citation_marks,
        shall_remove_markdown=shall_remove_markdown,
    )


def get_raw_message_content(raw_message: Message) -> str:
    first_block = raw_message.content[0] if raw_message.content else None
    if not isinstance(first_block, TextContentBlock):
        raise NotImplementedError(
            f"Unsupported message content type: {type(first_block)}"
        )
    return first_block.text.value
