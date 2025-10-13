import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager
import sys
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

api_key_groq=os.getenv("API_KEY_GROQ")

if not api_key_groq:
    print("❌ Error: GROQ_API_KEY environment variable not set!")
    print("\nPlease set it using:")
    print("export GROQ_API_KEY='your-api-key-here'")
    sys.exit(1)

class TaskAssistantClient:
    """Client for interacting with the SmartTaskAssistant MCP server."""
    
    def __init__(self, server_script_path: str):
        self.server_script_path = "server.py"
        self.session = None
        
    @asynccontextmanager
    async def connect(self):
        """Context manager to establish connection with the MCP server."""
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script_path],
            env=None
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.session = session
                yield self
                
    async def call_tool(self, tool_name: str, arguments: dict):
        """Call any tool on the MCP server."""
        result = await self.session.call_tool(tool_name, arguments=arguments)
        return json.loads(result.content[0].text)


class TaskChatbot:
    """AI-powered chatbot using Groq to understand intent and call MCP tools."""
    
    def __init__(self, client: TaskAssistantClient):
        self.client = client
        self.groq_client = Groq(api_key=api_key_groq)
        self.conversation_history = []
        
        # Define available tools for Groq
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "add_task",
                    "description": "Add a new task with a title and optional due date. Use this when the user wants to create, add, or set a reminder for a task.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title or description of the task"
                            },
                            "due_date": {
                                "type": "string",
                                "description": "Optional due date for the task (can be in any format like '2025-10-15', 'tomorrow', 'next Monday', etc.)"
                            }
                        },
                        "required": ["title"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_tasks",
                    "description": "List all existing tasks. Use this when the user wants to see, view, or list their tasks.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "complete_task",
                    "description": "Mark a task as completed by its ID. Use this when the user wants to complete, finish, or mark a task as done.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "integer",
                                "description": "The ID of the task to mark as completed"
                            }
                        },
                        "required": ["task_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "summarize_tasks",
                    "description": "Get a summary of pending and completed tasks. Use this when the user wants an overview, summary, or status of their tasks.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
    "type": "function",
    "function": {
        "name": "tasks_by_date",
        "description": "List tasks for a specific date (supports natural language like 'tomorrow').",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date in YYYY-MM-DD format or natural language like 'tomorrow'"
                }
            },
            "required": ["date"]
        }
    }
}

        ]
        
        self.system_prompt = """You are a helpful and friendly task management assistant. Your role is to help users manage their tasks efficiently.

When the user asks to do something with their tasks, analyze their intent and call the appropriate function:
- add_task: When they want to create a new task or reminder
- list_tasks: When they want to see their tasks
- complete_task: When they want to mark a task as done (make sure you have the task ID)
- summarize_tasks: When they want an overview or summary

Be conversational and friendly. After executing a function, provide a natural response based on the results.
If you need more information (like a task ID), ask the user politely.

Keep your responses concise but helpful. Use emojis occasionally to make the interaction more engaging."""

    async def chat(self, user_message: str):
        """Process user message using Groq and execute appropriate tools."""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Get response from Groq
        messages = [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history
        
        response = self.groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # or "mixtral-8x7b-32768"
            messages=messages,
            tools=self.tools,
            tool_choice="auto",
            max_tokens=1000
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # If Groq wants to call a tool
        if tool_calls:
            # Add assistant's response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Call the MCP tool
                try:
                    tool_response = await self.client.call_tool(function_name, function_args)
                    tool_response_str = json.dumps(tool_response)
                except Exception as e:
                    tool_response_str = json.dumps({"error": str(e)})
                
                # Add tool response to history
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_response_str
                })
            
            # Get final response from Groq with tool results
            final_response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": self.system_prompt}
                ] + self.conversation_history,
                max_tokens=1000
            )
            
            final_message = final_response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": final_message
            })
            
            return final_message
        
        else:
            # No tool call needed, just return the response
            self.conversation_history.append({
                "role": "assistant",
                "content": response_message.content
            })
            return response_message.content
    
    def reset_conversation(self):
        """Reset the conversation history."""
        self.conversation_history = []


async def run_chatbot():
    """Run the AI-powered chatbot."""
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script.py>")
        print("\nMake sure to set your GROQ_API_KEY environment variable:")
        print("export GROQ_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    
    server_path = sys.argv[1]
    client = TaskAssistantClient(server_path)
    
    print("=" * 60)
    print("🤖 AI-Powered Smart Task Assistant (Using Groq)")
    print("=" * 60)
    print("Powered by Groq AI for intelligent task management")
    print("Type 'quit' to exit, 'reset' to clear conversation history\n")
    
    async with client.connect():
        chatbot = TaskChatbot(client)
        
        # Welcome message
        print("Bot: Hi! I'm your AI task assistant. I can help you manage your")
        print("     tasks using natural language. Just tell me what you need!\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["quit", "exit", "bye", "goodbye"]:
                    print("\nBot: Goodbye! Have a productive day! 👋\n")
                    break
                
                if user_input.lower() == "reset":
                    chatbot.reset_conversation()
                    print("\nBot: Conversation history cleared! Let's start fresh. 🔄\n")
                    continue
                
                # Get AI response
                print()
                response = await chatbot.chat(user_input)
                print(f"Bot: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\nBot: Goodbye! Have a productive day! 👋\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
                print("Please try again or type 'reset' to clear conversation history.\n")


if __name__ == "__main__":
    asyncio.run(run_chatbot())