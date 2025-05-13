## user
learner defined in the yaml is actually a record in the user table

use username in the yaml to find whether the user exists, if not existed, create a new user

## scenarios
use scenario name and created_by to find scenario, if not existed, create a new record

created by is learner's id

## agent_roles
use scenario id and name to map with the roles defined in the yaml

so do not create duplicated roles when execute python program second time

## states

use scenario id and name to map with the states defined in the yaml

so do not create duplicated states when execute python program second time

## state_transitions

use scenario id, from_state_id, to_state_id to map with the transitions defined in the yaml

in the yaml, the from and to is state name, so need to use name to find state id first


