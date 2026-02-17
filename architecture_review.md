# Architecture Review

This document provides a review of the `architecture.md` file based on the reviewer role defined in `agent_roles.md`.

## 1. Discovered Issues

### Contradictions and Ambiguities
- **Configuration Sources:** The design specifies both a `config.yaml` file and `.env` variables. The relationship and override priority between these two sources are not defined, which could lead to confusion during deployment and debugging.
- **LLM Model Choice:** The document suggests using a general-purpose LLM like `llama3.2` for generating embeddings. This is inefficient. Dedicated embedding models (like `nomic-embed-text`, which is mentioned as an alternative) are significantly faster and better suited for this task. The design should strongly recommend a dedicated embedding model.
- **File Naming:** The document refers to itself as `workflow.md` in the file structure section, but the filename is `architecture.md`. The file structure also lists `design.md`, creating confusion about which document is canonical.
- **HTML Template Location:** The HTML for the email is embedded directly in the design document, but the proposed file structure includes a `templates/email.html` file. The design should be consistent and recommend using the external template file.
- **Deduplication Logic:** The design states it will deduplicate based on "Same URL (exact match)" and title similarity, but the provided code examples and primary description focus only on title-based embedding similarity. The exact sequence of deduplication steps is not clear.

### Missing Edge Cases and Failure Modes
- **Failed Run Recovery:** The system is scheduled to run every 12 hours and process data from the last 12 hours. If a run fails, the articles from that 12-hour window will be permanently missed. There is no mechanism to handle this data gap (e.g., by saving the timestamp of the last successful run).
- **LLM Output Quality:** The error handling for the Ollama service covers availability but not data integrity. The system does not account for the possibility of the LLM returning malformed or garbage embeddings, which could corrupt the deduplication process.
- **Timezone Ambiguity:** The design mentions normalizing dates to UTC but does not specify how to handle articles that have a publication date without any timezone information. Assuming a default timezone can lead to incorrect filtering.
- **Email Size Limit:** The workflow does not consider the case where an unusually high number of unique articles could result in an extremely large HTML email. This might cause issues with email clients or spam filters.

## 2. Improvement Suggestions

1.  **Clarify Configuration:** Explicitly state the configuration loading priority. A common and effective pattern is: `.env` file loads into environment -> `config.yaml` is read -> environment variables (if present) override YAML values.
2.  **Optimize LLM Usage:** Officially recommend a dedicated, efficient embedding model (e.g., `nomic-embed-text`) as the default for the deduplication task. The use of a large chat model like `llama3.2` should be noted as a possible but inefficient alternative.
3.  **Implement State Persistence:** To prevent data loss from failed runs, the system should save the timestamp of the last successfully processed article or the timestamp of the last successful run. The next run should use this timestamp as the starting point for the time window, ensuring no articles are missed.
4.  **Refine Deduplication Strategy:** Define a clear, multi-stage deduplication process:
    -   **Step 1:** Remove articles with identical `link` values, keeping the most recent one.
    -   **Step 2:** For the remaining articles, perform title-based similarity clustering using embeddings.
5.  **Specify Clustering Algorithm:** For the embedding-based deduplication, specify the clustering algorithm. For example: "Use Agglomerative Clustering with cosine similarity and a distance threshold defined in the configuration."
6.  **Add Configuration for Preferred Sources:** To resolve ambiguity in which article to select from a duplicate cluster, add a `preferred_sources` list to the configuration file. The selection logic should be: "Select the newest article, unless another article in the cluster is from a preferred source."
7.  **Add a Hard Limit:** To prevent oversized emails, introduce a configurable `max_articles_per_email` limit in `config.yaml`. If the number of articles exceeds this limit, the system could either truncate the list or send a warning instead of the full digest.
8.  **Formalize Timezone Handling:** Specify the policy for timezone-naive dates. A safe default is to assume UTC but log a warning. E.g., "If `published_parsed` lacks timezone info, assume UTC and log a `WARNING`."

## 3. Verdict

**Needs Revision**

The architecture is a solid foundation but requires revisions to address the identified ambiguities and missing edge cases before implementation begins. The proposed improvements will make the system more robust, efficient, and reliable.
