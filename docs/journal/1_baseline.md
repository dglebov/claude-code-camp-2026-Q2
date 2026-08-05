# Week 1 Technical Documentation

## Technical Goal

In Week 1 we will create a baseline agent that can play a MUD on behalf of the player. We will use the provided Ruby agent and a ported Python version.

The agent should include:
- A simple agentic loop
- A tool registry with associated tools
- Support for multiple backends
- Logging capabilities
- A DSL so the agent can be used like an SDK
- Global binary execution to interact via the CLI
- An optional CLI model
- Context management that compacts messages when a size limit is reached
- Its own configuration directory

## Technical Observability

The Opus‑5 model works very well for planning and executing code transitions from Ruby to Python.

After I close the project and rerun it, the model can hallucinate severely—even when using Claude.MD or similar. Enhancing Claude doesn’t always help, and I have to give very precise instructions to get it to follow the required steps. 

That adds another layer of observability, allowing planning to work exceptionally well. When I schedule something in advance, I ask Claude to plan it too. This approach works, and when I refer back to Claude about the original plan and our decisions to port the code, the results are usually excellent. 



## Technical Uncertainty

- I am uncertain about my code‑reading skills; a lot of information remains unclear during code conversion and overall architecture design.  
- I am unsure how reliably the cloud will convert code from Ruby to Python.  
- I lack confidence in testing this code. Even with Ruby, some code needs adjustment. Standard tools sometimes produce input that doesn’t match the video series. Fortunately, I captured a screenshot showing the expected result, and the cloud could fix it. However, I am uncertain whether I can rely on this approach for a real project in the future.
- as we grow it's harder to understand code 


## Technical Hypotheses

Next time I need to design the architecture of an agent or any cloud‑based application, I’ll plan ahead and leverage existing skills and solutions developed by others, rather than waiting for the cloud to ask countless questions before I start coding. 