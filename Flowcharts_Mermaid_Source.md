# Flowcharts — Mermaid Source

Same flowcharts as in the Word doc, in raw Mermaid syntax, for pasting into
Obsidian (or any Mermaid-compatible tool). Word can't render Mermaid natively,
so the `.docx` uses rendered images of these same diagrams — this file is the
editable source.

**Color language.** Every edge is a named, animated link (`@{ animation: slow }`)
so the diagrams read like a moving current, not a static wiring chart. Edge
color always means the same thing across every diagram:

| Edge color | Meaning |
|---|---|
| 🟢 Green `#00C853` | normal forward flow — this step succeeded, moving on |
| 🔴 Red `#D50000` | error / retry / refuse / give-up — something failed |
| 🟠 Amber `#FFAB00` | caution — flagged, low-confidence, needs clarification (not a hard failure) |
| 🟣 Lavender `#7B5EA7` | conversation memory — read, write, or append to the recent-turns buffer |
| 🔵 Blue `#2E86C1` | vector / retrieval — embeddings, similarity search, the reviews tool |
| 🟧 Orange `#C2703D` | orchestrator / routing decision — which tool handles this question |
| 🔵🟣🟦 (bright variants) | reserved for the Provider Factory / Roadmap diagrams, to tell parallel branches or phase groups apart at a glance |

Box colors, unchanged:

| Box class | Fill / Border |
|---|---|
| Normal | `#FFFFFF` / `#3F4A5A` |
| Good | `#DFF6DD` / `#4F8A57` |
| Check | `#FFF4CC` / `#B88A00` |
| Bad | `#FDE2E1` / `#C84C4C` |
| Memory | `#EDE3F8` / `#7B5EA7` |
| Vector | `#D6EAF8` / `#2E86C1` |
| Route | `#FFE0CC` / `#C2703D` |

---

## 1. High-Level Pipeline (agent architecture — memory + routing to SQL or Reviews tool)

```mermaid
flowchart TD
    Q["User Question"]:::good
    Mem[("Recent conversation<br/>(memory.py)")]:::memory
    Route{"Orchestrator:<br/>classify question"}:::route
    SQL["SQL Tool<br/>(existing pipeline)"]
    Rev["Reviews Tool<br/>(vector search + summarize)"]:::vector
    Merge["Merge if both"]
    A["Plain-English Answer"]:::good

    Q L_Q_Mem_0@--> Mem
    Mem L_Mem_Route_0@--> Route
    Route L_Route_SQL_0@-->|sql| SQL
    Route L_Route_Rev_0@-->|reviews| Rev
    Route L_Route_SQL_1@-->|both| SQL
    Route L_Route_Rev_1@-->|both| Rev
    SQL L_SQL_Merge_0@--> Merge
    Rev L_Rev_Merge_0@--> Merge
    Merge L_Merge_A_0@--> A
    A L_A_Mem_0@-.->|append turn| Mem

    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef memory fill:#EDE3F8,stroke:#7B5EA7,color:#1F2937
    classDef vector fill:#D6EAF8,stroke:#2E86C1,color:#1F2937
    classDef route fill:#FFE0CC,stroke:#C2703D,color:#1F2937

    linkStyle 0 stroke:#7B5EA7,fill:none
    linkStyle 1 stroke:#7B5EA7,fill:none
    linkStyle 2 stroke:#00C853,fill:none
    linkStyle 3 stroke:#2E86C1,fill:none
    linkStyle 4 stroke:#00C853,fill:none
    linkStyle 5 stroke:#2E86C1,fill:none
    linkStyle 6 stroke:#00C853,fill:none
    linkStyle 7 stroke:#2E86C1,fill:none
    linkStyle 8 stroke:#00C853,fill:none
    linkStyle 9 stroke:#7B5EA7,fill:none

    L_Q_Mem_0@{ animation: slow }
    L_Mem_Route_0@{ animation: slow }
    L_Route_SQL_0@{ animation: slow }
    L_Route_Rev_0@{ animation: slow }
    L_Route_SQL_1@{ animation: slow }
    L_Route_Rev_1@{ animation: slow }
    L_SQL_Merge_0@{ animation: slow }
    L_Rev_Merge_0@{ animation: slow }
    L_Merge_A_0@{ animation: slow }
    L_A_Mem_0@{ animation: slow }
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

    In L_In_A_0@--> A
    A L_A_B_0@--> B
    B L_B_C_0@--> C
    C L_C_Out_0@--> Out

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#00C853,fill:none
    linkStyle 2 stroke:#00C853,fill:none
    linkStyle 3 stroke:#00C853,fill:none

    L_In_A_0@{ animation: slow }
    L_A_B_0@{ animation: slow }
    L_B_C_0@{ animation: slow }
    L_C_Out_0@{ animation: slow }
```

## 3. Block — Generate SQL

```mermaid
flowchart TD
    In["Context + Question"]:::good
    A["Build LangChain<br/>PromptTemplate / FewShotPromptTemplate"]
    B["Call LLM via llm_client.py<br/>get_llm(provider) — Groq / Gemini / Ollama"]
    Out["Raw SQL text"]:::good

    In L_In_A_0@--> A
    A L_A_B_0@--> B
    B L_B_Out_0@--> Out

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#00C853,fill:none
    linkStyle 2 stroke:#00C853,fill:none

    L_In_A_0@{ animation: slow }
    L_A_B_0@{ animation: slow }
    L_B_Out_0@{ animation: slow }
```

## 3b. Block — Provider Factory (llm_client.py)

Three branch colors so it's visually obvious these are alternatives, not a
sequence — they all merge back to the same green "normal flow" once a
provider is picked.

```mermaid
flowchart TD
    In["Startup: --provider flag<br/>(groq / gemini / ollama)"]:::good
    F{"llm_client.py<br/>get_llm(provider)"}
    Groq["ChatGroq (API)"]
    Gem["ChatGoogleGenerativeAI (API)"]
    Oll["ChatOllama (local model)"]
    Out["Same interface everywhere —<br/>sql_agent.py + answer_synth.py<br/>never know which one it is"]:::good

    In L_In_F_0@--> F
    F L_F_Groq_0@-->|groq| Groq
    F L_F_Gem_0@-->|gemini| Gem
    F L_F_Oll_0@-->|ollama| Oll
    Groq L_Groq_Out_0@--> Out
    Gem L_Gem_Out_0@--> Out
    Oll L_Oll_Out_0@--> Out

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#2979FF,fill:none
    linkStyle 2 stroke:#AA00FF,fill:none
    linkStyle 3 stroke:#00BFA5,fill:none
    linkStyle 4 stroke:#00C853,fill:none
    linkStyle 5 stroke:#00C853,fill:none
    linkStyle 6 stroke:#00C853,fill:none

    L_In_F_0@{ animation: slow }
    L_F_Groq_0@{ animation: slow }
    L_F_Gem_0@{ animation: slow }
    L_F_Oll_0@{ animation: slow }
    L_Groq_Out_0@{ animation: slow }
    L_Gem_Out_0@{ animation: slow }
    L_Oll_Out_0@{ animation: slow }
```

## 3c. Block — Reviews Tool (RAG over real review text)

```mermaid
flowchart TD
    Src["olist_order_reviews_dataset<br/>review_comment_message<br/>(~41% filled, Portuguese)"]
    Clean["Drop nulls, basic text cleanup"]
    Emb["Embed each review<br/>(Ollama, multilingual-capable model)"]:::vector
    DB[("Chroma: 'reviews'<br/>collection")]:::vector
    Q["Question"]:::good
    Search["Similarity search"]:::vector
    Snip["Top-k relevant<br/>review snippets"]
    LLM["LLM summarizes snippets<br/>into plain-English answer"]
    Out["Answer"]:::good

    Src L_Src_Clean_0@--> Clean
    Clean L_Clean_Emb_0@--> Emb
    Emb L_Emb_DB_0@--> DB
    Q L_Q_Search_0@--> Search
    DB L_DB_Search_0@--> Search
    Search L_Search_Snip_0@--> Snip
    Snip L_Snip_LLM_0@--> LLM
    LLM L_LLM_Out_0@--> Out

    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef vector fill:#D6EAF8,stroke:#2E86C1,color:#1F2937

    linkStyle 0 stroke:#2E86C1,fill:none
    linkStyle 1 stroke:#2E86C1,fill:none
    linkStyle 2 stroke:#2E86C1,fill:none
    linkStyle 3 stroke:#00C853,fill:none
    linkStyle 4 stroke:#2E86C1,fill:none
    linkStyle 5 stroke:#00C853,fill:none
    linkStyle 6 stroke:#00C853,fill:none
    linkStyle 7 stroke:#00C853,fill:none

    L_Src_Clean_0@{ animation: slow }
    L_Clean_Emb_0@{ animation: slow }
    L_Emb_DB_0@{ animation: slow }
    L_Q_Search_0@{ animation: slow }
    L_DB_Search_0@{ animation: slow }
    L_Search_Snip_0@{ animation: slow }
    L_Snip_LLM_0@{ animation: slow }
    L_LLM_Out_0@{ animation: slow }
```

## 3d. Block — Retrieval Infrastructure (shared, both collections)

```mermaid
flowchart TD
    E1["examples.jsonl"]
    E2["schema_cards.yaml"]
    R1["review_comment_message<br/>(cleaned)"]
    Emb["Ollama embeddings"]:::vector
    C1[("Chroma: 'context'<br/>collection")]:::vector
    C2[("Chroma: 'reviews'<br/>collection")]:::vector

    E1 L_E1_Emb_0@--> Emb
    E2 L_E2_Emb_0@--> Emb
    R1 L_R1_Emb_0@--> Emb
    Emb L_Emb_C1_0@--> C1
    Emb L_Emb_C2_0@--> C2

    classDef vector fill:#D6EAF8,stroke:#2E86C1,color:#1F2937

    linkStyle 0 stroke:#2E86C1,fill:none
    linkStyle 1 stroke:#2E86C1,fill:none
    linkStyle 2 stroke:#2E86C1,fill:none
    linkStyle 3 stroke:#2E86C1,fill:none
    linkStyle 4 stroke:#2E86C1,fill:none

    L_E1_Emb_0@{ animation: slow }
    L_E2_Emb_0@{ animation: slow }
    L_R1_Emb_0@{ animation: slow }
    L_Emb_C1_0@{ animation: slow }
    L_Emb_C2_0@{ animation: slow }
```

## 3e. Block — Conversation Memory

```mermaid
flowchart TD
    Q["New question"]:::good
    Buf[("Buffer: last N turns<br/>(question, tool, answer)")]:::memory
    Add["Formatted into prompt<br/>as RECENT CONVERSATION"]:::memory
    Ans["New answer produced"]:::good
    Append["Append turn,<br/>drop oldest if over N"]:::memory

    Q L_Q_Buf_0@--> Buf
    Buf L_Buf_Add_0@--> Add
    Add L_Add_Ans_0@-.-> Ans
    Ans L_Ans_Append_0@--> Append
    Append L_Append_Buf_0@-. next turn .-> Buf

    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef memory fill:#EDE3F8,stroke:#7B5EA7,color:#1F2937

    linkStyle 0 stroke:#7B5EA7,fill:none
    linkStyle 1 stroke:#7B5EA7,fill:none
    linkStyle 2 stroke:#7B5EA7,fill:none
    linkStyle 3 stroke:#7B5EA7,fill:none
    linkStyle 4 stroke:#7B5EA7,fill:none

    L_Q_Buf_0@{ animation: slow }
    L_Buf_Add_0@{ animation: slow }
    L_Add_Ans_0@{ animation: slow }
    L_Ans_Append_0@{ animation: slow }
    L_Append_Buf_0@{ animation: slow }
```

## 3f. Block — Orchestrator (orchestrator.py)

The dispatcher, not an agent. It makes exactly **one** LLM classification
call, then hands off to whichever fixed pipeline(s) it picked — each of
which already has its own validator / categorical check / execute (SQL
Tool) or embed / search / summarize (Reviews Tool) guardrails. The
orchestrator itself never touches the database, never re-decides mid-flight,
and never loops — that's what keeps it a dispatcher and not an autonomous
agent (Rule 3 in PROJECT.md).

```mermaid
flowchart TD
    Q["Question + recent<br/>conversation context"]:::good
    Mem[("memory.py buffer")]:::memory
    LLM{"ONE classification call:<br/>sql / reviews / both?"}:::route
    SQL["SQL Tool<br/>(validator → categorical_check → execute)"]
    Rev["Reviews Tool<br/>(embed → search → summarize)"]:::vector
    Merge["Merge results if both"]
    Out["Return to answer_synth.py<br/>+ append turn to memory"]:::good
    Note["Rule 3: exactly one call in,<br/>fixed pipeline out —<br/>never a free-roaming agent"]:::check

    Q L_Q_LLM_0@--> LLM
    Mem L_Mem_LLM_0@--> LLM
    LLM L_LLM_SQL_0@-->|sql| SQL
    LLM L_LLM_Rev_0@-->|reviews| Rev
    LLM L_LLM_SQL_1@-->|both| SQL
    LLM L_LLM_Rev_1@-->|both| Rev
    SQL L_SQL_Merge_0@--> Merge
    Rev L_Rev_Merge_0@--> Merge
    Merge L_Merge_Out_0@--> Out
    LLM L_LLM_Note_0@-.-> Note

    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef memory fill:#EDE3F8,stroke:#7B5EA7,color:#1F2937
    classDef vector fill:#D6EAF8,stroke:#2E86C1,color:#1F2937
    classDef route fill:#FFE0CC,stroke:#C2703D,color:#1F2937
    classDef check fill:#FFF4CC,stroke:#B88A00,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#7B5EA7,fill:none
    linkStyle 2 stroke:#00C853,fill:none
    linkStyle 3 stroke:#2E86C1,fill:none
    linkStyle 4 stroke:#00C853,fill:none
    linkStyle 5 stroke:#2E86C1,fill:none
    linkStyle 6 stroke:#00C853,fill:none
    linkStyle 7 stroke:#2E86C1,fill:none
    linkStyle 8 stroke:#00C853,fill:none
    linkStyle 9 stroke:#FFAB00,fill:none

    L_Q_LLM_0@{ animation: slow }
    L_Mem_LLM_0@{ animation: slow }
    L_LLM_SQL_0@{ animation: slow }
    L_LLM_Rev_0@{ animation: slow }
    L_LLM_SQL_1@{ animation: slow }
    L_LLM_Rev_1@{ animation: slow }
    L_SQL_Merge_0@{ animation: slow }
    L_Rev_Merge_0@{ animation: slow }
    L_Merge_Out_0@{ animation: slow }
    L_LLM_Note_0@{ animation: slow }
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

    In L_In_P_0@--> P
    P L_P_D1_0@--> D1
    D1 L_D1_D2_0@-->|yes| D2
    D1 L_D1_Block_0@-->|no| Block
    D2 L_D2_Cap_0@-->|yes| Cap
    D2 L_D2_Block_0@-->|no| Block
    Cap L_Cap_Pass_0@--> Pass

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef bad fill:#FDE2E1,stroke:#C84C4C,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#00C853,fill:none
    linkStyle 2 stroke:#00C853,fill:none
    linkStyle 3 stroke:#D50000,fill:none
    linkStyle 4 stroke:#00C853,fill:none
    linkStyle 5 stroke:#D50000,fill:none
    linkStyle 6 stroke:#00C853,fill:none

    L_In_P_0@{ animation: slow }
    L_P_D1_0@{ animation: slow }
    L_D1_D2_0@{ animation: slow }
    L_D1_Block_0@{ animation: slow }
    L_D2_Cap_0@{ animation: slow }
    L_D2_Block_0@{ animation: slow }
    L_Cap_Pass_0@{ animation: slow }
```

## 5. Block — Categorical Check (categorical_check.py)

```mermaid
flowchart TD
    In["Validated SQL"]:::good
    Ex["Extract literal values compared to<br/>categorical columns (status, payment_type...)"]
    Chk{"Value exists in real<br/>distinct-values list?"}
    Ok["Run it (pass to execute.py)"]:::good
    Flag["Flag: low-confidence<br/>Ask user to clarify<br/>(never auto-correct)"]:::bad

    In L_In_Ex_0@--> Ex
    Ex L_Ex_Chk_0@--> Chk
    Chk L_Chk_Ok_0@-->|yes| Ok
    Chk L_Chk_Flag_0@-->|no| Flag

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef bad fill:#FDE2E1,stroke:#C84C4C,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#00C853,fill:none
    linkStyle 2 stroke:#00C853,fill:none
    linkStyle 3 stroke:#FFAB00,fill:none

    L_In_Ex_0@{ animation: slow }
    L_Ex_Chk_0@{ animation: slow }
    L_Chk_Ok_0@{ animation: slow }
    L_Chk_Flag_0@{ animation: slow }
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

    In L_In_Run_0@--> Run
    Run L_Run_D_0@--> D
    D L_D_Rows_0@-->|no| Rows
    D L_D_Retry_0@-->|yes| Retry
    Retry L_Retry_Feed_0@-->|yes| Feed
    Retry L_Retry_Give_0@-->|no| Give
    Feed L_Feed_Run_0@--> Run

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef bad fill:#FDE2E1,stroke:#C84C4C,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#00C853,fill:none
    linkStyle 2 stroke:#00C853,fill:none
    linkStyle 3 stroke:#FFAB00,fill:none
    linkStyle 4 stroke:#D50000,fill:none
    linkStyle 5 stroke:#D50000,fill:none
    linkStyle 6 stroke:#D50000,fill:none

    L_In_Run_0@{ animation: slow }
    L_Run_D_0@{ animation: slow }
    L_D_Rows_0@{ animation: slow }
    L_D_Retry_0@{ animation: slow }
    L_Retry_Feed_0@{ animation: slow }
    L_Retry_Give_0@{ animation: slow }
    L_Feed_Run_0@{ animation: slow }
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

    In L_In_Case_0@--> Case
    Case L_Case_Empty_0@--> Empty
    Case L_Case_LowConf_0@--> LowConf
    Case L_Case_Normal_0@--> Normal
    Empty L_Empty_Out_0@--> Out
    LowConf L_LowConf_Out_0@--> Out
    Normal L_Normal_Out_0@--> Out

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#FFAB00,fill:none
    linkStyle 2 stroke:#FFAB00,fill:none
    linkStyle 3 stroke:#00C853,fill:none
    linkStyle 4 stroke:#FFAB00,fill:none
    linkStyle 5 stroke:#FFAB00,fill:none
    linkStyle 6 stroke:#00C853,fill:none

    L_In_Case_0@{ animation: slow }
    L_Case_Empty_0@{ animation: slow }
    L_Case_LowConf_0@{ animation: slow }
    L_Case_Normal_0@{ animation: slow }
    L_Empty_Out_0@{ animation: slow }
    L_LowConf_Out_0@{ animation: slow }
    L_Normal_Out_0@{ animation: slow }
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
        G1 L_G1_G2_0@--> G2
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
        E1 L_E1_E2_0@--> E2
    end

    subgraph B6["6. answer_synth.py"]
        A1["LLM writes plain-English answer from result rows"]
    end

    Ans["Answer shown to user"]:::good

    Q L_Q_C1_0@--> C1
    C3 L_C3_G1_0@--> G1
    G2 L_G2_V1_0@--> V1
    V1 L_V1_Block1_0@-->|fail| Block1
    V1 L_V1_K1_0@-->|pass| K1
    K1 L_K1_Flag1_0@-->|unknown value| Flag1
    K1 L_K1_E1_0@-->|ok| E1
    E2 L_E2_G2_0@-. retry .-> G2
    E2 L_E2_A1_0@-->|success| A1
    A1 L_A1_Ans_0@--> Ans
    Flag1 L_Flag1_Ans_0@--> Ans

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef bad fill:#FDE2E1,stroke:#C84C4C,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#00C853,fill:none
    linkStyle 2 stroke:#00C853,fill:none
    linkStyle 3 stroke:#00C853,fill:none
    linkStyle 4 stroke:#00C853,fill:none
    linkStyle 5 stroke:#D50000,fill:none
    linkStyle 6 stroke:#00C853,fill:none
    linkStyle 7 stroke:#FFAB00,fill:none
    linkStyle 8 stroke:#00C853,fill:none
    linkStyle 9 stroke:#D50000,fill:none
    linkStyle 10 stroke:#00C853,fill:none
    linkStyle 11 stroke:#00C853,fill:none
    linkStyle 12 stroke:#FFAB00,fill:none

    L_G1_G2_0@{ animation: slow }
    L_E1_E2_0@{ animation: slow }
    L_Q_C1_0@{ animation: slow }
    L_C3_G1_0@{ animation: slow }
    L_G2_V1_0@{ animation: slow }
    L_V1_Block1_0@{ animation: slow }
    L_V1_K1_0@{ animation: slow }
    L_K1_Flag1_0@{ animation: slow }
    L_K1_E1_0@{ animation: slow }
    L_E2_G2_0@{ animation: slow }
    L_E2_A1_0@{ animation: slow }
    L_A1_Ans_0@{ animation: slow }
    L_Flag1_Ans_0@{ animation: slow }
```

> **Note on edge order:** Mermaid numbers `linkStyle` indices by the order
> edges appear in the source, *including* edges declared inside subgraphs —
> so `G1 --> G2` and `E1 --> E2` (declared up top, inside `B2`/`B5`) are
> indices `0` and `1`, before the edges declared in the main flow further
> down. If you add or remove an edge in this diagram, recount before editing
> `linkStyle`.

---

## 9. Complete Build Roadmap — All Phases

Color grouped by what each phase is really about — data, safety/testing, LLM
connect, retrieval + memory, routing/reviews, then finishing — so the
roadmap tells its own story at a glance, not just a plain progress bar.

```mermaid
---
config:
  layout: fixed
---
flowchart LR
    P0["Phase 0 <br>Real Data and Database"] L_P0_P1_0@--> P1["Phase 1 <br>Semantic Layer"]
    P1 L_P1_P2_0@--> P2["Phase 2<br>Safety layer"]
    P2 L_P2_P3_0@--> P3["Phase 3<br>Value check"]
    P3 L_P3_P4_0@--> P4["Phase 4<br>Gold Test Set"]
    P4 L_P4_P5_0@--> P5["Phase 5<br>Connect Real LLM"]
    P5 L_P5_P55a_0@--> P55a["Phase<br> 5.5a<br>Retrieval + Memory"]
    P55a L_P55a_P55b_0@--> P55b["Phase<br> 5.5b<br>Reviews Tool + Orchestrator"]
    P55b L_P55b_P6_0@--> P6["Phase 6<br>Full Agent"]
    P6 L_P6_P7_0@--> P7["Phase 7<br>Answer Synthesis"]
    P7 L_P7_P8_0@--> P8["Phase 8<br>Interface"]
    P8 L_P8_P9_0@--> P9["Phase 9<br>Polishing And Completion"]

     P55a:::memory
     P55b:::route
     P9:::good
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef memory fill:#EDE3F8,stroke:#7B5EA7,color:#1F2937
    classDef route fill:#FFE0CC,stroke:#C2703D,color:#1F2937
    linkStyle 0 stroke:#2979FF,fill:none
    linkStyle 1 stroke:#2979FF,fill:none
    linkStyle 2 stroke:#FFAB00,fill:none
    linkStyle 3 stroke:#FFAB00,fill:none
    linkStyle 4 stroke:#AA00FF,fill:none
    linkStyle 5 stroke:#7B5EA7,fill:none
    linkStyle 6 stroke:#C2703D,fill:none
    linkStyle 7 stroke:#00C853,fill:none
    linkStyle 8 stroke:#00C853,fill:none
    linkStyle 9 stroke:#00C853,fill:none
    linkStyle 10 stroke:#00C853,fill:none

    L_P0_P1_0@{ animation: slow } 
    L_P1_P2_0@{ animation: slow } 
    L_P2_P3_0@{ animation: slow } 
    L_P3_P4_0@{ animation: slow } 
    L_P4_P5_0@{ animation: slow } 
    L_P5_P55a_0@{ animation: slow } 
    L_P55a_P55b_0@{ animation: slow } 
    L_P55b_P6_0@{ animation: slow } 
    L_P6_P7_0@{ animation: slow } 
    L_P7_P8_0@{ animation: slow } 
    L_P8_P9_0@{ animation: slow }
```