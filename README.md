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

## Graph Overview

```
START
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 1 · enrich_decompose                                  │
│  Tools : (none — pure LLM reasoning)                        │
│  Output: enriched_query, search_topics, research_plan       │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 2 · data_gathering                                    │
│  Tools : openalex_search   (academic_search_tools.py)       │
│          arxiv_search      (academic_search_tools.py)       │
│          web_search        (playwright_tools.py) [fallback] │
│          scrape_page       (playwright_tools.py)            │
│  Output: paper_shortlist, paper_summaries, scraped_data     │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 3 · synthesis                                         │
│  Tools : index_scraped_content  (index_manager.py)          │
│          VectorStoreIndex query (index_manager.py)          │
│          PropertyGraphIndex query — GraphRAG (index_manager)│
│  Output: insight_synthesis                                  │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 4 · report_writer                                     │
│  Tools : fact_checker          (llamaindex_tools.py)        │
│          resolve_contradiction (contradiction_tools.py)     │
│            └─ internally uses web_search + scrape_page      │
│  Output: research_report, citation_source_list              │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
 END
```

---

## 🗺️ Architecture Flowchart

### Full LangGraph Workflow

```mermaid
flowchart TD
    USER(["👤 User\nPOST /run\n{query}"])
    FLASK["🌐 Flask API\nrun.py"]

    USER -->|HTTP POST| FLASK
    FLASK -->|Invoke graph| START

    subgraph LANGGRAPH["LangGraph — Linear 4-Node Workflow"]
        direction TB

        START([▶ START])

        %% ── Node 1 ───────────────────────────────────────────────
        subgraph N1["Node 1 · enrich_decompose"]
            direction TB
            N1A["🔍 Initial Generation\nLLM → InitialPlan\nenriched_query + 3-5 search topics"]
            N1B["🔎 Critique\nLLM → CritiquePlan\nidentify gaps & blind spots"]
            N1C["✏️ Refinement\nLLM → FinalPlan\nbalanced query + 4-6 final topics"]
            N1A --> N1B --> N1C
        end

        %% ── Node 2 ───────────────────────────────────────────────
        subgraph N2["Node 2 · data_gathering"]
            direction TB
            N2A["🔬 Parallel Academic Search\n(per search_topic)"]
            subgraph N2TOOLS["Academic Tools — run in parallel"]
                N2OA["openalex_search\n250M+ works\nsorted by citation count"]
                N2AX["arxiv_search\nCS/AI preprints\nsorted by relevance"]
                N2BING["web_search (Bing)\nFallback only if both\nacademic sources empty"]
            end
            N2B["🚫 Junk-domain Blocklist\nfilter non-academic URLs"]
            N2C["🌍 Parallel Scraping\nPlaywright Chromium\n(headless browser)"]
            N2D["📄 LLM Summary per page\nLLM → PaperSummary\ntitle + url + summary + relevance_score"]
            N2A --> N2TOOLS --> N2B --> N2C --> N2D
        end

        %% ── Node 3 ───────────────────────────────────────────────
        subgraph N3["Node 3 · synthesis"]
            direction TB
            N3A["📥 Index scraped content\nindex_manager.index_scraped_content()"]
            subgraph N3STORES["Dual-Store Indexing"]
                N3VS["📊 VectorStoreIndex\nLlamaIndex + text-embedding-3-large\nPersisted to /app/data/storage"]
                N3MG["🕸️ PropertyGraphIndex\nMemgraph (Bolt)\nLLM-extracted entity-relationship triplets\nembed_kg_nodes=False"]
            end
            N3B["🔍 Vector Retrieval\nSemantic similarity search\nover scraped summaries"]
            N3C["🔗 GraphRAG Retrieval\nTriplet path traversal\nentities + relationships"]
            N3D["🧠 LLM Compilation\nMerge Vector + GraphRAG context\n→ InsightSynthesis"]
            N3A --> N3STORES
            N3STORES --> N3B & N3C
            N3B & N3C --> N3D
        end

        %% ── Node 4 ───────────────────────────────────────────────
        subgraph N4["Node 4 · report_writer"]
            direction TB
            N4A["✍️ Draft\nLLM → initial markdown report"]
            N4B["🔎 Critique\nLLM → identify unsupported claims"]
            N4C["✅ Fact-Check\nLLM → verify each assertion\nagainst paper_summaries"]
            N4D["⚡ Contradiction Detection\ncheck_for_contradictions tool\nfind conflicting claims"]
            N4E["🔄 Reconcile\nLLM → resolve contradictions"]
            N4F["📑 Refine\nLLM → polish & finalize\ncitation_source_list validated"]
            N4A --> N4B --> N4C --> N4D --> N4E --> N4F
        end

        END(["⏹ END"])

        START --> N1
        N1 --> N2
        N2 --> N3
        N3 --> N4
        N4 --> END
    end

    END -->|JSON Response| FLASK
    FLASK -->|HTTP 200| USER

    %% ── External Services ─────────────────────────────────────────
    GPT["🤖 GPT-4.1\nOpenAI-compatible API\n(Core42 Compass)"]
    EMB["📐 text-embedding-3-large\n3072-dim vectors"]
    MGDB[("🕸️ Memgraph DB\nbolt://127.0.0.1:7687\nProperty Graph Store")]
    OA["📚 OpenAlex API\nhttps://api.openalex.org"]
    ARX["📄 arXiv API\nhttps://export.arxiv.org"]
    BING["🔍 Bing Web Search\nPlaywright tool"]

    N1A & N1B & N1C -.->|structured_output| GPT
    N2D -.->|summarize| GPT
    N3MG -.->|entity extraction| GPT
    N3D & N4A & N4B & N4C & N4E & N4F -.->|generate| GPT
    N3VS -.->|embed| EMB
    N3MG -.->|store graph| MGDB
    N3C -.->|query graph| MGDB
    N2OA -.->|REST| OA
    N2AX -.->|Atom API| ARX
    N2BING -.->|search| BING
```

---

### Tool Interaction Map

```mermaid
flowchart LR
    subgraph TOOLS["🛠️ Tools & Utilities"]
        T1["openalex_search\ntools/academic_search_tools.py"]
        T2["arxiv_search\ntools/academic_search_tools.py"]
        T3["web_search\ntools/playwright_tools.py"]
        T4["scrape_page\ntools/playwright_tools.py"]
        T5["check_for_contradictions\ntools/contradiction_tools.py"]
        T6["index_scraped_content\nmodels/index_manager.py"]
    end

    subgraph NODES["📦 LangGraph Nodes"]
        ND1["enrich_decompose"]
        ND2["data_gathering"]
        ND3["synthesis"]
        ND4["report_writer"]
    end

    subgraph STATE["🗂️ ResearchState"]
        S1["query"]
        S2["research_plan\n(elaborated_query, search_topics)"]
        S3["paper_shortlist"]
        S4["paper_summaries"]
        S5["scraped_data"]
        S6["insight_synthesis\n(vector_context, graphrag_context)"]
        S7["research_report"]
        S8["citation_source_list"]
        S9["contradictions"]
    end

    ND1 -->|writes| S2
    ND2 -->|uses| T1 & T2 & T3
    ND2 -->|uses| T4
    ND2 -->|writes| S3 & S4 & S5
    ND3 -->|uses| T6
    ND3 -->|writes| S6
    ND4 -->|uses| T5
    ND4 -->|writes| S7 & S8 & S9
    S1 -->|reads| ND1
    S2 -->|reads| ND2
    S4 & S5 & S6 -->|reads| ND4
```

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

### 1. Build and Run with the Entrypoint Script
```bash
./entrypoint.sh
```

---

## 📊 Viewing Logs and Telemetry

The application uses **structured JSON logging** inside Docker and pretty logs locally. The custom logger instruments token counters (input, output, and total tokens) and execution durations for every step.

### View Container Logs
```bash
docker logs <container-id>
```

### Stream Live Logs in Real-time
```bash
docker logs -f <container-id>
```

Inside the container, the supervisor script writes:
- API logs to `/app/logs/app.log`
- Memgraph logs to `/app/logs/memgraph.log`

---

## 🚀 Triggering Deep Research (API Endpoints)

The Flask web server is hosted on port **`8000`** inside the container and mapped directly to your localhost.

### 1. Standard Submission Endpoint
*   **URL:** `http://localhost:8000/run`
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
     http://localhost:8000/run
```

**Expected Response Layout:**
Returns the standardized Agentathon response:
*   `status`: success/error.
*   `use_case_id`: selected challenge ID.
*   `result.summary`: user-facing summary output.
*   `result.recommendations`: actionable recommendations.
*   `result.artifacts`: references/citation artifacts.
*   `agents_used`: workflow roles.
*   `trace_id`: execution trace identifier.
*   `runtime_seconds`: end-to-end runtime.

### 2. Service Health Status Endpoint
*   **URL:** `http://localhost:8000/`
*   **Method:** `GET`

**Example Curl Command:**
```bash
curl -s http://localhost:8000/
```

---

## 🧪 Verification and Test Suite

You can execute node-specific and end-to-end integration tests directly inside the running single container:

### 1. Run Synthesis Verification (Node 3)
```bash
docker exec -it <container-id> python tests/test_synthesis.py
```

### 2. Run Report Writer Verification (Node 4)
```bash
docker exec -it <container-id> python tests/test_report_writer.py
```

### 3. Run End-to-End Integration Verification
Runs the entire LangGraph workflow from search to the final fact-checked report:
```bash
docker exec -it <container-id> python tests/test_end_to_end.py
```

---

## 📁 Submission Artifacts

The repository includes the mandatory submission assets:
- `app/` for submission-facing orchestration helpers.
- `input_examples/` with at least 3 reproducible request payloads.
- `output_examples/` with at least 3 matching structured outputs.
- `logs/` with sample agent interaction traces.
