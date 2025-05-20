# Book Reading Feature

The book reading feature allows an agent to process and learn from text content such as books, articles, or papers. This capability enhances the agent's knowledge base and enables it to reference and reflect on the read materials during conversations.

## Overview

When an agent reads a book:

1. The text is divided into manageable chunks
2. Each chunk is processed to extract knowledge
3. The agent creates a reflection for each chunk
4. A final reflection on the entire book is generated
5. A clear memory record is stored indicating the book has been read

All of these memories become part of the agent's knowledge base and can be retrieved during conversations or other interactions.

## Usage

### Basic Command

```bash
make read_book USERNAME=alice_007 BOOK_PATH="scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt"
```

### Required Parameters

- `USERNAME`: The username of the agent who will read the book
- `BOOK_PATH`: Path to the text file containing the book content

### Prerequisites

1. The user specified by USERNAME must exist in the system
2. The user must have an LLM model configured (the `llm_model` field)
3. The book file must be accessible at the specified path

## How It Works

### Step 1: Preparation

The system first checks if the user exists and has a valid LLM model configured. It then reads the book file and prepares it for processing.

### Step 2: Reading Record

A high-importance memory is created to record that the user has read this book. This ensures the agent can later recall having read the book when asked.

### Step 3: Content Processing

The book is divided into chunks (approximately 2000 characters each), and for each chunk:

1. The content is processed to extract knowledge
2. A memory is created with the extracted knowledge
3. A reflection is generated about this section of the book
4. Another memory is created with this reflection

### Step 4: Final Reflection

After processing all chunks, a final reflection on the entire book is generated and stored as a memory with high importance.

## Memory Types

The following memory types are created during book reading:

| Memory Type | Description | Importance |
|-------------|-------------|------------|
| `book_reading_record` | Records that the book was read | 0.95 |
| `book_knowledge` | Knowledge extracted from book content | 0.80 |
| `book_section_reflection` | Reflection on each section | 0.85 |
| `book_reflection` | Final reflection on the entire book | 0.90 |

Higher importance memories (closer to 1.0) are more likely to be retrieved during memory search operations.

## Use Cases

- Building a knowledge base for agents from educational materials
- Allowing agents to learn from specialized texts in domains like medicine, law, or science
- Creating agents with specific knowledge from literature or academic papers
- Enhancing an agent's ability to discuss and reference specific works

## Example Workflow

```bash
# Ensure database is migrated
make migrate

# Create a user (or use existing one)
# The user must have a valid LLM model configured

# Process a book to create memories
make read_book USERNAME=alice_007 BOOK_PATH="scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt"

# Chat with the user to see their knowledge of the book
make chat AGENT=alice_007
```

During the chat, you can ask questions like:
- "Have you read any books recently?"
- "What do you know about the psychology of emotions?"
- "Can you summarize the main points from the book you read?"

## Technical Implementation

The book reading functionality is implemented in:
- `src/reading/book_reader.py`: Core processing logic
- `commands/read_book.py`: Command-line interface
- `Makefile`: Simplified command access 