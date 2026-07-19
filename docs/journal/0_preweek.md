# Pre-week technical documentation 

## Technical goal 

Let's explore how the cloud functions within an agent‑based environment, covering how to create agents, operate them, and leverage AI agents to achieve greater capabilities. 
We should also explore different models to determine the minimal model capable of playing our game.

Examples of different engines:
- A playing agent  
- An agent that utilizes skills  
- A sub‑agent used as an SDK  
- A sub‑agent that skills 

## Technical observability 

- The agent initiated a fight without my prompting.  
- The agent began exploring and independently designed its memory, which was impressive. 

## Techicak Uncertainty

- I'm uncertain whether the agentic loop is effective enough to drive a non‑coding workflow.  
- I'm uncertain whether Telnet or Netcat (nc) is the best tool to use.  
- I'm uncertain if we can implement a single connection instead of creating a new separate connection for each move. 

## Technical Hypotheses

- I think the small model alone will not be dependable, and that each responsibility moved from the model into code will recover part of the gap.
- I think instructions alone will not make the model keep memory or follow plans, something will have to enforce both.
- We'll need an interface as man aging telnet session makes things difficult 
