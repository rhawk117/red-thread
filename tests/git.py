"""The git settings every test repository runs with: a fixed identity, no signing and no hooks."""

GIT_SETTINGS = (
    '-c',
    'user.name=test',
    '-c',
    'user.email=test@example.invalid',
    '-c',
    'commit.gpgsign=false',
    '-c',
    'core.hooksPath=/dev/null',
)
