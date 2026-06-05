Parser Agent

Purpose:
Convert uploaded resumes into structured user profiles.

Functions:

extract_pdf_text(pdf_path)

parse_resume(pdf_path)

split_profile_data(profile)

process_resume(pdf_path, user_id)

Pipeline:

PDF
↓
Text Extraction
↓
Gemini Parsing
↓
JSON Profile
↓
Privacy Split
↓
Database Storage

Output Schema:

{
    name,
    email,
    phone,
    education,
    skills,
    experience
}