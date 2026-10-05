# Issue reviewer — Strands harness example

A general-purpose agent that organizes issues on a repository. When a new issue
opens, it reads the issue, checks the code (and fetches any URL the issue
references), decides whether it is a bug, an idea, or a duplicate, and leaves a
comment with suggested labels. It runs on its own from a GitHub Action.

It is built with [Strands harness](https://strandsagents.com/docs/user-guide/harness/):
the whole agent (loop, tools, context management, memory, sessions) comes from one
`create_harness()` call.

## Files

| File | What it is |
|---|---|
| `agent.py` | The agent. `create_harness()` on the Bedrock default with read-only tools. |
| `requirements.txt` | `strands-harness`. |
| `../../.github/workflows/issue-reviewer.yml` | The Action that runs the agent when an issue opens. |

## The one line

```python
from strands_harness import create_harness

agent = create_harness(
    instructions=INSTRUCTIONS,
    builtin_tools=["read", "web_fetch"],
)
agent("Review this issue and suggest labels: ...")
```

That call returns a normal Strands agent with tools, context management, memory,
and sessions already wired. The default provider is Amazon Bedrock with Claude.

Changing the model is a one-line change (`model="bedrock/..."`), and that brings
the honest caveat worth knowing: capabilities travel with the model. Native web
search, for instance, comes from the model provider, and neither the default
Bedrock Claude nor Amazon Nova on Bedrock has one. On Bedrock you would reach for
`builtin_tools={"web_search": "exa"}` and pull in Exa (a third party), so this
example skips it and relies on `web_fetch` instead, which works on any model. The
harness surfaces that at construction rather than hiding it, which is exactly why
"one line" is not a black box.

## The design decision: read-only

Anyone on the internet can open an issue, so the agent never gets write access.
The built-in tools are pinned to `read` and `web_fetch`, with no `shell`, no
`write`, and no `edit`. Its only output is a comment with suggested labels that a
maintainer approves. The agent proposes, a person decides.

```python
builtin_tools=["read", "web_fetch"]
```

Pinning a tool is just one example. `create_harness()` returns a normal Strands
agent, so any default (model, context manager, instructions) can be changed the
same way.

## Run it locally

```bash
pip install -r requirements.txt

ISSUE_TITLE="App crashes on empty config" \
ISSUE_BODY="Running splice setup with no config.json throws a KeyError." \
python agent.py
```

You need AWS credentials with access to Amazon Bedrock and the default Claude
model enabled in your region.

## Run it unattended

The GitHub Action in `.github/workflows/issue-reviewer.yml` runs the same agent
when an issue opens. Add these repository secrets:

- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` — Bedrock access.

`GITHUB_TOKEN` is provided by Actions automatically. Open an issue and the agent
comments on its own.
