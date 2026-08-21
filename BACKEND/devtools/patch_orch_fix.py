import os

filepath = r"c:\Users\ANSH DARJI\Documents\NYAAY AI\BACKEND\app\ai\orchestrator.py"
with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# We fix the `temp_client` bug by capturing the current key in the outer scope
old_str = """        try:
            model_name = getattr(settings, "CIVIC_MODEL", "gemini-2.5-flash")"""

new_str = """        try:
            model_name = getattr(settings, "CIVIC_MODEL", "gemini-flash-lite-latest")
            current_key = key_rotator.get()"""

old_thread = """            def run_gen():
                try:
                    temp_client = genai.Client(api_key=key_rotator.get())"""

new_thread = """            def run_gen():
                try:
                    temp_client = genai.Client(api_key=current_key)"""

old_catch = """                        if "GenerateRequestsPerDayPerProject" in error_str:
                            key_rotator.remove_key(temp_client.api_key)"""

new_catch = """                        if "GenerateRequestsPerDayPerProject" in error_str:
                            key_rotator.remove_key(current_key)"""

# Also fix the fallback method
old_fallback = """        model_name = getattr(settings, "CIVIC_MODEL", "gemini-2.5-flash")"""
new_fallback = """        model_name = getattr(settings, "CIVIC_MODEL", "gemini-flash-lite-latest")"""

old_fallback_catch = """                if "GenerateRequestsPerDayPerProject" in error_str:
                    logger.warning("Daily quota exhausted, dropping key.")
                    key_rotator.remove_key(temp_client.api_key)"""

new_fallback_catch = """                if "GenerateRequestsPerDayPerProject" in error_str:
                    logger.warning("Daily quota exhausted, dropping key.")
                    key_rotator.remove_key(current_key)"""

old_fallback_try = """            try:
                temp_client = genai.Client(api_key=key_rotator.get())"""
new_fallback_try = """            try:
                current_key = key_rotator.get()
                temp_client = genai.Client(api_key=current_key)"""

code = code.replace(old_str, new_str)
code = code.replace(old_thread, new_thread)
code = code.replace(old_catch, new_catch)
code = code.replace(old_fallback, new_fallback)
code = code.replace(old_fallback_catch, new_fallback_catch)
code = code.replace(old_fallback_try, new_fallback_try)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("orchestrator.py bug fixed!")
