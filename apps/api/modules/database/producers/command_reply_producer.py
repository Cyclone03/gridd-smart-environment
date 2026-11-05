from shared.contracts.event_types import EventTypes


class CommandReplyProducer:
    """Répond aux commandes sur le topic indiqué par leur émetteur."""

    SOURCE = "database"

    def __init__(self, publisher):
        self._publisher = publisher

    def succeeded(self, command, data):
        self._reply(command, EventTypes.COMMAND_SUCCEEDED, {"data": data})

    def failed(self, command, error):
        self._reply(command, EventTypes.COMMAND_FAILED, {"error": error.to_payload()})

    def _reply(self, command, reply_type, payload):
        if command.reply_to and command.correlation_id:
            reply = command.reply(reply_type, payload, self.SOURCE)
            self._publisher.publish(command.reply_to, reply, key=command.correlation_id)
