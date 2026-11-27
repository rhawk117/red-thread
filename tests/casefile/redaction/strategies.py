"""Planted secrets: one strategy per pattern family, each with the text the scrubber must leave."""

from dataclasses import dataclass

from hypothesis import strategies as st

BODY = r'[A-Za-z0-9+/=\n]{0,120}'
ASSIGNMENT_KEYS = ('password', 'api_key', 'secret', 'token', 'DB_PASSWORD')
ASSIGNMENT_SEPARATORS = ('=', ': ', ' = ')


@dataclass(slots=True, kw_only=True, frozen=True)
class Planted:
    family: str
    whole: str
    redacted: str


@dataclass(slots=True, kw_only=True, frozen=True)
class Family:
    name: str
    planted: st.SearchStrategy[Planted]


def plant(family: str, secret: str) -> Planted:
    return Planted(family=family, whole=secret, redacted=f'[REDACTED:{family}]')


def plant_private_key(body: str) -> Planted:
    begin = '-----BEGIN RSA PRIVATE KEY-----'
    end = '-----END RSA PRIVATE KEY-----'
    return plant('private-key', f'{begin}\n{body}\n{end}')


def plant_url_credentials(user: str, password: str) -> Planted:
    return Planted(
        family='basic-auth-credentials',
        whole=f'https://{user}:{password}@host.example/path',
        redacted=f'https://{user}:[REDACTED:basic-auth-credentials]@host.example/path',
    )


def plant_assignment(key: str, separator: str, value: str) -> Planted:
    return Planted(
        family='secret-keyword',
        whole=f'{key}{separator}{value}',
        redacted=f'{key}{separator}[REDACTED:secret-keyword]',
    )


def plant_bearer(token: str) -> Planted:
    return Planted(
        family='bearer-token',
        whole=f'Bearer {token}',
        redacted='Bearer [REDACTED:bearer-token]',
    )


def match_family(family: str, pattern: str) -> Family:
    secrets = st.from_regex(pattern, fullmatch=True)
    return Family(name=family, planted=st.builds(plant, st.just(family), secrets))


FAMILIES = (
    Family(
        name='private-key',
        planted=st.builds(plant_private_key, st.from_regex(BODY, fullmatch=True)),
    ),
    match_family('aws-access-key', r'(AKIA|ASIA)[0-9A-Z]{16}'),
    match_family('github-token', r'gh[pousr]_[A-Za-z0-9]{36,50}'),
    match_family('slack-token', r'xox[abposr]-[0-9]{10,13}-[a-z0-9]{10,30}'),
    match_family('stripe-access-key', r'[rs]k_(live|test)_[A-Za-z0-9]{16,30}'),
    match_family('api-key', r'sk-(ant-)?[A-Za-z0-9_-]{20,40}'),
    match_family(
        'json-web-token', r'eyJ[A-Za-z0-9_-]{4,20}\.[A-Za-z0-9_-]{4,20}\.[A-Za-z0-9_-]{4,20}'
    ),
    Family(
        name='bearer-token',
        planted=st.builds(plant_bearer, st.from_regex(r'[A-Za-z0-9._~+/-]{12,30}', fullmatch=True)),
    ),
    Family(
        name='basic-auth-credentials',
        planted=st.builds(
            plant_url_credentials,
            st.from_regex(r'[A-Za-z0-9._~-]{1,12}', fullmatch=True),
            st.from_regex(r'[A-Za-z0-9!$%^&*()_+=-]{1,16}', fullmatch=True),
        ),
    ),
    Family(
        name='secret-keyword',
        planted=st.builds(
            plant_assignment,
            st.sampled_from(ASSIGNMENT_KEYS),
            st.sampled_from(ASSIGNMENT_SEPARATORS),
            st.from_regex(r'[A-Za-z]{6,20}', fullmatch=True),
        ),
    ),
)
planted_secrets = st.one_of(*(family.planted for family in FAMILIES))
