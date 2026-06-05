# Saransh — AI Document Intelligence

Saransh is an agentic multimodal document summarizer and resume matcher. Powered by **Amazon Bedrock (Nova Micro & Titan Embeddings)** and orchestrated using **LangGraph**, it uses a multi-agent system to intelligently parse, analyze, retrieve context (RAG), summarize documents, and match resumes against job profiles.

## Architecture

- **Frontend**: React + Vite + Tailwind CSS v3
- **Backend**: FastAPI + LangGraph + FAISS
- **AI/LLM**: Amazon Bedrock
  - LLM: `amazon.nova-micro-v1:0` (Fast, cost-effective reasoning)
  - Embeddings: `amazon.titan-embed-text-v2:0` (For RAG and semantic job matching)
- **Local Fallback**: Gracefully degrades to local TF-IDF and `sentence-transformers` if AWS credentials are not provided during development.

## Features & Security

- **Multi-Agent Orchestration**: Specialized agents for parsing, analysis, retrieval, summarization, quality checking, and career advice.
- **Resume Mode**: Extracts structured profile data from resumes and matches them against job postings using semantic similarity.
- **Security & Rate Limiting**:
  - IP-based rate limiting (10 requests/min max)
  - Strict file size limits (10MB max)
  - Server-side file extension validation
  - In-memory processing (files are never saved to disk to maintain data privacy)
- **Cost Optimization**: Utilizes Bedrock's most economical models (Nova Micro) and local FAISS indexes.

---

## 🚀 Quick Start (Local Development)

### 1. Backend Setup

1. Open a terminal in the `backend` folder.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows Command Prompt / PowerShell
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
   Add your AWS credentials to `.env`. Set `USE_BEDROCK=true`.
4. Start the server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### 2. Frontend Setup

1. Open a terminal in the `frontend` folder.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```
4. Open `http://localhost:5173` in your browser.

---

## 🌍 Deployment Guide

### Backend — AWS Elastic Beanstalk (Free Tier)

We will deploy the FastAPI backend to an AWS Elastic Beanstalk Python environment.

1. **Prerequisites**: 
   - Install the [EB CLI](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-install.html).
   - Ensure your IAM user has `AWSElasticBeanstalkFullAccess`.

2. **Initialize EB in the backend folder**:
   ```bash
   cd backend
   eb init -p python-3.12 saransh-api --region us-east-1
   ```

3. **Create the Environment (Free Tier - t3.micro)**:
   ```bash
   eb create saransh-api-env --instance_type t3.micro --single -ip aws-elasticbeanstalk-ec2-role
   ```

4. **Configure Environment Variables**:
   Set your Bedrock and AWS credentials in the Beanstalk environment.
   ```bash
   eb setenv USE_BEDROCK=true \
             AWS_ACCESS_KEY_ID="your_key" \
             AWS_SECRET_ACCESS_KEY="your_secret" \
             AWS_DEFAULT_REGION="us-east-1" \
             CORS_ORIGINS="https://your-frontend-url.vercel.app"
   ```

5. **Deploy**:
   ```bash
   eb deploy
   ```
   *Note: Beanstalk will automatically use the `requirements.txt` and look for `application.py` or use a Procfile. Ensure you have configured the entry point properly (e.g., creating a `Procfile` with `web: uvicorn app.main:app --host=0.0.0.0 --port=$PORT`).*

### Frontend — Vercel

The React frontend can be quickly deployed to Vercel.

1. Create a GitHub repository and push your code.
2. Go to [Vercel](https://vercel.com) and click **Add New Project**.
3. Import your GitHub repository.
4. Set the **Framework Preset** to `Vite`.
5. Set the **Root Directory** to `frontend`.
6. Add the following **Environment Variable**:
   - `VITE_API_URL`: The URL of your deployed Elastic Beanstalk backend (e.g., `http://saransh-api-env.eba-xxxx.us-east-1.elasticbeanstalk.com`).
7. Click **Deploy**.

## Security Considerations for Production

1. **IAM Roles (Best Practice)**: Instead of passing hardcoded `AWS_ACCESS_KEY_ID` into the Elastic Beanstalk environment variables, assign an **IAM Instance Profile** to the EC2 instances running your Beanstalk environment with `AmazonBedrockFullAccess`. The `boto3` client will automatically pick up the role.
2. **CORS Configuration**: Restrict the `CORS_ORIGINS` in your backend `.env` to ONLY your production frontend domain (e.g., `https://saransh.vercel.app`).
3. **HTTPS**: If using Beanstalk, set up a Load Balancer with an ACM (AWS Certificate Manager) SSL certificate to ensure secure `https://` communication between the Vercel frontend and the AWS backend.
4. **Rate Limits**: The app currently uses IP-based rate-limiting via `slowapi` (10 RPM). Adjust `RATE_LIMIT_PER_MINUTE` depending on expected traffic to prevent Bedrock abuse.

---
Built by Chinmay.
