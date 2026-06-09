# test_goal.py

from agent.goal_agent import extract_goal


profile = {
    "professional": {
        "skills": ["Python", "Langchain", "PyTorch"],
        "education": [{"degree": "B.E Electronics"}],
        "experience": [{"title": "LLM Research"}],
    }
}

result = extract_goal("I want to work in Germany.")

print(result)
