# Flowcharts — Mermaid Source

Same 9 flowcharts as in the Word doc, in raw Mermaid syntax, for pasting into
Obsidian (or any Mermaid-compatible tool). Word can't render Mermaid natively,
so the `.docx` uses rendered images of these same diagrams — this file is the
editable source.

---

## 1. High-Level Pipeline

```mermaid
flowchart TD
    Q["User Question<br/>(plain English)"]:::good
    R["Understand the Question<br/>Pull matching schema cards, glossary terms,<br/>and similar examples"]
    G["Generate SQL<br/>LangChain + LLM<br/>(provider picked at runtime)"]
    S["Safety Checks<br/>Structure valid? Real values?"]:::check
    E["Run Query<br/>Read-only database"]
    A["Plain-English Answer"]:::good

    Q --> R --> G --> S --> E --> A
    E -.->|"error → retry (max 2)"| G

    classDef good fill:#D9F2D9,stroke:#3C8A3C
    classDef check fill:#FFF3CD,stroke:#B8860B
```

---

## 2. Block — Understand the Question

```mermaid
flowchart TD
    In["Question in"]:::good
    A["Pull relevant<br/>schema_cards.yaml entries"]
    B["Pull relevant<br/>glossary.yaml terms"]
    C["Pick 2-3 similar<br/>examples.jsonl examples"]
    Out["Assembled context<br/>→ handed to LLM prompt"]:::good

    In --> A --> B --> C --> Out
    classDef good fill:#D9F2D9,stroke:#3C8A3C
```

## 3. Block — Generate SQL

```mermaid
flowchart TD
    In["Context + Question"]:::good
    A["Build LangChain<br/>PromptTemplate / FewShotPromptTemplate"]
    B["Call LLM via llm_client.py<br/>get_llm(provider) — Groq / Gemini / Ollama"]
    Out["Raw SQL text"]:::good

    In --> A --> B --> Out
    classDef good fill:#D9F2D9,stroke:#3C8A3C
```

## 3b. Block — Provider Factory (llm_client.py)

```mermaid
flowchart TD
    In["Startup: --provider flag<br/>(groq / gemini / ollama)"]:::good
    F{"llm_client.py<br/>get_llm(provider)"}
    Groq["ChatGroq (API)"]
    Gem["ChatGoogleGenerativeAI (API)"]
    Oll["ChatOllama (local model)"]
    Out["Same interface everywhere —<br/>sql_agent.py + answer_synth.py<br/>never know which one it is"]:::good

    In --> F
    F -->|groq| Groq
    F -->|gemini| Gem
    F -->|ollama| Oll
    Groq --> Out
    Gem --> Out
    Oll --> Out

    classDef good fill:#D9F2D9,stroke:#3C8A3C
```

## 4. Block — Validator (validator.py)

```mermaid
flowchart TD
    In["Raw SQL text"]:::good
    P["Parse into AST (sqlglot)"]
    D1{"SELECT-only?"}
    D2{"Only allow-listed tables?"}
    Cap["Add row limit"]
    Pass["Pass to categorical_check.py"]:::good
    Block["Refuse — never touches DB"]:::bad

    In --> P --> D1
    D1 -->|yes| D2
    D1 -->|no| Block
    D2 -->|yes| Cap
    D2 -->|no| Block
    Cap --> Pass

    classDef good fill:#D9F2D9,stroke:#3C8A3C
    classDef bad fill:#FBE1E1,stroke:#B84A4A
```

## 5. Block — Categorical Check (categorical_check.py)

```mermaid
flowchart TD
    In["Validated SQL"]:::good
    Ex["Extract literal values compared to<br/>categorical columns (status, payment_type...)"]
    Chk{"Value exists in real<br/>distinct-values list?"}
    Ok["Run it (pass to execute.py)"]:::good
    Flag["Flag: low-confidence<br/>Ask user to clarify<br/>(never auto-correct)"]:::bad

    In --> Ex --> Chk
    Chk -->|yes| Ok
    Chk -->|no| Flag

    classDef good fill:#D9F2D9,stroke:#3C8A3C
    classDef bad fill:#FBE1E1,stroke:#B84A4A
```

## 6. Block — Execute + Repair (execute.py)

```mermaid
flowchart TD
    In["Checked SQL"]:::good
    Run["Run on read-only SQLite connection"]
    D{"Error?"}
    Retry{"Retry count < 2?"}
    Feed["Feed error back to LLM, regenerate SQL"]
    Give["Give up — report failure"]:::bad
    Rows["Real result rows"]:::good

    In --> Run --> D
    D -->|no| Rows
    D -->|yes| Retry
    Retry -->|yes| Feed
    Retry -->|no| Give
    Feed --> Run

    classDef good fill:#D9F2D9,stroke:#3C8A3C
    classDef bad fill:#FBE1E1,stroke:#B84A4A
```

## 7. Block — Answer Synthesis (answer_synth.py)

```mermaid
flowchart TD
    In["Result rows + original question"]:::good
    Case{"Which case?"}
    Empty["Empty result → say so plainly"]
    LowConf["Low-confidence flag → ask to clarify"]
    Normal["Normal result → LLM writes plain-English sentence"]
    Out["Answer shown to user"]:::good

    In --> Case
    Case --> Empty
    Case --> LowConf
    Case --> Normal
    Empty --> Out
    LowConf --> Out
    Normal --> Out

    classDef good fill:#D9F2D9,stroke:#3C8A3C
```

---

## 8. Complete Pipeline — All Blocks Combined

```mermaid
flowchart TD
    Q["User Question (plain English)"]:::good

    subgraph B1["1. Understand the Question"]
        C1["schema_cards.yaml"]
        C2["glossary.yaml"]
        C3["examples.jsonl (2-3 similar)"]
    end

    subgraph B2["2. Generate SQL"]
        G1["LangChain prompt template"]
        G2["get_llm(provider) — Groq / Gemini / Ollama"]
        G1 --> G2
    end

    subgraph B3["3. validator.py"]
        V1{"SELECT-only? allow-listed tables?<br/>(sqlglot AST check)"}
    end
    Block1["Refuse"]:::bad

    subgraph B4["4. categorical_check.py"]
        K1{"Do the literal values really exist?"}
    end
    Flag1["Flag low-confidence, ask to clarify"]:::bad

    subgraph B5["5. execute.py"]
        E1["Run on read-only DB"]
        E2{"Error? retry ≤ 2x"}
        E1 --> E2
    end

    subgraph B6["6. answer_synth.py"]
        A1["LLM writes plain-English answer from result rows"]
    end

    Ans["Answer shown to user"]:::good

    Q --> C1
    C3 --> G1
    G2 --> V1
    V1 -->|fail| Block1
    V1 -->|pass| K1
    K1 -->|unknown value| Flag1
    K1 -->|ok| E1
    E2 -.->|retry| G2
    E2 -->|success| A1
    A1 --> Ans
    Flag1 --> Ans

    classDef good fill:#D9F2D9,stroke:#3C8A3C
    classDef bad fill:#FBE1E1,stroke:#B84A4A
```

---

## 9. Complete Build Roadmap — All Phases

```mermaid
flowchart LR
    P0["Phase 0<br/>Real Data & Database"]
    P1["Phase 1<br/>Semantic Layer"]
    P2["Phase 2<br/>Safety Layer"]
    P3["Phase 3<br/>Value Check"]
    P4["Phase 4<br/>Gold Test Set"]
    P5["Phase 5<br/>Connect Real LLM"]
    P6["Phase 6<br/>Full Agent"]
    P7["Phase 7<br/>Answer Synthesis"]
    P8["Phase 8<br/>Interface"]
    P9["Phase 9<br/>Handoff"]:::good

    P0 --> P1 --> P2 --> P3 --> P4 --> P5 --> P6 --> P7 --> P8 --> P9

    classDef good fill:#D9F2D9,stroke:#3C8A3C
```
