## 1. Create an episode
episode 

## 2. Find the first state to execute
The first state can be identified using state_transitions

state_transitions contains scenario_id, from_state_id, to_state_id

Using the scenario_id, find all state_transitions, then analyze the from and to ids. First list all the to_ids, then find the state_id that is not in the to_ids list - that's the first state

## 3. Using the identified state, find the associated agent role

## 4. Based on the agent role, find or create a user
In the database's agent_assignments table, search for agent_assignments using role_id and episode_id.
If found, continue using it.
If not found, create a user or find a suitable user, then create agent_assignment

## 5. Create the step corresponding to the state
Have the agent with assigned role request the appropriate LLM based on the model specified for the user, providing information about what this user needs to do for the current state. The LLM generates the corresponding data.

Save the data generated by the LLM in the response field of the steps table

## 6. Find the next state based on state_transition
If the found transition has a condition, check the previous state's step to determine the situation, then decide the next state based on the condition

Sometimes one from_state_id might correspond to multiple to_state_ids under different conditions. For example, for "Post-Hospital Follow-up" the patient might have recovered so the to_state is "case closed", or if the patient hasn't recovered, it's "triage".
To determine if the patient has recovered, check the previous state (e.g., "Recovery") by passing the response from the corresponding step to the LLM to check whether the patient has recovered or not. This determines the final to_state.

Following steps 3-5 above, create the next step
Find the user corresponding to this step, find the associated model, request the appropriate LLM

When requesting the LLM, provide the response information from the previous step

## 7. Continue this process until there is no next state
