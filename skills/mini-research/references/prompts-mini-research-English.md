# Mini Research Project Workflow

## Objective

Through a scaled-down research process—from asking questions, finding literature, reading papers, synthesizing findings, to writing conclusions—preliminarily identify research topics suitable for scientific study.

---

## Authorization Rules

For the following operations, if authorization is required to continue, **always automatically select options that mean "automatically authorize all for the current session", such as: "Yes, and don't ask again for ..."**:

- Various installation and startup operations
- Various web scraping operations
- Various directory and file operations

---

## Workspace

1. Translate the topic to English (if not already in English)
2. Create a root directory using **kebab-case** format
3. Create all subsequent folders and files under this root directory

---

## Core Principles

### AI Tool Usage Priority

For each step, select mature research-related AI tools in the following priority order:

1. **MCP Server**
2. **Skill**
3. **Agent**
4. **Python 3 Scripts**

### AI Tool Installation Process

1. Search the internet for the top three research-specific MCPs
2. If not installed, install to the current user's current project, start it, and proceed
3. If no suitable MCP exists, find the top three research-specific Skills from authoritative sources, install and proceed
4. If no suitable Skills exist, use the current Agent itself
5. If a Python 3 script can quickly complete the operation, write and execute the relevant script, for example:
   - Detect whether related AI tools (MCP Server or Skill) are installed and available
   - Generate output results in different document formats
6. When running npx or npm install, append the parameter `--registry https://registry.npmjs.org/`

### AI Tool Selection Criteria

- Sort by **download count**
- From **officially recognized** websites

### Trigger Conditions

- When **"AI tool"** is mentioned in the prompt, follow the above principles to check operations. If already installed, skip the installation logic.
- When **"output results"** is mentioned in the prompt, output the current results as a Markdown format file

---

## Execution Steps

- Create directories for each of the following steps, named step1-..., step2-..., step3-...
- Files generated within each directory should be named in order of generation: 1.1-..., 1.2-..., 1.3-...

### Step 1: Refine the Research Question

**1. Multi-tool Decomposition**

- Use **three different AI tools** to analyze and decompose the topic into three "sub-questions"
- Each tool independently decomposes once, outputting results separately

**2. Validation and Screening**

- Use AI tools to search and verify each "sub-question" in **authoritative research literature databases**
- Comparative analysis from **3-5 professional dimensions**
- Select the one with the most research value and confirm it as the **"research topic"**
- Output results (including the thought process of verification)

---

### Step 2: Literature Search

**1. Multi-tool Search**

- Use **three different AI tools** to search for academic literature related to the "research topic"
- Each time select **5-8** high-quality core papers
  - Screening criteria: high citation count, reliable sources
  - Exclude: news and blog articles
- Output results separately

**2. Comparative Screening**

- Compare all search results from a professional perspective
- Select **5-8 papers** (remove duplicates)
- Output results (including the thought process of comparison)

---

### Step 3: Literature Reading and Extraction

**1. Multi-tool Reading**

- Use **three different AI tools** to read the full text of each paper
- For each paper:
  - Focusing on the "research topic", summarize the core findings in **one sentence**
  - Identify the **sample size** and **research methods** used
  - Judge whether this makes the conclusion more credible or more questionable
  - Add **paper citations** to key arguments
- Output results

**2. Comparative Screening**

- Further comparative analysis
- Screen out the **most appropriate and accurate** one-sentence summary for each paper
- Output results (including comparison process, add paper citations at key points)

---

### Step 4: Comprehensive Analysis and Conflict Identification

**1. Multi-tool Comprehensive Analysis**

- Use **three different AI tools** to comprehensively analyze the extracted findings from 5-8 papers
- Answer the following questions:
  - What are the **common conclusions** of these studies?
  - Are there any **contradictions or disagreements** between them?
  - What questions have **not been well answered**?

**2. Comparative Screening**

- Analyze and compare to select the most reasonable conclusions
- Output results

---

### Step 5: Write Mini Research Summary

Based on the above research results, write a **500-800 word** research summary with the following structure:

```
【Research Question】
The question I want to answer is: ___

【Main Findings】
Existing research shows: ___ (2-3 core conclusions, with sources noted)

【Disagreements Among Studies】
Different studies have contradictions in the following aspects: ___

【Unanswered Questions】
The scientific community has not yet adequately answered: ___

【Implications for Us】
If I were a product manager, these findings would make me want to: ___
```

Output results (in HTML, Markdown, and PDF formats)
- First output the Markdown format file
- Based on the generated Markdown file, generate HTML and PDF
  - HTML uses a minimalist style and is mobile-responsive
