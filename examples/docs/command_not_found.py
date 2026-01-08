import re

from inspect_ai.model import ChatMessageTool
from inspect_scout import Result, Scanner, Transcript, scanner, tool_callers
from pydantic import BaseModel, Field

@scanner(messages="all")
def command_not_found() -> Scanner[Transcript]:
    """Detects "command not found" errors in tool outputs.

    Returns a list of results, one for each "command not found" error found.
    Each result contains structured observations with:
        message_id: The ID of the assistant message that made the tool call.
        command: The command that was not found.
        tool: The name of the tool that produced the output. 
    """

    async def scan(transcript: Transcript) -> list[Result]:
        """Find all 'command not found' errors in the transcript."""
        results: list[Result] = []

        # Build a mapping from tool_call_id to assistant message
        tool_call_to_assistant = tool_callers(transcript)

        # Pattern to match "command not found" errors
        pattern = r"(\w+): line \d+: (\w+): command not found"

        # Iterate through all tool messages with tool call ids
        for message in (m for m in transcript.messages if isinstance(m, ChatMessageTool)):
         
            # skip messages with no tool_call_id
            if message.tool_call_id is None:
                continue

            # look for 'command not found'
            match = re.search(pattern, message.text)
            if match:
                # extract the command and tool name
                command = match.group(2)
                tool_name = message.function

                # find the assistant message that made this tool call
                # (skip messages with no correpsonding assistant message)
                assistant_msg, assistant_idx = tool_call_to_assistant.get(
                    message.tool_call_id, (None, 0)
                )
                if assistant_msg is None:
                    continue
                
                results.append(
                    Result(
                        value=dict(
                            message_id=f"M{assistant_idx}",
                            command=command,
                            tool=tool_name,
                        ),
                        explanation=(
                            f"[M{assistant_idx}] Found 'command not found' for command '{command}' in "
                            f"{tool_name} output"
                        ),
                        references=[create_assistant_reference(assistant_msg, assistant_idx)],
                    )
                )
               

        return results

    return scan









