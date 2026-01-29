# ChartSense Multi-Agent System

## How It Works

You only interact with **ONE bot** - the PM Bot. It automatically spawns sub-agents for:
- **Coding** - Implements features and fixes
- **Code Review** - Checks quality and security
- **QA Testing** - Runs tests and validates UI

## Quick Start

1. Double-click `start-pm.bat` in the project root
2. When Claude opens, paste:
   ```
   Read .agents/pm/AGENT.md and follow those instructions.
   ```
3. Tell the PM what you want to build
4. Sit back - it handles everything else

## What Happens Behind the Scenes

```
You → PM Bot → Spawns Coder Agent → Code written
                    ↓
              Spawns Review Agent → Code reviewed
                    ↓
              Spawns QA Agent → Tests run
                    ↓
         PM reports back to you
```

## File Structure

```
.agents/
├── pm/AGENT.md        # PM Bot instructions (the orchestrator)
├── coder/AGENT.md     # Coder persona (spawned by PM)
├── reviewer/AGENT.md  # Reviewer persona (spawned by PM)
├── qa/AGENT.md        # QA persona (spawned by PM)
├── task-queue.json    # Current tasks and status
├── dashboard.json     # Progress summary
└── tasks/             # Individual task specs
```

## Commands You Can Give the PM

- "Add [feature] to [location]"
- "Fix the bug where [description]"
- "Refactor [component] to [improvement]"
- "What's the current status?"
- "Continue working on [task]"

The PM handles breaking it down, delegating, reviewing, testing, and reporting back.
