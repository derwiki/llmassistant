import os
import re
import traceback

import openai


def query(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model='gpt-4', messages=[{"role": "user", "content": prompt}], temperature=0
    )
    return response.choices[0].message.content.strip()


PROMPT_TEMPLATE = """You are my coding assistant. Write clear, concise and well-typed Python code for me.

{prompt}"""

UNIT_TEST_TEMPLATE = """You are my coding testing assistant. Write unit tests in pytest that verify this function works:

# Code start
{code}
# Code end

The function is already in the current namespace; you don't need to import it.
The original prompt for this question was:
{prompt}
"""

EXCEPTION_IN_CODE_PROMPT = f"""The last code you generated:

{code}

resulted in this exception:
{exception_msg}.

Please try again."""


def extract_python(s: str) -> str:
    match = re.search(r"```python(.*?)```", s, re.DOTALL)
    return match.group(1).strip() if match else None


def try_in_loop(prompt):
    retries = 3
    while retries:
        try:
            print(prompt)
            prompt_response = query(PROMPT_TEMPLATE.format(prompt=prompt))
            code = extract_python(prompt_response)

            yield code

            return code
        except Exception as e:
            exception_msg = f"Exception {type(e)}: {e}\n{traceback.format_exc()}"
            print(exception_msg)
            prompt += f"""The last code you generated:
            
{code}

resulted in this exception:
{exception_msg}.

Please try again."""
            retries -= 1


if __name__ == "__main__":
    prompt = os.getenv("PROMPT")

    retries = 4
    while retries:
        try:
            print(prompt)
            prompt_response = query(PROMPT_TEMPLATE.format(prompt=prompt))
            code = extract_python(prompt_response)
            print(code)
            context = {}
            print("Compiling...")
            exec(code, context)
            new_fun = context[list(context.keys())[-1]]
            print("Running...")
            new_fun_result = new_fun()
            print(f"new_fun_result: {new_fun_result}")
            print(f"Program compiles and runs 🎉")
            break
        except Exception as e:
            exception_msg = f"Exception {type(e)}: {e}\n{traceback.format_exc()}"
            print(exception_msg)
            prompt += EXCEPTION_IN_CODE_PROMPT.format(code=code, exception_msg=exception_msg)
            retries -= 1

    retries = 4

    while retries:
        try:
            print(prompt)
            prompt_response = query(UNIT_TEST_TEMPLATE.format(prompt=prompt, code=code))
            unit_test_code = extract_python(prompt_response)
            print(unit_test_code)
            print("Running...")
            exec(unit_test_code, context)
            print(f"Program compiles 🎉")
            unit_test_fun = context[list(context.keys())[-1]]
            unit_test_fun_result = unit_test_fun()
            print(f"Program runs 🎉")
            break
        except Exception as e:
            exception_msg = f"Exception {type(e)}: {e}\n{traceback.format_exc()}"
            print(exception_msg)
            prompt += EXCEPTION_IN_CODE_PROMPT.format(code=code, exception_msg=exception_msg)
            retries -= 1

    with open("generated.py", "w+") as f:
        print("### code ###")
        print(code)
        f.write(f"{code}\n")
        print("### unit test ###")
        print(unit_test_code)
        f.write(f"{unit_test_code}\n")

