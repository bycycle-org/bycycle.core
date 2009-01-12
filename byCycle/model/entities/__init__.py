from byCycle.model.entities.base import *
from byCycle.model.entities.public import *


# Monkey-patch the Entity class
from elixir import Entity as __Entity
def __to_builtin(self):
    return dict([(col.key, getattr(self, col.key)) for col in self.c])
__Entity.to_builtin = __to_builtin
def __to_json(self):
    return simplejson.dumps(self.to_builtin())
__Entity.to_json = __to_json
def __repr(self):
    return repr(self.to_builtin())
__Entity.__repr__ = __repr
