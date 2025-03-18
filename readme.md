# **Content Recommendation Microservice**

A scalable and personalized content recommendation microservice built with **Python**, **FastAPI**, and **GenAI technologies**. It employs an **embedding-based recommendation algorithm** leveraging **Facebook BART Large MNLI** for content categorization and Kafka for asynchronous messaging.

---

## **Table of Contents**

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Technologies Used](#technologies-used)
5. [API Endpoints](#api-endpoints)
6. [Database Schema](#database-schema)
7. [Installation](#installation)
8. [Usage](#usage)
9. [Deployment](#deployment)
10. [Future Improvements](#future-improvements)

---

## **Overview**

This microservice provides personalized content recommendations to users based on their interests. It leverages:

- **GenAI** models for embedding-based recommendations.
- Scalable and conflict-free service architecture with clear separation of concerns.
- Kafka for asynchronous event handling.

### **Key Components**

1. **UserService**: Manages user embeddings, interactions, and real-time recommendations.
2. **FeedbackService**: Logs user feedback and balances user interests.
3. **ContentIngestService**: Processes and stores new content and metadata.

---

## **Features**

- Personalized recommendations based on user interests.
- Embedding-based categorization and retrieval using **Facebook BART Large MNLI**.
- Asynchronous updates via **Kafka**.
- Optimized for scalability, maintainability, and conflict-free operations.
- Supports real-time feedback to refine recommendations.

---

## **Architecture**

![Architecture Diagram Placeholder](#) _(Include or reference a diagram if available)_

### **Workflow Highlights**

- **UserService** exclusively manages embeddings with **Qdrant**.
- **Redis** caches category embeddings for fast user embedding computation.
- **MongoDB** stores user preferences and content metadata.
- Smart embedding updates triggered by **ContentIngestService**.

---

## **Technologies Used**

- **Python** & **FastAPI**: Backend development.
- **Facebook BART Large MNLI**: GenAI model for content categorization.
- **Kafka**: Event-driven architecture.
- **Qdrant**: Embedding storage and retrieval.
- **Redis**: In-memory caching for category embeddings.
- **MongoDB**: Storage for user preferences and content metadata.

---

## **API Endpoints**

### 1. **User Interest Submission**

**POST** `/api/user/interests`  
_Submits user interests and updates their embeddings._

### 2. **Content Recommendation Retrieval**

**GET** `/api/recommendations`  
_Returns personalized content recommendations._

### 3. **Feedback Collection**

**POST** `/api/user/feedback`  
_Logs feedback and adjusts user interests._

---

## **Database Schema**

### **Collections and Tables**

1. **User Interests**
   - UserID, Preferences, Embeddings, Interaction History
2. **Content Metadata**
   - ContentID, Title, Description, Category, Embeddings
3. **Feedback Logs**
   - UserID, FeedbackType, ContentID, Timestamp

### **Indexes**

- Use **FAISS** or **Annoy** for faster vector similarity searches on embeddings.

---

## **Installation**

### **Prerequisites**

- Python 3.12+
- Docker (optional, for containerized deployment)

### **Steps**

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo-url.git
   cd content-recommendation-microservice
   ```
## **Deployment**
   version: '3.8'

## Docker Compose Configuration

Below is the Docker Compose configuration for deploying the microservices:

```yaml
version: '3.8'

services:
  user-service:
    build: ./user-service
    ports:
      - "8001:8000"
    env_file:
      - ./user-service/.env
    depends_on:
      - mongodb
      - qdrant
      - kafka
      - redis
    networks:
      - microservices_network

  feedback-service:
    build: ./feedback-service
    ports:
      - "8002:8000"
    env_file:
      - ./feedback-service/.env
    depends_on:
      - mongodb
      - kafka
    networks:
      - microservices_network

  content-service:
    build: ./content-service
    ports:
      - "8003:8000"
    env_file:
      - ./content-service/.env
    depends_on:
      - kafka
    networks:
      - microservices_network

  # mongodb:
  #   image: mongo:6.0
  #   container_name: mongodb
  #   restart: always
  #   ports:
  #     - "27017:27017"
  #   volumes:
  #     - mongo_data:/data/db
  #   networks:
  #     - microservices_network

  qdrant:
    image: qdrant/qdrant
    container_name: qdrant
    restart: always
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - microservices_network
  
  redis:
    image: redis:latest
    container_name: redis
    restart: always
    ports:
      - "6379:6379"
    networks:
      - microservices_network

  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    container_name: zookeeper
    restart: always
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    networks:
      - microservices_network

  kafka:
    image: confluentinc/cp-kafka
    container_name: kafka
    restart: always
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    depends_on:
      - zookeeper
    networks:
      - microservices_network

networks:
  microservices_network:
    driver: bridge

volumes:
  qdrant_storage:
  mongo_data:

