# Deep Research Flow Agent 🚀

A containerized, multi-agent Deep Research orchestrator built using **LangGraph**, **LlamaIndex**, **Memgraph (GraphRAG)**, **Flask**, and **Playwright Chromium**. 

The agent conducts autonomous query decomposition, parallel Bing searches, live Playwright SPA scraping, vector and property graph ingestion, GraphRAG path lookups, peer-reviewed fact-checking, and final publication-ready report drafting.

---

## 🛠️ Architecture Overview

The system runs a **4-node linear LangGraph workflow**:
1. 🔍 **Enrich & Decompose (Node 1):** Elaborates query viewpoints (points vs counter-points) and decomposes them into precise search terms.
2. 🌐 **Data Gathering (Node 2):** Performs parallel web searches, scrapes pages concurrently using Playwright Chromium, and compiles individual paper summaries.
3. 🧠 **Synthesis (Node 3):** Indexes scraped documents into LlamaIndex's Vector Store and extracts entity-relationship triplets into the **Memgraph** Graph Database, synthesizing Vector + GraphRAG insights.
4. 📝 **Report Writer (Node 4):** Executes a strict self-correction loop (Draft -> Critique -> Fact-Check assertions -> Reconcile contradictions -> Refine) to produce the final citation-grounded report.

---

## ⚙️ Environment Setup

Create a `.env` file in the root directory (based on `.env.example`). For standard production execution on Core42's Compass gateway, configure the following:

```env
OPENAI_API_KEY="your-core42-compass-api-key"
OPENAI_BASE_URL="https://api.core42.ai/v1"
OPENAI_MODEL="gpt-4.1"
EMBEDDING_MODEL="text-embedding-3-large"
```

---

## 🐳 Building and Running the System

### 1. Build and Start Containers
To build the Docker images and launch the cluster (Flask web server + Memgraph Database) in the background:
```bash
docker compose up -d --build
```

### 2. Stop Containers
To stop and clean up all active containers, networks, and volumes:
```bash
docker compose down
```

---

## 📊 Viewing Logs and Telemetry

The application uses **structured JSON logging** inside Docker and pretty logs locally. The custom logger instruments token counters (input, output, and total tokens) and execution durations for every step.

### View All Logs (Flask + Memgraph)
```bash
docker compose logs
```

### Stream Live Logs in Real-time
```bash
docker compose logs -f
```

### Stream Flask App Logs Only
```bash
docker compose logs -f flask-app
```

### Stream Memgraph Database Logs Only
```bash
docker compose logs -f memgraph
```

---

## 🚀 Triggering Deep Research (API Endpoints)

The Flask web server is hosted on port **`8000`** inside the container and mapped directly to your localhost.

### 1. Deep Research Query Endpoint
*   **URL:** `http://localhost:8000/research`
*   **Method:** `POST`
*   **Headers:** `Content-Type: application/json`
*   **Request Body:**
    ```json
    {
      "query": "Should artificial intelligence coding assistants write code autonomously?"
    }
    ```

**Example Curl Command:**
```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"query": "Should artificial intelligence coding assistants write code autonomously?"}' \
     http://localhost:8000/research
```

**Expected Response Layout:**
Returns the **6 expected outputs** required by judges:
*   `query`: The original query.
*   `research_plan`: Decomposed sub-queries and elaborated points.
*   `paper_shortlist`: Promising papers/resources discovered.
*   `paper_summaries`: Factual summaries of scraped pages with relevance ratings.
*   `insight_synthesis`: High-fidelity semantic findings and GraphRAG path connections.
*   `research_report`: Polished, citation-grounded markdown research report.
*   `citation_source_list`: Ordered list of cited bibliography sources.

---

### 2. Service Health Status Endpoint
*   **URL:** `http://localhost:8000/`
*   **Method:** `GET`

**Example Curl Command:**
```bash
curl -s http://localhost:8000/
```

---

## 🧪 Verification and Test Suite

You can execute node-specific and end-to-end integration tests directly inside the running `flask-app` container:

### 1. Run Synthesis Verification (Node 3)
```bash
docker compose exec flask-app python tests/test_synthesis.py
```

### 2. Run Report Writer Verification (Node 4)
```bash
docker compose exec flask-app python tests/test_report_writer.py
```

### 3. Run End-to-End Integration Verification (POST /research)
Runs the entire LangGraph workflow from search to the final fact-checked report:
```bash
docker compose exec flask-app python tests/test_end_to_end.py
```
