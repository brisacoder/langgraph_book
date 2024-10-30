class Prompts:
    REACT = """
Answer the following question as best as you can.

Think carefully about how to approach the problem step by step.

Respond in the following format:

Question: The input question you must answer.
Thought: Begin by considering what the question is asking. Is the information sufficient, or do you need clarifications?
     Always start with a thought; never jump straight to the final answer.
Action: Describe the steps you will take to solve the problem, such as breaking it down into smaller parts, performing
     calculations, or exploring different possibilities.

(This Thought/Action cycle can repeat as needed)

Thought: Conclude your reasoning and ensure you have arrived at a solution.
Final Answer: Provide the final answer to the original question, incorporating all suggestions and reasoning from the
     previous steps. Ensure that the final answer is formatted so that each line does not exceed 80 characters.

Begin!

Question: {input}}
"""
