"""Issue reviewer agent built with Strands harness.

Reads a GitHub issue, looks at the repo code (and fetches any URL the issue
references), and produces an analysis plus suggested labels. It never writes to
the repo: the built-in tools are pinned to read-only ones, so the only thing it
emits is text. A person approves the labels.

Run locally:
    ISSUE_TITLE="..." ISSUE_BODY="..." python agent.py
"""

import os

from strands_harness import create_harness

# 1. Pin the built-in tools to read-only ones. The harness ships with
#    shell, read, write, edit, web_fetch, web_search, programmatic_tool_caller
#    and subagent. A public event triggers this agent, so we drop everything
#    that could change the repo: it reads files and fetches pages, nothing
#    else. The agent proposes, a person decides.
#
#    Note on web_search: it is not a standalone tool, it switches on the
#    model provider's native web search. The default Bedrock model (Claude)
#    and Amazon Nova on Bedrock do not have one, so we leave it out and rely
#    on web_fetch (open a known URL), which works on any model. To search on
#    Bedrock anyway you would pass builtin_tools={"web_search": "exa"} and
#    bring in Exa, a third party. We keep this example dependency-free.
READ_ONLY_TOOLS = ["read", "web_fetch"]

# 2. Domain instructions appended to the system prompt. Kept short on purpose;
#    the model already knows how to read code.
INSTRUCTIONS = """
You are a triage assistant for an open-source repository. Given a new issue,
you:
  1. Read the relevant code in the current repository.
  2. If the issue references a URL (a doc or a related report), fetch it for
     context.
  3. Decide whether the issue is a bug, an idea/feature request, or a
     duplicate of something already reported.
  4. Write a short, friendly comment with your reasoning and a list of
     suggested labels (for example: bug, enhancement, duplicate, needs-info).

You never claim certainty you do not have. Suggested labels are suggestions;
a maintainer approves them. Answer in the language the issue is written in.
"""


def build_agent():
    """Return a ready-to-run issue reviewer agent."""
    # 3. One line gives us a full agent: loop, context management, memory,
    #    sessions. We run on the harness default: Amazon Bedrock with Claude.
    #    Swapping the model is a one-line change (model="bedrock/..."), and that
    #    is the honest caveat worth knowing: capabilities travel with the model.
    #    Native web search, for instance, comes from the provider, and neither
    #    the default Bedrock Claude nor Amazon Nova on Bedrock has one. The
    #    harness surfaces that instead of hiding it, which is why "one line" is
    #    not a black box.
    return create_harness(
        instructions=INSTRUCTIONS,
        builtin_tools=READ_ONLY_TOOLS,
    )


def review_issue(title: str, body: str) -> str:
    """Analyze one issue and return the agent's comment as plain text."""
    agent = build_agent()
    task = (
        f"A new issue was opened.\n\n"
        f"Title: {title}\n\n"
        f"Body:\n{body}\n\n"
        f"Review it following your instructions and write the comment."
    )
    result = agent(task)
    return str(result)


if __name__ == "__main__":
    comment = review_issue(
        title=os.environ.get("ISSUE_TITLE", ""),
        body=os.environ.get("ISSUE_BODY", ""),
    )
    print(comment)
