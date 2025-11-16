# Shoply support bot

A small console-level support assistant for the fictional store Shoply.
Scope is intentionally narrow: load internal data, perform minimal retrieval,
and delegate short answers to an LLM with strict constraints.

## Problem statement

The required functionality:

- Maintain multi-turn dialog (short memory window).
- Retrieve FAQ entries from a local JSON file.
- Handle `/order <id>` and expose order status from a structured JSON dataset.
- Log every session as structured JSONL, including token usage.
- Enforce concise, factual, non-hallucinatory answers.

The assignment _does not target production LLM patterns_ (like vector DB,
embeddings, chunking). The goal is a small, auditable RAG toy.

## Implementation notes

Core design principles:

- **Retrieval before generation**. FAQ answers are not selected via exact string
  match. A minimal lexical overlap matcher extracts the top FAQ candidates; only
  they are added to the model context.

- **Order data injected into model context.** Implementation of `/order` returns
  a human-readable summary and stores a structured context block so follow-up
  questions reference the same order without reconstruction.

- **LLM wrapper is isolated.** The model call is a thin, mockable layer; tests
  do not depend on API availability.

- **Session state is explicit.** History, last order context, and usage totals
  are kept in a single state object with deterministic truncation rules.

## Interaction model

1. User inputs free-form text or `/order <id>`.
2. System evaluates:

   - retrieval: top-K FAQ matches,
   - session: whether an order context is active.

3. A combined context block is passed to the LLM:

   - system prompt (policy),
   - extracted FAQ snippets,
   - active order summary (optional),
   - clipped message history.

4. The LLM produces a short, bounded reply.
5. Logs append:

   - role,
   - message content,
   - token usage,
   - optional metadata (`source: faq|orders`).

The dialog loop remains deterministic: no hidden state, no implicit memory.

## Failure model

The system prefers clarity and observability over silent fallback behavior.
Expected degradations and handling:

- **FAQ miss** -> retrieval returns empty -> LLM receives instruction to admit
  insufficient information. No hallucinations, no guessing.

- **Unknown order** -> `/order` returns a controlled error message; order 
  context is cleared.

- **Context window overflow** -> history is trimmed to a fixed window; old
  interactions are discarded intentionally.

- **OpenAI API unavailable** -> bot remains operational for `/order`, but cannot
  answer free-form questions; the failure is explicit in the output and logged.

- **Corrupted JSON data** -> loading failure stops startup early; no partial run
  with inconsistent FAQ/orders.
