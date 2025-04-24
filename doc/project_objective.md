Idea: Learning from Experience

There are some users existed in the database, these users are llm-powered users.

For example, some users are doctors, but doctors need treat real patients to acquire expertise.

The objective of this project is to use the process to train the learner (one user from database).

tables process, process_roles, process_nodes, process_transitions define the information of process

tables process_instances, process_instance_steps, process_role_users used to execute the process.

when execute the process, created a process instance, adn create or find a suitable user which is used process_role_users to map the user and process role to execute the process instance step
