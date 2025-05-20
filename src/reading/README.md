# Book Reading Module

This module provides functionality to read books and create user memories based on the content.

## Usage

Takes a username (e.g., alice_007) and a book's local path (e.g., /scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt).

The system will:
1. Read the book
2. Process the content in manageable chunks
3. Use the LLM model specified in the user's profile to reflect on the content
4. Create user memories associated with the user's ID (found by username)

## Running via Makefile

```bash
# Replace with actual username and book path
make read_book USERNAME=alice_007 BOOK_PATH="scenarios/books/THE PSYCHOLOGY OF THE EMOTIONS.txt"
```

## Implementation Details

The system:
- Divides the book into manageable chunks
- Processes each chunk to extract knowledge using the LLM model
- Creates memories for each chunk
- Generates a final reflection on the entire book
- All memories are associated with the user's ID and can be retrieved through the normal memory retrieval mechanisms