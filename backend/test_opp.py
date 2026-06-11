# test_opportunity.py

from services.opportunity_service import get_opportunities

goal = {
    "goal_type": "Higher Studies",
    "degree": "MS",
    "field": "Artificial Intelligence",
    "country": "Germany",
    "timeline": "Fall 2027",
    "needs_scholarship": False,
    "raw_query": "I want to pursue MS in AI in Germany with scholarships"
}

profile = {
    "personal": {
        "full_name": "Test User",
        "nationality": "Indian",
        "age": 21
    },
    "academic": {
        "institution": "BITS Hyderabad",
        "gpa": 8.4,
        "degree_level": "Bachelor"
    },
    "professional": {
        "skills": [
            "Python",
            "Machine Learning",
            "Deep Learning"
        ],
        "experience": [
            {
                "title": "ML Intern"
            }
        ]
    }
}

result = get_opportunities(goal, profile)

print(result)