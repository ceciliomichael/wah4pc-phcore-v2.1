# Ask Only Mode

## Agent Behavior Rule

When this command is active, the agent MUST operate in **ASK ONLY MODE** with the following strict restrictions:

### PROHIBITED ACTIONS
- **NO FILE CREATION**: Agent cannot create any new files
- **NO FILE MODIFICATION**: Agent cannot edit, update, or modify existing files
- **NO CODE IMPLEMENTATION**: Agent cannot write or implement any code
- **NO SYSTEM CHANGES**: Agent cannot make any changes to the project structure
- **NO TOOL EXECUTION**: Agent cannot use tools that modify the codebase or system state

### ALLOWED ACTIONS
- **ANSWER QUESTIONS**: Provide detailed explanations and answers
- **CODE ANALYSIS**: Analyze and explain existing code (read-only)
- **GUIDANCE**: Offer advice, suggestions, and best practices
- **DOCUMENTATION**: Explain concepts, patterns, and methodologies
- **INFORMATION RETRIEVAL**: Search and read files for informational purposes only

### RESPONSE FORMAT
The agent should:
1. Provide comprehensive answers to questions
2. Include code examples only for illustration (not implementation)
3. Suggest approaches and solutions without implementing them
4. Offer step-by-step guidance for manual implementation
5. Clearly state when implementation would be needed but cannot be performed

This mode ensures the agent acts purely as an informational assistant without making any changes to the codebase or project.