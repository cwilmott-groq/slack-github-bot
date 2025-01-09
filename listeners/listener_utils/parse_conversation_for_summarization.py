def parse_slack_conversation(conversation):
    """
    Parses Slack conversation data to extract relevant information for LLM summarization.

    Args:
        conversation (list): List of Slack messages.

    Returns:
        str: Formatted conversation string suitable for LLM consumption.
    """
    parsed_messages = []

    for message in sorted(conversation, key=lambda x: x['ts']):
        user = message.get('user', 'System')
        text = message.get('text', '').strip()

        # Include blocks or attachments if the main text is empty
        if not text:
            if 'blocks' in message:
                for block in message['blocks']:
                    if block['type'] == 'rich_text':
                        text += ''.join(
                            elem.get('text', '')
                            for elem in block.get('elements', [])
                            if elem.get('type') == 'text'
                        )
            elif 'attachments' in message:
                for attachment in message['attachments']:
                    text += attachment.get('text', '')

        # Remove empty messages
        if not text:
            continue

        # Format the message for readability
        if 'subtype' in message and message['subtype'] == 'channel_join':
            action = f"{user} joined the channel."
        elif 'subtype' in message and message['subtype'] == 'bot_message':
            action = f"[Bot Message] {text}"
        else:
            action = f"{user}: {text}"

        parsed_messages.append(action)

    # Combine messages into a single string for LLM
    return "\n".join(parsed_messages)