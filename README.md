# TimeSliceIQ

> **Ask questions about video lectures with millisecond-exact, click-to-seek citations.**  
> Built for 1–3 hour academic lectures, technical tutorials, and keynote presentations. Designed with **Swiss Minimalism**—dark, flat 2D, zero gradients, zero shadows, pure typography, and accessible high-contrast mechanics.

---

## 1. Project Overview & Product Philosophy

Long-form educational videos (1–3 hours) are rich in technical depth but frustratingly opaque to navigate. Finding the exact 20 seconds where a lecturer clarifies a mathematical proof, code algorithm, or architecture design usually requires scrubbing through endless video timelines or reading unindexed auto-generated captions.

**TimeSliceIQ** transforms any YouTube video into an interactive, grounded knowledge workspace:
- **Instant Ingestion**: Paste a YouTube lecture URL to retrieve transcripts, parse semantic metadata, and index lecture chunks into an in-memory vector store in seconds.
- **Grounded AI Answers**: Powered by Google Gemini 2.5 Flash, TimeSliceIQ answers questions using *only* the retrieved transcript chunks. Every factual statement is backed by verifiable citations.
- **Click-to-Seek Precision**: Citations are rendered as interactive timestamp chips (`12:45`, `01:04:22`). Clicking any chip immediately seeks the embedded YouTube player to the exact second and highlights the corresponding line in the synchronized transcript pane.
- **Hallucination Prevention**: Gemini is constrained via strict JSON schema outputs to cite abstract chunk IDs (`["c0", "c17"]`) rather than generating freeform timestamps. The backend cross-references and validates every chunk ID against indexed timecodes, completely preventing hallucinated timestamps. If a concept is not covered in the lecture, the system explicitly states: *"This is not covered in the video."*

### Product & Design Philosophy: Swiss Minimalism
The user interface follows the core tenets of the International Typographic Style (Swiss Design), adapted for modern dark-mode software:
- **Dark, Flat 2D Palette**: Background `--bg` (`#0D0D0D`), cards `--surface` (`#151515`), elevated panels `--surface-2` (`#1E1E1E`), and hairline rules `--rule` (`#2B2B2B`).
- **No Skeuomorphism, No Fluff**: 0 drop shadows, 0 text shadows, 0 gradients, and 0 blur/frosted-glass backdrop filters.
- **Geometric Restraint**: All borders use an intentional, crisp 2px radius (`--radius: 2px`).
- **Typography as Primary Interface**: Single typeface family **Inter**, restricted to regular (400) and semibold (600) weights. All time displays, timestamps, and search counters strictly utilize monospace tabular numbers (`font-variant-numeric: tabular-nums`).
- **Strict Accent Budget**: The vibrant International Orange accent (`--accent: #FF6A00`) is budgeted to less than 10% of screen surface area. All text placed atop `--accent` strictly uses dark ink (`--accent-ink: #0D0D0D`), surpassing WCAG AA standards with a verified **6.77:1 contrast ratio**.

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend Client (React SPA · Vite · TypeScript)"]
        UI["Landing / AppShell Layout\n(12-Column Responsive Grid)"]
        Chat["Chat Thread & Composer\n(TanStack Query useChat)"]
        Player["YouTube Player Pane\n(YouTube IFrame API · 16:9)"]
        TranscriptUI["Synchronized Transcript Panel\n(Time-highlighting & Search)"]
    end

    subgraph Gateway["Vercel Edge & Serverless Gateway"]
        Rewrites["vercel.json Routing Rules\nStatic Frontend (/*) vs API (/api/*)"]
        Headers["Strict Security Headers\n(CSP, nosniff, Referrer-Policy)"]
    end

    subgraph Backend["Backend API (FastAPI · Python 3.12/3.13)"]
        RateLimiter["Sliding Window Rate Limiter\n(60 req/min per IP)"]
        IngestRoute["/api/ingest\n(Concurrent Fetch & Pipeline)"]
        ChatRoute["/api/chat\n(Grounded RAG Pipeline)"]
        
        subgraph Pipeline["Ingest & Indexing Pipeline"]
            URLParser["URL Parser\n(11-char ID regex & domain whitelist)"]
            YTFetcher["Transcript Fetcher\n(youtube-transcript-api + optional Proxy)"]
            Chunker["Overlapping Chunker\n(60s / 220 words / 20% overlap)"]
            GeminiEmbed["Gemini Embedder\n(gemini-embedding-001 · 768-dim)"]
        end

        subgraph Storage["Vector Store"]
            VecStore["NumpyVectorStore\n(Pure NumPy Cosine Similarity · < 5ms)"]
        end

        subgraph Synthesis["Grounded Synthesis Engine"]
            GeminiLLM["Gemini 2.5 Flash\n(response_schema=GeminiResponseSchema)"]
            CitationMapper["Citation Validator\n(Chunk ID -> Label & Seconds)"]
        end
    end

    %% Client Gateway Interactions
    UI -->|HTTP POST /api/ingest| Rewrites
    Chat -->|HTTP POST /api/chat| Rewrites
    Rewrites --> RateLimiter

    %% Ingest Pipeline
    RateLimiter --> IngestRoute
    IngestRoute --> URLParser
    URLParser --> YTFetcher
    YTFetcher --> Chunker
    Chunker --> GeminiEmbed
    GeminiEmbed -->|Embeddings + Chunks| VecStore

    %% Chat Pipeline
    RateLimiter --> ChatRoute
    ChatRoute -->|Query Embedding| VecStore
    VecStore -->|Top-8 Relevant Chunks| GeminiLLM
    GeminiLLM -->|Structured JSON: Answer Blocks + Chunk IDs| CitationMapper
    CitationMapper -->|ChatResponse: Text Blocks + Verified Citations| Chat

    %% Player Seeking
    Chat -->|Click Citation Chip\nseconds: 765.0| Player
    Player -.->|Playback Time Update| TranscriptUI
```

### Video Ingestion & Question-Answering Walkthrough
1. **Ingest**: The user submits a YouTube URL. The backend validates the 11-character video ID, asynchronously fetches video metadata and transcript snippets in parallel, groups snippets into readable ~12-second lines for the UI, and chunks the transcript into overlapping 60-second semantic windows.
2. **Embed & Index**: Chunk texts are embedded via `gemini-embedding-001` in batches of 100 with exponential backoff and indexed into the high-performance in-memory `NumpyVectorStore`.
3. **Chat**: The user asks a question. The query is converted into an embedding, retrieving the top 8 most semantically relevant chunks (cosine similarity benchmarked at < 1ms).
4. **Structured Synthesis**: The retrieved chunks and question are sent to `gemini-2.5-flash` with a strict prompt and JSON schema. Gemini provides answers referencing only chunk IDs (`["c0", "c3"]`).
5. **Interactive Seeking**: The backend maps valid chunk IDs to exact video timestamps (`seconds: 765.0`, `label: "12:45"`). When the user clicks the resulting chip, the frontend calls `player.seekTo(765.0, true)`, jumping immediately to the cited moment.

---

## 3. Monorepo Directory Layout

```
TimeSliceIQ/
├── backend/                        # FastAPI Python serverless backend
│   ├── app/
│   │   ├── config.py               # Pydantic Settings & environment parsing
│   │   ├── dependencies.py         # FastAPI dependency injection providers
│   │   ├── errors.py               # Centralized exception handlers & error schemas
│   │   ├── main.py                 # Application factory, middlewares & routes
│   │   ├── schemas.py              # Pydantic domain models & ErrorCode enum
│   │   ├── routes/
│   │   │   ├── chat.py             # POST /api/chat endpoint & lazy indexing
│   │   │   └── ingest.py           # POST /api/ingest endpoint
│   │   └── services/
│   │       ├── chroma_store.py     # Optional ChromaDB vector store backend
│   │       ├── chunker.py          # Overlapping sliding-window transcript chunker
│   │       ├── embedder.py         # Gemini batch embedding with tenacity retries
│   │       ├── metadata.py         # YouTube oEmbed metadata fetcher
│   │       ├── numpy_store.py      # Production pure-NumPy vector store (< 5ms)
│   │       ├── prompt.py           # System instructions & JSON response schema
│   │       ├── retriever.py        # Top-k cosine similarity chunk retriever
│   │       ├── synthesizer.py      # Gemini structured synthesis & citation mapper
│   │       ├── transcript.py       # youtube-transcript-api async wrapper & proxy
│   │       └── url_parser.py       # YouTube URL parser & 11-char ID validation
│   ├── eval/                       # Evaluation suites & benchmark questions
│   │   └── questions.json          # Curated evaluation dataset
│   ├── scripts/
│   │   ├── bench_vector_store.py   # Latency benchmark for vector store (< 5ms)
│   │   └── export_openapi.py       # Exports openapi.json from FastAPI app
│   ├── tests/                      # Pytest suite & Hypothesis property tests
│   ├── pyproject.toml              # Ruff & Pyright tool configuration
│   ├── pytest.ini                  # Pytest asyncio settings
│   └── requirements.txt            # Python dependencies (pinned versions)
│
├── frontend/                       # Vite + React 18 + TypeScript SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── AppShell/           # Header, dual-pane desktop & mobile layouts
│   │   │   ├── ChatComposer/       # Textarea, char counter, and send button
│   │   │   ├── ChatThread/         # Message bubbles, claim blocks, citation chips
│   │   │   ├── ErrorState/         # Typed error alerts, countdowns, retry actions
│   │   │   ├── Landing/            # Typographic hero & flush-left URL input
│   │   │   ├── PlayerPane/         # YouTube IFrame player & metadata display
│   │   │   ├── primitives/         # Button, TextInput, Tabs, Chip, Rule, Skeleton
│   │   │   ├── TimestampChip/      # Tabular timecode chip with seekTo handler
│   │   │   └── TranscriptPanel/    # Full synchronized transcript with search
│   │   ├── contexts/
│   │   │   └── PlayerContext.tsx   # YouTube player state & seekTo dispatcher
│   │   ├── hooks/
│   │   │   ├── useChat.ts          # TanStack mutation hook for /api/chat
│   │   │   ├── useIngest.ts        # TanStack mutation hook for /api/ingest
│   │   │   └── useYouTubePlayer.ts # Custom hook wrapping player context
│   │   ├── lib/
│   │   │   ├── api-client.ts       # Typed Fetch HTTP client mapping errors
│   │   │   └── format.ts           # Millisecond/second to HH:MM:SS formatters
│   │   ├── types/
│   │   │   └── api.ts              # Auto-generated TypeScript types from OpenAPI
│   │   ├── App.tsx                 # Root application state & screen coordinator
│   │   ├── CONTRAST_REPORT.md      # WCAG 2.1 AAA/AA relative luminance report
│   │   ├── DESIGN_AUDIT.md         # Design QA audit validating Swiss Minimalism
│   │   ├── main.tsx                # React DOM root & QueryClientProvider
│   │   ├── reset.css               # Box-sizing reset & modern browser normalizer
│   │   └── tokens.css              # CSS custom properties (colors, type scale)
│   ├── tests/                      # Vitest test suites (115 passing tests)
│   ├── package.json                # Frontend npm scripts & dependencies
│   ├── tsconfig.json               # Strict TypeScript configuration
│   └── vite.config.ts              # Vite dev server & proxy configuration
│
├── scripts/
│   ├── generate-types.ps1          # Windows PowerShell script to export API types
│   └── generate-types.sh           # Bash script to export API types
│
├── .env.example                    # Environment variable template
├── openapi.json                    # Exported OpenAPI 3.1.0 schema specification
├── package.json                    # Monorepo workspaces definition
└── vercel.json                     # Multi-service Vercel deployment configuration
```

---

## 4. Environment Variables

All backend configuration is managed through strongly typed Pydantic settings (`app/config.py`).

| Variable | Type | Default | Secret? | Description |
|---|---|---|---|---|
| `GEMINI_API_KEY` | String | `""` | **Yes (Secret)** | **Required.** Google Gemini API key from Google AI Studio. Used for embeddings and LLM answer generation. |
| `GEMINI_MODEL` | String | `gemini-2.5-flash` | No (Public) | Model name used for question synthesis and follow-up generation. |
| `GEMINI_EMBED_MODEL`| String | `gemini-embedding-001` | No (Public) | Model name used for generating 768-dimensional transcript chunk embeddings. |
| `VECTOR_BACKEND` | String | `numpy` | No (Public) | Vector store implementation (`numpy` or `chroma`). `numpy` is recommended for serverless deployment (zero native C++ dependencies). |
| `YT_PROXY_URL` | String | `None` | **Yes (Secret)** | *Optional.* HTTP/HTTPS proxy URL (`http://user:pass@proxy:port`) to bypass YouTube datacenter IP rate limits. |
| `RATE_LIMIT_PER_MINUTE` | Integer | `60` | No (Public) | Max requests allowed per client IP per minute before returning HTTP 429 (`RATE_LIMITED`). |

Create your local `.env` file at the root of the workspace:
```bash
cp .env.example .env
```

---

## 5. Quickstart & Local Development

### Prerequisites
- **Node.js**: v18.0.0 or higher
- **npm** or **pnpm**: v9+
- **Python**: v3.11, v3.12, or v3.13
- **Google Gemini API Key**: [Get a key at Google AI Studio](https://aistudio.google.com/)

---

### Method A: Single Command with `vercel dev` (Recommended)
Running through the Vercel CLI closely mirrors production, routing frontend requests and `/api/*` rewrites identically through a single local port (`http://localhost:3000`).

1. **Install Vercel CLI**:
   ```bash
   npm install -g vercel
   ```

2. **Install Dependencies**:
   ```bash
   # Install root and frontend packages
   npm install

   # Setup Python virtual environment
   python -m venv .venv
   # Windows:
   .venv\Scripts\Activate.ps1
   # macOS / Linux:
   source .venv/bin/activate

   pip install -r backend/requirements.txt
   ```

3. **Configure Environment**:
   Ensure `.env` exists in the project root with your `GEMINI_API_KEY`.

4. **Start Development Environment**:
   ```bash
   vercel dev
   ```
   Open `http://localhost:3000` in your browser.

---

### Method B: Concurrent Development Servers
You can also run the FastAPI backend and Vite frontend dev servers independently.

#### 1. Backend Server (Port 8000)
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
FastAPI interactive docs will be available at: `http://localhost:8000/docs`.

#### 2. Frontend Server (Port 5173)
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Vite dev server starts on `http://localhost:5173`. Frontend API calls are automatically proxied to `http://localhost:8000` via `vite.config.ts`.

---

## 6. Testing & Quality Bars

TimeSliceIQ adheres to strict quality benchmarks across both backend and frontend codebases.

### Backend Testing Suite

```bash
cd backend

# 1. Run all unit, integration, and property tests
pytest

# 2. Run with verbose output
pytest -v

# 3. Code formatting & linting with Ruff
ruff check .

# 4. Type checking with Pyright
pyright
```

#### Property-Based Testing with Hypothesis
The transcript chunker (`backend/app/services/chunker.py`) is verified using `hypothesis` property-based testing (`backend/tests/test_chunker.py`):
- **Monotonic Ordering**: Validates that chunk start times are strictly non-decreasing across arbitrary inputs (`test_property_chunks_ordered_by_start_s`).
- **Sequential ID Format**: Verifies all chunk IDs match the strict `c\d+` regex (`c0`, `c1`, `c2`, ...).
- **Infinite Loop Termination**: Fuzzes chunking logic with NaN, positive/negative infinity, extreme windows, and negative durations to guarantee termination without hanging.

#### Vector Store Query Latency Benchmark
To verify that pure-NumPy vector search meets the sub-5ms requirement for interactive chat:
```bash
cd backend
python scripts/bench_vector_store.py
```
*Benchmark Results (AMD Ryzen / Apple Silicon / Intel i7):*
- `N = 50 chunks` (15-min video): **~0.15 ms** (target: < 5.0 ms)
- `N = 200 chunks` (1-hour lecture): **~0.38 ms** (target: < 5.0 ms)
- `N = 500 chunks` (2.5-hour lecture): **~0.92 ms** (target: < 5.0 ms)

---

### Frontend Testing Suite

```bash
cd frontend

# 1. Run Vitest component & unit tests (115 tests)
npm test

# 2. TypeScript strict typecheck
npm run typecheck

# 3. ESLint with zero-warning threshold
npm run lint

# 4. Production bundle build
npm run build
```

#### Synchronizing TypeScript Types with OpenAPI
Whenever backend Pydantic models change, update the OpenAPI spec and frontend contract:
```powershell
# Windows
.\scripts\generate-types.ps1

# Linux / macOS
./scripts/generate-types.sh
```

---

## 7. Vercel Deployment Instructions

TimeSliceIQ is configured as a **single-project monorepo** on Vercel using the modern `services` specification in `vercel.json`.

### `vercel.json` Configuration
```json
{
  "services": {
    "frontend": {
      "root": "frontend/",
      "framework": "vite"
    },
    "backend": {
      "root": "backend/",
      "entrypoint": "app.main:create_app"
    }
  },
  "rewrites": [
    { "source": "/api/:path*", "destination": { "service": "backend" } },
    { "source": "/(.*)", "destination": { "service": "frontend" } }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()" },
        {
          "key": "Content-Security-Policy",
          "value": "default-src 'self'; frame-src https://www.youtube-nocookie.com; script-src 'self' 'unsafe-inline' https://www.youtube.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' https://i.ytimg.com data:; connect-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com;"
        }
      ]
    }
  ],
  "functions": {
    "backend/**/*.py": {
      "maxDuration": 60
    }
  }
}
```

### Deployment Steps
1. **Push to Git**: Push the repository to GitHub or GitLab.
2. **Import into Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new).
   - Select the repository.
   - Leave the root directory as `./` (the monorepo root).
3. **Configure Environment Secrets**:
   In the Vercel Project Settings under **Environment Variables**, add:
   - `GEMINI_API_KEY`: Your Google AI Studio API key.
   - `VECTOR_BACKEND`: `numpy`
   - `YT_PROXY_URL`: *(Optional)* Your residential or datacenter proxy URL.
4. **Deploy**:
   Click **Deploy**. Vercel will build the Vite frontend bundle and package the Python FastAPI function.
5. **Verify maxDuration**:
   Because analyzing long lecture transcripts (1–3 hours) involves fetching transcripts, computing batch embeddings, and streaming LLM answers, the backend functions are allocated `maxDuration: 60` seconds (available on Vercel Pro/Enterprise).

---

## 8. Known Limitations & Architecture Trade-offs

| Architecture Decision | Trade-off / Limitation | Mitigation & Implementation Details |
|---|---|---|
| **YouTube Cloud IP Blocking** | YouTube frequently rate-limits or blocks known datacenter IP blocks (AWS, Vercel, GCP) with HTTP 429 or bot challenges when calling transcript endpoints. | TimeSliceIQ intercepts these exceptions and maps them to a typed `ErrorCode.TRANSCRIPT_BLOCKED`. The `backend/app/services/transcript.py` fetcher natively supports configuring a proxy (`YT_PROXY_URL`) using `youtube-transcript-api`'s `GenericProxyConfig` to tunnel requests through residential proxies. |
| **Serverless Memory vs Ephemeral VectorStore** | Vercel Serverless Functions spin up on demand and do not share in-memory state across instances. A vector collection created in an ingest request may not be present in memory on a subsequent chat request hitting a different instance. | Rather than bundling heavyweight persistent database engines like ChromaDB (which exceed Vercel's 250MB uncompressed limit and require C++ build tools), TimeSliceIQ uses `NumpyVectorStore`. In `backend/app/routes/chat.py`, `ensure_indexed()` lazily re-indexes transcript chunks on cold starts, providing instant recovery with minimal latency overhead. |
| **Strict 11-Character Video ID Regex** | Any URL that does not strictly conform to standard YouTube video identifiers (`^[a-zA-Z0-9_\-]{11}$`) is rejected immediately. Non-standard playlists, channel URLs, or embeds with unresolvable IDs fail at input validation. | Rejections occur immediately at the perimeter with an informative `ErrorCode.INVALID_URL`, avoiding wasted Gemini API tokens or unhandled upstream network exceptions. |
| **Token Window vs Chunk Density for 3h Lectures** | A 3-hour lecture produces ~180 minutes of continuous audio. Chunking every 60s with 20% overlap yields ~220 chunks. Sending all chunks to an LLM context window would be slow and costly. | TimeSliceIQ uses two-stage retrieval: embeddings index all chunks, and `retrieve_chunks()` extracts only the top-8 most semantically relevant chunks. This keeps the LLM prompt under 4,000 tokens while preserving high answer accuracy. |
| **Deterministic Timestamp Mapping** | Large language models frequently make arithmetic errors when asked to output timestamps (e.g. converting 125 seconds into `02:05`). | Gemini is strictly instructed **never** to write timestamps in answer text. Instead, Gemini provides chunk IDs (`["c12"]`), and the Python backend deterministically maps the chunk ID to verified seconds (`720.0`) and formatted labels (`"12:00"`). |

---

## 9. License

MIT License. See [LICENSE](LICENSE) for details.
