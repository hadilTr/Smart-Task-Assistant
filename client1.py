from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
import asyncio
import os

load_dotenv()

# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful and friendly task management assistant. Your role is to help users manage their tasks efficiently and send notifications.

When the user asks to do something with their tasks, analyze their intent and call the appropriate function:
- add_task: When they want to create a new task or reminder
- list_tasks: When they want to see their tasks
- complete_task: When they want to mark a task as done (make sure you have the task ID)
- delete_task: When they want to remove a task
- summarize_tasks: When they want an overview or summary
- send_notification: When they want to send a notification or reminder

Be conversational and friendly. After executing a function, provide a natural response based on the results.
If you need more information (like a task ID or notification details), ask the user politely.

Keep your responses concise but helpful. Use emojis occasionally to make the interaction more engaging."""


class TaskAssistantAgent:
    """
    A LangGraph-based agent that manages tasks and notifications using MCP servers.
    """
    
    def __init__(self):
        self.client = None
        self.graph = None
        self.model = None
        
    async def setup(self):
        """Initialize the MCP client, tools, and LangGraph workflow."""
        
    
        api_key_groq = os.getenv("API_KEY_GROQ")
        if not api_key_groq:
            raise ValueError("API_KEY_GROQ not found in environment variables")
        
        self.model = init_chat_model(
            "llama-3.3-70b-versatile",
            model_provider="groq",
            api_key=api_key_groq,
            temperature=0
        )
        
        # Setup MCP client with both servers
        self.client = MultiServerMCPClient(
            {
                "Task management": {
                    "command": "python",
                    "args": ["server.py"],
                    "transport": "stdio",
                },
                "Notification": {
                    "command": "python",
                    "args": ["server_notif.py"],
                    "transport": "stdio",
                }
            }
        )
        
        tools = await self.client.get_tools()
        print(f"✅ Loaded {len(tools)} tools from MCP servers")
        
        model_with_tools = self.model.bind_tools(tools)
        
        # Create tool execution node
        tool_node = ToolNode(tools)
        
        # Define the conditional edge logic
        def should_continue(state: MessagesState):
            """Determine if we should continue to tools or end."""
            messages = state["messages"]
            last_message = messages[-1]
            
            # If the last message has tool calls, route to tools
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            return END
        
        # Define the model calling function
        async def call_model(state: MessagesState):
            """Call the language model with the current state."""
            messages = state["messages"]
            
            # Add system prompt if this is the first turn
            if not any(isinstance(msg, SystemMessage) for msg in messages):
                messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
            
            response = await model_with_tools.ainvoke(messages)
            return {"messages": [response]}
        
        # Build the graph
        builder = StateGraph(MessagesState)
        
        # Add nodes
        builder.add_node("call_model", call_model)
        builder.add_node("tools", tool_node)
        
        # Add edges
        builder.add_edge(START, "call_model")
        builder.add_conditional_edges("call_model", should_continue)
        builder.add_edge("tools", "call_model")
        
        # Compile the graph
        self.graph = builder.compile()
        
        print("✅ Agent setup complete!")
        
    async def run(self, user_input: str):
        """
        Process a user input through the agent.
        
        Args:
            user_input: The user's message
            
        Returns:
            The agent's response
        """
        if not self.graph:
            raise RuntimeError("Agent not initialized. Call setup() first.")
        
        # Stream the agent's response
        response_content = ""
        async for event in self.graph.astream(
            {"messages": [("user", user_input)]},
            stream_mode="values"
        ):
            # Get the last message
            last_message = event["messages"][-1]
            
            # If it's an AI message without tool calls, it's the final response
            if hasattr(last_message, 'content') and last_message.content:
                response_content = last_message.content
        
        return response_content
    
    async def run_interactive(self):
        """Run an interactive chat loop."""
        print("\n🤖 Task Assistant Agent")
        print("=" * 50)
        print("Type your requests (or 'quit' to exit)\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Get response from agent
                response = await self.run(user_input)
                print(f"\n🤖 Assistant: {response}\n")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.client:
            # Close MCP client connections if needed
            pass


async def main():
    """Main entry point for the application."""
    agent = TaskAssistantAgent()
    
    try:
        # Setup the agent
        await agent.setup()
        
        # Run interactive mode
        await agent.run_interactive()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await agent.cleanup()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())