class EventTypes:
    """Types d'événements échangés entre modules (champ ``type`` de l'enveloppe).

    Le contenu de chaque événement est décrit dans docs/events.md.
    """

    # ingestion → database (topic ingestion.observations)
    OBSERVATION_VALIDATED = "observation.validated"

    # alarms → database (topic alarms.events)
    ALERT_RAISED = "alert.raised"
    ALERT_RESOLVED = "alert.resolved"
    ALARM_STATE_SAVED = "alarm_state.saved"
    ALARM_RULE_RESET = "alarm_rule.reset"
    ALARM_RULE_SEVERITY_PROPAGATED = "alarm_rule.severity_propagated"

    # alarms → database : commandes avec réponse (topic alarms.commands)
    ALARM_RULE_CREATE = "alarm_rule.create"
    ALARM_RULE_UPDATE = "alarm_rule.update"
    ALARM_RULE_DELETE = "alarm_rule.delete"

    # comfort → database (topic comfort.events) et commandes (comfort.commands)
    COMFORT_ASSESSED = "comfort.assessed"
    COMFORT_PROFILE_SAVE = "comfort_profile.save"
    COMFORT_PROFILE_RESET = "comfort_profile.reset"

    # energy → database (topic energy.events) et commandes (energy.commands)
    ENERGY_ESTIMATED = "energy.estimated"
    ENERGY_PROFILE_SAVE = "energy_profile.save"
    ENERGY_PROFILE_RESET = "energy_profile.reset"

    # database → modules (topic database.events) : faits persistés
    OBSERVATION_PERSISTED = "observation.persisted"
    ALERTS_CHANGED = "alerts.changed"
    ALARM_RULE_CHANGED = "alarm_rule.changed"
    COMFORT_PERSISTED = "comfort.persisted"
    ENERGY_PERSISTED = "energy.persisted"

    # database → émetteur d'une commande (topic database.replies)
    COMMAND_SUCCEEDED = "command.succeeded"
    COMMAND_FAILED = "command.failed"
