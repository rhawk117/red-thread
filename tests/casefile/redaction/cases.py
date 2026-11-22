"""Scenarios for secret redaction."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from _pytest.mark import ParameterSet
    from red_thread_casefile.redaction import PatternName

PRIVATE_KEY = (
    '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAx3f9\nabcdefghijklmnop\n'
    '-----END RSA PRIVATE KEY-----'
)


@dataclass(slots=True, kw_only=True, frozen=True)
class SecretCase:
    name: str
    text: str
    leaked: str
    pattern: PatternName

    @property
    def param(self) -> ParameterSet:
        return pytest.param(self, id=self.name)


def secret_params() -> list[ParameterSet]:
    cases = [
        SecretCase(
            name='aws-access-key',
            text='key AKIAIOSFODNN7EXAMPLE in use',
            leaked='AKIAIOSFODNN7EXAMPLE',
            pattern='aws-key',
        ),
        SecretCase(
            name='github-token',
            text='token ghp_' + 'a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8' + ' pasted',
            leaked='ghp_a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8',
            pattern='github-token',
        ),
        SecretCase(
            name='slack-token',
            text='hook xoxb-1234567890-abcdefghij sent',
            leaked='xoxb-1234567890-abcdefghij',
            pattern='slack-token',
        ),
        SecretCase(
            name='stripe-key',
            text='billing sk_live_abcdefghijklmnop1234 charged',
            leaked='sk_live_abcdefghijklmnop1234',
            pattern='stripe-key',
        ),
        SecretCase(
            name='api-key',
            text='client sk-ant-abcdefghijklmnopqrstuvwx called',
            leaked='sk-ant-abcdefghijklmnopqrstuvwx',
            pattern='api-key',
        ),
        SecretCase(
            name='jwt',
            text='session eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJl expired',
            leaked='eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJl',
            pattern='jwt',
        ),
        SecretCase(
            name='bearer-header',
            text='sent Bearer abcdefghijklmnop1234 upstream',
            leaked='abcdefghijklmnop1234',
            pattern='bearer',
        ),
        SecretCase(
            name='url-credentials',
            text='dsn postgres://admin:hunter2pass@db.internal/app',
            leaked='admin:hunter2pass',
            pattern='url-credentials',
        ),
        SecretCase(
            name='password-assignment',
            text='set password=correcthorsebattery now',
            leaked='correcthorsebattery',
            pattern='assignment',
        ),
        SecretCase(
            name='quoted-secret-assignment',
            text='CLIENT_SECRET: "s3cr3tValue99"',
            leaked='s3cr3tValue99',
            pattern='assignment',
        ),
        SecretCase(
            name='api-key-assignment',
            text='api_key = "abcd1234efgh"',
            leaked='abcd1234efgh',
            pattern='assignment',
        ),
        SecretCase(
            name='private-key-block',
            text=f'found {PRIVATE_KEY} in the repo',
            leaked='MIIEowIBAAKCAQEAx3f9',
            pattern='private-key',
        ),
    ]
    return [case.param for case in cases]


def ordinary_text_params() -> list[ParameterSet]:
    texts = {
        'max-tokens-assignment': 'max_tokens=4096',
        'max-tokens-with-colon': 'max_tokens: 4096',
        'max-tokens-in-a-sentence': 'the call sets max_tokens=4096 and retries',
        'token-count': 'token_count = 12',
        'timeout': 'timeout=30 seconds',
        'path-cite': 'see src/auth/session.py:42 for the check',
        'word-secret-in-prose': 'the secret to the fix is a lock',
        'prose-about-keys': 'rows are sorted by key before the merge',
        'git-sha': 'at commit 1111111111111111111111111111111111111111',
        'plain-url': 'https://example.invalid/docs/retries#backoff',
        'url-with-port': 'http://localhost:8080/health',
    }
    return [pytest.param(text, id=name) for name, text in texts.items()]
