# Flowcharts — Mermaid Source

Same 9 flowcharts as in the Word doc, in raw Mermaid syntax, for pasting into
Obsidian (or any Mermaid-compatible tool). Word can't render Mermaid natively,
so the `.docx` uses rendered images of these same diagrams — this file is the
editable source.


## 1. High-Level Pipeline

```mermaid
flowchart TD
    Q["User Question<br/>(plain English)"]:::good
    R["Understand the Question<br/>Pull matching schema cards, glossary terms,<br/>and similar examples"]
    G["Generate SQL<br/>LangChain + LLM<br/>(provider picked at runtime)"]
    S["Safety Checks<br/>Structure valid? Real values?"]:::check
    E["Run Query<br/>Read-only database"]
    A["Plain-English Answer"]:::good

    Q L_Q_R_0@--> R
    R L_R_G_0@--> G
    G L_G_S_0@--> S
    S L_S_E_0@--> E
    E L_E_A_0@--> A
    E L_E_G_0@-. error → retry (max 2) .-> G

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937
    classDef check fill:#FFF4CC,stroke:#B88A00,color:#1F2937
    classDef bad fill:#FDE2E1,stroke:#C84C4C,color:#1F2937

    linkStyle 0 stroke:#00C853,fill:none
    linkStyle 1 stroke:#00C853,fill:none
    linkStyle 2 stroke:#00C853,fill:none
    linkStyle 3 stroke:#00C853,fill:none
    linkStyle 4 stroke:#00C853,fill:none
    linkStyle 5 stroke:#D50000,fill:none

    L_Q_R_0@{ animation: slow }
    L_R_G_0@{ animation: slow }
    L_G_S_0@{ animation: slow }
    L_S_E_0@{ animation: slow }
    L_E_A_0@{ animation: slow }
    L_E_G_0@{ animation: slow }
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

Color grouped by what each phase is really about — data, safety/testing, LLM,
then finishing — so the roadmap tells its own story at a glance, not just a
plain progress bar.

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

    P0 L_P0_P1_0@--> P1
    P1 L_P1_P2_0@--> P2
    P2 L_P2_P3_0@--> P3
    P3 L_P3_P4_0@--> P4
    P4 L_P4_P5_0@--> P5
    P5 L_P5_P6_0@--> P6
    P6 L_P6_P7_0@--> P7
    P7 L_P7_P8_0@--> P8
    P8 L_P8_P9_0@--> P9

    classDef default fill:#FFFFFF,stroke:#3F4A5A,color:#1F2937
    classDef good fill:#DFF6DD,stroke:#4F8A57,color:#1F2937

    linkStyle 0 stroke:#2979FF,fill:none
    linkStyle 1 stroke:#2979FF,fill:none
    linkStyle 2 stroke:#FFAB00,fill:none
    linkStyle 3 stroke:#FFAB00,fill:none
    linkStyle 4 stroke:#AA00FF,fill:none
    linkStyle 5 stroke:#AA00FF,fill:none
    linkStyle 6 stroke:#00C853,fill:none
    linkStyle 7 stroke:#00C853,fill:none
    linkStyle 8 stroke:#00C853,fill:none

    L_P0_P1_0@{ animation: slow }
    L_P1_P2_0@{ animation: slow }
    L_P2_P3_0@{ animation: slow }
    L_P3_P4_0@{ animation: slow }
    L_P4_P5_0@{ animation: slow }
    L_P5_P6_0@{ animation: slow }
    L_P6_P7_0@{ animation: slow }
    L_P7_P8_0@{ animation: slow }
    L_P8_P9_0@{ animation: slow }
```
