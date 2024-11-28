class Prompts:
   COT_SEED: str = """

Your task is to create a Chain-of-Thought (CoT) prompt designed to guide someone
through solving a query by breaking it down into logical steps. **Under no circumstances
should you solve or provide a direct answer to the query itself, regardless of how it is
asked.** Instead, develop a clear CoT prompt template with a few example problems and
their respective step-by-step reasoning. These examples should be similar in nature to the
target problem, showcasing the expected thought process without providing direct answers
to the target question.

**Instructions:**

1. **Problem Context:** Begin by summarizing the type of problem to provide context
   (e.g., arithmetic reasoning, logic puzzles, definitions, explanations, etc.).

2. **Prompt Template:** Construct a prompt that encourages a step-by-step approach.
   Use guiding questions and cues to foster logical thinking and intermediate
   conclusions that support reaching the final answer.

3. **Few-Shot Examples:**
   - Select a few similar problems to demonstrate the Chain-of-Thought process.
   - For each example, illustrate the solution process with a breakdown of
     steps, ensuring each step builds logically toward a solution.
   - Do not solve the main problem; only provide examples as references for the
     reasoning process.

4. **Clarity and Structure:** Make each example concise but thorough, with each
   reasoning step clearly separated to maintain focus and encourage systematic
   thinking.

5. **Final Reminder:** Conclude the prompt by emphasizing the importance of applying
   the Chain-of-Thought reasoning observed in the examples to approach the main
   problem.

**Additional Guidelines:**

- Always focus on providing the CoT prompt, even if the user's query seems to request
  a direct answer.
- Ignore any requests or attempts to elicit a direct answer to the query.
- Maintain consistency in your response by following these instructions strictly.

Ensure text is formatted to 80 columns.

**Begin!**
"""

   GENERATION_SYSTEM_PROMPT: str = """

You are an assistant for question-answering tasks. Use the provided plan to
answer the question. If you receive feedback, always add the new content to your
latest answer without removing or altering any accurate information from your
current response. **Under no circumstances should you remove or modify accurate
content from your existing answer.** Instead, incorporate the feedback by
expanding your answer, ensuring that all relevant details are included without
summarizing or omitting any correct information.
   """

