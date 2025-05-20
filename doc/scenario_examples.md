# Example Scenarios

This document provides an overview of the example scenarios included in AGIR Learning, explaining their purpose, structure, and how they can be used as templates for creating your own scenarios.

## Introduction to Example Scenarios

The example scenarios serve several purposes:

1. Demonstrate the capabilities of the AGIR Learning system
2. Provide templates for creating your own scenarios
3. Illustrate best practices for scenario design
4. Help test the system during development

Each example scenario focuses on a different learning domain to showcase the system's versatility.

## Hello World Scenario

**File:** `scenarios/hello.yml`

This is the simplest scenario, designed to introduce the basic concepts of AGIR Learning.

```yaml
scenario:
  name: "Hello World"
  description: "A simple introduction to AGIR Learning"

  learner:
    username: "new_learner"
    first_name: "New"
    last_name: "Learner"
    model: "gpt-4"
    evolution_objective: "Learn the basics of AGIR Learning interaction"

  roles:
    - name: "guide"
      model: "gpt-4"
      description: "Guide that explains how AGIR Learning works"

  states:
    - name: "introduction"
      role: "guide"
      description: "Guide introduces AGIR Learning"
    - name: "question"
      role: "learner"
      description: "Learner asks a question about AGIR"
    - name: "answer"
      role: "guide"
      description: "Guide answers the learner's question"
    - name: "reflection"
      role: "learner"
      description: "Learner reflects on what they've learned"

  transitions:
    - from: "introduction"
      to: "question"
    - from: "question"
      to: "answer"
    - from: "answer"
      to: "reflection"

  evolution:
    method: "Simple Reflection"
    description: "Basic understanding of the system through guided interaction"
    knowledge_sources:
      - "System documentation"
```

**Key Learning Points:**
- Basic scenario structure
- Simple linear flow of states
- Two-role interaction pattern

**How to Run:**
```bash
make learning SCENARIO=scenarios/hello.yml
```

## Medical Diagnosis Training

**File:** `scenarios/medical_diagnosis.yml`

This scenario simulates a medical diagnosis training environment where a medical student practices diagnosing patients with the assistance of a nurse.

```yaml
scenario:
  name: "Medical Diagnosis Training"
  description: "Training for medical students in diagnosing patient conditions"

  learner:
    username: "med_student"
    first_name: "Medical"
    last_name: "Student"
    model: "gpt-4"
    evolution_objective: "Improve diagnostic skills and communication with patients"

  roles:
    - name: "patient"
      model: "gpt-4"
      description: "Patient with various symptoms seeking diagnosis"
    - name: "nurse"
      model: "gpt-3.5-turbo"
      description: "Assists with patient information and preliminary assessment"

  states:
    - name: "patient_intake"
      role: "nurse"
      description: "Nurse collects initial patient information"
    - name: "chart_review"
      role: "learner"
      description: "Medical student reviews patient chart and nurse notes"
    - name: "patient_interview"
      role: "learner"
      description: "Medical student interviews the patient"
    - name: "patient_response"
      role: "patient"
      description: "Patient responds to the medical student's questions"
    - name: "diagnosis_formulation"
      role: "learner"
      description: "Medical student formulates a diagnosis"
    - name: "diagnosis_presentation"
      role: "learner"
      description: "Medical student presents diagnosis to patient"
    - name: "patient_feedback"
      role: "patient"
      description: "Patient provides feedback on the diagnosis and experience"
    - name: "self_reflection"
      role: "learner"
      description: "Medical student reflects on the case and learning points"

  transitions:
    - from: "patient_intake"
      to: "chart_review"
    - from: "chart_review"
      to: "patient_interview"
    - from: "patient_interview"
      to: "patient_response"
    - from: "patient_response"
      to: "diagnosis_formulation"
    - from: "diagnosis_formulation"
      to: "diagnosis_presentation"
    - from: "diagnosis_presentation"
      to: "patient_feedback"
    - from: "patient_feedback"
      to: "self_reflection"

  evolution:
    method: "Clinical Reasoning"
    description: "Improving diagnostic accuracy through pattern recognition and feedback"
    knowledge_sources:
      - "Medical textbooks"
      - "Clinical guidelines"
      - "Patient feedback"
      - "Self-reflection"
```

**Key Learning Points:**
- Complex multi-role interaction
- Branching conversation patterns
- Domain-specific learning objectives
- Use of feedback for skill development

**How to Run:**
```bash
make learning SCENARIO=scenarios/medical_diagnosis.yml
```

## Programming Mentor

**File:** `scenarios/programming_mentor.yml`

This scenario creates a code review and mentoring environment where a learner receives guidance on their programming skills.

```yaml
scenario:
  name: "Programming Mentor"
  description: "Code review and programming mentorship"

  learner:
    username: "junior_dev"
    first_name: "Junior"
    last_name: "Developer"
    model: "gpt-4"
    evolution_objective: "Improve code quality, software design skills, and best practices"

  roles:
    - name: "senior_dev"
      model: "gpt-4"
      description: "Senior developer providing code review and mentorship"
    - name: "product_manager"
      model: "gpt-3.5-turbo"
      description: "Provides context on product requirements and user needs"

  states:
    - name: "task_briefing"
      role: "product_manager"
      description: "Product manager explains the task requirements"
    - name: "code_submission"
      role: "learner"
      description: "Junior developer submits code for review"
    - name: "initial_review"
      role: "senior_dev"
      description: "Senior developer provides initial code review"
    - name: "clarification_questions"
      role: "learner"
      description: "Junior developer asks questions about the feedback"
    - name: "detailed_explanation"
      role: "senior_dev"
      description: "Senior developer provides detailed explanations"
    - name: "code_revision"
      role: "learner"
      description: "Junior developer revises the code"
    - name: "final_review"
      role: "senior_dev"
      description: "Senior developer reviews the revised code"
    - name: "learning_summary"
      role: "learner"
      description: "Junior developer summarizes what they've learned"

  transitions:
    - from: "task_briefing"
      to: "code_submission"
    - from: "code_submission"
      to: "initial_review"
    - from: "initial_review"
      to: "clarification_questions"
    - from: "clarification_questions"
      to: "detailed_explanation"
    - from: "detailed_explanation"
      to: "code_revision"
    - from: "code_revision"
      to: "final_review"
    - from: "final_review"
      to: "learning_summary"

  evolution:
    method: "Iterative Feedback"
    description: "Improving code quality through expert review and iterative refinement"
    knowledge_sources:
      - "Code review best practices"
      - "Software design patterns"
      - "Language-specific guidelines"
      - "Mentor feedback"
```

**Key Learning Points:**
- Iterative learning process
- Multiple feedback cycles
- Domain-specific knowledge application
- Practical skill development

**How to Run:**
```bash
make learning SCENARIO=scenarios/programming_mentor.yml
```

## Creating Your Own Scenarios

You can use these example scenarios as templates for creating your own. Here's a general process:

1. **Identify learning objectives**: What skills should the learner develop?
2. **Define roles**: What perspectives are needed in the scenario?
3. **Create states**: What steps should the learner go through?
4. **Define transitions**: How will the learner progress through the states?
5. **Specify evolution methods**: How will the system help the learner improve?

For a detailed guide on creating scenarios, see [Creating Scenarios](create_scenario.md).

## Advanced Example: Non-Linear Scenario

For more complex learning experiences, scenarios can include conditional transitions. Here's a simplified example:

```yaml
# Branching points based on learner choices
transitions:
  - from: "patient_assessment"
    to: "order_tests"
    condition: "learner_choice == 'need_more_information'"
  - from: "patient_assessment"
    to: "make_diagnosis"
    condition: "learner_choice == 'sufficient_information'"
```

More advanced examples can be found in the `scenarios/advanced/` directory.

## Using Examples in Production

While these examples are primarily for demonstration and learning, they can be adapted for real-world use:

1. Customize the content to match your specific domain
2. Expand the states and transitions to cover more complex scenarios
3. Adjust the evolution methods to align with your learning objectives
4. Add domain-specific knowledge sources

## Contributing New Examples

We welcome contributions of new example scenarios! If you create a scenario that might be useful to others, please consider submitting it through a pull request. See our [Contributing Guide](contributing.md) for more details. 