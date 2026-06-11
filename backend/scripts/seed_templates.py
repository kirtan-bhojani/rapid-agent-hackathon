import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

uri = os.environ.get("MONGO_URI") or os.environ.get("MDB_MCP_CONNECTION_STRING")
client = MongoClient(uri)
db = client.get_database("rapid")
collection = db.get_collection("role_templates")

templates = [
    {
        "role": "ML Engineer",
        "required_skills": ["Python", "TensorFlow", "PyTorch", "SQL", "Scikit-Learn", "MLOps", "Docker"],
        "recommended_projects": ["Train and deploy an end-to-end CV model", "Build a recommendation system API"],
        "recommended_certifications": ["AWS Certified Machine Learning - Specialty", "Google Cloud Professional Machine Learning Engineer"],
        "suggested_timeline": "6-9 months"
    },
    {
        "role": "AI Engineer",
        "required_skills": ["Python", "LLMs", "LangChain", "Vector Databases", "Prompt Engineering", "RAG", "FastAPI"],
        "recommended_projects": ["Build an AI Agent with Memory", "Implement a RAG pipeline over documentation"],
        "recommended_certifications": ["Azure AI Engineer Associate", "DeepLearning.AI Specialization"],
        "suggested_timeline": "3-6 months"
    },
    {
        "role": "Data Scientist",
        "required_skills": ["Python", "R", "SQL", "Pandas", "Statistics", "Data Visualization", "A/B Testing"],
        "recommended_projects": ["Customer Churn Prediction Model", "Interactive Streamlit Dashboard for Sales"],
        "recommended_certifications": ["IBM Data Science Professional Certificate"],
        "suggested_timeline": "6-12 months"
    },
    {
        "role": "Software Engineer",
        "required_skills": ["JavaScript", "Python", "Java", "Data Structures", "Algorithms", "Git", "REST APIs", "CI/CD"],
        "recommended_projects": ["Full-stack e-commerce app", "Open source contribution to a known library"],
        "recommended_certifications": ["AWS Certified Developer"],
        "suggested_timeline": "6-12 months"
    },
    {
        "role": "Cloud Architect",
        "required_skills": ["AWS/GCP/Azure", "Terraform", "Kubernetes", "Networking", "Security", "System Design"],
        "recommended_projects": ["Deploy a highly available microservices architecture", "Implement infrastructure as code for a web app"],
        "recommended_certifications": ["AWS Certified Solutions Architect - Professional", "Google Cloud Professional Cloud Architect"],
        "suggested_timeline": "9-18 months"
    },
    {
        "role": "Product Manager",
        "required_skills": ["Agile/Scrum", "Jira", "User Research", "Wireframing", "Data Analysis", "A/B Testing", "Stakeholder Management"],
        "recommended_projects": ["Conduct a case study on improving a known app", "Launch a small indie product on Product Hunt"],
        "recommended_certifications": ["Certified Scrum Product Owner (CSPO)", "Pragmatic Institute Certification"],
        "suggested_timeline": "3-6 months"
    }
]

def seed():
    print(f"Connected to db: {db.name}. Dropping existing templates...")
    collection.drop()
    
    print("Inserting new templates...")
    result = collection.insert_many(templates)
    print(f"Successfully inserted {len(result.inserted_ids)} templates.")

if __name__ == "__main__":
    seed()
