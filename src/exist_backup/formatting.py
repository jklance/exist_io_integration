"""Value formatting helpers for human-readable display."""


def format_value(raw_value, value_type, user_profile=None):
    """Format a raw attribute value into a human-readable string.

    Args:
        raw_value: The raw value from the database (string or None).
        value_type: Integer type code (0-8).
        user_profile: Optional user profile dict (for unit preferences).

    Returns:
        Formatted string.
    """
    if raw_value is None or raw_value == "":
        return "\u2013"  # en-dash

    try:
        if value_type == 0:
            # Integer
            return f"{int(float(raw_value)):,}"

        elif value_type == 1:
            # Float/Decimal
            return str(round(float(raw_value), 1))

        elif value_type == 2:
            # String
            return str(raw_value)

        elif value_type == 3:
            # Duration (minutes)
            minutes = int(float(raw_value))
            if minutes < 60:
                return f"{minutes}m"
            hours = minutes // 60
            mins = minutes % 60
            if mins == 0:
                return f"{hours}h"
            return f"{hours}h {mins}m"

        elif value_type == 4:
            # Time of day (minutes from midnight)
            minutes = int(float(raw_value))
            hour = minutes // 60
            minute = minutes % 60
            period = "AM" if hour < 12 else "PM"
            display_hour = hour % 12 or 12
            return f"{display_hour}:{minute:02d} {period}"

        elif value_type == 5:
            # Percentage (0.0-1.0)
            pct = float(raw_value) * 100
            return f"{pct:.0f}%"

        elif value_type == 6:
            # Time of day (minutes from midday)
            minutes = int(float(raw_value))
            total_minutes = 720 + minutes  # midday = 720 min from midnight
            hour = total_minutes // 60
            minute = total_minutes % 60
            period = "AM" if hour < 12 else "PM"
            display_hour = hour % 12 or 12
            return f"{display_hour}:{minute:02d} {period}"

        elif value_type == 7:
            # Boolean (0/1)
            return "Yes" if int(float(raw_value)) else "No"

        elif value_type == 8:
            # Scale (1-9)
            return f"{int(float(raw_value))}/9"

        else:
            return str(raw_value)

    except (ValueError, TypeError):
        return str(raw_value)
