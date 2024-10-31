class Prompts:
    REACT: str = """
    Answer the following questions as best you can.
    You have access to a number of tools, use them to get the answer to the question.

    Reply in the following format:

    Question: the input question you must answer
    Thought: you should always think about what to do. Is the information so far sufficient,
        or are more tool calls needed? ALWAYS start with a thought, NEVER just reply with a tool call.       
    Action: the action to take, such as breaking the problem into smaller parts, performing
        calculations, or calling one of the tools
    Tool output: the result of the tool call
    ... (this Thought/Action/Tool output can repeat N times)
    Thought: I now know the final answer
    Final Answer: Provide the final answer to the original question incorporating all content from previous cycles. Ensure text is formatted to 80 columns.

    Begin!
    """
