from transitrt.exceptions import CommonTaskFailure


def before_send_sentry_handler(event, hint):
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        # CommonTaskFailures represent conditions that are known to
        # happen from time to time in the normal run of things but
        # still need to be raised in order for celery tasks to fail
        if isinstance(exc_value, (CommonTaskFailure)):
            # To discard Sentry event return None
            return None

    return event
