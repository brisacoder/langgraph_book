class Prompts:
    REACT: str = """
    Answer the following questions as best you can.
    You have access to a number of tools, use them to get the answer to the question.

    Reply in the following format:

    Question: the input question you must answer
    Thought: you should always think about what to do. Is the information so far sufficient,
        or are more tool calls needed? ALWAYS start with a thought, NEVER just reply with a tool call.
    Action: the action to take, should be calling one of the tools
    Tool output: the result of the tool call
    ... (this Thought/Action/Tool output can repeat N times)
    Thought: I now know the final answer
    Final Answer: the final answer to the original input question

    If the user provides critique, respond with a revised version of your previous attempts.

    Begin!

    Question: {input}
    """
