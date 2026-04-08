"""PIN code generation for media credential retrieval."""
import random


def generate_pin_code() -> str:
    """Generate a 6-digit PIN in format WFP-XXXXXX."""
    digits = random.randint(100000, 999999)
    return f"WFP-{digits}"
