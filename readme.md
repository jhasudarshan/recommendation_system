# **Content Recommendation Microservice**

A scalable and personalized content recommendation microservice built with **Python**, **FastAPI**, and **GenAI technologies**. It employs an **embedding-based recommendation algorithm** leveraging **Facebook BART Large MNLI** for content categorization and Kafka for asynchronous messaging.

---

## **Table of Contents**

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture & Workflow](#architecture--workflow)
4. [Technologies Used](#technologies-used)
5. [API Endpoints](#api-endpoints)
6. [Future Improvements](#future-improvements)

---

## **Overview**

This microservice provides personalized content recommendations to users based on their interests. It leverages:

- **GenAI** models for embedding-based recommendations.
- Scalable and conflict-free service architecture with clear separation of concerns.
- Kafka enables asynchronous communication, decoupling microservices for scalability and fault tolerance.

### **Key Components**

**1. UserService**: Manages user embeddings, interactions, and real-time recommendations.
**2. ContentService**: Processes new articles, updates metadata, and tracks user feedback.

---

## **Features**

- Personalized recommendations based on user interests.
- Category classification using **Facebook BART Large MNLI**.
- Asynchronous updates via **Kafka**.
- Optimized for scalability, maintainability, and conflict-free operations.
- Supports real-time feedback to refine recommendations.

---

## **Architecture & Workflow**

### **Microservices Overview**

**1️. UserService (Handles User Interests & Recommendations)**

- Stores and updates content embeddings in **Qdrant** for personalized recommendations.
- Uses **Redis** to cache category embeddings, ensuring fast computation of user embedding based on user-interest.
- Exposes an API to **log user interests** and **retrieve personalized recommendations**.

**2️. ContentService (Handles Content Processing & Feedback Tracking)**

- Processes new articles, categorizes them using **GenAI (Facebook BART Large MNLI)**, and stores metadata in **MongoDB**.
- Tracks **interaction metrics** (likes, shares, clicks) and updates content metadata.
- Exposes APIs to process new content and handle metadata updates.
- **Produces Kafka events**:
  - `embedding_update_required` → Triggers embedding updates when significant content changes.
  - `balance_user_interest` → Sends computed user interest adjustments to **UserService**.
- **ContentService API Endpoints:**
  - `POST /content/process` → Processes new content and categorizes it.
  - `POST /content/process_metadata_update` → Logs interaction metrics and updates metadata.

### **Workflow Summary**

- A **new article** is ingested → **ContentService** processes and categorizes it using GenAI.
- **Content metadata is updated** → Triggers `embedding_update_required` for **UserService** to keep latest relevant recommendations.
- **Users interact** with content (likes, shares, clicks) → **ContentService** logs feedback & computes user interest weights.
- **ContentService sends `balance_user_interest` event** → **UserService** updates user interest.
- **User requests recommendations** → **UserService** retrieves top results from **Qdrant** using updated embeddings.
- **Kafka ensures smooth, asynchronous communication** between services.

---

## **Technologies Used**

- **Python** & **FastAPI**: Backend development.
- **Facebook BART Large MNLI**: GenAI model for content categorization.
-**all-MiniLM-L6-v2, sentence_transformers**: For generating embeddings.
-**PCA**: For reducing embedding dimensions for predefined categories
- **Kafka**: Event-driven architecture.
- **Qdrant**: Embedding storage and retrieval.
- **Redis**: In-memory caching for category embeddings.
- **MongoDB**: Storage for user preferences and content metadata.

---

## **API Endpoints**

### 1. **User Interest Submission**

**POST** `/users/log-interest`
_Submits user interests._

### 2. **Content Recommendation Retrieval**

**GET** `/recommend`
_Returns personalized content recommendations._

### 3. **Content Processing**

**POST** `/content/process`
_Processes new content and categorizes it._

### 4. **Metadata Update Processing**

**POST** `/content/process_metadata_update`
_Logs interaction metrics and updates content metadata._

---
## **Postman Collection**

We have provided a **Postman collection** to test all API endpoints. You can find the collection in the postman/ folder within this repository. Import it into Postman to quickly test the available endpoints.
---

## **Future Improvements**

- **Optimizing embedding storage and retrieval** for large-scale users.
- Improving recommendation diversification using **re-ranking techniques** after embedding generation  or multi-objective ranking for balancing relevance, diversity, and freshness.