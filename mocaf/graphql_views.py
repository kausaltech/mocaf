import orjson
import logging
import sentry_sdk
from graphene_django.views import GraphQLView


logger = logging.getLogger(__name__)


class MocafGraphQLView(GraphQLView):
    def execute_graphql_request(self, request, data, query, variables, operation_name, *args, **kwargs):
        transaction = sentry_sdk.Hub.current.scope.transaction

        query_str = query.strip()
        if variables:
            query_str += '\nVariables: %s' % variables
        logger.info("GraphQL query:\n%s" % query_str)

        with sentry_sdk.push_scope() as scope:
            scope.set_context('graphql_variables', variables)
            scope.set_tag('graphql_operation_name', operation_name)

            if transaction is not None:
                span = transaction.start_child(op='graphql query', description=operation_name)
                span.set_data('graphql_variables', variables)
                span.set_tag('graphql_operation_name', operation_name)
            else:
                # No tracing activated, use an inert Span
                span = sentry_sdk.tracing.Span()

            with span:
                result = super().execute_graphql_request(
                    request, data, query, variables, operation_name, *args, **kwargs
                )

            if result.errors:
                self._capture_sentry_exceptions(result.errors)

        return result

    def _capture_sentry_exceptions(self, errors):
        for error in errors:
            try:
                sentry_sdk.capture_exception(error.original_error)
            except AttributeError:
                sentry_sdk.capture_exception(error)

    def json_encode(self, request, d, pretty=False):
        if not (self.pretty or pretty) and not request.GET.get("pretty"):
            return orjson.dumps(d)
        return orjson.dumps(d, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2)
