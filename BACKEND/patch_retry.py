import re
import os

filepath = r"app/ai/orchestrator.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# I will replace `temp_client.models.generate_content(` with a loop to retry up to 3 times
retry_wrapper = '''            import time
            for attempt in range(3):
                try:
                    res = temp_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_prompt,
                        config=types.GenerateContentConfig(system_instruction=sys_prompt)
                    )
                    break
                except Exception as e:
                    if "503" in str(e) and attempt < 2:
                        time.sleep(2)
                        continue
                    raise e'''

# In _analyze_and_expand_query
code = code.replace('''            res = temp_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(system_instruction=sys_prompt)
            )''', retry_wrapper)

retry_wrapper_filter = '''            import time
            for attempt in range(3):
                try:
                    res = temp_client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=sys_prompt,
                            response_mime_type="application/json"
                        )
                    )
                    break
                except Exception as e:
                    if "503" in str(e) and attempt < 2:
                        time.sleep(2)
                        continue
                    raise e'''

# In _filter_relevant_chunks
code = code.replace('''            res = temp_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=sys_prompt,
                    response_mime_type="application/json"
                )
            )''', retry_wrapper_filter)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("Retry patched successfully.")
