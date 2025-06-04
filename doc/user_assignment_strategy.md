# User Assignment Strategy

This document describes the user assignment strategy feature that allows flexible configuration of how users are assigned to episodes in scenarios.

## Overview

The user assignment strategy feature provides two main modes:

1. **Single Assignment Mode** (default): Each user can only be assigned to one episode per scenario
2. **Multi Assignment Mode**: Users can be assigned to multiple episodes with intelligent load balancing

## Configuration Parameters

### Command Line Arguments

- `--allow-multi-assign`: Enable multi-assignment mode (default: false)
- `--start-assign-count`: Starting assignment count threshold for multi-assign mode (default: 1)

### Usage Examples

```bash
# Single assignment mode (default)
python scripts/run.py scenario.yml --episodes=5

# Multi assignment mode with default settings
python scripts/run.py scenario.yml --episodes=5 --allow-multi-assign

# Multi assignment mode with custom starting count
python scripts/run.py scenario.yml --episodes=10 --allow-multi-assign --start-assign-count=2

# Using Makefile
make learning SCENARIO=scenario.yml EPISODES=5
make learning SCENARIO=scenario.yml EPISODES=5 ALLOW_MULTI_ASSIGN=true
make learning_multi SCENARIO=scenario.yml EPISODES=10 START_ASSIGN_COUNT=3
```

## Single Assignment Mode

In single assignment mode (default behavior):

- Each user can only be assigned to one episode within a scenario
- The system first tries to reuse existing users from other scenarios
- If no suitable user exists, a new user is created
- This maintains the original behavior for backward compatibility

### Algorithm

1. Check if a user is already assigned to the current episode
2. If yes, return that user
3. If no, search for users assigned to this role in other scenarios
4. Select a user who hasn't been assigned to any episode in the current scenario
5. If no such user exists, create a new user

## Multi Assignment Mode

In multi assignment mode:

- Users can be assigned to multiple episodes
- The system implements intelligent load balancing
- Assignment counts are tracked globally across all roles
- When all users reach the current threshold, the threshold is incremented

### Algorithm

1. Check if a user is already assigned to the current episode
2. If yes, return that user
3. If no, get all users who have been assigned to this role
4. Select users with the least number of assignments
5. Check if all users have reached the current assignment threshold
6. If yes, increment the threshold for future assignments
7. Assign the selected user and track the assignment

### Load Balancing

The load balancing algorithm ensures fair distribution of work:

```
Example with 3 users and start_assign_count=1:

Episode 1: User A (1 assignment)
Episode 2: User B (1 assignment) 
Episode 3: User C (1 assignment)
Episode 4: User A (2 assignments) - threshold incremented to 2
Episode 5: User B (2 assignments)
Episode 6: User C (2 assignments)
Episode 7: User A (3 assignments) - threshold incremented to 3
...
```

## Implementation Details

### Global State Management

The system uses a global configuration and tracking system:

- `assignment_config.py`: Manages configuration and assignment tracking
- Thread-safe tracking of assignment counts per role and user
- Automatic threshold management

### Key Functions

- `set_assignment_config()`: Configure assignment strategy
- `track_user_assignment()`: Track when a user is assigned
- `get_least_assigned_users()`: Get users with minimum assignments
- `should_increment_assign_count()`: Check if threshold should be incremented

### Database Integration

- Counts are initialized from existing database records when starting
- Validation functions ensure tracking matches database state
- Assignment records are created in the `agent_assignments` table

## Performance Considerations

### Single Assignment Mode
- Fast database queries to find available users
- Minimal memory overhead
- Suitable for scenarios with many users

### Multi Assignment Mode
- In-memory tracking for fast assignment decisions
- O(n) complexity for user selection where n = number of users per role
- Suitable for scenarios requiring balanced workload distribution

## Use Cases

### Single Assignment Mode
- Traditional scenarios where each user represents a unique individual
- Large-scale scenarios with many episodes
- When user memory and context should be episode-specific

### Multi Assignment Mode
- Resource-constrained environments with limited users
- Scenarios testing user adaptation and learning
- Load testing with consistent user behavior patterns

## Configuration Best Practices

1. **Start Assignment Count**: Set to 1 for immediate load balancing, higher values for less frequent reassignment
2. **Episode Planning**: Consider the total number of episodes and desired distribution when choosing parameters
3. **Memory Management**: Multi-assignment mode accumulates user memories across episodes

## Monitoring and Debugging

### Assignment Statistics

```python
from src.evolution.assignment_config import get_assignment_stats

stats = get_assignment_stats()
print(f"Config: {stats['config']}")
print(f"Role assignments: {stats['role_assignments']}")
```

### Validation

```python
from src.evolution.assignment_config import validate_assignment_counts

# Validate tracking matches database
is_valid = validate_assignment_counts(db, scenario_id)
```

## Testing

Run the test script to see the assignment strategy in action:

```bash
python scripts/test_assignment_strategy.py
```

This script demonstrates:
- Single vs multi assignment mode differences
- Load balancing behavior
- Threshold increment mechanics
- Assignment distribution patterns

## Migration from Previous Versions

The new system is fully backward compatible:

- Existing scenarios work without changes
- Default behavior remains the same (single assignment)
- No database schema changes required
- Existing user assignments are respected

To enable multi-assignment for existing scenarios, simply add the `--allow-multi-assign` flag to your run commands. 