"""SOS alert policy constants."""

from __future__ import annotations

# Minimum accepted buddies required to create an SOS
MIN_BUDDIES_FOR_SOS = 1

# Cooldown between SOS blasts in seconds (60s = 1 minute)
COOLDOWN_SECONDS = 60

# Minutes to wait before escalation is allowed
ESCALATE_AFTER_MIN = 1

# Extra recipients to add on escalation
ESCALATE_MORE_RECIPIENTS = 3

# Default SOS vicinity radius in kilometers
DEFAULT_SOS_RADIUS_KM = 50
