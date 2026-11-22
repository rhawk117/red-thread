# Security Policy

This repository distributes a Claude Code plugin. Its components can influence agent behavior, run local commands, read and write files, and start external tools. Review plugin updates and executable components before you enable them in a sensitive environment.

## Supported versions

Security fixes go to the latest published release and the `main` branch. Older releases may not get backports. If you find an issue in an older release, report it with the affected version so maintainers can assess its impact.

| Version | Receives security fixes |
| --- | --- |
| `main` | Yes |
| Latest published release | Yes |
| Older releases | Not guaranteed |

## Reporting a vulnerability

> [!IMPORTANT]
> Report vulnerabilities privately. Do not put exploit details, credentials or sensitive files in a public issue or pull request.

1. Open the repository's **Security** tab and select **Report a vulnerability**, if private vulnerability reporting is enabled.
2. Describe the affected release or commit, the plugin component, any prerequisites, the steps to reproduce and the potential impact. Add a minimal proof of concept when it helps, with all secrets removed.
3. If private reporting is unavailable, open a public issue that asks for a private security contact channel and nothing else. Leave the vulnerability details out of it.

Maintainers will assess reports, coordinate a fix, and decide whether a GitHub Security Advisory or release notice is appropriate. Timing depends on severity, reproducibility and maintainer availability. No fixed service-level agreement is implied.

## What to report

Reports are most useful when they involve one of these areas.

| Area | Examples |
| --- | --- |
| Hooks and executables | Unsafe subprocess execution, command injection, unexpected side effects, access outside intended paths |
| Skills, commands, agents and workflows | Instructions that lead to unsafe tool use, disclose sensitive data or bypass expected user approval |
| Case files and published pages | A secret that reaches a case file or a page unredacted, a citation check that reads outside the repository, a page that loads a script without an integrity hash |
| Plugin manifests and configuration | Unsafe defaults, path traversal, unintended component loading, insecure handling of environment variables |
| Dependencies and releases | Compromised packages, vulnerable transitive dependencies, tampered artifacts, weaknesses in CI and release automation |

## Automated security checks

The repository uses PySentry to audit Python dependency metadata and resolved dependencies. Scanner policy, including failure thresholds and advisory sources, lives in `pyproject.toml`. uv installs the scanner through the `security` dependency group.

| Check | Workflow | Behavior |
| --- | --- | --- |
| Dependency audit in CI | `.github/actions/pysentry`, run by the quality job in `.github/workflows/ci.yml` before any dependency is installed | A composite action that checks dependencies. A successful result can be reused from a cache keyed to dependency metadata and an ISO-week window. |
| Scheduled audit | `.github/workflows/weekly-security-scan.yml` | Runs weekly and forces a fresh scan whether or not dependencies changed. It can also be started manually. |

What happens with the results:

- SARIF reports go to GitHub Code Scanning where repository permissions and features allow it.
- Scheduled runs also keep a report artifact when one is produced.
- A failing scheduled audit creates or updates a GitHub issue with an audit summary and any available findings. A later successful audit closes the open tracking issue.

> [!NOTE]
> An audit can fail for reasons other than a known vulnerability, such as a scanner or infrastructure error. A missing SARIF report does not mean the repository passed its security checks.

### Limitations

These checks find issues covered by their advisory sources and configured policies. They do not show that the plugin, its dependencies or its releases are free of malicious behavior. Dependency auditing in particular does not reliably detect prompt injection, unsafe agent instructions, malicious hooks, compromised MCP servers, secret exfiltration or undisclosed vulnerabilities.

> [!WARNING]
> Automated tracking issues are public, so they are not a disclosure channel. If a finding involves an unreported exploitable weakness or sensitive data, report it privately and keep the extra details out of the issue.

## What the plugin's hooks do

The plugin ships one hook. `hooks/hooks.json` runs `hooks/roster.py` before every Agent tool call. The script reads the call and prints a decision. It refuses a dispatch only when a red-thread agent dispatches another red-thread agent outside its roster: a lead may dispatch the four scouts, and a scout or the skeptic dispatches nobody. A dispatch whose caller or target is not a red-thread agent is left alone. When the hook cannot read its input, or cannot run at all, the dispatch goes ahead. It is not a permission control: it does not run or approve commands, and it does not replace the permission prompts of Claude Code.

## Local working state

A case's working files live in `.red-thread/<case-id>/` at the root of the repository under investigation: the case record, the ledger, the thread files, the rendered board and the exported outputs. Entries quote lines of code and command output, and either can hold a secret. The case-file script redacts the secret patterns it knows from every free-text field before it stores an entry, which lowers that risk and does not remove it. When a case is created, the script adds `.red-thread/` to git's local exclude file (`info/exclude`), so the directory stays out of git without a commit, and a careless `git add -A` cannot ship it. Never commit it or move the exclusion into a tracked `.gitignore`.

A case stays on the machine unless its owner chooses at framing to publish it. A published case is a private page on claude.ai that holds what the board holds, and comments on that page are read back into the case as entries. The page, local or published, loads its stylesheet build and its diagram library from cdnjs at pinned versions with integrity hashes.

## Guidance for users

- Install updates from trusted repository releases, and review changes to hooks, scripts, executables and external-tool configuration.
- Run the plugin with the fewest privileges it needs. Don't give agent processes broad access to credentials, production infrastructure or unrelated files.
- Review requests to run commands, especially when they come from untrusted content.
- Keep dependencies and the plugin current, and look into security advisories for the version you have installed.

Security tooling reduces exposure. It does not replace reviewing what executable plugin behavior does and which permissions it holds.
