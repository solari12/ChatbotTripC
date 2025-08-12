# TripC.AI Chatbot - LangGraph Workflow

## Workflow Diagram

```mermaid
graph TD
    validate_platform[validate_platform<br/>Validation]
    classify_intent[classify_intent<br/>Intent Classification]
    route_to_agent[route_to_agent<br/>Agent Routing]
    add_cta[add_cta<br/>CTA Enhancement]
    format_response[format_response<br/>Response Formatting]
    validate_platform --> classify_intent
    classify_intent --> route_to_agent
    route_to_agent --> add_cta
    add_cta --> format_response
    format_response --> END
    validate_platform -->|error| END
```

## Workflow Description

This LangGraph workflow processes chatbot requests through the following steps:

1. **Platform Validation** - Validates platform-device compatibility
2. **Intent Classification** - Classifies user intent (QnA, Service, Booking)
3. **Agent Routing** - Routes to appropriate AI agent
4. **CTA Enhancement** - Adds platform-specific call-to-action
5. **Response Formatting** - Formats final response

## Error Handling

- Platform validation errors terminate the workflow early
- Agent errors are caught and formatted as error responses
- All errors include retry suggestions for users

## Benefits of LangGraph

- **Visual Workflow**: Clear visualization of request processing
- **State Management**: Centralized state handling across nodes
- **Error Handling**: Graceful error handling with early termination
- **Extensibility**: Easy to add new nodes and modify flow
- **Debugging**: Better visibility into workflow execution
