class Prompts:
    COT = """
Your task is to create a Chain-of-Thought (CoT) prompt designed to guide someone
through solving the question by breaking it down into logical steps. You should not
solve the question itself. Instead, develop a clear CoT prompt template with a
few example problems and their respective step-by-step reasoning. These examples
should be similar in nature to the target problem, showcasing the expected
thought process without providing direct answers to the target question.

Instructions:

1. Problem Context: Begin by summarizing the type of problem to provide context
   (e.g., arithmetic reasoning, logic puzzles, etc.).

2. Prompt Template: Construct a prompt that encourages a step-by-step approach.
   Use guiding questions and cues to foster logical thinking and intermediate
   conclusions that support reaching the final answer.

3. Few-Shot Examples:
   - Select a few similar problems to demonstrate the Chain-of-Thought process.
   - For each example, illustrate the solution process with a breakdown of
     steps, ensuring each step builds logically toward a solution.
   - Do not solve the main problem; only provide examples as references for the
     reasoning process.

4. Clarity and Structure: Make each example concise but thorough, with each
   reasoning step clearly separated to maintain focus and encourage systematic
   thinking.

5. Final Reminder: Conclude the prompt by emphasizing the importance of applying
   the Chain-of-Thought reasoning observed in the examples to approach the main
   problem.

Begin!

"""
