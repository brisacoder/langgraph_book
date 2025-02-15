class Prompts:
    REACT = """
Answer the following question as best as you can.

If you receive feedback, always add the new content to your
latest answer without removing or altering any accurate information from your
current response. **Under no circumstances should you remove or modify accurate
content from your existing answer.** Instead, incorporate the feedback by
expanding your answer, ensuring that all relevant details are included without
summarizing or omitting any correct information.

Think carefully about how to approach the problem step by step.

Respond in the following format:

Question: The input question you must answer.
Thought: Begin by considering what the question is asking. Is the information sufficient, or do you need clarifications?
     Always start with a thought; never jump straight to the final answer.
Action: Describe the steps you will take to solve the problem, such as breaking it down into smaller parts, performing
     calculations, or exploring different possibilities.

(This Thought/Action cycle can repeat as needed)

Thought: I know the final answer
Final Answer: Provide the final answer to the original question incorporating all content from previous cycles. 
     Ensure text is formatted to 80 columns.

Begin!
"""
