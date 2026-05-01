_"Helping readers find the perfect book they've been missing."_

---

## Project Overview

The **Book Recommender System** is designed to help users discover books that truly resonate with them — emotionally, thematically, or intellectually.  
By combining **Large Language Models (LLMs)** with **embedding-based similarity search**, the system can understand **semantic**, **mood-based**, and **vibes** to suggest books that align with the user's intent.

Unlike general-purpose AI models such as ChatGPT, Gemini, or Claude, this project focuses exclusively on **book discovery** and **user experience** tailored for recommending books and transparency around the recommendation system.

It operates on a **contained catalog of 5,000+ books**, which acts as the **source of truth** for all recommendations.  
This design enables:
- **Personalized and transparent recommendations**
- **A curated experience** (similar to a local library or personal catalog)
- **Community-driven preferences** 

By combining modern AI with catalog constraints, the system provides **trustworthy**, **context-aware**, and **reproducible** book recommendations — something unbounded LLMs cannot easily achieve.

---

## Deployment

After completing end-to-end development, a **pre-release version** was deployed for limited users to test functionality and feedback.

In this version, the system can:
- Stream live responses  
- Interpret and understand user queries  
- Recommend relevant books from the catalog  

However, it still lacks full-scale testing, optimization, and several upcoming features.

> _If you'd like to provide feedback or suggestions, please contact me at_  
> **tuanqpham0921@gmail.com**

---

## Architecture & Design Choices

### **Early Iterations (v1 & v2)**

The initial design used a **tool-calling agent** approach.  
While functional, this setup became difficult to maintain and scale:
- Managing multiple tool definitions was cumbersome  
- Debugging LLM-driven flows was inefficient  
- Scaling required full vertical expansion (entire LLM re-runs per user query)  

To solve this, the project transitioned to a **Task-Based Orchestration Architecture**.

---

### Task-Based Orchestration

Instead of letting the LLM dynamically decide every action at runtime, the system **pre-generates a dependency graph** of tasks and executes them deterministically.

This allows:
- **Horizontal scaling** (tasks can run independently across machines)  
- **Transparent task flow** for debugging and visualization  
- **Human-in-the-loop control** before execution  

![Task-Based Orchestration Flow](blog-posts/task_orchestration.svg)

_Note: This is the current simplified version of the archecture. In the future, caching layers, and messages queues can be added to the system._

---

### Why Not a Fixed Graph?

Fixed graph architectures often become **fully connected** as features grow — meaning every node can route to every other.  
This complexity makes it nearly impossible to maintain or extend.

Instead, this project **dynamically generates graphs per user query**, based on the user's intent and the strategy plan.

> **Query**: "Find horror novels like It by Stephen King. Then compare the book results"

![Dependency Resolver Example](/blog-posts/dependency_resolver.svg)

---

## RAG-Based Flow (Retrieval → Analysis → Generation)

The system follows a **RAG-style pipeline**.  
Every user request starts with **retrieval**, proceeds through **analysis**, and ends in **generation**.

Rather than having the LLM decide the next action at runtime, the system **plans ahead** — creating a structured task list with clear dependencies.

> **Query**: "compare Dune to the Iliad based on rating and page numbers. Then compare Dune to To Kill a Mockingbird theme. Then recommend me some books similar to the first two books"

![Multistage Dependency Resolver](/blog-posts/multi_stage.svg)

_Notice: each retrieval node is mapped to its corresponding analysis strategy. To Kill a Mockingbird is not passed into the recommendation node._


---

### Benefits

- **Dynamic flexibility** — each query builds a unique graph  
- **Intent-focused** — plans are based on "what to do," not "how to do it"  
- **Simpler orchestration** — no per-step routing logic  
- **Human validation** — before task execution for transparency
- **Horizontal scalability** — easily distributed tasks  
- **Reusability** — one retrieval can feed multiple analysis tasks  
- **Deterministic order** — supports topological sorting  
- **Reduced token cost** — less repetition across nodes  

---

### Limitations

- Requires **manual validation** of plans  
- Planning adds a small **pre-execution delay**  
- Less suitable for **spontaneous, evolving queries**  
- Fixed **token cost per plan**  
- Potential **hallucination in dependency resolution**
- Requires more **up-front LLM calls**

Despite these trade-offs, this design provides **transparency**, **control**, and **scalability** — ideal for a domain-contained AI system like this one.

A future **hybrid model** may blend pre-planning with limited run-time reasoning for even greater flexibility.

---

## Development Experience

### 1. Design Around Limitation and Restriction
It can be overwhelming at first due to the large number of possible user requests, even for a small domain book recommender system. I have realized that it's important to have a way to restrict the features. I solve this problem by starting with the possible **retrieval strategies** first and basing my available features on them. By focusing first on **retrieval strategies** (e.g., `FindByTitle`, `FindByTraits`), I defined the project's true scope early and avoided unnecessary complexity. At the same time, I was able to easily help guide the users to available features in a contained system.

### 2. Balance Validation with Flexibility
Initially, I focused on validation to prevent hallucinations. I thought **enforcing correctness** would help with development cycles. While this added safety, it also **slowed progress** dramatically. Unlike traditional software engineering where inputs are predictable, LLM outputs are **non-deterministic** and user queries are **highly variable**, making extensive validation impractical and leading to an **unmaintainable codebase** early.

The better approach:
- Start with **loosely typed schemas** (use strings and numbers)
- Let the **LLM generate outputs freely**  
- Add **validation later**, once patterns stabilize from end to end

This approach made development **much faster** without sacrificing correctness.

---

## Future Plans

- Personalized user preferences  
- Human-in-the-loop feedback  
- Better Parallel task execution  
- Performance and cost tracking  
- Comprehensive testing and QA  

The long-term goal is to deliver a **unique**, **trustworthy**, and **transparent** reading discovery experience that sets this system apart from typical LLM chatbots.

---

## Outro

The **Book Recommender System** is still evolving, but it already demonstrates how LLMs can be specialized into domain-focused agents with rich reasoning and transparency.

If you'd like to share ideas, feedback, or collaborate:

Email: tuanqpham0921@gmail.com  
GitHub: [Book-Recommender-Public](https://github.com/tuanqpham0921/Book-Recommender-Public)

---

> _"The more I read, the more I acquire, the more certain I am that I know nothing."_  
> — Voltaire