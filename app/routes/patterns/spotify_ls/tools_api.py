from langchain_core.utils.function_calling import convert_to_openai_function


def wrap_as_tool(function):
    # Use convert_to_openai_function to get the OpenAI Tool representation
    openai_function = convert_to_openai_function(function)

    # Wrap it in the desired structure
    return {"type": "function", "function": openai_function}
