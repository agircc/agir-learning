## user
learner defined in the yaml is actually a record in the user table

use usename in the yaml to find whether the user is existed, if not existed, create a new user

## processes
use process name and created_by to find process, if not existed, create a new record

created by is learner's id

## process_roles
used process id and name to map with the roles defined in the yaml

so do not create duplicated roles when execute python program second time

## process_nodes

use process id and name to map with the nodes defined in the yaml

so do not create duplicated nodes when execute python program second time

## process_transitions

use process id, from_node_id, to_node_id to map with the tranistions defined in the yaml

in the yaml, the from and to is node name, so need to use name find node id at first


