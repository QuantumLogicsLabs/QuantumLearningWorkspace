<div align="center">

# 🧠 StudyMind AI

### *Your Personal AI-Powered Learning Workspace*

<img src="https://readme-typing-svg.demolab.com?font=Inter&weight=600&size=24&pause=1000&color=6C63FF&center=true&vCenter=true&width=700&lines=Learn+Smarter.;Chat+with+Your+Notes.;Generate+Flashcards.;Build+Knowledge.;Powered+by+AI." />

---

### 📚 Upload • 💬 Ask • 🧠 Understand • 🎯 Master

*A next-generation AI learning platform that transforms your PDFs, YouTube lectures, articles, and notes into an intelligent personal tutor.*

![React](https://img.shields.io/badge/React-19-blue?style=for-the-badge&logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.12-yellow?style=for-the-badge&logo=python)
![MongoDB](https://img.shields.io/badge/MongoDB-Database-green?style=for-the-badge&logo=mongodb)
![OpenAI](https://img.shields.io/badge/OpenAI-LLM-black?style=for-the-badge&logo=openai)
![RAG](https://img.shields.io/badge/RAG-AI-purple?style=for-the-badge)

</div>

---

# 🚀 Overview

**StudyMind AI** isn't just another chatbot.

It's your **personal AI learning ecosystem** that understands everything you study, remembers it, connects concepts together, and helps you master subjects through intelligent conversations and personalized learning.

Instead of searching through dozens of PDFs, YouTube videos, or lecture notes, simply upload everything once—and let AI do the heavy lifting.

---

# ✨ Core Features

## 📄 Multi-Source Learning

Bring all your learning material together.

- 📚 PDF Notes
- 🎥 YouTube Lectures
- 🌐 Web Articles
- 📝 Personal Notes

---

## 🧠 AI Understanding

StudyMind doesn't just store files.

It:

- Extracts information
- Understands concepts
- Creates semantic embeddings
- Connects related topics
- Builds your personal knowledge base

---

## 💬 RAG Chatbot

Talk directly with your study material.

```text
You:
Explain Binary Search Tree deletion.

StudyMind:
Uses your uploaded notes + textbooks + lecture transcripts
to generate an accurate answer with context.
```

---

## 🗺️ Knowledge Graph

Automatically discovers relationships between concepts.

```text
Data Structures
      │
      ├── Trees
      │      │
      │      ├── BST
      │      ├── AVL
      │      └── Heap
      │
      └── Graphs
             │
             ├── BFS
             └── DFS
```

---

## 🃏 AI Study Aids

Generate in seconds:

- Flashcards
- MCQs
- Short Questions
- Long Questions
- Revision Notes
- Summaries

---

## 📈 Personalized Learning

StudyMind continuously learns about **you**.

It identifies:

- Weak topics
- Strong concepts
- Learning patterns
- Progress over time

Then recommends exactly what to study next.

---

## 🧠 Long-Term Memory

Unlike ordinary chatbots,

StudyMind remembers:

- Previous conversations
- Your uploaded material
- Earlier explanations
- Learning progress

Every conversation becomes smarter than the last.

---

# 🎯 Project Goals

- Centralize learning resources
- Understand content using AI
- Build a Retrieval-Augmented Generation (RAG) pipeline
- Generate intelligent study material
- Track learning progress
- Deliver personalized recommendations
- Maintain conversational memory across sessions

---

# 🏗️ Project Architecture

```text
                        ┌────────────────────┐
                        │     React UI       │
                        └─────────┬──────────┘
                                  │
                            REST API
                                  │
                     ┌────────────▼────────────┐
                     │      FastAPI Server     │
                     └────────────┬────────────┘
                                  │
          ┌───────────────────────┼────────────────────────┐
          │                       │                        │
          ▼                       ▼                        ▼

   Ingestion Engine        Vector Database          RAG Engine
(PDF • YouTube • Web)   (Embeddings Search)      (LLM + Retrieval)

          │                       │                        │
          └───────────────┬───────┴────────────────────────┘
                          ▼
                  Personalized Memory
```

---

# 📂 Repository Structure

```text
studymind-ai/
│
├── web/
│   ├── frontend/
│   └── backend/
│
├── ai-ml/
│   ├── ingestion/
│   ├── embeddings/
│   └── quiz-generator/
│
├── chatbot/
│   ├── rag-engine/
│   └── memory/
│
└── docs/
    ├── architecture.md
    ├── api-contracts.md
    └── meeting-notes.md
```

---

# 👥 Teams

| Team | Directory | Responsibilities |
|-------|-----------|------------------|
| 🌍 Team Pluto | `web/` | Frontend, Backend API, Authentication, Dashboard |
| 🤖 Team Lambda | `ai-ml/` | OCR, Embeddings, Vector Search, Quiz Generator |
| 🧠 Team Mu | `chatbot/` | RAG Pipeline, AI Chat, Memory |

---

# 🤝 Collaboration Rules

✔ Work only inside your assigned folder.

✔ Communicate through API contracts.

✔ Never modify another team's code directly.

✔ Keep pull requests small and focused.

---

# 🌱 Development Philosophy

StudyMind AI is built **incrementally**.

Every feature starts simple and evolves over time.

```
Foundation
      ↓
Upload Files
      ↓
Extract Text
      ↓
Embeddings
      ↓
RAG Chat
      ↓
Knowledge Graph
      ↓
Flashcards
      ↓
Personal Memory
      ↓
Learning Recommendations
```

---

# 🌳 Git Workflow

```text
main
 │
 ├── web/upload-ui
 │
 ├── web/auth
 │
 ├── ai/pdf-parser
 │
 ├── ai/embeddings
 │
 ├── chatbot/rag
 │
 └── chatbot/memory
```

### Rules

- 🚫 Never push directly to `main`
- 🌿 Create a feature branch
- 📤 Open a Pull Request
- 👀 Request Review
- ✅ Merge after approval

---

# 🛠️ Tech Stack

| Layer | Technology |
|--------|------------|
| Frontend | React + Vite + TailwindCSS |
| Backend | FastAPI |
| Database | MongoDB / PostgreSQL |
| Vector DB | ChromaDB / Qdrant |
| AI Models | OpenAI / Anthropic |
| OCR | PyMuPDF / Tesseract |
| YouTube | youtube-transcript-api / Whisper |
| Embeddings | OpenAI / Sentence Transformers |

---

# 🚀 Future Roadmap

- [ ] PDF Upload
- [ ] YouTube Import
- [ ] Web Article Import
- [ ] Semantic Search
- [ ] AI Chatbot
- [ ] Flashcards
- [ ] Quiz Generator
- [ ] Knowledge Graph
- [ ] Personalized Study Planner
- [ ] Mobile Application

---

# ❤️ Why StudyMind AI?

Most AI tools answer questions.

**StudyMind AI helps you learn.**

It understands your material, remembers your progress, identifies your weaknesses, and grows with you—becoming a true AI learning companion.

---

<div align="center">

## ⭐ If you like this project, give it a star!

**Made with ❤️, ☕**

</div>