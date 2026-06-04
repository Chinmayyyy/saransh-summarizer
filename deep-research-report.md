# Executive Summary

Amazon Bedrock enables building retrieval-augmented-generation (RAG) pipelines that ingest documents, compute embeddings, and call LLMs (Claude, CoHere, Titan, etc.) for tasks like summarization.  For example, Bedrock is explicitly promoted for “data summarization – extract key insights and generate concise summaries from large datasets”. In practice, a complete summarizer/agent pipeline involves: ingesting documents (PDF/Word/CSV/JSON), cleaning and chunking text, computing embeddings with a Bedrock embedding model, storing them in a vector store, then using a Bedrock LLM for summarization or answering user queries. The pipeline can be exposed via a FastAPI backend and a simple React/Vite frontend, and deployed on AWS free-tier resources (EC2, Lightsail, Elastic Beanstalk). This report covers the full end-to-end design and steps: architecture (with diagrams), code snippets, AWS Bedrock API usage (via boto3), prompt templates, vector database choices (FAISS, Milvus, Weaviate, Pinecone, OpenSearch, etc.), RAG strategy, agent orchestration (LangChain/LangGraph), testing/CI-CD, Docker/IAM, cost trade-offs, local dev/testing, frontend/API, deployment, GitHub repo structure, README outlines, demo checklist, and even a concise resume bullet. Official AWS sources and examples are cited throughout to ground the recommendations.

## Architecture Overview  

 *Figure: Example RAG-based document summarization architecture. A user sends a text or file via a REST API (e.g. Amazon API Gateway) to a backend (e.g. AWS Lambda or EC2/FastAPI). The backend parses and cleans the document, splits it into chunks, computes embeddings (using Cohere or Titan) and stores them in a vector DB (Amazon OpenSearch or similar). Upon a user query or summarization request, the system converts the query to an embedding, retrieves top-k relevant chunks, and sends them (with a prompt) to a Bedrock LLM (e.g. Claude 3) to generate the summary or answer. The response is returned through the API to the user. This high-level serverless workflow (API Gateway → Lambda → Bedrock) is illustrated in AWS reference architectures.* 

```mermaid
graph LR
    subgraph Client
      U[User (UI)] -->|Uploads PDF/Query| API[API Gateway/React Frontend]
    end
    subgraph Server
      API --> B[Backend (FastAPI/Lambda)]
      B --> P[Document Parser (PDF/DOCX/CSV/JSON)]
      P --> C[Text Cleaning & Chunking]
      C --> E[Embeddings (Bedrock/Boto3)]
      E --> V[Vector Database (OpenSearch/Milvus/etc.)]
      V --> R[RAG Retrieval (k-NN search)]
      R --> H[Bedrock LLM (e.g. Claude 3)]
      H --> S[Summarizer/Agent Logic]
      S --> API
    end
    API --> FE[Frontend (React/Vite UI)]
```

The flow (1–7) matches AWS’s documented RAG app example: the user query hits API Gateway, invokes Lambda to call Bedrock (Claude) which retrieves context from a vector store (OpenSearch) and returns a response. Our architecture replaces Lambda with a Python FastAPI app (on free-tier EC2/Beanstalk/Lightsail) and uses Amazon’s embedding models or self-hosted LLMs for local dev. We use IAM roles that grant only `bedrock:InvokeModel` (and related) permissions to follow least-privilege principles.

## Document Ingestion & Parsing  

We support multiple file formats. **PDFs** can be parsed using libraries like [pdfplumber](https://pypi.org/project/pdfplumber/) or [PyMuPDF (fitz)](https://pymupdf.readthedocs.io) to extract text. For example:

```python
from pypdf import PdfReader
reader = PdfReader("file.pdf")
pages = [page.extract_text() for page in reader.pages]
text = "\n".join(pages)
```

According to benchmarks, `pdfplumber` or `PyMuPDF` give clean text, and pdfplumber excels at table extraction. **DOCX** files can be read with `python-docx` or `docx2txt` to extract paragraphs. **CSV/JSON** data can be read with Pandas (`pandas.read_csv/read_json`) or the standard `csv`/`json` libraries. In all cases, we extract the raw text content. For scanned PDFs or images, AWS Textract or OCR could be used, but for a fresher’s POC we assume text-embedded PDFs.

Once text is extracted, we remove boilerplate (headers/footers), normalize whitespace, and clean up any non-text artifacts. We may also remove stop words or perform basic NLP cleaning (e.g. using `nltk` or `re` for tokenization). For simplicity, we typically convert to lower case and strip non-ASCII if needed.

## Text Cleaning & Chunking  

Large documents must be split into manageable chunks before embedding or LLM processing. We first break text into paragraphs or fixed-length segments. For example, we can split by sentence and group ~200–500 words (or ~1000 tokens) per chunk:

```python
import nltk
sentences = nltk.sent_tokenize(text)
chunks = []
current = ""
for sent in sentences:
    if len(current) + len(sent) < 1000:
        current += " " + sent
    else:
        chunks.append(current.strip())
        current = sent
if current: chunks.append(current)
```

This yields a list of text chunks of ~500–1000 tokens. AWS best practices note that even though Titan embeddings can handle up to 8192 tokens, for retrieval it’s recommended to “segment documents into logical segments” (e.g. paragraphs) rather than sending whole books. We also filter out empty or very short chunks. These clean chunks are what we embed.

## Embeddings: Model Selection & Dimension  

We embed each chunk into a high-dimensional vector. AWS Bedrock offers several embedding models. A good choice is **Amazon Titan Embed Text v2.0** (model_id `amazon.titan-embed-text-v2:0`), which is optimized for retrieval tasks. Titan v2.0 accepts up to ~8,192 tokens (≈50k characters) and outputs a 1,024-dimensional vector by default (dimensions can be reduced to 512 or 256 if needed). Another option is **Cohere Embed v4 (multilingual)** (`cohere-embed-multilingual-v4:0`), which can take extremely long context (128k tokens per document) and output 256/512/1024/1536 dims. For simplicity, we typically use Titan for English or whichever is freely accessible.

We call the Bedrock embedding API via boto3. For example, using Titan v2:

```python
import boto3, json

client = boto3.client("bedrock-runtime", region_name="us-east-1")
model_id = "amazon.titan-embed-text-v2:0"
native_request = {"inputText": chunk_text}
response = client.invoke_model(modelId=model_id, body=json.dumps(native_request))
model_response = json.loads(response["body"].read())
embedding = model_response["embedding"]  # list of floats
# embedding is a 1024-dim vector by default
print(f"Generated embedding of length {len(embedding)}")
```

This matches AWS’s example code (see). We can batch multiple inputs per request if supported (e.g. Cohere’s Python API allows up to 96 texts per call). The output embeddings (lists of floats) are then stored in a vector store. Titan embeddings are relatively cheap: AWS pricing notes roughly $0.00002 per 1,000 tokens (nearly free), whereas generative tokens cost ~$6–$30 per million (see below).

## Vector Database Options  

For RAG retrieval, we need to store and query vectors. Options include self-hosted libraries and managed services:

| Vector Store         | Type           | Key Features                                                                                                   | Notes                                                                       |
|----------------------|----------------|---------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|
| **OpenSearch (AWS ES)** | Open-source | Full-text + vector hybrid search; supports HNSW k-NN; scalable shards; free open-source (no license fee). Integrates with AWS (managed OpenSearch Service supports vectors). | Good if already on ES; hybrid queries. High-capacity but not vector-specialized. |
| **Pinecone**         | SaaS         | Fully-managed vector DB; horizontal scale; free starter tier; pay-per-query. Claims sub-10ms for millions of vectors.  | Very fast and simple to use. Starts with free $0 tier; for production ~$0.096/hr pod. |
| **Weaviate**         | Open-source (BSD) + Cloud | Vector DB with GraphQL API; built-in modules (auto-embedding via OpenAI/Cohere, hybrid search). Can auto-vectorize uploads.  | Weaviate Cloud (WCS) is managed SaaS (pay $25+/mo + vector dims ~$0.095/million). Good for knowledge-graph style schemas.   |
| **Milvus (Zilliz)**  | Open-source (Apache) + Cloud | Highly scalable; supports CPU/GPU, multiple index types (IVF, HNSW, ANNOY). Managed Zilliz Cloud has free 5GB tier.  | Enterprise-grade for billions of vectors. More complex to run. |
| **Chroma**           | Open-source + Cloud | Python-first (pip install); HNSW indexing; easy API; good LangChain/LLM integration. Cloud has free $5 credits.  | Great for quick Python prototyping; up to ~10M vectors on one machine. |
| **pgvector (Postgres)** | Open-source  | Postgres extension for vectors; ACID DB; easy if already using RDS.  | Best for small-medium scale (millions of vectors); limited to CPU and degrades on large scale.  |
| **Redis (RediSearch)** | Open-source + Cloud | In-memory vector search; sub-ms latency; managed Redis Enterprise offers vector indexing.  | Very fast, but expensive (dedicated memory). Good if already on Redis. |

In summary, for a fresher’s AWS POC we might start with **AWS OpenSearch Service** (free-tier eligible) or **Chroma Cloud** (free tier), and later consider Pinecone or Weaviate for production. Each option above has trade-offs in cost, management, and scale. For prototyping, an in-memory FAISS index (Python library) could even be used for ~1M vectors, but for simplicity we use an external store.

## RAG Retrieval & Summarization Workflow  

At query time, we take the user query (or summarization request) and perform the following steps: (a) **Query embedding** – encode the query or prompt into a vector (using the same model, e.g. Titan v2). (b) **Nearest-neighbor search** – find the top-k document chunks from the vector DB by cosine or dot-product similarity. (c) **Context assembly** – fetch the corresponding text chunks. (d) **LLM prompt** – send those chunks as context to the Bedrock LLM along with an instruction (e.g. “Summarize the above text” or the user’s question). (e) **Generate answer/summary** – the LLM returns the summary. This is classic RAG: the LLM reasons over the retrieved context to produce a concise answer or summary. AWS’s example workflow explicitly has the Bedrock model do the similarity search inside the Knowledge Base: in practice, our app does the search externally but the idea is the same.  

We typically retrieve 3–5 chunks to keep prompts < context limit. A sample retrieval function (using Elastic/OpenSearch or Pinecone SDK) would return the nearest texts. Those are concatenated (with separators) into the prompt for summarization. For example: 

```
# Pseudocode for RAG prompt
context = "\n\n".join(top_k_chunks)
prompt = "Please provide a concise summary of the following document excerpts:\n\n" + context
response = bedrock_client.invoke_model(modelId="anthropic.claude-v2", body=json.dumps({
    "prompt": prompt,
    "temperature": 0.5,
    "max_tokens_to_sample": 500
}))
summary = json.loads(response["body"].read())["completion"]
```

This follows AWS guidance on using Bedrock for text generation.  

## Prompt Engineering  

Effective prompts greatly improve results. We use a **system prompt** to set the role, e.g.: “You are a highly efficient text summarizer. Provide a concise summary of the provided text.” This matches AWS examples: e.g. “You are a highly efficient text summarizer. Provide a concise summary of the prompted text…”. The **user prompt** then contains the chunked document (or concatenation of chunks). For multi-turn chat or agent tasks, we can prepend an instruction to the user’s question. Always include context-limiting parameters (max tokens) and control randomness (`temperature`, `topP`) in the Bedrock call. For example, we might set `temperature=0.2, topP=0.9` for factual summaries. AWS docs also recommend providing examples or bullet points in the prompt if needed. We test prompt variants manually to ensure coherent summaries.  

## Agent Orchestration (LangChain/LangGraph)  

To orchestrate multi-step logic, we can use frameworks like **LangChain** or **LangGraph**. AWS notes that LangChain supports Amazon Bedrock (including Nova/Premier models) out-of-the-box. LangGraph extends LangChain with graph-based workflows for complex agents. For example, one could define a LangChain RetrievalQA chain with a Bedrock LLM and an OpenSearch vector store. Or use LangGraph to chain multiple steps (e.g. question decomposition). In our simple POC, we implement a custom FastAPI route, but for production we could leverage LangChain’s `Bedrock` LLM class and `VectorDBQAChain` to simplify. The AWS Prescriptive Guidance highlights that LangChain/LangGraph provide “standardized interfaces” for Bedrock models and complex autonomous workflows. 

## Evaluation Metrics  

We evaluate summary quality using established metrics. AWS SageMaker documentation suggests **ROUGE-L**, **METEOR**, and **BERTScore** for text summarization accuracy. For a demo, we might manually compare to expected summaries or use a small test set. In CI we can run a few examples with known outputs and compute ROUGE-L (via HuggingFace’s `datasets` or `rouge_score` library) to detect regressions. Latency and throughput (requests per second) are also key metrics. We can log execution time for embedding lookup and LLM inference (Bedrock has ~300-500ms latency for Claude) to estimate cost and performance. Additionally, monitor token usage (Bedrock returns `inputTextTokenCount`) to analyze prompt lengths.  

## Testing & CI/CD  

We include unit tests (e.g. using `pytest`) for individual components: parsing, embedding calls (mocking Bedrock), vector search (mock vectors), and the FastAPI endpoints. For end-to-end testing, we use a small sample PDF/CSV to verify the summary output. For CI/CD, we can set up a GitHub Actions workflow (`.github/workflows/ci.yml`) that lints (flake8), runs tests, and optionally builds a Docker image. Upon pushes to `main`, the pipeline could deploy to AWS (e.g. via EB CLI or AWS CLI). For deployment automation: use Terraform or AWS CDK for infra, or use EB’s “`eb deploy`” in CI. 

```yaml
name: CI
on: [push]
jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt
      - name: Run tests
        run: |
          pytest --maxfail=1 --disable-warnings -q
```

## Docker, .env, and IAM Policies  

We provide a `Dockerfile` to containerize the backend (for EB or ECS). For example:

```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ . 
EXPOSE 80
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80"]
```

Environment variables (in `.env`) hold sensitive info: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `BEDROCK_MODEL_ID`, etc. We use `python-dotenv` or `os.getenv()` in code to load these. For AWS IAM, we attach a minimal policy to the service role or user. A least-privilege example for calling Bedrock is:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ],
    "Resource": "*"
  }]
}
```

As AWS docs show, you only need the `bedrock:InvokeModel` actions for inference. If using AWS services (API Gateway, S3, OpenSearch), grant only needed access (e.g. `s3:GetObject`, `es:ESHttp*`).

## Cost and Latency Considerations  

Costs scale with model choice and usage. For example, Anthropic Claude on Bedrock is relatively expensive: **\$6 per 1M input tokens and \$30 per 1M output tokens**. Titan embeddings are much cheaper (on the order of \$0.02 per 1k tokens, i.e. a few cents per million). Therefore, use smaller embedding dims (256) if cost-sensitive, and batch calls. Free-tier resources (t2.micro EC2, AWS Lightsail \$3.50/mo, S3, OpenSearch t3.small) can host the demo at negligible cost. Monitor Bedrock usage (via AWS Cost Explorer) and consider using asynchronous batch mode for large volumes. Latency-wise, Claude invocation is ~0.3–1s per call. We can trade off prompt length vs calls: summarizing all chunks individually vs sequential summarization. A reasonable strategy is two-tier summarization: first summarize each chunk with Bedrock, then summarize the summaries.

## Local Development & Mocking  

During development (no Bedrock access), we can mock the LLM. One approach is to run a local LLM (e.g. a small GPT-J or LLaMA model via HuggingFace) and expose a similar REST API. LangChain’s `Bedrock` integration is identical in code to `OpenAI` integration, so swapping to a local GPT model is easy. For embeddings, we can use open-source text embeddings (like SentenceTransformers) as stand-ins for Titan. AWS’s Bedrock doesn’t have a local emulator, but by designing our code around a generic “LLM client” interface, we can substitute calls in tests. 

## Frontend (React/Vite)  

A minimal UI can be built with React (using Vite or `create-react-app`). The frontend has a file upload or text input form and shows the summary. It calls the backend API (e.g. `/summarize`) using `fetch` or `axios`. For example:

```jsx
// React snippet (using fetch)
async function summarizeDoc(file) {
  const text = await file.text();
  const res = await fetch("https://<api-endpoint>/summarize", {
    method: "POST",
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ text })
  });
  const data = await res.json();
  setSummary(data.summary);
}
```

Alternatively, AWS Amplify UI components or Material-UI can be used. For hosting, the React app can be deployed on **Vercel** (free hobby tier) or **AWS Amplify Hosting**. The API contract is simple: POST `/summarize` with `{ "text": "<document text>" }`, returns `{ "summary": "<result>" }`.

AWS’s example fullstack app shows a React frontend sending chat inputs to Bedrock via AppSync. We can do a simpler REST approach. 

## Deployment to AWS Free Tier  

On the AWS Free Tier, you get 750 hours/month of t2.micro or t3.micro EC2/Lightsail. We can deploy the FastAPI backend on an EC2 instance (with Security Group allowing HTTPS). Alternatively, **Elastic Beanstalk** can auto-manage this: EB itself is free (you only pay for the EC2 instance). For example:

```bash
eb init -p python-3.9 doc-summarizer-app
eb create doc-summarizer-env --instance_type t2.micro
```

This will launch the app behind a load balancer with SSL (if set up). For lightweight use, **AWS Lightsail** (\$3.50/mo Ubuntu plan) can also host our Docker container. The frontend can be on Vercel or AWS Amplify (both have free tiers for low traffic).

We should enable HTTPS (Let’s Encrypt or AWS Certificate Manager) in prod. Use CloudWatch logs for Lambda/EC2. For CI/CD, we can push to GitHub, and configure EB to auto-deploy on new tags. 

## GitHub Repository Structure  

A clear structure helps reviewers:

```
doc-summarizer/                # Root of repo
├── backend/                   # FastAPI backend code
│   ├── app.py                # FastAPI endpoints (e.g. /summarize)
│   ├── doc_parser.py         # PDF/CSV parsing utilities
│   ├── rag.py                # RAG orchestration logic
│   ├── requirements.txt      # Python dependencies (fastapi, boto3, uvicorn, pandas, PyPDF2, etc.)
│   └── Dockerfile            # Container build (as above)
│
├── frontend/                  # React frontend (optional)
│   ├── src/
│   │   └── App.jsx           # File upload form, fetch to API
│   ├── package.json
│   └── vite.config.js
│
├── .github/workflows/         # CI/CD configurations
│   └── ci.yml                # (see above)
│
├── .env.example              # Example environment variables file
├── .gitignore
├── README.md                 # Project overview and setup (see below)
└── LICENSE                   # e.g. MIT
```

## README Sections  

The `README.md` should include: 

- **Project Title & Description** – Brief summary of the app (e.g. “AWS Bedrock Document Summarizer POC” and its purpose).  
- **Architecture Diagram** – Embed the Mermaid or image from above, with a caption explaining the flow.  
- **Features** – List key features (PDF parsing, Bedrock integration, RAG, FastAPI endpoints, React UI).  
- **Getting Started** – Setup steps (Python env, AWS creds, install requirements) with shell commands, e.g.: 
  - `git clone ...`
  - `python3.9 -m venv venv && source venv/bin/activate`
  - `pip install -r requirements.txt`  
  - Create `.env` with AWS keys, Bedrock model ID, etc.  
  - `uvicorn app:app --reload` to run locally.  
- **Deployment** – How to deploy on AWS: e.g. using Elastic Beanstalk CLI or Lightsail.  
- **API Contract** – Describe the endpoint (POST `/summarize` expecting JSON with `text` or `file` and returning the summary).  
- **Usage** – Example requests and screenshot of output (if possible).  
- **Folder Structure** – Explain the code organization (as above).  
- **Dependencies** – List main libraries (FastAPI, Boto3, LangChain if used, PyPDF2, etc.).  
- **Limitations** – E.g. current model choices, single-user, etc.  
- **Future Work / Alternatives** – E.g. adding LangChain agents, more models, etc.  
- **License / Authors** – Attribution (for open-source license).  

Tables (e.g. vector DB comparison, embedding models) and Mermaid diagrams can be included in the README for clarity.

## Demo / Acceptance Checklist  

Before demo, ensure: 
- [ ] A test PDF/CSV can be uploaded via the UI or API and summarized meaningfully.  
- [ ] The summary quality is reasonable (no hallucinations).  
- [ ] Logging shows invocation count and latency for Bedrock.  
- [ ] All required AWS resources are provisioned with correct IAM.  
- [ ] Instructions in README work (someone can follow them to run the app).  
- [ ] Demo script ready: e.g. “Uploading this government report results in this summary.”  

Any failing test (parsing bug, timeouts, etc.) should be fixed beforehand.

## Assumptions and Alternatives

- *Assumption:* Freshers may not have Bedrock access by default. We assume Athena/Claude models are available in us-east-1. **Alternative:** Use open-source LLMs (Llama-3) locally if not.  
- *Assumption:* All docs are text-based (not scanned images). **Alternative:** Integrate AWS Textract or OCR library.  
- *Assumption:* Budget is minimal. We use free-tier or minimal AWS resources. **Alternative:** For production, scale to larger instances or dedicated managed services (Aurora, ECS, etc.).  
- *Assumption:* Single-user, small-scale usage. **Alternative:** Containerize and use auto-scaling groups for concurrent queries.  
- *Assumption:* Internet connectivity and API Key config. **Alternative:** Provide scripted export of outputs for offline review.  

Each choice (e.g. Titan vs Cohere, OpenSearch vs Pinecone) was made to balance ease-of-use and AWS integration, but alternatives (OpenAI GPT, Redis, etc.) could be substituted.

## Sample Shell Commands  

```bash
# Clone and set up environment
git clone https://github.com/<your-username>/doc-summarizer.git
cd doc-summarizer/backend
python3.9 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# AWS CLI configure (or set environment variables)
aws configure   # enter Access Key, Secret, region=us-east-1

# Run the FastAPI app locally
uvicorn app:app --reload

# (Optional) Build and run Docker container
docker build -t bedrock-summarizer:latest .
docker run -p 80:80 --env-file .env bedrock-summarizer:latest
```

## Sample FastAPI Skeleton  

```python
# backend/app.py
from fastapi import FastAPI
from pydantic import BaseModel
import boto3, os, json

app = FastAPI()
bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION"))

class SummarizeRequest(BaseModel):
    text: str

@app.post("/summarize")
async def summarize(req: SummarizeRequest):
    chunks = chunk_and_clean(req.text)      # your implemented function
    embeddings = []
    for chunk in chunks:
        response = bedrock.invoke_model(
            modelId=os.getenv("BEDROCK_MODEL_ID"),
            body=json.dumps({"inputText": chunk})
        )
        model_resp = json.loads(response["body"].read())
        embeddings.append(model_resp["embedding"])
    # Perform vector DB search (pseudo-code)
    docs = vector_search(embeddings)        # your implemented function
    context = "\n\n".join(docs)
    prompt = f"Summarize the following text:\n\n{context}"
    llm_resp = bedrock.invoke_model(
        modelId=os.getenv("BEDROCK_SUMMARY_MODEL"),
        body=json.dumps({"prompt": prompt, "max_tokens_to_sample": 500})
    )
    summary = json.loads(llm_resp["body"].read()).get("completion")
    return {"summary": summary}
```

This minimal app reads environment vars for AWS credentials, invokes Bedrock for embeddings and summarization, and returns JSON. In practice, error handling and batching would be added.

## Cost Example  

Using Bedrock pricing, summarizing a 5,000-token document (input+output) with Anthropic Claude might cost ~$0.00003 (5 * \$6/1M) for input and $0.00015 (5 * \$30/1M) for output, i.e. \$0.00018 per call. Embedding the same text with Titan (5k tokens) costs ~$0.0000001 (negligible). Thus, Bedrock inference costs dominate. We mitigate cost by summarizing chunks separately or using cheaper models for non-core tasks.

## Conclusion

We’ve outlined a comprehensive pipeline for a Bedrock-powered document summarizer/agent: from parsing to embedding to summarization, including code snippets and AWS best practices. This showcases skills in AWS GenAI services, Python API development, and full-stack deployment – all valuable for AI/GenAI roles at TCS. 

**Exact Resume Bullet:** *“Developed a Bedrock-powered document summarization POC: ingested PDF/CSV, cleaned and chunked text, generated embeddings (Amazon Titan), built an OpenSearch vector index, and invoked Amazon Bedrock LLM (Anthropic Claude) via a FastAPI Python backend. Deployed on AWS free-tier (Elastic Beanstalk + React front-end), implemented CI/CD and IAM least-privilege. Resulted in an end-to-end RAG summary demo for large documents.”* 

**References:** Implementation details and examples are drawn from AWS docs and sample apps.