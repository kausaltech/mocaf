import re

import graphene
from graphene_django import DjangoObjectType
from graphene.utils.trim_docstring import trim_docstring


class DjangoNode(DjangoObjectType):
    @classmethod
    def __init_subclass_with_meta__(cls, **kwargs):
        if 'name' not in kwargs:
            # Remove the trailing 'Node' from the object types
            kwargs['name'] = re.sub(r'Node$', '', cls.__name__)

        model = kwargs['model']
        is_autogen = re.match(r'^\w+\([\w_, ]+\)$', model.__doc__)
        if 'description' not in kwargs and not cls.__doc__ and not is_autogen:
            kwargs['description'] = trim_docstring(model.__doc__)

        super().__init_subclass_with_meta__(**kwargs)

    class Meta:
        abstract = True


class AuthenticatedDeviceNode(graphene.ObjectType):
    pass
