import logging

logger = logging.getLogger("vone.push")


def announcement_saved(sender, instance, **kwargs):
    """A company notice that has just become visible is pushed once to everyone who allowed notifications."""
    try:
        from portal import push
        if push.enabled() and push.notice_is_due(instance):
            push.push_company_notice(instance)
    except Exception:  # pushing must never break saving content
        logger.exception("Could not push company notice")
