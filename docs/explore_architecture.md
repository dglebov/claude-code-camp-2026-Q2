# Explore Agent Architecture

We will explore multiple agent architecture to determine fit for our agent workflow. 


## 1. Agent file with references files

An agent file with references file example agent.md, @~/docs/*.MD


### Techical Observations

#### Haiku
- The coding agent created temporary scripts to manage the socket connection.
- The agent struggled with the deterministic MUD login flow.
- The agent read unrelated repository files and used unnecessary tokens.
- Increasing the model intelligence did not resolve the core connection issue.
- The agent had poor visibility into its failed login attempts.


#### Sonet 5 

- The coding agent created temporary scripts to manage the socket connection.  
- The agent found a proper way to log in using a Python script.  
- Each step required to run the script was inefficient, so the flow was not optimal.  
- Eventually, the agent reached out to the backend and fulfilled the task. 
- player.md and world.md was updated 



## 2. Agent Skills driven by main agent eg ~/.skills

A very common way to drive specific functionality is through Agent Skills, an open format for agents adopted by many coding harnesses and agent SDKs. 


I want a skill that can play a MUD that is running on localhost port 4000. It's a tbaMUD, a variant of circleMUD. I have a player already created, credientials are-  dummy / helloworld. Can you create that skill and create a script to manage the telnet connection and issue commands. 