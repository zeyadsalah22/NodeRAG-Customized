# NodeRAG Customization for Job Application Auto-Fill

## Overview

This repository contains a customized version of NodeRAG (Xu et al., 2025) specifically adapted for automated job application form filling. The customization extends the original NodeRAG framework with multi-user support, structured Question-Answer (Q&A) node integration, and first-person answer generation capabilities.

**Original Paper**: [NodeRAG: Structuring Graph-based RAG with Heterogeneous Nodes](https://arxiv.org/abs/2504.11544)  
**Authors**: Tianyang Xu, Haojie Zheng, Chengze Li, Haoxiang Chen, Yixin Liu, Ruoxi Chen, Lichao Sun

## Key Customizations

### 1. Multi-User Graph Architecture

**Objective**: Enable isolated knowledge graphs per user to maintain data privacy and support multi-tenant deployments.

**Implementation**:
- Modified `config/Node_config.py` to accept `user_id` parameter
- Implemented `effective_main_folder` routing: `main_folder/users/user_{user_id}/`
- Updated all pipeline components to use user-specific paths
- Ensured complete data isolation between users

**Files Modified**:
- `config/Node_config.py`
- `build/pipeline/INIT_pipeline.py`
- `WebUI/app.py`
- `Vis/html/visual_html.py`

**Backward Compatibility**: System works without `user_id` parameter, defaulting to original behavior.

### 2. Question-Answer Node Integration

**Objective**: Integrate structured Q&A pairs from job application history into the knowledge graph for answer reuse and style consistency.

**New Node Types**:

**Question Node** (`Q`):
- Attributes: `text`, `question_id`, `job_title`, `company_name`, `submission_date`, `embedding`
- Relationships: `has_answer → Answer Node`
- Indexed in separate HNSW index for semantic search

**Answer Node** (`A`):
- Attributes: `text`, `question_id`
- Relationships: `answers → Question Node`

**Implementation**:
- Created `build/component/question.py` and `build/component/answer.py`
- Implemented `build/pipeline/qa_pipeline.py` for Q&A node creation
- Built separate HNSW index for Question nodes (`question_hnsw.bin`)
- Integrated Q&A API client (`utils/qa_api_client.py`) supporting both mock and production modes

**Files Added**:
- `build/component/question.py`
- `build/component/answer.py`
- `build/pipeline/qa_pipeline.py`
- `utils/qa_api_client.py`
- `utils/readable_index.py` (extended with `question_index` and `answer_index`)

**Files Modified**:
- `build/Node.py` (added `QA_PIPELINE` state)
- `build/pipeline/__init__.py` (registered QA pipeline)
- `config/Node_config.py` (added Q&A paths and configuration)

### 3. Enhanced Search with Q&A Integration

**Objective**: Enable semantic search over Q&A pairs and integrate them into the retrieval pipeline for answer generation.

**Implementation**:
- Added `_search_qa_pairs()` method in `search/search.py` for Question node semantic search
- Integrated Q&A search into main `search()` method
- Implemented similarity threshold filtering (`qa_similarity_threshold`, default: 0.6)
- Configured top-k Q&A retrieval (`qa_top_k`, default: 3)
- Boosted Q&A nodes in PageRank personalization when similarity exceeds threshold
- Stored Q&A results in `Retrieval.qa_results` for answer generation

**Search Flow**:
1. Query decomposition (entities extraction)
2. Dual search: exact search + HNSW semantic search
3. Q&A semantic search (if Question HNSW index exists)
4. PageRank boosting with Q&A nodes (if similarity ≥ threshold)
5. Top-k retrieval with Q&A nodes included

**Files Modified**:
- `search/search.py` (Q&A search integration)
- `search/Answer_base.py` (Q&A results storage)
- `config/Node_config.py` (Q&A search parameters)

### 4. First-Person Answer Generation

**Objective**: Generate answers in first-person perspective as if the candidate is writing them, maintaining style consistency with previous answers.

**Implementation**:
- Rewrote answer prompt in `utils/prompt/answer.py` for first-person responses
- Added support for `job_context` parameter (job description)
- Added support for `qa_history` parameter (previous Q&A pairs for style consistency)
- Modified `answer()` and `answer_async()` methods to accept `job_context` parameter
- Formatted Q&A history from `retrieval.qa_results` for prompt inclusion

**Prompt Structure**:
```
CANDIDATE PROFILE: {info}
JOB CONTEXT (if available): {job_context}
PREVIOUS ANSWERS (for style consistency): {qa_history}
QUESTION: {query}
```

**Instructions**:
1. Write in first person (I/my/me)
2. Be specific and authentic
3. Reference actual experiences
4. Match writing style of previous answers
5. Tailor to job description when relevant

**Files Modified**:
- `utils/prompt/answer.py` (complete prompt rewrite)
- `search/search.py` (answer generation with job context and Q&A history)

## Architecture Changes

### Graph Construction Pipeline

The original NodeRAG pipeline (G₀ → G₄) has been extended with a Q&A integration phase:

**Original Pipeline**:
1. **Graph Decomposition** (G₀ → G₁): Text → Semantic Units (S), Entities (N), Relationships (R)
2. **Graph Augmentation** (G₁ → G₃): Attributes (A), High-level Elements (H), Overviews (O)
3. **Graph Enrichment** (G₃ → G₄): Text nodes (T), HNSW index, semantic edges

**Extended Pipeline**:
4. **Q&A Integration** (G₄ → G₅): Question nodes (Q), Answer nodes (A), Question HNSW index

**State Sequence**:
```
INIT → Document Pipeline → Text Pipeline → Graph Pipeline → QA Pipeline → 
Attribute Pipeline → Embedding Pipeline → Summary Pipeline → Insert Text Pipeline → HNSW Pipeline
```

### Search Pipeline

The search pipeline has been enhanced with Q&A semantic search:

**Original Search Flow**:
1. Query decomposition (entity extraction)
2. Dual search (exact + HNSW semantic)
3. Personalized PageRank (PPR)
4. Top-k retrieval
5. Answer generation

**Enhanced Search Flow**:
1. Query decomposition (entity extraction)
2. Dual search (exact + HNSW semantic)
3. **Q&A semantic search** (Question HNSW index)
4. Personalized PageRank (PPR) with Q&A boosting
5. Top-k retrieval (including Q&A nodes)
6. Answer generation with job context and Q&A history

## Configuration

### Multi-User Configuration

```yaml
user_id: 2  # Optional: enables user-specific routing
main_folder: "POC_Data/documents"
# Routes to: POC_Data/documents/users/user_2/
```

### Q&A Integration Configuration

```yaml
qa_api:
  enabled: true
  use_mock: true  # Use mock JSON file for development
  mock_data_path: "mock_data/mock_qa_data.json"
  base_url: "https://api.example.com"  # Production API URL
```

### Q&A Search Configuration

```yaml
qa_top_k: 3  # Number of Q&A pairs to retrieve
qa_similarity_threshold: 0.6  # Minimum similarity for PageRank boosting
```

## Usage Example

```python
from NodeRAG.search.search import NodeSearch
from NodeRAG.config.Node_config import NodeConfig

# Initialize configuration with user_id
config = NodeConfig(
    main_folder="POC_Data/documents",
    user_id=2  # User-specific graph
)

# Initialize search engine
search = NodeSearch(config)

# Search with job context
job_description = """
Python Developer position at TechCorp.
Requirements: 5+ years Python, Django, REST APIs.
"""

answer = search.answer(
    query="Describe a challenging project you've worked on",
    job_context=job_description
)

# Access Q&A results
qa_results = search.retrieval.qa_results
for qa_pair in qa_results:
    print(f"Question: {qa_pair['question']}")
    print(f"Answer: {qa_pair['answer']}")
    print(f"Similarity: {qa_pair['similarity']}")
```

## File Structure

```
NodeRAG-Customized/
├── build/
│   ├── component/
│   │   ├── question.py          # Question node class
│   │   ├── answer.py            # Answer node class
│   │   └── ...
│   ├── pipeline/
│   │   ├── qa_pipeline.py      # Q&A node creation pipeline
│   │   └── ...
│   └── Node.py                  # Main build orchestrator
├── config/
│   └── Node_config.py           # Configuration with user_id support
├── search/
│   ├── search.py                # Enhanced search with Q&A integration
│   └── Answer_base.py           # Retrieval class with qa_results
├── utils/
│   ├── qa_api_client.py         # Q&A API client
│   ├── prompt/
│   │   └── answer.py            # First-person answer prompt
│   └── ...
└── ...
```

## Technical Details

### Q&A Node Embeddings

- Question nodes are embedded using the same embedding client as other semantic nodes
- Question embeddings are stored in a separate HNSW index (`question_hnsw.bin`)
- Answer nodes are not embedded (linked via `has_answer` edges)

### Q&A Search Algorithm

1. Generate query embedding using same model as Question nodes
2. Search Question HNSW index for top-k similar questions
3. Retrieve connected Answer nodes via `has_answer` edges
4. Calculate similarity scores (1 - distance) for ranking
5. Filter by similarity threshold before PageRank boosting

### PageRank Boosting

- Q&A nodes with similarity ≥ `qa_similarity_threshold` receive 20% weight boost
- Boosted nodes are included in PageRank personalization vector
- Enhances retrieval of relevant Q&A pairs in final results

### Answer Generation

- Retrieves top-k Q&A pairs (default: 3) for style consistency
- Formats Q&A history as "Q: {question}\nA: {answer}" pairs
- Includes job description context when available
- Generates first-person responses matching previous answer style

## Bug Fixes

Several pre-existing bugs were identified and fixed during customization:

1. **Graph Pipeline DataFrame Iteration**: Fixed `itertuples()` vs `iterrows()` inconsistency
2. **Relationship Loading**: Fixed numpy array to frozenset conversion
3. **Embedding Client**: Fixed `Embedding_message` handling for OpenAI and Gemini
4. **Error Handling**: Fixed exception handling in async error decorators
5. **Graph Traversal**: Fixed undirected graph traversal (`neighbors()` vs `successors()`)
6. **Mapper Integration**: Added Q&A parquet files to mapper for visualization support

See `TRACK_CHANGES.md` for detailed bug fix documentation.

## Testing

A test script `search_resumes.py` is provided for testing Q&A integration:

```bash
python search_resumes.py
```

The script includes:
- Mock job description for Python Developer role
- Interactive Q&A search testing
- Q&A results display
- Answer generation with job context

## Dependencies

- Python 3.11+
- NetworkX (graph operations)
- OpenAI API or Gemini API (for embeddings and LLM)
- hnswlib (HNSW index)
- pandas (data handling)
- pyyaml (configuration)

## License

This customization maintains the same license as the original NodeRAG framework.

## Citation

If you use this customized version, please cite both the original NodeRAG paper and this customization:

```bibtex
@article{xu2025noderag,
  title={NodeRAG: Structuring Graph-based RAG with Heterogeneous Nodes},
  author={Xu, Tianyang and Zheng, Haojie and Li, Chengze and Chen, Haoxiang and Liu, Yixin and Chen, Ruoxi and Sun, Lichao},
  journal={arXiv preprint arXiv:2504.11544},
  year={2025}
}
```

## Acknowledgments

- Original NodeRAG framework: [NodeRAG GitHub](https://github.com/NodeRAG/NodeRAG)
- Paper authors for the foundational graph-based RAG framework

## Contact

For questions or issues related to this customization, please refer to the original NodeRAG repository or create an issue in this repository.

