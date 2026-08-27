# AutoDocGen — AI-Based Automated Document Generation System

An AI-powered, human-in-the-loop documentation platform that automatically generates and maintains Software Development Life Cycle (SDLC) documentation from data collected across project management and development platforms.

AutoDocGen integrates with tools such as **GitHub, Trello, and Slack**, processes project data through an AI-driven workflow, retrieves relevant contextual information, and generates structured documentation for different SDLC phases.

---

## 📌 Overview

Software projects generate large amounts of information across issue trackers, repositories, communication platforms, and project management tools. Manually converting this information into structured SDLC documentation is time-consuming and difficult to maintain.

**AutoDocGen** automates this process.

The system:

1. Connects to project management and development platforms.
2. Fetches relevant project data.
3. Processes and organizes the collected information.
4. Retrieves relevant context using a hybrid retrieval pipeline.
5. Generates documentation using Large Language Models (LLMs).
6. Allows users to review and refine generated documents.
7. Maintains document versions.
8. Monitors connected platforms for changes.
9. Notifies users when relevant project changes occur.

The system follows a **Human-in-the-Loop (HITL)** approach, allowing users to review AI-generated content before finalizing documentation.

---

## ✨ Key Features

### 🤖 AI-Powered Document Generation

Generate structured SDLC documentation using LLM-powered workflows.

Supported documentation includes:

- Software Requirements Specification (SRS)
- Software Design Documents
- Project Plans
- Test Plans
- Meeting Documentation
- Technical Documentation
- User Stories
- System Documentation
- And other SDLC-related document types

The system supports **13+ document types**.

---

### 🔗 Project Management & Development Integrations

AutoDocGen can collect project information from external platforms including:

- GitHub
- Trello
- Slack

The collected information becomes the source context for document generation.

---

### 🧠 Hybrid Information Retrieval

AutoDocGen uses a hybrid retrieval pipeline to improve the relevance of information provided to the LLM.

The retrieval system combines:

- **TF-IDF** — lexical similarity
- **BM25** — probabilistic keyword retrieval
- **Sentence Transformers** — semantic similarity
- **MiniLM embeddings** — dense vector representations
- **Chroma** — vector database

This combination allows the system to retrieve information using both keyword-based and semantic similarity.

---

### 🔄 LangGraph Workflow

Document generation is implemented as a structured workflow using **LangGraph**.

A simplified workflow is:

```text
Project Data
     ↓
Data Collection
     ↓
Data Processing
     ↓
Context Retrieval
     ↓
LLM Processing
     ↓
Document Generation
     ↓
Validation
     ↓
Human Review
     ↓
Final Document
