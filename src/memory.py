MAX_TURNS = 5

class ConversationMemory:
    """
    Manages a sliding window conversation buffer for multi-turn chat interactions.
    """
    def __init__(self, max_turns: int = MAX_TURNS):
        self.max_turns = max_turns
        self.turns = []

    def add_turn(self, question: str, tool: str, answer: str):
        """
        Records a completed conversational turn.

        Args:
            question (str): The user's input question.
            tool (str): The pipeline route that handled the turn ("sql", "reviews", or "both").
            answer (str): The synthesized response provided by the bot.
        """
        self.turns.append({
            "question": question,
            "tool": tool,
            "answer": answer,
        })

        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

    def get_recent_turns(self):
        """
        Retrieves the current conversation buffer.

        Returns:
            list[dict]: A copy of the recent turns, oldest first.
        """
        return self.turns.copy()

    def format_for_prompt(self) -> str:
        """
        Formats the recent turns into a plain-text block for prompt injection.

        Returns:
            str: The formatted conversation history, or an empty string if none exists.
        """
        if not self.turns:
            return ""

        lines = []
        for turn in self.turns:
            lines.append(f"Q: {turn['question']}")
            lines.append(f"A: {turn['answer']}")
            lines.append("")

        return "\n".join(lines)

    def clear(self):
        """
        Clears the conversation buffer.
        """
        self.turns = []