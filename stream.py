import os
import re
import traceback
import subprocess

import openai

MODEL = os.getenv("MODEL")


def streaming_query(prompt: str, temperature=0.01) -> str:
    buffer = ''
    response = openai.ChatCompletion.create(
        model='gpt-4', messages=[{"role": "user", "content": prompt}], temperature=temperature, stream=True
    )
    for message in response:
        chunk = message.choices[0].get("delta", {}).get('content', "")
        print(chunk, end="")
        buffer += chunk
    return buffer


PROMPT_TEMPLATE = """You are my coding assistant. Write clear & concise Python code for me.

Function definitions should contain typing information.
Create a local variable test_input and assign it a value from the Python code you wrote.

{prompt}"""

UNIT_TEST_TEMPLATE = """You are my coding testing assistant. Write unit tests in pytest that verify this function works:

# Code start
{code}
# Code end

The function is already in the current namespace; you don't need to import it.
The original prompt for this question was:
{prompt}
"""

EXCEPTION_IN_CODE_PROMPT = """The last code you generated:

{code}

resulted in this exception:
{exception_msg}.

Try your best to explain what went wrong, how you can address it, and then please generate the code again."""


def extract_python(s: str) -> str:
    match = re.search(r"```python(.*?)```", s, re.DOTALL)
    return match.group(1).strip() if match else None


if __name__ == "__main__":
    prompt = os.getenv("PROMPT")

    retries = 4
    code = ""
    while retries:
        try:
            print(prompt)
            prompt_response = streaming_query(PROMPT_TEMPLATE.format(prompt=prompt))
            code = extract_python(prompt_response)
            print(code)
            context = {}
            print("Compiling...")
            exec(code, context)
            new_fun = context[list(context.keys())[-1]]
            # how to get the arity right?
            print(f"Program compiles and runs 🎉")
            break
        except Exception as e:
            exception_msg = f"Exception {type(e)}: {e}\n{traceback.format_exc()}"
            print(exception_msg)
            prompt += EXCEPTION_IN_CODE_PROMPT.format(code=code, exception_msg=exception_msg)
            retries -= 1

    retries = 10
    # TODO make sure it doesn't get stuck in a loop
    temperature = 0.01
    while retries:
        try:
            print(prompt)
            prompt_response = streaming_query(UNIT_TEST_TEMPLATE.format(prompt=prompt, code=code))
            unit_test_code = extract_python(prompt_response)
            print(unit_test_code)
            print("Running...")
            exec(unit_test_code, context)
            print("Program compiles 🎉")
            print(f"test_input: {context.get('test_input')}")
            result = subprocess.run(["python", "-m", "pytest", "generated.py"], capture_output=True, text=True)
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            if result.returncode != 0:
                raise RuntimeError(f"Running pytest resulted in these test failures:\n{result.stdout}\n{result.stderr}")
            # Print the stdout and stderr
            print(f"Program runs 🎉")
            break
        except Exception as e:
            exception_msg = f"Exception {type(e)}: {e}\n{traceback.format_exc()}"
            print(exception_msg)
            prompt += EXCEPTION_IN_CODE_PROMPT.format(code=code, exception_msg=exception_msg)
            temperature *= 2
            retries -= 1

    with open("generated.py", "w+") as f:
        print("### code ###")
        print(code)
        f.write(f"{code}\n")
        print("### unit test ###")
        print(unit_test_code)
        f.write(f"{unit_test_code}\n")
