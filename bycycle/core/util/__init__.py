def joinAttrs(attrs, join_string=' '):
    """Join the values in attrs, leaving out empty values."""
    if isinstance(attrs, dict):
        attrs = attrs.values()
    return join_string.join([str(a) for a in attrs if a])
