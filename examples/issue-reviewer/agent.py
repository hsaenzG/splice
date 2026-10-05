"""Issue reviewer agent built with Strands harness.

Reads a GitHub issue, looks at the repo code (and fetches any URL the issue
references), and produces an analysis plus suggested labels. It never writes to
the repo: the built-in tools are pinned to read-only ones, so the only thing it
emits is text. A person approves the labels.

Run locally:
    OPENAI_API_KEY="..." ISSUE_TITLE="..." ISSUE_BODY="..." python agent.py
"""

import os

from strands_harness import create_harness

# 1. Pin the built-in tools to read-only ones. The harness ships with
#    shell, read, write, edit, web_fetch, web_search, programmatic_tool_caller
#    and subagent, all on by default. A public event triggers this agent, so we
#    drop everything that could change the repo: it reads files, fetches pages,
#    and searches the web, nothing else. The agent proposes, a person decides.
#
#    web_search here is the harness's native web search: it is not a standalone
#    tool, it switches on the model provider's own search. It works on OpenAI,
#    Anthropic, and Google, so because we run on OpenAI (below) we can keep it.
#    On Amazon Bedrock the available models (Claude, Nova) do not expose a
#    native search, so there you would drop web_search and rely on web_fetch
#    (open a known URL) instead. Capabilities travel with the provider.
READ_ONLY_TOOLS = ["read", "web_fetch", "web_search"]

# 2. Domain instructions appended to the system prompt. Kept short on purpose;
#    the model already knows how to read code.
INSTRUCTIONS = """
You are a triage assistant for an open-source repository. Given a new issue,
you:
  1. Read only the few files directly relevant to the issue. Do not survey the
     whole repository; a handful of targeted reads is enough.
  2. If the issue references a URL, fetch it at most once for context. Do not
     re-fetch a page you have already read.
  3. Decide whether the issue is a bug, an idea/feature request, or a
     duplicate of something already reported.
  4. Write a short, friendly comment with your reasoning and a list of
     suggested labels (for example: bug, enhancement, duplicate, needs-info).

Be decisive: once you have enough to form a view, stop investigating and write
the comment. You never claim certainty you do not have. Suggested labels are
suggestions; a maintainer approves them. Answer in the language the issue is
written in.
"""


def build_agent():
    """Return a ready-to-run issue reviewer agent."""
    # 3. One line gives us a full agent: loop, context management, memory,
    #    sessions. We pick OpenAI with a single model argument so the native
    #    web_search tool above actually works. The harness takes the key from
    #    OPENAI_API_KEY in the environment. effort="medium" is enough for triage
    #    and converges in a handful of tool calls; "high" reasons harder but
    #    tends to over-investigate (reading far more of the repo than needed).
    #
    #    Swapping the model is a one-line change (model="bedrock/..." for the
    #    AWS default, "anthropic/..." or "google/..." for those providers). That
    #    is the honest caveat worth knowing: capabilities travel with the model.
    #    Native web search comes from the provider, so on a Bedrock model you
    #    would drop web_search from the tool list. The harness surfaces that
    #    instead of hiding it, which is why "one line" is not a black box.
    return create_harness(
        model="openai/gpt-5.6-sol",
        effort="medium",
        instructions=INSTRUCTIONS,
        builtin_tools=READ_ONLY_TOOLS,
        # Suppress the default streaming handler. It prints every tool call and
        # the streamed answer to stdout, which is handy in a terminal but wrong
        # for CI: the workflow does `agent.py > comment.md`, so that noise (and
        # a duplicated final answer) would end up in the posted comment. With
        # the handler off, stdout carries only our own print(comment) below.
        callback_handler=None,
    )


def review_issue(title: str, body: str) -> str:
    """Analyze one issue and return the agent's comment as plain text."""
    # Guard against an empty task. With no title and no body there is nothing
    # to review, and an autonomous agent handed an empty goal will wander,
    # reading the repo and searching the web looking for an issue that isn't
    # there. Fail fast with a clear message instead.
    if not title.strip() and not body.strip():
        raise ValueError(
            "No issue to review: both ISSUE_TITLE and ISSUE_BODY are empty. "
            "Set them in the environment (see .env.example) or pass them inline."
        )

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
