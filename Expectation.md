# Project Expectations & Vision

> [!IMPORTANT]
> **Project Assignment:** You are taking over an existing software project.
> - Your role is **NOT** to experiment.
> - Your role is **NOT** to redesign randomly.
> - Your role is to **complete this project exactly according to the product vision below.**

---

## 🛠️ Existing Repository Setup

Treat the existing implementation as a partially completed prototype. The architecture should evolve only when necessary to satisfy the vision below.

The current repository already contains:
- **React** frontend
- **FastAPI** backend
- **Gemini** integration
- **MongoDB** & **MongoDB MCP**
- **Authentication**
- **Resume upload** & **Profile management**
- **Goal input** & **Initial roadmap generation**
- **Multiple AI agents**

---

## 🎯 1. Project Vision

This product is an **AI Goal Execution Platform**.

*   This is **NOT** an AI chatbot.
*   This is **NOT** an AI roadmap generator.
*   This is **NOT** a career dashboard.

Its purpose is to help users achieve complex long-term goals that require planning, bureaucracy, documentation, research, and execution.

### Example User Goals
- Master's in Germany (Microelectronics)
- PhD in AI
- Embedded Engineer at Qualcomm
- Software Engineer at Google
- MBA abroad
- Government Scholarship
- Research Internship

### Core User Questions to Answer
- *"What exactly am I missing?"*
- *"What should I do next?"*
- *"What opportunities exist for me?"*
- *"How do I execute the application?"*

---

## 🧠 2. Core Philosophy

> **The roadmap is NOT the product.** The roadmap is only one artifact.

### Core Product Execution Flow
```
Goal ➔ Requirement Discovery ➔ Gap Analysis ➔ Execution Plan ➔ Opportunity Discovery ➔ Application Assistance ➔ Persistent Memory ➔ Goal Achievement
```
Everything revolves around these steps.

---

## 🗺️ 3. User Journey

1. **Sign Up:** User creates an account.
2. **Profile Upload:**
   - Resume
   - Academic information
   - Skills & Experience
   - Certificates & Test scores *(optional)*
3. **Goal Entry:** User enters target goal (e.g., *"I want to pursue a Master's in Germany in Microelectronics."*).
4. **Goal Analysis (AI-Driven):**
   - **NOT** generic roadmap generation.
   - The analysis should be **exhaustive** and identify:
     - Destination & Field
     - Timeline & Required qualifications
     - Required exams & Required documents
     - Financial requirements & Visa requirements
     - Language requirements & Experience expectations
     - Application requirements & Scholarships
     - Anything else required.

---

## 📊 4. Gap Analysis

The system compares: **Current Profile** vs. **Required Profile**.

The gap analysis should become the **central feature** of the product.

### Output Categories
- **Already Completed**
- **Missing**
- **Recommended**
- **Critical**
- **Optional**

### Example Gap Analysis Output
| Requirement | Status | Type |
| :--- | :--- | :--- |
| Passport | ✔️ | Completed |
| IELTS | ❌ | Missing / Critical |
| Research Experience | ❌ | Missing |
| Publication | ❌ | Missing |
| Recommendation Letters | ❌ | Missing |
| German Language | ℹ️ | Optional |
| Blocked Account | ⚠️ | Required |
| APS Certificate | ⚠️ | Required |

---

## 📌 5. Roadmap

- **Never Generic:** Every roadmap item must exist because of the previous Goal Analysis.
- **Justification Required:** Every recommendation must include **WHY**.
  - ❌ **Bad:** *"Take IELTS."*
  - ✔️ **Good:** *"Register for IELTS before August 12 because scores require approximately two weeks and several target universities close applications in September."*
- **Task Metadata:** Every task should have:
  - Reason
  - Estimated effort
  - Dependencies
  - Priority
  - Completion status
- **Dynamic:** Tasks should evolve as the user progresses.

---

## 💾 6. Persistent Memory

Persistent memory is one of the **flagship features**. It should **NOT** simply store conversation history; it represents an **evolving case file**.

### What to Store
- Goal & Profile
- Completed tasks & Current roadmap
- Uploaded documents & Applications
- Deadlines & Exam scores
- Progress & Previous recommendations
- Missing requirements

*Future interactions should always reason over previous state.*

---

## 💡 7. Opportunities

The Opportunities page should **NEVER** contain placeholders. Remove every placeholder and replace with a functional experience.

### Included Opportunities
- Scholarships
- Research programs & openings
- Internships
- University deadlines
- Application portals
- Entrance exams
- Visa appointments *(where feasible)*
- Relevant conferences

### Required Fields for Each Opportunity
- Description
- Eligibility
- Deadline *(when available)*
- Official Link
- Reason for recommendation
- Estimated Match

---

## 📝 8. Application Assistance

> **Flagship Feature:** The project should eventually support browser-assisted applications.

### Application Workflow
1. User opens an official application page.
2. A browser extension *(future component)* scans the page and extracts:
   - Labels, Inputs, Dropdowns, Required fields, Textareas.
3. Backend compares detected fields against the stored profile.
4. System reports:
   - **Can Autofill**
   - **Missing Information**
   - **Missing Documents**
   - **Warnings**
   - **Estimated Completion**

#### Example Report
- **Detected Fields:** 42
- **Can Autofill:** 34
- **Missing:** IELTS Score, Passport Expiry, Motivation Letter
- **Warnings:** *"Passport expires in 5 months. University requires 6 months validity."*

> [!CAUTION]
> **Do NOT implement fully autonomous submission.** The user should remain in control. Autofill should assist, not replace, the user.

---

## 🏗️ 9. Architecture

- **Preserve Modularity:** Improve existing architecture only when justified.
- **Single-Responsibility Agents:**
  - Goal Analysis Agent
  - Gap Analysis Agent
  - Roadmap Planning Agent
  - Progress Update Agent
  - Opportunity Discovery Agent
  - Application Assistant Agent
  - Memory Management Agent
- **Principles:** Avoid giant monolithic prompts. Prefer structured outputs and deterministic pipelines.

---

## 🎨 10. User Interface (UI)

- The application should feel like a polished product.
- **Avoid** placeholder cards, "Coming Soon", dummy data, or lorem ipsum.
- Every page should have a clear purpose.
- Every interaction should provide value.

---

## 🛡️ 11. Implementation Principles

- **Data Integrity:** Never invent fake data, fabricate deadlines, or fabricate opportunities.
- **Transparency:** When real data is unavailable, clearly indicate limitations.
- **Sources:** Prefer official sources whenever external links are shown.

---

## ⚡ 12. Testing Constraints

> [!WARNING]
> **Gemini API credits are extremely limited.** Avoid repeated expensive LLM calls during development.

### Development Strategies
- Cache responses
- Mock Gemini outputs for development
- Isolate prompt testing
- Use deterministic fixtures
- Unit-test business logic independently of Gemini
- Separate integration tests from unit tests
- Only perform real Gemini calls for final verification

*Design the codebase so that most testing can be completed without consuming API credits.*

---

## ✅ 13. Success Criteria

A user should be able to:
```
Upload Profile ➔ Specify Ambitious Goal ➔ Exhaustive Goal Analysis ➔ Personalized Gap Analysis ➔ Justified Roadmap ➔ Track Progress ➔ Evolving Recommendations ➔ Discover Opportunities ➔ Open Official Portals ➔ Identify Missing Info ➔ Autofill Supported Fields
```
...all without feeling that the application is just another ChatGPT wrapper.

---

## 🏁 14. Final Instructions

Do not stop after making the project functional. Continue refining until:
- Every page has a clear purpose.
- No placeholders remain.
- No dummy data remains.
- The product feels cohesive.
- Architecture remains maintainable.
- Every AI decision is explainable.
- Every recommendation has reasoning.
- Every major feature supports the overall vision.

*Treat this as building a production-quality MVP that could realistically be demonstrated to users, recruiters, judges, or collaborators.*