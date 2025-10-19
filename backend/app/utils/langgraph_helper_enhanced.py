#!/usr/bin/env python3
"""
Enhanced LangGraph Helper with Advanced Agent Integration
Uses the new MrWhiteAgentManager for better memory and state management
"""

import os
from typing import Dict, List, Any, Optional, TypedDict, Annotated, Sequence
from datetime import datetime, timezone
import uuid

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState

from flask import current_app
from app.agents.agent_manager import get_agent_manager
from app.utils.cache import cached, performance_monitor


class LangGraphHelperState(TypedDict):
    """State for the LangGraph helper processing system"""
    messages: Annotated[Sequence[BaseMessage], "The conversation messages"]
    user_id: int
    user_email: str
    conversation_id: int
    thread_id: Optional[str]
    agent_type: Optional[str]
    memory_context: Optional[str]
    performance_data: Optional[Dict[str, Any]]


class EnhancedLangGraphProcessor:
    """Enhanced LangGraph processor with agent management"""
    
    def __init__(self):
        self.agent_manager = get_agent_manager()
        self.memory_saver = MemorySaver()
        self.conversation_threads = {}
        
    def create_enhanced_graph(self) -> StateGraph:
        """Create an enhanced graph with multi-agent support"""
        
        def route_to_agent(state: LangGraphHelperState) -> str:
            """Route to appropriate agent based on query analysis"""
            if not state.get("messages"):
                return "general_chat"
            
            # Get the latest user message
            latest_message = state["messages"][-1]
            if isinstance(latest_message, HumanMessage):
                query = latest_message.content
                
                # Use agent manager to determine best agent
                agent_type = self.agent_manager.determine_agent_type(query)
                return agent_type
            
            return "general_chat"
        
        def process_with_agent(state: LangGraphHelperState) -> LangGraphHelperState:
            """Process message with the selected agent"""
            try:
                # Extract conversation history
                conversation_history = []
                for msg in state["messages"][:-1]:  # Exclude current message
                    if isinstance(msg, HumanMessage):
                        conversation_history.append({"type": "user", "content": msg.content})
                    elif isinstance(msg, AIMessage):
                        conversation_history.append({"type": "ai", "content": msg.content})
                
                # Get current query
                current_query = state["messages"][-1].content
                
                # Process with agent manager
                result = self.agent_manager.process_message(
                    user_id=state["user_id"],
                    user_email=state["user_email"],
                    conversation_id=state["conversation_id"],
                    query=current_query,
                    conversation_history=conversation_history,
                    thread_id=state.get("thread_id")
                )
                
                if result["success"]:
                    # Add AI response to messages
                    new_messages = list(state["messages"]) + [AIMessage(content=result["response"])]
                    
                    return {
                        **state,
                        "messages": new_messages,
                        "thread_id": result["thread_id"],
                        "agent_type": result["agent_type"],
                        "performance_data": result.get("metadata", {})
                    }
                else:
                    # Handle error case
                    error_response = result["response"]
                    new_messages = list(state["messages"]) + [AIMessage(content=error_response)]
                    
                    return {
                        **state,
                        "messages": new_messages,
                        "agent_type": "error_handler",
                        "performance_data": {"error": result.get("error")}
                    }
                    
            except Exception as e:
                current_app.logger.error(f"Error in process_with_agent: {str(e)}")
                error_msg = f"I apologize, but I am unable to help with your request. Please try again."
                new_messages = list(state["messages"]) + [AIMessage(content=error_msg)]
                
                return {
                    **state,
                    "messages": new_messages,
                    "agent_type": "error_handler",
                    "performance_data": {"error": str(e)}
                }
        
        # Create the graph
        workflow = StateGraph(LangGraphHelperState)
        
        # Add the main processing node
        workflow.add_node("process_message", process_with_agent)
        
        # Set entry point and end
        workflow.set_entry_point("process_message")
        workflow.add_edge("process_message", END)
        
        return workflow.compile(checkpointer=self.memory_saver)
    
    @performance_monitor
    def process_enhanced_message(self, user_id: int, user_email: str, conversation_id: int,
                               query: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Process a message through the enhanced graph system"""
        try:
            # Create conversation thread ID
            thread_id = f"enhanced_{user_id}_{conversation_id}"
            
            # Convert conversation history to messages
            messages = []
            if conversation_history:
                for msg in conversation_history[-10:]:  # Keep last 10 messages
                    if msg['type'] == 'user':
                        messages.append(HumanMessage(content=msg['content']))
                    else:
                        messages.append(AIMessage(content=msg['content']))
            
            # Add current query
            messages.append(HumanMessage(content=query))
            
            # Create initial state
            initial_state = LangGraphHelperState(
                messages=messages,
                user_id=user_id,
                user_email=user_email,
                conversation_id=conversation_id,
                thread_id=thread_id
            )
            
            # Create and run the graph
            graph = self.create_enhanced_graph()
            
            # Run with thread configuration
            config = {"configurable": {"thread_id": thread_id}}
            final_state = graph.invoke(initial_state, config=config)
            
            # Extract the AI response
            ai_response = final_state["messages"][-1].content
            
            return {
                "success": True,
                "response": ai_response,
                "thread_id": final_state.get("thread_id"),
                "agent_type": final_state.get("agent_type", "unknown"),
                "performance_data": final_state.get("performance_data", {}),
                "memory_enabled": True
            }
            
        except Exception as e:
            current_app.logger.error(f"Error in process_enhanced_message: {str(e)}")
            return {
                "success": False,
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "error": str(e),
                "memory_enabled": False
            }
    
    def get_thread_status(self, thread_id: str) -> Dict[str, Any]:
        """Get status of a specific thread"""
        thread_memory = self.agent_manager.get_thread_memory(thread_id)
        
        if thread_memory:
            return {
                "exists": True,
                "user_id": thread_memory["user_id"],
                "conversation_id": thread_memory["conversation_id"],
                "created_at": thread_memory["created_at"].isoformat(),
                "has_memory": True,
                "session_data": thread_memory.get("session_data", {})
            }
        else:
            return {
                "exists": False,
                "has_memory": False
            }
    
    def cleanup_threads(self, max_age_hours: int = 24) -> int:
        """Clean up old threads"""
        return self.agent_manager.cleanup_old_threads(max_age_hours)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        agent_status = self.agent_manager.get_agent_status()
        
        return {
            "enhanced_processor": "operational",
            "memory_saver_enabled": True,
            "active_threads": len(self.conversation_threads),
            "agent_manager": agent_status,
            "langgraph_version": "0.4.8",
            "features": [
                "Multi-agent routing",
                "Conversation memory",
                "Thread management", 
                "Performance monitoring",
                "Specialized agents",
                "Error handling"
            ]
        }


# Global instance
enhanced_processor = None

def get_enhanced_processor() -> EnhancedLangGraphProcessor:
    """Get or create the global enhanced processor"""
    global enhanced_processor
    if enhanced_processor is None:
        enhanced_processor = EnhancedLangGraphProcessor()
    return enhanced_processor


@performance_monitor
def process_with_enhanced_graph(user_id: int, user_email: str, conversation_id: int,
                              query: str, conversation_history: List[Dict] = None) -> str:
    """
    Main function for processing messages with the enhanced graph system
    
    This is the primary interface for the chatbot route to use
    """
    try:
        # Import the conversation context manager
        from app.utils.conversation_context_manager import get_context_manager
        
        # Get the conversation context manager
        context_manager = get_context_manager()
        
        # Check if this is a document-related query using the context manager
        is_document_query = context_manager.is_document_query(
            user_id=user_id,
            conversation_id=conversation_id,
            query=query,
            conversation_history=conversation_history
        )
        
        # If the query is related to documents, use the agent with tools
        if is_document_query:
            current_app.logger.info(f"Document query detected by context manager: '{query}'")
            
            # Register this as a document query in the context manager
            context_manager.register_document_query(
                user_id=user_id,
                conversation_id=conversation_id,
                query=query
            )
            
            # Import the agent from the chatbot module
            from app.routes.chatbot import agent
            
            # Convert conversation history to LangChain message format
            messages = []
            if conversation_history:
                for msg in conversation_history[-5:]:  # Keep last 5 messages for context
                    if msg['type'] == 'user':
                        messages.append(HumanMessage(content=msg['content']))
                    else:
                        messages.append(AIMessage(content=msg['content']))
            
            # Set environment variable for tools to access
            os.environ["CURRENT_USER_ID"] = str(user_id)
            current_app.logger.info(f"Set CURRENT_USER_ID environment variable to {user_id}")
            
            # Run the agent with the query
            try:
                # For document queries, add a hint to encourage tool usage
                enhanced_query = query
                
                # Get document context to enhance the query
                document_context = context_manager.get_document_context(user_id, conversation_id)
                if document_context and document_context.get("document_names"):
                    doc_names = ", ".join(document_context.get("document_names", []))
                    enhanced_query = f"{query} (Please use the summarize_files tool to provide information from my documents: {doc_names})"
                    current_app.logger.info(f"Enhanced query with document context: {enhanced_query}")
                elif "summarize" in query.lower() or "summary" in query.lower():
                    enhanced_query = f"{query} (Please use the summarize_files tool to provide information from my documents)"
                    current_app.logger.info(f"Enhanced query with tool hint: {enhanced_query}")
                
                # Log the agent invocation
                current_app.logger.info(f"Invoking agent with tools for document query. User ID: {user_id}")
                
                # Invoke the agent
                agent_result = agent.invoke({"input": enhanced_query, "chat_history": messages})
                
                # Log the agent's actions
                if hasattr(agent_result, 'intermediate_steps') and agent_result.intermediate_steps:
                    for i, step in enumerate(agent_result.intermediate_steps):
                        if len(step) >= 2:
                            action = step[0]
                            tool_name = getattr(action, 'tool', 'unknown_tool')
                            tool_input = getattr(action, 'tool_input', 'unknown_input')
                            current_app.logger.info(f"Agent tool use - Step {i+1}: Tool={tool_name}, Input={tool_input}")
                
                current_app.logger.info(f"Agent response received for document query")
                
                # Process the agent's result
                if agent_result and hasattr(agent_result, 'output'):
                    current_app.logger.info(f"Returning agent output (attribute)")
                    return agent_result.output
                elif isinstance(agent_result, dict) and 'output' in agent_result:
                    current_app.logger.info(f"Returning agent output (dict)")
                    return agent_result['output']
                elif isinstance(agent_result, str):
                    current_app.logger.info(f"Returning agent output (string)")
                    return agent_result
                else:
                    # Fallback if agent result format is unexpected
                    current_app.logger.warning(f"Unexpected agent result format: {type(agent_result)}")
                    # Continue with normal processing
            except Exception as agent_error:
                current_app.logger.error(f"Error using agent with tools: {str(agent_error)}")
                import traceback
                current_app.logger.error(f"Agent error traceback: {traceback.format_exc()}")
                # Continue with normal processing as fallback
                current_app.logger.info("Falling back to normal processing after agent error")
        
        # Default processing using the enhanced graph system
        current_app.logger.info(f"Using default enhanced graph processing for query: '{query}'")
        processor = get_enhanced_processor()
        result = processor.process_enhanced_message(
            user_id=user_id,
            user_email=user_email,
            conversation_id=conversation_id,
            query=query,
            conversation_history=conversation_history
        )
        
        # If the processing was successful, update thread session data with document context
        if result["success"] and result.get("thread_id"):
            thread_id = result.get("thread_id")
            # Update thread session data with document context
            context_manager.update_thread_session_data(user_id, conversation_id, thread_id)
        
        if result["success"]:
            current_app.logger.info(f"Enhanced processing successful - Agent: {result.get('agent_type')}, Thread: {result.get('thread_id')}")
            return result["response"]
        else:
            current_app.logger.error(f"Enhanced processing failed: {result.get('error')}")
            return result["response"]
            
    except Exception as e:
        current_app.logger.error(f"Critical error in enhanced graph processing: {str(e)}")
        import traceback
        current_app.logger.error(f"Critical error traceback: {traceback.format_exc()}")
        return f"I apologize, but I encountered a critical error processing your request. Please try again."


def get_agent_system_status() -> Dict[str, Any]:
    """Get comprehensive status of the agent system"""
    try:
        processor = get_enhanced_processor()
        return processor.get_system_status()
    except Exception as e:
        return {
            "error": str(e),
            "status": "error"
        }


# Backward compatibility function
def process_with_graph(user_id, user_email, query, conversation_history=None):
    """Backward compatibility wrapper for the old function name"""
    return process_with_enhanced_graph(user_id, user_email, 1, query, conversation_history) 