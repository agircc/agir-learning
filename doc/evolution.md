# Scenario Evolution in AGIR Learning

This document explains the evolution phase in AGIR Learning, where scenarios are executed to create interactive learning experiences that help learners develop skills through simulated practice and guided reflection.

## Overview

Evolution is the core learning process in AGIR Learning. It brings constructed scenarios to life by executing the defined states and transitions through AI agents that interact with the learner. This creates a dynamic, responsive learning environment that adapts to the learner's responses.

```mermaid
flowchart TD
    A[Run Evolution] --> B[Create Episode]
    B --> C[Get Initial State]
    C --> D[Process Current State]
    D --> E{Has Next State?}
    E -->|Yes| F[Get Next State]
    F --> D
    E -->|No| G[Complete Episode]
    G --> H[Create Memory]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#bbf,stroke:#333,stroke-width:2px
    style H fill:#bfb,stroke:#333,stroke-width:2px
```

## Evolution Process

The evolution process follows a dynamic execution model with the following steps:

### 1. Episode Creation

An episode represents a single run-through of a scenario:

- System creates a new episode record linked to the scenario and learner
- Sets the initial status to RUNNING
- Prepares the context for agent interactions

```mermaid
sequenceDiagram
    participant EM as Evolution Manager
    participant DB as Database
    
    EM->>DB: a_create_or_find_episode(scenario_id)
    DB-->>EM: new Episode object
    EM->>DB: Set episode.status = RUNNING
    DB-->>EM: Confirm status update
```

### 2. State Processing

For each state in the scenario, the system:

- Identifies the roles involved in the current state
- Creates or retrieves users for each role
- Processes the state according to its type:
  - For single-agent states: Generates a response from the agent
  - For multi-agent states: Conducts a multi-turn conversation

### 3. Step Creation and Execution

Each state execution is tracked as a step:

- System creates a step record with RUNNING status
- For single-agent responses:
  - Generates the LLM response based on the state, role, and context
  - Updates the step with the generated content
  - Marks the step as COMPLETED
- For multi-agent conversations:
  - Creates a conversation record linked to the step
  - Facilitates a multi-turn interaction between agents
  - Stores messages from all participants
  - Updates the step with conversation results

```mermaid
sequenceDiagram
    participant EM as Evolution Manager
    participant LLM as LLM Provider
    participant DB as Database
    
    EM->>DB: e_create_or_find_step(episode_id, state_id, user_id)
    DB-->>EM: step_id
    
    alt Single Agent State
        EM->>LLM: f_generate_llm_response(state, role, user, history)
        LLM-->>EM: response
        EM->>DB: g_update_step(step_id, response, COMPLETED)
    else Multi-Agent State
        EM->>DB: h_create_conversation(state, episode_id, role_users, step_id)
        DB-->>EM: conversation
        EM->>LLM: i_conduct_multi_turn_conversation(conversation, state, role_users)
        LLM-->>EM: conversation_result
        EM->>DB: g_update_step(step_id, conversation_result, COMPLETED)
    end
    
    EM->>DB: Update episode.current_state_id = current_state.id
```

### 4. State Transition

After completing a state, the system determines the next state:

- Queries the database for valid transitions from the current state
- If multiple transitions exist, uses context and agent input to select the appropriate one
- If no transitions exist, the episode is complete

### 5. Episode Completion

When all states have been processed:

- System marks the episode as COMPLETED
- Creates memories based on the episode experience
- These memories can be used for future scenarios or episodes

### 6. Memory Creation

A critical component of the evolution process is memory creation:

- System summarizes the episode experience
- Extracts key insights and learning points
- Creates a permanent memory record for the learner
- These memories form the foundation for skill development and progression

```mermaid
sequenceDiagram
    participant EM as Evolution Manager
    participant DB as Database
    participant LLM as LLM Provider
    
    EM->>DB: Query Episode as COMPLETED
    EM->>DB: Retrieve all steps and conversations
    EM->>LLM: create_episode_memories(episode_data)
    LLM-->>EM: memory_summaries
    EM->>DB: Store memories for learner
    DB-->>EM: Confirm memory creation
```

## Code Structure

The evolution process is implemented through a set of modular files:

- `run_evolution.py` - Main entry point for evolution
- `a_create_or_find_episode.py` - Handles episode creation
- `b_get_initial_state.py` - Identifies the starting state
- `c_get_state_roles.py` - Retrieves roles for a state
- `d_get_or_create_user_for_state.py` - Handles user creation for roles
- `e_create_or_find_step.py` - Creates step records
- `f_generate_llm_response.py` - Generates LLM responses
- `g_update_step.py` - Updates step records
- `h_create_conversation.py` - Creates conversation records
- `i_conduct_multi_turn_conversation.py` - Handles multi-agent conversations
- `j_get_next_state.py` - Determines the next state
- `k_create_memory.py` - Creates memory records

## Running Multiple Episodes

The evolution system supports running multiple episodes for a scenario:

```mermaid
flowchart TD
    A[Run Evolution] --> B[Episode 1]
    A --> C[Episode 2]
    A --> D[Episode n]
    B --> E[Create Memories]
    C --> E
    D --> E
    E --> F[Skill Development]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style F fill:#bfb,stroke:#333,stroke-width:2px
```

This multi-episode approach allows for:
- Iterative skill development
- Practice with variations in the scenario
- Progressive difficulty increases
- Comparative analysis of learner improvement

## Error Handling

The evolution process includes robust error handling:

- If a step fails, it's marked with FAILED status and includes error details
- If an episode encounters critical errors, it's marked as FAILED
- All errors are logged for analysis and debugging
- The system can recover from certain errors and continue execution

## Extending the Evolution Process

The modular nature of the evolution process makes it easy to extend:

1. Add new step types by extending the step processing logic
2. Implement new conversation patterns in the multi-turn conversation handler
3. Create specialized memory creation methods for different learning domains
4. Add analytics and visualization components to track learner progress

These extension points allow AGIR Learning to adapt to diverse learning domains while maintaining a consistent evolution process.
