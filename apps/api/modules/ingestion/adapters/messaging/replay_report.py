from collections import Counter
from dataclasses import dataclass, field


@dataclass
class ReplayReport:
    """Bilan d'un rejeu des topics capteurs."""

    planned: int = 0
    read: int = 0
    accepted: int = 0
    rejected: int = 0
    reasons: Counter = field(default_factory=Counter)

    def reject(self, error):
        self.rejected += 1
        # « … error=zone incohérente pour … » → « zone incohérente pour … »
        reason = str(error).split("error=")[-1].split(":")[0].strip()
        self.reasons[reason] += 1
