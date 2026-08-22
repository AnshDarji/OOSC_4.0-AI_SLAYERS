import json
from app.ai.orchestrator import rag_orchestrator

query = """A municipal authority has repeatedly failed to collect garbage from my residential area for several weeks, resulting in accumulated waste, foul smell, and serious sanitation problems. Despite multiple complaints through the municipal helpline and written complaints to the local ward office, no effective action has been taken. I have photographs and videos of the accumulated garbage, copies of my complaints, complaint numbers, dates, and communications with municipal officials. What legal and administrative remedies are available to me? Give me a step-by-step action plan, identify the exact municipal authorities I should approach and the escalation hierarchy, list all evidence I should preserve, explain whether I can seek directions from a court or other authority if the municipality remains inactive, and identify the relevant statutory provisions and judicial precedents supporting my rights."""

res = rag_orchestrator.trigger_pipeline(query, filters={}, task_type='CIVIC')

with open("test_failing_query.json", "w") as f:
    json.dump(res, f, indent=2)

print("Saved output to test_failing_query.json")
