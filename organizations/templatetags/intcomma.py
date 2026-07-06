from django import template

register = template.Library()


@register.filter
def intcomma(value):
    """
    Formats a number with thousands separator (.) and decimal separator (,).
    Example: 1234567.89 -> 1.234.567,89
    """
    try:
        # Convert to float if it's a string
        if isinstance(value, str):
            value = float(value)
        
        # Handle None or empty values
        if value is None:
            return value
        
        # Check if negative
        is_negative = value < 0
        value = abs(value)
        
        # Split into integer and decimal parts
        str_value = f"{value:.2f}"
        parts = str_value.split('.')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "00"
        
        # Add thousands separator (.)
        integer_part_with_separator = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                integer_part_with_separator = "." + integer_part_with_separator
            integer_part_with_separator = digit + integer_part_with_separator
        
        # Combine with decimal separator (,)
        result = f"{integer_part_with_separator},{decimal_part}"
        
        if is_negative:
            result = "-" + result
        
        return result
    except (ValueError, TypeError):
        return value


@register.filter
def intcomma_rate(value):
    """
    Formats a rate number with thousands separator (.) and decimal separator (,),
    using 4 decimal places for rates.
    Example: 45.6789 -> 45,6789
    """
    try:
        # Convert to float if it's a string
        if isinstance(value, str):
            value = float(value)
        
        # Handle None or empty values
        if value is None:
            return value
        
        # Check if negative
        is_negative = value < 0
        value = abs(value)
        
        # Split into integer and decimal parts
        str_value = f"{value:.4f}"
        # Remove trailing zeros but keep at least 2 decimal places
        str_value = str_value.rstrip('0')
        if '.' in str_value:
            decimal_places = len(str_value.split('.')[1])
            if decimal_places < 2:
                str_value = f"{value:.2f}"
        
        parts = str_value.split('.')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "00"
        
        # Add thousands separator (.)
        integer_part_with_separator = ""
        for i, digit in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                integer_part_with_separator = "." + integer_part_with_separator
            integer_part_with_separator = digit + integer_part_with_separator
        
        # Combine with decimal separator (,)
        result = f"{integer_part_with_separator},{decimal_part}"
        
        if is_negative:
            result = "-" + result
        
        return result
    except (ValueError, TypeError):
        return value
