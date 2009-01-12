cascade_arg = 'all, delete-orphan'


# These "constants" are used when creating the adjacency matrix for a region
# The number of digits to save when encoding a float as an int
float_exp = 6
# Multiplier to create int-encoded float
float_encode = 10 ** float_exp
# Multiplier to get original float value back
float_decode = 10 ** -float_exp


def encodeFloat(f):
    """Encode the float ``f`` as an integer."""
    return int(round(f * float_encode))


def decodeFloat(i):
    """Decode the int ``i`` back to its original float value."""
    return i * float_decode
