def joinAttrs(attrs, join_string=' '):
    """Join the values in attrs, leaving out empty values."""
    if isinstance(attrs, dict):
        attrs = attrs.values()
    return join_string.join([str(a) for a in attrs if a])


def swapKeysAndValues(old_dict):
    """Make a new dict with keys and values in given dict swapped.

    In other words, make a new dict that has the keys of the old dict as the
    values and the respective values of the old dict as the keys to those
    values.

    """
    new_dict = {}
    for k in old_dict:
        new_dict[old_dict[k]] = k
    return new_dict
