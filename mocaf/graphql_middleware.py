from django.conf import settings
from django.core.exceptions import ValidationError
from graphql.error import GraphQLError
from .graphql_helpers import GraphQLAuthFailedError, GraphQLAuthRequiredError
from graphql.language.ast import Variable

from trips.models import Device
from .graphql_types import AuthenticatedDeviceNode


class APITokenMiddleware:
    def authenticate_device(self, info):
        raise GraphQLError('Token not found', [info])

    def process_device_directive(self, info, directive):
        dev = None
        token = None
        variable_vals = info.variable_values
        for arg in directive.arguments:
            if arg.name.value == 'uuid':
                if isinstance(arg.value, Variable):
                    val = variable_vals.get(arg.value.name.value)
                else:
                    val = arg.value.value
                try:
                    dev = Device.objects.get(uuid=val)
                except Device.DoesNotExist:
                    raise GraphQLAuthFailedError("Device not found", [arg])
                except ValidationError:
                    raise GraphQLAuthFailedError("Invalid UUID", [arg])

            elif arg.name.value == 'token':
                if isinstance(arg.value, Variable):
                    val = variable_vals.get(arg.value.name.value)
                else:
                    val = arg.value.value
                token = val

        if not token:
            raise GraphQLAuthFailedError("Token required", [directive])
        if not dev:
            raise GraphQLAuthFailedError("Device required", [directive])
        if dev.token != token:
            raise GraphQLAuthFailedError("Invalid token", [directive])
        if not dev.enabled and info.field_name != 'enableMocaf' and info.field_name != 'disableMocaf':
            raise GraphQLAuthFailedError("Mocaf disabled", [directive])

        info.context.device = dev

    def resolve(self, next, root, info, **kwargs):
        context = info.context

        if root is None:
            info.context.device = None
            operation = info.operation
            for directive in operation.directives:
                if directive.name.value == 'device':
                    self.process_device_directive(info, directive)

        rt = info.return_type
        gt = getattr(rt, 'graphene_type', None)
        if gt and issubclass(gt, AuthenticatedDeviceNode):
            if not getattr(context, 'device', None):
                raise GraphQLAuthRequiredError("Authentication required", [info])
        return next(root, info, **kwargs)


class LocaleMiddleware:
    def process_locale_directive(self, info, directive):
        for arg in directive.arguments:
            if arg.name.value == 'lang':
                lang = arg.value.value
                if lang not in settings.MODELTRANS_AVAILABLE_LANGUAGES:
                    raise GraphQLError("unsupported language: %s" % lang, [info])
                info.context.language = lang

    def resolve(self, next, root, info, **kwargs):
        if root is None:
            info.context.language = None
            operation = info.operation
            for directive in operation.directives:
                if directive.name.value == 'locale':
                    self.process_locale_directive(info, directive)
        return next(root, info, **kwargs)
