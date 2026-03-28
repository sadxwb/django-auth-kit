# SMS Backends

Django Auth Kit uses a pluggable SMS backend system, modelled after Django's email backend. The default backend prints messages to the console, which is useful during development.

## Built-in Backends

### `ConsoleSmsBackend`

Writes SMS messages to stdout. This is the default.

```python
AUTH_KIT = {
    "SMS_BACKEND": "django_auth_kit.otp.backends.console.ConsoleSmsBackend",
}
```

## Writing a Custom Backend

Subclass `BaseSmsBackend` and implement `send_messages()`:

```python
from django_auth_kit.otp.backends.base import BaseSmsBackend


class TwilioSmsBackend(BaseSmsBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.client = TwilioClient(ACCOUNT_SID, AUTH_TOKEN)
        self.from_number = FROM_NUMBER

    def send_messages(self, messages):
        sent = 0
        for message in messages:
            for recipient in message.to:
                try:
                    self.client.messages.create(
                        body=message.body,
                        from_=self.from_number,
                        to=recipient,
                    )
                    sent += 1
                except Exception:
                    if not self.fail_silently:
                        raise
        return sent
```

Then point `SMS_BACKEND` to your class:

```python
AUTH_KIT = {
    "SMS_BACKEND": "myapp.sms.TwilioSmsBackend",
}
```

## `BaseSmsBackend` Interface

| Method | Description |
|--------|-------------|
| `__init__(fail_silently=False, **kwargs)` | Constructor. Store any connection config here. |
| `open() -> bool \| None` | Open a network connection (optional). |
| `close() -> None` | Close the connection (optional). |
| `send_messages(messages) -> int` | Send a list of `SmsMessage` objects. Return the count sent. **Required.** |

### `SmsMessage`

```python
from django_auth_kit.otp.service import SmsMessage

message = SmsMessage(
    body="Your code is 123456",
    to=["+61400000000"],
)
```

The backend can also be used as a context manager:

```python
backend = TwilioSmsBackend()
with backend:
    backend.send_messages([message])
```
