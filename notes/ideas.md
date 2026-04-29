# Ideas

Use this for loose ideas, extensions, questions, and half-formed directions.


## Checking the Models

The purpose of this task is to test and correct the model classifications I have within the Model_Characteristics_corrections.xlsx. You will query ChatGPT to have it read through all papers to say whether or not the models have the features that Model_Characteristics_corrections.xlsx indicates. When the Model_Characteristics_corrections.xlsx differs from what ChatGPT finds, I want you to ask ChatGPT for an explanation with a specific page number. In a spreadsheet labeled model_audit.csv, log the entries of the Model_Characteristics_corrections.xlsx with differences from what ChatGPT says and the explanation (columns: model, variable, right_coding, explanation).

In the open Browser Use is my ChatGPT. I want you to work in the project folder titled "MMB Set 1" (more such project folders will be uploaded in time). I have already uploaded the papers corresponding to the models that I wish for you to cover in there. See /notes/mmb_model_paper_map.md for a map of the models in the "Model" column of Model_Characteristics_corrections.xlsx to the papers. 

For each model with a paper within the "MMB Set 1" local sources, letting y be the paper corresponding to the model that you take from mmb_model_paper_map.md, I want you to:

- make a new chat within the ChatGPT project
  
- In that specific chat, ask ChatGPT to "Read the model in y like you are a PhD macroeconomist economist with a wealth of modeling experience. You tell things straight and directly. No need to summarize the model or paper---just add it to your context as I will ask questions on it."

- WAIT FOR CHATGPT's RESPONSE BETWEEN THE ABOVE MESSAGE AND EACH OF THE BELOW QUESTIONS
  
- For each of the x snippets below (and sub-snippets only if it says True for the parent question), ask ChatGPT the snippets below. WAIT FOR CHATGPT'S RESPONSE BETWEEN EACH QUESTION. Compare that response to what is in Model_Characteristics_corrections.xlsx. If ChatGPT's answer differs from what is contained in Model_Characteristics_corrections.xlsx, record in model_audit.csv the following: the parenthesis variable in "variable" column, ChatGPT's True/False answer in the "right_coding" column, and ChatGPT's explanation in the "explanation" column. If ChatGPT's answer does not differ, no do log it. Do this logging in model_audit.csv between each question below and not all at once for a given model.
  
  "'x'? Give a sort explanation for your answer (not more than 2 sentences) with a specific page number of the paper to cite if possible." 
  
  Below I provide a list of those attributes with the corresponding column names of Model_Characteristics_corrections.xlsx in parenthesis. If ChatGPT's answer differs from what is contained in Model_Characteristics_corrections.xlsx, record in model_audit.csv the following: the parenthesis variable in "variable" column, ChatGPT's True/False answer in the "right_coding" column, and ChatGPT's explanation in the "explanation" column.
  
  - "True or False: Does this model have authors who've worked at a central bank PRIOR to publication of the paper? Specifically search and look through the economists' CVs, websites, backgrounds, or anything else to ascertain if so. If multiple authors, report the fraction in a percentage. Consultancies, visiting scholar positions, graduate research programs, and internships do NOT count as working at a central bank." (CB_Authors)

  - "True or False: Does this model have an open economy?" (Open)

  - "True or False: Does this model have government spending in a nontrivial way that affects equilibrium?" (Gov_Spend)

  - "True or False: Does this model have taxes in a nontrivial way that affects equilibrium?" (Tax)

  - "True or False: Does this model have government debt in a nontrivial way that affects equilibrium?" (Gov_Debt)

  - "True or False: Does this model have learning?" (Learning)

  - "True or False: Does this model have rational expectations?" (Rational_Expectations)

  - "True or False: Does this model have lagged terms in a nontrivial way that affects equilibrium?" (Lagged_Terms)

  - "True or False: Does this model have sticky prices?" (Sticky_Prices)

    - "if so, what is their sticky price method? Choose between Calvo, Rotemberg, or Other." (Sticky_Price_Method)

    - "if so, in what sector do sticky prices apply? Choose between All Sectors, Final Goods Firms, Intermediate Goods Firms, or Other" (Sticky_Price_Sector)

  - "True or False: Does this model have sticky wages?" (Sticky_Wages)

    - "If so, what is their sticky wage method? Choose between Calvo, Rotemberg, Wage Contracting, Bargaining, or Other." (Sticky_Wage_Method)

  - "True or False: Does this model have price indexation?"  (Price_Indexation)

    - "if so, by what method? Choose between Prev Price Inflation, Multiple (e.g., a weighted combination of past inflation and the target), Steady State Inflation, or Other" (Price_Index_Method)

    - "Does price indexation have partial or full coverage? Answer one or the other." (Price_Index_Coverage)

  - "Does this model have wage indexation?" (Wage_Indexation)

    - "if so, by what method? Choose between Prev Price Inflation, Prev Wage Inflation, Steady State Inflation, Multiple (e.g., a weighted combination of past wage inflation and the steady state), Prev Wages, or Other" (Wage_Index_Method)

    - "does wage indexation have partial or full coverage?" (Wage_Index_Coverage)

  - "When was this model published?" (Date_Pub)

  - "Is this only ever published as a working paper?" (Working_Paper)

  - "Is this model published in an academic journal?" (Published)

  - "Was this model estimated?" (Estimated)

    - "What is the estimate date range start?" (Est_Date_Range_Start)
    - "What is the estimate date range end?" (Est_Date_Range_End)

  - "Was this model calibrated?" (Calibrated)






