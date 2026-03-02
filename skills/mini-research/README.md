# Mini Research Skill

A Claude Code skill that guides you through a scaled-down academic research workflow—from formulating questions to writing research summaries.

## Purpose

Help users systematically identify and explore research topics suitable for scientific study through:
- Multi-tool validation and comparison
- Literature search and analysis
- Structured research output

## Workflow Steps

| Step | Description |
|------|-------------|
| **1. Refine Research Question** | Decompose topic into sub-questions using multiple AI tools, validate against literature databases, select the most valuable research topic |
| **2. Literature Search** | Search academic databases with multiple tools, select 5-8 high-quality papers based on citations and source reliability |
| **3. Literature Reading** | Extract core findings, sample sizes, and research methods from each paper with citations |
| **4. Comprehensive Analysis** | Identify common conclusions, contradictions, and unanswered questions across papers |
| **5. Write Summary** | Generate a 500-800 word research summary |

## Output

The skill produces a structured research summary containing:
- Research Question
- Main Findings (with citations)
- Disagreements Among Studies
- Unanswered Questions
- Practical Implications

Output formats: **Markdown**, **HTML** (mobile-responsive), and **PDF**

## Usage

Invoke the skill in Claude Code:

```
/itpretty-skills:mini-research [your research topic]
```

All files are organized in step-based directories (`step1-...`, `step2-...`, etc.) under a kebab-case root folder named after your topic.
