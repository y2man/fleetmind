from app.celery_app import celery_app
from app.services.email import send_email


class EmailDeliveryError(Exception):
    pass


@celery_app.task(
    name="fleetmind.email.deliver",
    ignore_result=True,
    autoretry_for=(EmailDeliveryError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def deliver_email(to: str, subject: str, body: str) -> None:
    if not send_email(to, subject, body):
        raise EmailDeliveryError("Email provider did not accept the message")
