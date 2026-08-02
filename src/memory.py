"""
memory.py
---------
Phase 5.5a: a tiny conversation buffer -- keeps the last N turns
(question, tool used, answer) so follow-up questions like "what about
payment type?" can be understood without the user re-stating context.

Deliberately NOT a database, NOT LangGraph, NOT an external service --
just a plain Python list, capped at a fixed size. This matches Hard
Rule 3 (no autonomous multi-tool orchestration machinery) and PROJECT.md
9b's explicit call: "a plain Python list for conversation memory."

One ConversationMemory object = one conversation. In chat_cli.py
(Phase 8), a single instance of this class will be created when the
terminal loop starts, and live for the whole session.
"""

# How many past turns to keep. Older turns are dropped once this cap
# is hit -- deliberately small, since every turn kept here gets pasted
# into every future prompt, and prompts aren't free (cost + speed).
MAX_TURNS = 5


class ConversationMemory:
    def __init__(self, max_turns: int = MAX_TURNS):
        self.max_turns = max_turns

        # Each entry will be a dict: {"question": ..., "tool": ..., "answer": ...}
        # A plain list, oldest turn at index 0, newest at the end --
        # matches how a conversation actually unfolds in time.
        self.turns = []

    def add_turn(self, question: str, tool: str, answer: str):
        """
        Call this once per completed turn, AFTER an answer has been
        produced -- e.g. right after answer_synth.py returns its
        plain-English sentence, in the future full pipeline.

        tool: which pipeline handled this turn -- "sql", "reviews", or
        "both" (set later by orchestrator.py in Phase 5.5b). For now,
        while only the SQL tool exists, this will always be "sql".
        """
        self.turns.append({
            "question": question,
            "tool": tool,
            "answer": answer,
        })

        # If we've gone over the cap, drop the OLDEST turn (index 0).
        # This keeps the buffer's size fixed no matter how long the
        # conversation runs -- a sliding window, not an ever-growing log.
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

    def get_recent_turns(self):
        """
        Returns the current buffer as-is -- a list of dicts, oldest
        first. prompt_builder.py will call this and format it into
        the prompt later; this class doesn't know or care about
        prompt formatting, only about storing and trimming turns.
        """
        return self.turns.copy()

    def format_for_prompt(self):
        """
        Turns the buffer into a plain text block ready to paste
        straight into a prompt, e.g.:

            Q: Which state has the most orders?
            A: São Paulo (SP) has the most orders.

            Q: What about payment type?
            A: ...

        Returns an empty string if there's no history yet -- so the
        very first question in a session doesn't get a pointless
        empty "RECENT CONVERSATION" section glued onto its prompt.
        """
        if not self.turns:
            return ""

        lines = []
        for turn in self.turns:
            lines.append(f"Q: {turn['question']}")
            lines.append(f"A: {turn['answer']}")
            lines.append("")  # blank line between turns, easier to read

        return "\n".join(lines)

    def clear(self):
        """
        Wipes the buffer -- e.g. if chat_cli.py later adds a way to
        start a fresh conversation without restarting the whole program.
        Not used anywhere yet, but a one-line method worth having now
        rather than bolting it on awkwardly later.
        """
        self.turns = []