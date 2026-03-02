# itpretty-skills

A Claude Code plugin package with custom skills.

## Installation

**Option 1: Using Claude Code CLI (Recommended)**

```bash
# start claude
claude

# add new market
/plugin marketplace add itpretty/skills

# install skill mini-research
/plugin install mini-research@itpretty-skills
```

**Option 2: Manual Installation**

Clone the repository to your plugins directory:

```bash
git clone https://github.com/itpretty/skills ~/.claude/plugins/itpretty-skills
```

## Skills

### Mini Research

A scaled-down research workflow—from asking questions, finding literature, reading papers, synthesizing findings, to writing conclusions.

**Usage:**

```
/mini-research [your research topic]
```

[Learn more](./skills/mini-research/README.md)

## Plugin Structure

```
skills/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── skills/
│   └── mini-research/       # Mini Research skill
│       ├── SKILL.md
│       └── README.md
└── README.md
```

## License

MIT
