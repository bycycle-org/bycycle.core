from collections import Mapping, Sequence

from sqlalchemy.schema import MetaData
from sqlalchemy.ext.declarative import declarative_base


metadata = MetaData()


class Entity(object):

    json_fields = '*'
    """Specifies which fields to include/exclude in/from JSON data.


    Used in :meth:`__json_data__`.

    Can be:

        - '*' to include all public attributes
        - A list to include specific attributes
        - A dict to specify includes and/or excludes
          {'include': [...], 'exclude': [...]}

    '*' can also be used in an include list to include all public
    attributes. This can be useful if you want to include most of the
    default fields and then include some extra fields and/or exclude
    some fields.

    Field names can include dots to retrieve fields from attributes.

    """

    def __json_data__(self):
        data = {}

        fields = self.json_fields
        default_include = (k for k in self.__dict__ if not k.startswith('_'))
        default_exclude = ('json_fields',)

        if fields == '*':
            # Include all public attributes by default
            include = default_include
            exclude = default_exclude
        elif isinstance(fields, Sequence) and not isinstance(fields, str):
            # Include the specified fields
            include = fields
            exclude = ()
        elif isinstance(fields, Mapping):
            include = fields.get('include', default_include)
            exclude = fields.get('exclude', default_exclude)
        else:
            raise ValueError('Bad JSON field spec: {}'.format(fields))

        fields = set(include)
        if '*' in fields:
            fields.remove('*')
            fields |= set(default_include)
        fields -= set(exclude)

        for field in fields:
            v = self
            for name in field.split('.'):
                v = getattr(v, name)
            if hasattr(v, '__json_data__'):
                v = v.__json_data__()
            data[field] = v
        return data


Base = declarative_base(metadata=metadata, cls=Entity)
