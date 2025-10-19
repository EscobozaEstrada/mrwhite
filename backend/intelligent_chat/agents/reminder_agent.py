"""
Reminder Agent - Handles multi-turn reminder creation with state tracking.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, AIMessage

from .state import ReminderState
from .tools.reminder_tools import (
    extract_reminder_info,
    validate_reminder_datetime,
    create_reminder,
    get_user_dogs,
    search_existing_reminders
)

logger = logging.getLogger(__name__)


class ReminderAgent:
    """
    Agent for handling reminder creation through multi-turn conversations.
    Uses LangGraph for state management and tool orchestration.
    """
    
    def __init__(self):
        self.graph = self._build_graph()
        self.app = self.graph.compile()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine."""
        graph = StateGraph(ReminderState)
        
        # Add nodes
        graph.add_node("get_dogs", self._get_user_dogs)
        graph.add_node("extract_info", self._extract_information)
        graph.add_node("validate", self._validate_fields)
        graph.add_node("create", self._create_reminder)
        graph.add_node("respond", self._generate_response)
        
        # Define flow
        graph.add_edge(START, "get_dogs")
        graph.add_edge("get_dogs", "extract_info")
        
        graph.add_conditional_edges(
            "extract_info",
            self._check_completeness,
            {
                "validate": "validate",
                "ask_missing": "respond",
            }
        )
        
        graph.add_conditional_edges(
            "validate",
            self._check_validation,
            {
                "create": "create",
                "ask_fix": "respond",
            }
        )
        
        graph.add_edge("create", "respond")
        graph.add_edge("respond", END)
        
        return graph
    
    async def _get_user_dogs(self, state: ReminderState) -> Dict[str, Any]:
        """Fetch user's dogs."""
        try:
            dogs = await get_user_dogs.ainvoke({"user_id": state.user_id})
            return {"available_dogs": dogs}
        except Exception as e:
            logger.error(f"Failed to get user dogs: {e}")
            return {"available_dogs": []}
    
    async def _extract_information(self, state: ReminderState) -> Dict[str, Any]:
        """Extract reminder information from the latest message."""
        latest_message = state.messages[-1].content if state.messages else ""
        
        try:
            # Call extraction tool
            extracted = await extract_reminder_info.ainvoke({
                "message": latest_message,
                "user_id": state.user_id,
                "available_dogs": state.available_dogs
            })
            
            if "error" in extracted:
                logger.warning(f"Extraction error: {extracted['error']}")
                return {"missing_fields": ["title", "reminder_datetime"]}
            
            # Update state with extracted info
            updates = {}
            
            if extracted.get("title"):
                updates["title"] = extracted["title"]
            
            if extracted.get("description"):
                updates["description"] = extracted["description"]
            
            if extracted.get("reminder_datetime"):
                updates["reminder_datetime"] = extracted["reminder_datetime"]
            
            if extracted.get("reminder_type"):
                updates["reminder_type"] = extracted["reminder_type"]
            
            if extracted.get("recurrence"):
                updates["recurrence"] = extracted["recurrence"]
            
            # Handle dog selection
            if extracted.get("dog_name"):
                dog_name = extracted["dog_name"]
                
                if dog_name == "all":
                    updates["dog_name"] = "all"
                else:
                    # Find matching dog
                    matching_dog = next(
                        (dog for dog in state.available_dogs if dog["name"].lower() == dog_name.lower()),
                        None
                    )
                    if matching_dog:
                        updates["dog_profile_id"] = matching_dog["id"]
                        updates["dog_name"] = matching_dog["name"]
            
            # Determine missing fields (check merged state)
            missing = []
            
            # Merge current state with updates to check completeness
            merged_title = updates.get("title") if updates.get("title") is not None else state.title
            merged_datetime = updates.get("reminder_datetime") if updates.get("reminder_datetime") is not None else state.reminder_datetime
            merged_dog_id = updates.get("dog_profile_id") if updates.get("dog_profile_id") is not None else state.dog_profile_id
            merged_dog_name = updates.get("dog_name") if updates.get("dog_name") is not None else state.dog_name
            
            print(f"📋 CHECKING MISSING FIELDS:")
            print(f"  Current state: title={state.title}, datetime={state.reminder_datetime}, dog={state.dog_name}")
            print(f"  Updates: title={updates.get('title')}, datetime={updates.get('reminder_datetime')}, dog={updates.get('dog_name')}")
            print(f"  Merged: title={merged_title}, datetime={merged_datetime}, dog={merged_dog_name}")
            
            if not merged_title:
                missing.append("title")
            if not merged_datetime:
                missing.append("reminder_datetime")
            
            # If user has multiple dogs and no specific dog chosen, add to missing
            if len(state.available_dogs) > 1:
                if not merged_dog_id and merged_dog_name != "all":
                    missing.append("dog")
            
            print(f"  Missing fields: {missing}")
            
            updates["missing_fields"] = missing
            
            return updates
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            return {"missing_fields": ["title", "reminder_datetime"]}
    
    def _check_completeness(self, state: ReminderState) -> str:
        """Check if all required fields are present."""
        if not state.missing_fields:
            return "validate"
        return "ask_missing"
    
    async def _validate_fields(self, state: ReminderState) -> Dict[str, Any]:
        """Validate the extracted fields."""
        errors = []
        
        # Validate datetime
        if state.reminder_datetime:
            validation = await validate_reminder_datetime.ainvoke({"dt": state.reminder_datetime})
            if not validation.get("valid"):
                errors.append(validation.get("error", "Invalid datetime"))
        
        # Validate dog (if multiple dogs and no dog specified)
        if len(state.available_dogs) > 1 and not state.dog_profile_id and state.dog_name != "all":
            # This is OK - we'll ask for clarification in response
            pass
        
        return {
            "validation_errors": errors,
            "ready_to_create": len(errors) == 0
        }
    
    def _check_validation(self, state: ReminderState) -> str:
        """Check if validation passed."""
        if state.validation_errors:
            return "ask_fix"
        return "create"
    
    async def _create_reminder(self, state: ReminderState) -> Dict[str, Any]:
        """Create the reminder in database."""
        
        # Handle "all dogs" case
        if state.dog_name == "all":
            # Create reminder for each dog
            results = []
            failed_dogs = []
            
            for dog in state.available_dogs:
                print(f"🔄 Creating reminder for dog: {dog['name']} (ID: {dog['id']})")
                result = await create_reminder.ainvoke({
                    "user_id": state.user_id,
                    "title": f"{state.title} ({dog['name']})",
                    "description": state.description,
                    "reminder_datetime": state.reminder_datetime,
                    "reminder_type": state.reminder_type or "other",
                    "dog_profile_id": dog["id"],
                    "recurrence": state.recurrence or "once"
                })
                
                print(f"  Result: {result}")
                
                if result.get("success"):
                    results.append(result)
                else:
                    failed_dogs.append(dog['name'])
                    error_msg = result.get("error", "Unknown error")
                    print(f"  ❌ Failed for {dog['name']}: {error_msg}")
            
            if len(results) == len(state.available_dogs):
                # All succeeded
                return {
                    "reminder_created": True,
                    "reminder_id": results[0].get("reminder_id")
                }
            elif len(results) > 0:
                # Some succeeded
                return {
                    "reminder_created": True,
                    "reminder_id": results[0].get("reminder_id"),
                    "validation_errors": [f"⚠️ Reminder created for some dogs, but failed for: {', '.join(failed_dogs)}"]
                }
            else:
                # All failed
                return {
                    "validation_errors": [f"Failed to create reminders. Please check the details and try again."]
                }
        
        # Single dog or no dog specified
        result = await create_reminder.ainvoke({
            "user_id": state.user_id,
            "title": state.title,
            "description": state.description,
            "reminder_datetime": state.reminder_datetime,
            "reminder_type": state.reminder_type or "other",
            "dog_profile_id": state.dog_profile_id,
            "recurrence": state.recurrence or "once"
        })
        
        if result.get("success"):
            return {
                "reminder_created": True,
                "reminder_id": result.get("reminder_id")
            }
        else:
            return {
                "validation_errors": [result.get("error", "Failed to create reminder")]
            }
    
    async def _generate_response(self, state: ReminderState) -> Dict[str, Any]:
        """Generate appropriate response based on state."""
        
        # Success case
        if state.reminder_created:
            # Convert UTC datetime back to user's timezone for display
            import pytz
            from .tools.reminder_tools import get_user_timezone
            
            user_tz_str = await get_user_timezone(state.user_id)
            user_tz = pytz.timezone(user_tz_str)
            
            # reminder_datetime is stored as naive UTC, localize it and convert to user timezone
            utc_time = pytz.utc.localize(state.reminder_datetime)
            local_time = utc_time.astimezone(user_tz)
            
            time_str = local_time.strftime("%B %d at %I:%M %p")
            dog_str = f" for {state.dog_name}" if state.dog_name and state.dog_name != "all" else ""
            
            if state.dog_name == "all":
                dog_names = ", ".join([dog["name"] for dog in state.available_dogs])
                response = f"✅ **Reminder created successfully!**\n\n"
                response += f"📋 **What**: {state.title}\n"
                response += f"⏰ **When**: {time_str}\n"
                response += f"🐕 **Dogs**: {dog_names}\n\n"
                response += f"I'll notify you at the scheduled time for each dog!\n\n"
                response += f"📅 [View all your reminders](/reminders)"
            else:
                response = f"✅ **Reminder created successfully!**\n\n"
                response += f"📋 **What**: {state.title}\n"
                response += f"⏰ **When**: {time_str}\n"
                if state.dog_name:
                    response += f"🐕 **Dog**: {state.dog_name}\n"
                response += f"\nI'll notify you at the scheduled time!\n\n"
                response += f"📅 [View all your reminders](/reminders)"
            
            return {"messages": [AIMessage(content=response)]}
        
        # Validation errors
        if state.validation_errors:
            response = "I noticed some issues:\n\n"
            for error in state.validation_errors:
                response += f"❌ {error}\n"
            response += "\nPlease provide the correct information."
            
            return {"messages": [AIMessage(content=response)]}
        
        # Missing fields
        if state.missing_fields:
            response = "I'd be happy to set a reminder for you! "
            
            missing_readable = []
            if "title" in state.missing_fields:
                missing_readable.append("what you'd like to be reminded about")
            if "reminder_datetime" in state.missing_fields:
                missing_readable.append("when you'd like to be reminded")
            
            if len(missing_readable) == 2:
                response += f"I need to know {missing_readable[0]} and {missing_readable[1]}."
            elif len(missing_readable) == 1:
                response += f"I need to know {missing_readable[0]}."
            elif len(missing_readable) == 0:
                response = "Great! "
            
            # If dog is in missing fields OR multiple dogs and no dog specified
            if "dog" in state.missing_fields or (len(state.available_dogs) > 1 and not state.dog_profile_id and state.dog_name != "all"):
                response += f"\n\nWhich dog is this reminder for?\n"
                for dog in state.available_dogs:
                    response += f"• {dog['name']}\n"
                response += "• All dogs"
            
            return {"messages": [AIMessage(content=response)]}
        
        # Default
        return {"messages": [AIMessage(content="How can I help you with reminders?")]}
    
    async def process(
        self, 
        user_id: int,
        conversation_id: int,
        message: str,
        existing_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message through the reminder agent.
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            message: User's message
            existing_state: Previously saved state (if continuing conversation)
            
        Returns:
            Dictionary with 'response' (str) and 'state' (dict to save)
        """
        try:
            # Initialize or load state
            if existing_state:
                state = ReminderState(**existing_state)
                state.messages.append(HumanMessage(content=message))
            else:
                state = ReminderState(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    mode="reminders",
                    messages=[HumanMessage(content=message)]
                )
            
            # Run the graph
            result = await self.app.ainvoke(state)
            
            # Extract response
            if result.get("messages"):
                response_message = result["messages"][-1].content
            else:
                response_message = "I'm having trouble processing that. Could you try rephrasing?"
            
            # Prepare state to save (only if not complete)
            state_to_save = None
            if not result.get("reminder_created"):
                state_to_save = {
                    "user_id": result.get("user_id"),
                    "conversation_id": result.get("conversation_id"),
                    "mode": result.get("mode"),
                    "title": result.get("title"),
                    "description": result.get("description"),
                    "reminder_datetime": result.get("reminder_datetime").isoformat() if result.get("reminder_datetime") else None,
                    "reminder_type": result.get("reminder_type"),
                    "dog_profile_id": result.get("dog_profile_id"),
                    "dog_name": result.get("dog_name"),
                    "recurrence": result.get("recurrence"),
                    "missing_fields": result.get("missing_fields", []),
                    "available_dogs": result.get("available_dogs", [])
                }
            
            return {
                "response": response_message,
                "state": state_to_save,
                "completed": result.get("reminder_created", False)
            }
            
        except Exception as e:
            logger.error(f"Reminder agent processing failed: {e}", exc_info=True)
            return {
                "response": "I encountered an error while processing your reminder. Please try again.",
                "state": None,
                "completed": False
            }



