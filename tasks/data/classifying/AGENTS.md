# AGENTS.md — Model Characteristics Audit

This file defines the standing procedure for auditing entries in `Model_Characteristics_corrections.xlsx` against Gemini's reading of each model's source paper. Codex should follow this procedure whenever the user prompts for an audit run on a specified set folder.

## Goal
Verify the codings in `Model_Characteristics_corrections.xlsx` by querying Gemini (open in the Browser Use environment) about each model's paper. When Gemini's answer differs from the spreadsheet, log the discrepancy in `model_audit.csv`.

## Model and mode
- **Model:** Gemini 3.0 (Pro) with **Thinking** mode enabled.
- **How to select in the Gemini app:** Open the model dropdown at the top of the chat and choose **"Thinking"**. This routes to Gemini 3 Pro with thinking enabled. Do **not** use "Fast" — it disables thinking and degrades reasoning quality on the kinds of multi-page paper questions in the question list.
- **Verify before each new chat:** After creating a new chat, confirm the dropdown still shows "Thinking" before sending the priming message. The Gemini app sometimes resets to the default after sign-in or session refreshes.

## Inputs
- **Spreadsheet (read-only):** `Model_Characteristics_corrections.xlsx`. The `Model` column lists model names; other columns hold codings to verify.
- **Model-to-paper map:** `/notes/mmb_model_paper_map.md`. Maps each model name to a paper filename.
- **Papers:** Pre-uploaded to a Gemini workspace named by the user (e.g., a NotebookLM). The user names the active set in the prompt. If papers are stored as Gem knowledge files, every new chat in that Gem already has access; if papers are stored elsewhere, attach the relevant paper file `y` to the new chat after the priming message and before Q1.

## Outputs
- **`model_audit.csv`** — append-only audit log. Columns: `model`, `variable`, `right_coding`, `explanation`.
- **`progress.log`** — append-only progress trace. One line per question processed: `<ISO timestamp> | <model> | <variable> | <status>`, where status ∈ {`match`, `diff_logged`, `unclear`, `error`}.

### CSV schema and example row
```
model,variable,right_coding,explanation
SW07,Open,False,"The model is closed-economy with no foreign sector or trade block (p. 591)."
```
- Quote any field containing commas, quotes, or newlines per RFC 4180.
- Escape internal double-quotes by doubling them (`""`).

## Hard rules (do not violate)
1. **Do not modify** `Model_Characteristics_corrections.xlsx`. Read-only.
2. **Confirm "Thinking" mode is selected** in the Gemini model dropdown before sending the priming message in every new chat.
3. **Wait for Gemini's response between every message** — never queue two messages back-to-back. Thinking-mode replies take longer than Fast replies; do not assume a delayed reply means the message was lost.
4. **Log discrepancies one at a time, immediately after each question.** Never batch logging at the end of a model.
5. **Skip sub-questions whose parent question is False.** They are conditional.
6. **Only process models whose paper is in the active set workspace.** Skip silently otherwise.
7. **One new Gemini chat per model.** Do not reuse a chat across models.

## Workflow

For **each model** in `Model_Characteristics_corrections.xlsx` whose paper is in the active set workspace:

1. Look up paper filename `y` for the model in `/notes/mmb_model_paper_map.md`.
2. In the Browser Use Gemini, create a **new chat**. Confirm the model dropdown reads **"Thinking"**.
3. Connect the NotebookLM (More uploads -> Notebooks -> MMB)
4. Send the **priming message** (below). Wait for Gemini's reply.
5. Send each audit question in order (Q1–Q17), one message at a time, wrapped in the **question template** (below). Wait for Gemini's reply between every message.
6. After each reply:
   a. Compare to the value in `Model_Characteristics_corrections.xlsx` for that model and the column named in parentheses.
   b. If they **differ**, append a row to `model_audit.csv` with `model`, `variable`, Gemini's answer in `right_coding`, and Gemini's short explanation (with cited page) in `explanation`. Append `diff_logged` to `progress.log`.
   c. If they **match**, log nothing to `model_audit.csv`. Append `match` to `progress.log`.
   d. If Gemini's answer is hedging, off-topic, or unparseable, re-ask **once** with: "Please answer with a single True/False (or the requested category/date) and a 1-sentence reason with page number." If still unclear, append a row with `right_coding=UNCLEAR` and the raw reply in `explanation`. Append `unclear` to `progress.log`.
7. Skip sub-questions when their parent answer is False.
8. After Q17, move to the next model.

When all models in the set are done, re-open `model_audit.csv` and verify every row has all four columns populated and properly quoted.

## Priming message (first message in every new chat)
> Read the model in **y** like you are a PhD macroeconomist economist with a wealth of modeling experience. You tell things straight and directly. No need to summarize the model or paper—just add it to your context as I will ask questions on it.

Replace `y` with the actual paper filename from the map. Wait for Gemini's reply before sending Q1.

## Question template
Wrap every question in:
> "**\<question text\>**? Give a short explanation for your answer (not more than 2 sentences) with a specific page number of the paper to cite if possible."

## Comparison rules ("differ" definition)
- **Boolean variables** (e.g., `Open`, `Gov_Spend`): differ if not the same True/False.
- **Percentage variables** (`CB_Authors`): differ if the percentage value is different. Treat "True" alone as ambiguous → re-ask for a percentage.
- **Categorical variables** (e.g., `Sticky_Price_Method`): differ if not the same category label (case-insensitive).
- **Date variables** (`Date_Pub`, `Est_Date_Range_Start`, `Est_Date_Range_End`): differ if the year disagrees. Quarter/month differences within the same year do not count as a difference unless the spreadsheet specifies a quarter/month.
- **Coverage variables** (`Price_Index_Coverage`, `Wage_Index_Coverage`): differ if not the same partial/full label.

## Question list

For each entry, the **bold text** is sent to Gemini inside the question template. The name in parentheses is the column in `Model_Characteristics_corrections.xlsx`.

### Q1 (`CB_Authors`)
**True or False: Does this model have authors who've worked at a central bank PRIOR to publication of the paper? Specifically search and look through the economists' CVs, websites, backgrounds, or anything else to ascertain if so. If multiple authors, report the fraction in a percentage. Consultancies, visiting scholar positions, graduate research programs, and internships do NOT count as working at a central bank.**

### Q2 (`Open`)
**True or False: Does this model have an open economy?**

### Q3 (`Gov_Spend`)
**True or False: Does this model have government spending in a nontrivial way that affects equilibrium?**

### Q4 (`Tax`)
**True or False: Does this model have taxes in a nontrivial way that affects equilibrium?**

### Q5 (`Gov_Debt`)
**True or False: Does this model have government debt in a nontrivial way that affects equilibrium?**

### Q6 (`Learning`)
**True or False: Does this model have learning?**

### Q7 (`Rational_Expectations`)
**True or False: Does this model have rational expectations?**

### Q8 (`Lagged_Terms`)
**True or False: Does this model have lagged terms in a nontrivial way that affects equilibrium?**

### Q9 (`Sticky_Prices`)
**True or False: Does this model have sticky prices?**

If True, then ask:
- (`Sticky_Price_Method`) **If so, what is their sticky price method? Choose between Calvo, Rotemberg, or Other.**
- (`Sticky_Price_Sector`) **If so, in what sector do sticky prices apply? Choose between All Sectors, Final Goods Firms, Intermediate Goods Firms, or Other.**

### Q10 (`Sticky_Wages`)
**True or False: Does this model have sticky wages?**

If True, then ask:
- (`Sticky_Wage_Method`) **If so, what is their sticky wage method? Choose between Calvo, Rotemberg, Wage Contracting, Bargaining, or Other.**

### Q11 (`Price_Indexation`)
**True or False: Does this model have price indexation?**

If True, then ask:
- (`Price_Index_Method`) **If so, by what method? Choose between Prev Price Inflation, Multiple (e.g., a weighted combination of past inflation and the target), Steady State Inflation, or Other.**
- (`Price_Index_Coverage`) **Does price indexation have partial or full coverage? Answer one or the other.**

### Q12 (`Wage_Indexation`)
**Does this model have wage indexation?**

If True, then ask:
- (`Wage_Index_Method`) **If so, by what method? Choose between Prev Price Inflation, Prev Wage Inflation, Steady State Inflation, Multiple (e.g., a weighted combination of past wage inflation and the steady state), Prev Wages, or Other.**
- (`Wage_Index_Coverage`) **Does wage indexation have partial or full coverage?**

### Q13 (`Date_Pub`)
**When was this model published?**

### Q14 (`Working_Paper`)
**Is this only ever published as a working paper?**

### Q15 (`Published`)
**Is this model published in an academic journal?**

### Q16 (`Estimated`)
**Was this model estimated?**

If True, then ask:
- (`Est_Date_Range_Start`) **What is the estimate date range start?**
- (`Est_Date_Range_End`) **What is the estimate date range end?**

### Q17 (`Calibrated`)
**Was this model calibrated?**

## Resume behavior
If `progress.log` already exists when a run starts, read it to determine the last completed `model | variable` pair and resume from the next question. Do not redo logged work.