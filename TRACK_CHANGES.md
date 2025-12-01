# NodeRAG Customization - Change Tracking

This document tracks all modifications made to the NodeRAG framework for the Auto-Fill Job Application use case.

## Phase 1: Multi-User Support

### 1. `NodeRAG/config/Node_config.py`
- Added `user_id` attribute extraction from configuration
- Implemented `effective_main_folder` logic: routes to `main_folder/users/user_{user_id}/` when `user_id` is provided, otherwise defaults to `main_folder`
- Updated all path definitions (`input_folder`, `cache`, `info`, `embedding_path`, etc.) to use `effective_main_folder` for user-specific routing
- Updated `config_integrity()` method to validate `effective_main_folder` existence
- Ensures backward compatibility: works without `user_id` parameter

### 2. `NodeRAG/build/pipeline/INIT_pipeline.py`
- Updated `check_folder_structure()` to use `self.config.effective_main_folder` for validation
- Added logic to create `input` folder within `effective_main_folder` if it doesn't exist
- Ensures proper folder structure initialization for new user directories

### 3. `NodeRAG/WebUI/app.py`
- Added `get_effective_main_folder()` helper function to retrieve user-specific path from `NodeConfig`
- Modified `load_config()` to create and store `NodeConfig` instance in `st.session_state.node_config`
- Updated all path references to use `effective_main_folder` instead of `main_folder`:
  - Building status checks (`info/state.json`)
  - Indices loading (`info/indices.json`)
  - File upload paths
  - Search engine initialization
  - Configuration display
- Updated "Main Folder" display in settings to show `effective_main_folder`

### 4. `NodeRAG/Vis/html/visual_html.py`
- Updated `visualize()` function to load `Node_config.yaml` and use `effective_main_folder` for graph data paths
- Fixed `filter_nodes()` function to handle disconnected graph components gracefully:
  - Added try-except block around `nx.bidirectional_dijkstra()` to catch `NetworkXNoPath` exceptions
  - Added informative console messages when paths cannot be found
  - Fixed bug where `final_nodes` was referenced before initialization when subgraph was connected
- Updated cache folder and output HTML paths to use `effective_main_folder`


---

## Phase 2: Q&A Node Integration

### 1. `NodeRAG/utils/readable_index.py`
- Added `question_index` class for Question node indexing
- Added `answer_index` class for Answer node indexing
- Follows same pattern as existing index classes (entity_index, relation_index, etc.)

### 2. `NodeRAG/build/component/question.py` (NEW)
- Created `Question` node class extending `Unit_base`
- Stores: question text, question_id, job_title, company_name, submission_date
- Implements `hash_id` and `human_readable_id` properties following NodeRAG pattern

### 3. `NodeRAG/build/component/answer.py` (NEW)
- Created `Answer` node class extending `Unit_base`
- Stores: answer text, question_id (link to Question)
- Implements `hash_id` and `human_readable_id` properties

### 4. `NodeRAG/build/component/__init__.py`
- Registered `Question` and `Answer` classes
- Exported `question_index_counter` and `answer_index_counter`
- Added to `__all__` list for proper module exports

### 5. `NodeRAG/utils/qa_api_client.py` (NEW)
- Created `QAAPIClient` class for fetching Q&A pairs from backend API
- Supports mock mode (`use_mock=true`) for development with JSON file
- Supports real API mode (`use_mock=false`) for production
- API endpoint: `GET {api_base_url}/api/questions/user/{user_id}`
- Validates API response structure (question_id, question, answer, job_title, company_name, submission_date)
- Handles errors gracefully with informative messages

### 6. `NodeRAG/build/pipeline/qa_pipeline.py` (NEW)
- Created `QA_Pipeline` class for building Q&A nodes during graph construction
- Fetches Q&A pairs from API client (or mock JSON)
- Creates Question and Answer nodes in graph
- Generates embeddings for Question nodes using existing embedding_client
- Builds separate HNSW index for Question nodes (for semantic search)
- Adds `has_answer` relationship edges between Question and Answer nodes
- Saves updated graph and HNSW index

### 7. `NodeRAG/build/pipeline/__init__.py`
- Registered `QA_Pipeline` in pipeline module exports

### 8. `NodeRAG/build/Node.py`
- Added `QA_Pipeline` import
- Added `_init_qa_api_client()` method to initialize API client from config
- Integrated Q&A pipeline to run conditionally after GRAPH_PIPELINE completes
- Q&A pipeline only runs if `qa_api.enabled=true` in config
- Fixed import path: `from ..utils.qa_api_client import QAAPIClient` (two dots, not three)

### 9. `NodeRAG/mock_data/mock_qa_data.json` (NEW)
- Created mock JSON file with sample Q&A data
- Flat list structure: `[{question_id, question, answer, job_title, company_name, submission_date}, ...]`
- Contains 5 sample Q&A pairs for testing

### 10. `POC_Data/documents/Node_config.yaml`
- Added `qa_api` configuration section:
  - `enabled`: Enable/disable Q&A integration
  - `use_mock`: Use mock JSON file (true) or call real API (false)
  - `mock_data_path`: Path to mock JSON file (relative to main_folder)
  - `base_url`: Backend API base URL (used when use_mock=false)

---

## Bug Fixes (Triggered by Phase 2)

### 1. `NodeRAG/build/pipeline/graph_pipeline.py`
- **Issue**: `load_relationship()` used `df.itertuples()` which returns named tuples, but `Relationship.from_df_row()` expects dictionary access
- **Root Cause**: This bug existed before Phase 2, but was exposed when:
  - Importing Question/Answer in `__init__.py` changed module initialization order
  - Building for user_2 with existing relationship data triggered the code path
- **Fix**: Changed `df.itertuples()` to `df.iterrows()` to match other DataFrame loading patterns in the codebase
- **Note**: Other pipelines (`text_pipeline.py`, `Insert_text.py`) already use `iterrows()` correctly

### 2. `NodeRAG/build/component/relationship.py`
- **Issue**: `from_df_row()` received `unique_relationship` as numpy array/pandas Series (from parquet), but `Relationship.__init__()` checks `elif frozen_set:` which fails for arrays
- **Root Cause**: When saving, `unique_relationship` is stored as a list. When loading from parquet, pandas converts it to array/Series, causing truthiness evaluation error
- **Fix**: Added conversion logic in `from_df_row()` to handle list/tuple/array/Series and convert to frozenset before passing to constructor

### 3. `NodeRAG/build/Node.py`
- **Issue**: Error handler raises string instead of Exception: `raise f'Error...'`
- **Fix**: Changed to `raise Exception(f'Error...')` (applies to both ERROR and ERROR_CACHE handlers)

### 4. `NodeRAG/build/pipeline/graph_pipeline.py` (Assertion Logic Fix)
- **Issue**: Assertions in `save_semantic_units()`, `save_entities()`, and `save_relationships()` compare NEW items from current run with ALL items in graph
- **Root Cause**: 
  - `self.semantic_units`, `self.entities`, `self.relationship` only contain NEW items created in current run
  - When graph already has nodes from previous build, they're NOT added to these lists
  - But assertions compare against ALL nodes in graph
  - This bug existed before Phase 2 but was exposed by multi-user support (graphs persist per user)
- **Fix**: Only assert when NOT appending (fresh build). When appending, skip assertion since existing nodes aren't tracked in lists

### 5. `NodeRAG/build/pipeline/graph_pipeline.py` (Relationship Node Loading Fix)
- **Issue**: `save_relationships()` tries to access `self.G.nodes[relationship.hash_id]['weight']` but relationship nodes loaded from parquet aren't added to graph
- **Root Cause**: 
  - `load_relationship()` loads relationships from parquet into `self.relationship` list
  - But relationship nodes are NOT added to graph during loading
  - Relationship nodes are only added when `add_relationships()` processes NEW data
  - When saving, relationships from parquet don't have corresponding graph nodes
  - This bug existed before Phase 2 but was exposed by incremental builds with existing relationship data
- **Fix**: Modified `load_relationship()` to add relationship nodes to graph when loading from parquet (for incremental builds)

### 6. `NodeRAG/build/Node.py` (QA Pipeline Execution Fix)
- **Issue**: QA Pipeline never executed because state check happened after state transition
- **Root Cause**: 
  - In `state_transition()`, state is transitioned from `GRAPH_PIPELINE` to `ATTRIBUTE_PIPELINE` BEFORE checking if QA pipeline should run
  - Check `if self.Current_state == State.GRAPH_PIPELINE:` always evaluated to False because state had already changed
  - QA Pipeline was never called, so no Question/Answer nodes or HNSW index were created
- **Fix**: Store `previous_state` before state transition, then check `if previous_state == State.GRAPH_PIPELINE:` to trigger QA pipeline after graph pipeline completes

### 7. `NodeRAG/build/Node.py` (QA Pipeline State Integration)
- **Issue**: QA Pipeline was conditionally executed after GRAPH_PIPELINE, but not as a proper state in the sequence
- **Root Cause**: 
  - QA Pipeline was added as conditional logic, not as a distinct state
  - This made it harder to track and debug pipeline execution
- **Fix**: Added `QA_PIPELINE` as a distinct state in the `State` enum and `state_sequence`, positioned after `GRAPH_PIPELINE`
- **Result**: QA Pipeline now executes as a regular state in the pipeline sequence, making execution flow clearer

### 8. `NodeRAG/config/Node_config.py` (QA Parquet Paths)
- **Issue**: QA Pipeline needed paths for saving questions and answers to parquet files
- **Fix**: Added `questions_path` and `answers_path` properties:
  - `self.questions_path = os.path.join(self.cache, 'questions.parquet')`
  - `self.answers_path = os.path.join(self.cache, 'answers.parquet')`
- **Note**: These paths use `effective_main_folder` automatically (via `self.cache`), ensuring user-specific file storage

### 9. `NodeRAG/build/pipeline/qa_pipeline.py` (Parquet File Saving Fix)
- **Issue**: `questions.parquet` and `answers.parquet` files were not being created in user-specific cache folders
- **Root Cause**: 
  - `save()` method only saved nodes that were *newly created* in the current run (tracked in `self.questions` and `self.answers` lists)
  - On subsequent runs (incremental builds), if nodes already existed in the graph, these lists were empty
  - Empty lists meant no parquet files were saved, even though nodes existed in the graph
  - The graph was the source of truth, but parquet files weren't reflecting the graph state
- **Fix**: 
  - Modified `save_questions()` and `save_answers()` to extract *all* nodes of type 'question' and 'answer' directly from `self.G` (networkx graph), not just new ones
  - Changed `save()` to always overwrite parquet files (not append) to ensure consistency with graph state
  - Added directory existence check (`os.makedirs()`) before saving
  - Added extensive `print()` statements with `sys.stdout.flush()` for persistent debug output (survives Rich console clearing)
  - Added exception handling with detailed error messages
- **Result**: Parquet files now correctly reflect all Question and Answer nodes in the graph, regardless of whether they were created in the current run or loaded from previous builds

---

### 10. `NodeRAG/config/Node_config.py` (Question HNSW Paths)
- **Issue**: Question HNSW index paths needed for Phase 2 search integration
- **Fix**: Added `question_hnsw_path` and `question_id_map_path` properties:
  - `self.question_hnsw_path = os.path.join(self.cache, 'question_hnsw.bin')`
  - `self.question_id_map_path = os.path.join(self.cache, 'question_id_map.parquet')`
- **Note**: These paths use `effective_main_folder` automatically (via `self.cache`), ensuring user-specific file access

### 11. `NodeRAG/search/search.py` (Phase 2 Q&A Search Integration)
- **Issue**: Q&A search functionality was not integrated into the main search flow
- **Root Cause**: Phase 2 only implemented Q&A node creation and HNSW index building, but not the search integration
- **Fix**: Integrated Q&A semantic search into `NodeSearch.search()` method:
  - Added `_load_question_hnsw_index()` method to load Question HNSW index and id_map during initialization
  - Added `_search_qa_pairs()` method to search Question nodes using Question HNSW index
  - Modified `search()` method to:
    1. Check if Question HNSW index exists
    2. Search Question nodes using query embedding
    3. Boost Q&A nodes in PageRank personalization (20% boost)
    4. Store Q&A results in `retrieval.qa_results`
    5. Add Q&A nodes to search results in `post_process_top_k()`
  - Q&A search is automatic and transparent - no special commands needed
  - Q&A nodes are boosted in PageRank when relevant to the query
  - Q&A nodes are included in retrieval results for answer generation
- **Result**: When users call `search.answer(query)`, Q&A nodes are automatically searched and included if relevant

### 12. `NodeRAG/search/Answer_base.py` (Q&A Results Storage)
- **Issue**: Retrieval class needed to store Q&A search results
- **Fix**: Added `qa_results = []` attribute to `Retrieval.__init__()` to store Q&A pairs found during search

### 13. `search_resumes.py` (Phase 2 Q&A Display)
- **Issue**: Test script needed to show when Q&A nodes are found in search results
- **Fix**: Updated test script to:
  - Display Q&A results if found in retrieval (from `ans.retrieval.qa_results`)
  - Show similarity scores, question/answer text, and job context
  - Removed duplicate Q&A search function (now handled by library)
  - Updated help text to indicate Q&A search is automatic

### 14. `NodeRAG/utils/graph_operator.py` (Edge Weight KeyError Fix)
- **Issue**: `unbalance_adjust()` method accessed `graph[node][neighbor]['weight']` directly, causing KeyError when edges don't have 'weight' attribute
- **Root Cause**: Phase 2 Q&A edges (`has_answer`) were created without `weight` attribute, and `unbalance_adjust()` assumed all edges have weight
- **Fix**: Changed `graph[node][neighbor]['weight']` to `graph[node][neighbor].get('weight', 1)` to handle edges without weight attribute gracefully

### 15. `NodeRAG/build/pipeline/qa_pipeline.py` (Edge Weight Attribute)
- **Issue**: `has_answer` edges created without `weight` attribute, causing issues in `unbalance_adjust()`
- **Fix**: Added `weight=1` parameter when creating `has_answer` edges:
  ```python
  self.G.add_edge(
      question_node.hash_id,
      answer_node.hash_id,
      type='has_answer',
      weight=1  # Add weight attribute for graph operations
  )
  ```

### 16. `NodeRAG/build/pipeline/qa_pipeline.py` (HNSW Index Building Logic Bug)
- **Issue**: `_build_question_hnsw_index()` was placed in the `else` block, meaning it only ran when embeddings were NOT generated. This caused Question HNSW index files (`question_hnsw.bin`, `question_id_map.parquet`) to never be created.
- **Root Cause**: Logic error - HNSW index building code was in the wrong conditional block
- **Fix**: Moved HNSW index building code into the `if` block that runs when embeddings ARE successfully generated:
  - Now runs after embeddings are generated and stored in graph nodes
  - Added debug print statements to track HNSW index building progress
  - Ensures `question_nodes_data` is populated before building index

### 17. `NodeRAG/search/search.py` (Better Q&A Index Loading Debug)
- **Issue**: No visibility into why Q&A search is disabled
- **Fix**: Added better error handling and debug output in `_load_question_hnsw_index()`:
  - Checks if both files exist before attempting to load
  - Prints warning to stderr if loading fails
  - Gracefully disables Q&A search if files don't exist (expected if QA pipeline hasn't run)

---
## Notes
- All changes maintain backward compatibility: system works without `user_id` parameter
- User-specific folders are automatically created when `user_id` is provided
- Folder structure: `main_folder/users/user_{user_id}/{input,cache,info}/`
- Q&A pipeline is optional: only runs if `qa_api.enabled=true` in config
- Mock data path is resolved relative to `main_folder` (not `effective_main_folder`) for shared mock data
- Phase 2 Q&A search can be tested using `search_resumes.py` with 'qa:' prefix

### Bug Fix: OpenAI Embedding Client List Handling
- **File**: `NodeRAG/LLM/LLM.py`
- **Issue**: `_create_embedding_async` and `_create_embedding` were passing `Embedding_message` dicts directly to OpenAI's API, but OpenAI expects strings or lists of strings. When a list of `Embedding_message` objects was passed, it caused errors.
- **Fix**: Modified both methods to extract the `input` field from `Embedding_message` objects:
  - If input is a list: extract `input` field from each `Embedding_message` object
  - If input is a dict: extract `input['input']`
  - Otherwise: use input as-is (for backward compatibility)
- **Impact**: Now the QA pipeline can correctly generate embeddings for question texts using the same pattern as `embedding.py`

### Bug Fix: Error Handler List Handling
- **File**: `NodeRAG/logging/error.py`
- **Issue**: `cache_error_async` was calling `.get()` on `input_data` without checking if it was a dict first, causing `AttributeError` when `input_data` was a list.
- **Fix**: Added `isinstance(input_data, dict)` check before calling `.get()`, matching the pattern used in the synchronous `cache_error` function.

### Bug Fix: Gemini Embedding Client List Handling (ROOT CAUSE)
- **File**: `NodeRAG/LLM/LLM.py` - `Gemini_Embedding` class
- **Issue**: 
  - `Gemini_Embedding._create_embedding_async` and `_create_embedding` were passing `Embedding_message` dicts directly to Gemini's API without extracting the `input` field
  - The backoff decorators were using lists `[ResourceExhausted, ...]` instead of tuples, which can cause "catching classes that do not inherit from BaseException" errors
  - This caused embedding generation to fail for Question nodes, preventing the creation of `question_hnsw.bin` and `question_id_map.parquet` files
  - Normal text unit embeddings worked because they use a different code path that was already working
- **Root Cause**: The user's config uses `gemini_embedding` provider, not OpenAI. The fix I applied earlier only fixed `OpenAI_Embedding`, but `Gemini_Embedding` had the same issue.
- **Fix**: 
  - Modified both `_create_embedding` and `_create_embedding_async` in `Gemini_Embedding` to extract the `input` field from `Embedding_message` objects (same logic as `OpenAI_Embedding`)
  - Changed backoff decorators to use tuples `(ResourceExhausted, TooManyRequests, InternalServerError)` instead of lists
- **Impact**: Now Question node embeddings will be generated correctly, and the HNSW index files (`question_hnsw.bin`, `question_id_map.parquet`) will be created in the user_2 folder

### Bug Fix: Undirected Graph Traversal in Q&A Search
- **File**: `NodeRAG/search/search.py` - `_search_qa_pairs()` method
- **Issue**: Code used `self.G.successors()` which only works for directed graphs (`DiGraph`), but NodeRAG uses undirected graphs (`Graph`). This caused `AttributeError: 'Graph' object has no attribute 'successors'` when searching for answer nodes connected to questions.
- **Root Cause**: NetworkX `Graph` (undirected) doesn't have `successors()` method - only `DiGraph` (directed) has it. NodeRAG uses `nx.Graph()` (undirected) as seen in `graph_pipeline.py`.
- **Fix**: 
  - Changed `self.G.successors(question_hash_id)` to `self.G.neighbors(question_hash_id)` for undirected graph traversal
  - Added check to verify neighbor is an answer node (`type == 'answer'`) before using it
  - Handles both edge directions `(question, answer)` and `(answer, question)` for safety
- **Impact**: Q&A search now correctly finds answer nodes connected to question nodes via `has_answer` edges

### Bug Fix: Q&A Nodes Missing from id_to_text Mapping
- **File**: `NodeRAG/search/search.py` - `__init__()` method
- **Issue**: Q&A nodes (question and answer) were being added to search results via PageRank boosting, but they weren't in the `id_to_text` dictionary. When `Answer_base.py` tried to access `id_to_text[qa_node_id]`, it raised `KeyError`.
- **Root Cause**: `id_to_text` is built from parquet files via `mapper.generate_id_to_text()`, which only includes specific node types (entities, high_level_elements, etc.). Q&A nodes are stored directly in the graph but not in parquet files, so they were missing from `id_to_text`.
- **Fix**: 
  - Added code to populate `id_to_text` with Q&A nodes from the graph after initial mapping is created
  - Iterates through all graph nodes and adds question/answer nodes with their text to `id_to_text`
  - Only adds nodes that have text content
- **Impact**: Q&A nodes can now be properly included in answer generation without KeyError exceptions

