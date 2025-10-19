# Intelligent Chat System - Complete Architecture Flow

## 🎯 High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Next.js)                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  User Interface                                                   │  │
│  │  - Chat Messages                                                  │  │
│  │  - Mode Toggles: [General] [Reminder] [Health] [Way of Dog]     │  │
│  │  - Dog Profile Sidebar                                            │  │
│  │  - Document Upload                                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                 │                                        │
│                                 ▼                                        │
│                    POST /api/v2/stream                                  │
│                    {                                                    │
│                      message: "user query",                             │
│                      active_mode: "health" | "reminders" | null,       │
│                      document_ids: [...]                                │
│                    }                                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKEND API (FastAPI)                                │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  api/routes/chat.py                                               │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  stream_message()                                           │  │  │
│  │  │  1. Authenticate user                                       │  │  │
│  │  │  2. Get/create conversation                                 │  │  │
│  │  │  3. Route to appropriate service ──────┐                    │  │  │
│  │  └────────────────────────────────────────┼────────────────────┘  │  │
│  │                                            │                       │  │
│  │  ┌─────────────────────────────────────────┼────────────────────┐  │  │
│  │  │  get_service_for_mode(active_mode)      │                    │  │  │
│  │  │  ┌──────────────────────────────────────┴──────────────────┐ │  │  │
│  │  │  │  if active_mode == "health":                             │ │  │  │
│  │  │  │      return health_service  ────────────────────┐        │ │  │  │
│  │  │  │  elif active_mode == "reminders":               │        │ │  │  │
│  │  │  │      return chat_service (has reminder_agent) ──┼───┐    │ │  │  │
│  │  │  │  else:  # General Mode                          │   │    │ │  │  │
│  │  │  │      return chat_service  ──────────────────────┼───┼─┐  │ │  │  │
│  │  │  └─────────────────────────────────────────────────┘   │ │  │ │  │  │
│  │  └────────────────────────────────────────────────────────┼─┼──┘ │  │  │
│  └───────────────────────────────────────────────────────────┼─┼────┘  │
└────────────────────────────────────────────────────────────┬──┼─┼───────┘
                                                             │  │ │
                    ┌────────────────────────────────────────┘  │ │
                    │                ┌──────────────────────────┘ │
                    │                │      ┌─────────────────────┘
                    ▼                ▼      ▼
┌───────────────────────────┬──────────────────────┬─────────────────────────┐
│   HealthChatService       │   ChatService        │   ChatService           │
│   (Health Mode)           │   (Reminder Mode)    │   (General Mode)        │
│                           │                      │                         │
│  Inherits from:           │  Original service    │  Original service       │
│  BaseChatService          │  with:               │  with:                  │
│                           │  - ReminderAgent     │  - General chat         │
│  Overrides:               │  - AgentStateService │  - Book access (low)    │
│  • _get_mode_name()       │                      │  - Mode enforcement     │
│    → "health"             │  Handles:            │                         │
│                           │  • Set reminders     │  Handles:               │
│  • _retrieve_memories()   │  • Stateful conv     │  • Dog care advice      │
│    → Prioritize vet       │  • Redirect to       │  • Training tips        │
│       reports (2.5x)      │    /reminders page   │  • Nutrition            │
│    → User docs (1.5x)     │                      │  • General questions    │
│    → Book health (1.3x)   │  Special Logic:      │                         │
│    → Skip for greetings   │  • Detect new vs     │  Special Logic:         │
│                           │    continuation      │  • Exclude vet reports  │
│  • _generate_system       │  • Save/clear state  │  • Redirect to modes    │
│    _prompt()              │  • Multi-turn flow   │  • Low book priority    │
│    → Professional tone    │                      │                         │
│    → Medical guidance     │                      │                         │
│    → Cite sources         │                      │                         │
│    → Compare reports      │                      │                         │
│                           │                      │                         │
│  Uses:                    │  Uses:               │  Uses:                  │
│  • Same DB                │  • Same DB           │  • Same DB              │
│  • Same Pinecone          │  • Same Pinecone     │  • Same Pinecone        │
│  • Same streaming         │  • Same streaming    │  • Same streaming       │
│  • Same document handling │  • Same doc handling │  • Same doc handling    │
└───────────┬───────────────┴──────────┬───────────┴─────────┬───────────────┘
            │                          │                     │
            └──────────────────────────┼─────────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     BaseChatService (Shared Base)                       │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Shared Methods (ALL modes use these):                           │  │
│  │                                                                   │  │
│  │  process_message()      ← Main entry point                       │  │
│  │  _build_context()       ← Fetch conversation history, dogs, prefs│  │
│  │  _store_message()       ← Save to DB + Pinecone                  │  │
│  │  _prepare_messages()    ← Format for AI with memory context      │  │
│  │  _format_memory_context() ← Format docs, images, book            │  │
│  │  _stream_and_store_response() ← Stream AI responses              │  │
│  │  _clean_roleplay_actions() ← Remove *smiles*, *chuckles*         │  │
│  │  _auto_format_markdown() ← Auto-format bullets                   │  │
│  │  _fetch_attached_documents() ← Get uploaded docs                 │  │
│  │  _calculate_credits()   ← Credit calculations                    │  │
│  │  _track_credit_usage()  ← Credit tracking                        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER (Shared by ALL modes)                   │
│  ┌───────────────────────────┬──────────────────────────────────────┐  │
│  │  PostgreSQL Database      │  Pinecone Vector Database            │  │
│  │  ┌─────────────────────┐  │  ┌────────────────────────────────┐ │  │
│  │  │ • conversations     │  │  │  Namespaces:                   │ │  │
│  │  │ • messages          │  │  │  ┌──────────────────────────┐  │ │  │
│  │  │ • ic_dog_profiles   │  │  │  │ intelligent-chat-        │  │ │  │
│  │  │ • ic_document_      │  │  │  │ conversations-dev        │  │ │  │
│  │  │   uploads           │  │  │  │ (All conversation        │  │ │  │
│  │  │ • user_preferences  │  │  │  │  memories)               │  │ │  │
│  │  │ • credit_usage      │  │  │  └──────────────────────────┘  │ │  │
│  │  └─────────────────────┘  │  │  ┌──────────────────────────┐  │ │  │
│  │                            │  │  │ user_248_docs            │  │ │  │
│  │  All modes write to        │  │  │ (User documents)         │  │ │  │
│  │  same tables               │  │  │ - Images                 │  │ │  │
│  │                            │  │  │ - PDFs                   │  │ │  │
│  │                            │  │  │ - Text files             │  │ │  │
│  │                            │  │  └──────────────────────────┘  │ │  │
│  │                            │  │  ┌──────────────────────────┐  │ │  │
│  │                            │  │  │ intelligent-chat-vet-    │  │ │  │
│  │                            │  │  │ reports-dev              │  │ │  │
│  │                            │  │  │ (Vet reports only)       │  │ │  │
│  │                            │  │  │ - Metadata: is_vet_      │  │ │  │
│  │                            │  │  │   report=True            │  │ │  │
│  │                            │  │  └──────────────────────────┘  │ │  │
│  │                            │  │  ┌──────────────────────────┐  │ │  │
│  │                            │  │  │ book-content-dev         │  │ │  │
│  │                            │  │  │ ("The Way of the Dog")   │  │ │  │
│  │                            │  │  │ - Chapters               │  │ │  │
│  │                            │  │  │ - Health sections        │  │ │  │
│  │                            │  │  └──────────────────────────┘  │ │  │
│  └───────────────────────────┴──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     MemoryService (Retrieval Logic)                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  retrieve_memories(query, user_id, active_mode, ...)             │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  Routes based on active_mode:                              │  │  │
│  │  │  ┌──────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  if active_mode == "health":                         │  │  │  │
│  │  │  │      _retrieve_health_memories()                     │  │  │  │
│  │  │  │      → Query vet reports (top_k=5)                   │  │  │  │
│  │  │  │      → Query user docs (top_k=5)                     │  │  │  │
│  │  │  │      → Query book health sections (top_k=5)          │  │  │  │
│  │  │  │      → Priority boost: vet=2.5x, docs=1.5x, book=1.3x│ │  │  │
│  │  │  │                                                       │  │  │  │
│  │  │  │  elif active_mode == "wayofdog":                     │  │  │  │
│  │  │  │      _retrieve_book_memories()                       │  │  │  │
│  │  │  │      → Query book comments namespace                 │  │  │  │
│  │  │  │                                                       │  │  │  │
│  │  │  │  elif active_mode == "reminders":                    │  │  │  │
│  │  │  │      _retrieve_reminder_context()                    │  │  │  │
│  │  │  │      → Query conversation namespace                  │  │  │  │
│  │  │  │                                                       │  │  │  │
│  │  │  │  else:  # General Mode                               │  │  │  │
│  │  │  │      _retrieve_general_memories()                    │  │  │  │
│  │  │  │      → Query conversations (top_k=3)                 │  │  │  │
│  │  │  │      → Query user docs (EXCLUDE vet reports!)        │  │  │  │
│  │  │  │      → Query book (low priority, 0.8x)               │  │  │  │
│  │  │  └──────────────────────────────────────────────────────┘  │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    StreamingService (AI Integration)                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  stream_chat_response(messages, system_prompt)                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  • Call Anthropic Claude (Bedrock)                         │  │  │
│  │  │  • System prompt (mode-specific)                           │  │  │
│  │  │  • Conversation history                                    │  │  │
│  │  │  • Retrieved context (docs, vet reports, book)            │  │  │
│  │  │  • Current message                                         │  │  │
│  │  │  • Stream response chunks (SSE format)                     │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Detailed Message Flow

### Example 1: Health Mode Query

```
1. USER (Frontend):
   ├─ Toggles Health Mode 🩺
   ├─ Types: "What should I do about Max's stiffness?"
   └─ Clicks Send

2. API Route (/api/v2/stream):
   ├─ Authenticates user (ID: 248)
   ├─ Gets conversation (ID: 123)
   ├─ Calls: get_service_for_mode("health")
   └─ Returns: health_service (HealthChatService instance)

3. HealthChatService.process_message():
   ├─ Stores user message in DB + Pinecone
   ├─ Calls: _retrieve_memories()
   │   ├─ Checks: Is greeting? NO (has "stiffness" keyword)
   │   ├─ Calls: memory.retrieve_memories(active_mode="health")
   │   │   ├─ Searches vet reports namespace → Found 1 report
   │   │   ├─ Searches user docs → Found 0
   │   │   └─ Searches book health sections → Found 3 chunks
   │   └─ Returns: [vet_report × 1, book_chunks × 3]
   ├─ Calls: _generate_system_prompt()
   │   └─ Returns: Professional health prompt with:
   │       ├─ "You are in Health Mode"
   │       ├─ "Always cite vet reports"
   │       ├─ "Use medical terminology"
   │       └─ Dog profile: Max (10 yo, Golden Retriever)
   ├─ Calls: _prepare_messages()
   │   └─ Formats context:
   │       ├─ "**🏥 VET REPORTS:**"
   │       ├─ "[📎 max_report_oct10.pdf](s3_url)"
   │       ├─ "Content excerpt: mild stiffness noted..."
   │       ├─ "**📖 EXPERT KNOWLEDGE from The Way of the Dog:**"
   │       └─ "Book excerpt: Joint supplements like glucosamine..."
   └─ Streams AI response:
       "Based on Max's vet report from October 10th noting mild stiffness,
        combined with The Way of the Dog's recommendations, I suggest:
        
        - 🦴 Glucosamine supplements (500mg daily for his weight)
        - 🏃‍♀️ Low-impact exercise (swimming is excellent)
        - 🩺 Monitor for worsening - consult vet if it increases
        
        [📎 Click to download: max_report_oct10.pdf](s3_url)"

4. Frontend:
   ├─ Receives SSE chunks
   ├─ Displays streaming response with markdown
   ├─ Renders download link as clickable button
   └─ Shows: "Based on Max's vet report..."
```

---

### Example 2: General Mode Query

```
1. USER (Frontend):
   ├─ No mode toggled (General Mode)
   ├─ Types: "What's the best food for puppies?"
   └─ Clicks Send

2. API Route:
   ├─ Calls: get_service_for_mode(None)
   └─ Returns: chat_service (ChatService instance)

3. ChatService.process_message():
   ├─ Checks: Is user trying to set reminder? NO
   ├─ Stores message in DB
   ├─ Calls: memory.retrieve_memories(active_mode=None)
   │   ├─ Searches conversations → Found 2
   │   ├─ Searches user docs (EXCLUDES vet reports) → Found 1
   │   └─ Searches book (low priority) → Found 2 chunks
   ├─ System prompt: General friendly tone
   └─ Streams response:
       "For puppies, you'll want high-quality food with:
        
        - 🍖 **High Protein**: At least 22-28% for growth
        - 🥩 **Quality Meat**: Real chicken, beef, or fish
        - 🧠 **DHA**: For brain development
        
        According to The Way of the Dog, puppy nutrition is crucial
        for their development. Look for AAFCO-approved puppy formulas!"

4. Note: NO vet reports in response (excluded from General Mode)
```

---

### Example 3: Reminder Mode Query

```
1. USER:
   ├─ Toggles Reminder Mode 🔔
   ├─ Types: "Set a reminder to give Max his heartworm pill"
   └─ Clicks Send

2. API Route:
   ├─ Calls: get_service_for_mode("reminders")
   └─ Returns: chat_service (has ReminderAgent)

3. ChatService.process_message():
   ├─ Detects: Reminder mode active
   ├─ Calls: _process_with_reminder_agent()
   │   ├─ ReminderAgent extracts info:
   │   │   ├─ Title: "Give Max heartworm pill"
   │   │   ├─ Dog: Max (detected from user's dogs)
   │   │   └─ When: MISSING
   │   └─ Agent asks: "When would you like this reminder?"
   └─ Streams: "I can set that reminder for you! When should I remind you?"

4. USER replies: "Every month on the 1st"

5. Agent:
   ├─ Updates state with recurrence: monthly
   ├─ Creates reminder in DB
   └─ Responds: "✅ Reminder set! I'll remind you monthly on the 1st"
```

---

## 📊 Data Flow Comparison

| Aspect | General Mode | Health Mode | Reminder Mode |
|--------|--------------|-------------|---------------|
| **Service** | ChatService | HealthChatService | ChatService |
| **Vet Reports** | ❌ Excluded | ✅ Highest Priority (2.5x) | N/A |
| **User Docs** | ✅ Standard | ✅ High Priority (1.5x) | N/A |
| **Book Content** | ✅ Low (0.8x) | ✅ Expert Reference (1.3x) | N/A |
| **Conversations** | ✅ Standard | ✅ Standard | ✅ For context |
| **Tone** | Friendly, casual | Professional, medical | Helpful, clarifying |
| **Citations** | Optional | ✅ Mandatory | N/A |
| **Special Logic** | Mode enforcement | Compare reports, greetings skip | Stateful multi-turn |

---

## 🎯 What Was Cleaned Up

### ❌ BEFORE (General ChatService had everything):
```python
# chat_service.py had 60+ lines of health instructions!
elif active_mode == "health":
    base_prompt += """
    HEALTH MODE ACTIVE - PROFESSIONAL VETERINARY CONSULTATION:
    You are now in Health Mode with access to...
    [60 lines of health-specific instructions]
    """
```

### ✅ AFTER (Separated & Clean):

**ChatService (General/Reminder):**
```python
# chat_service.py - CLEAN!
elif active_mode == "health":
    # Health Mode now handled by HealthChatService
    logger.warning("⚠️ Should be using HealthChatService!")
    base_prompt += "\n**Note:** Health mode handled by dedicated service."
```

**HealthChatService (Health Only):**
```python
# health_chat_service.py - ALL health logic here
async def _generate_system_prompt():
    base_prompt = self._get_base_prompt(username)
    base_prompt += """
    🩺 HEALTH MODE ACTIVE - PROFESSIONAL VETERINARY CONSULTATION:
    [All health-specific instructions - 60+ lines]
    """
```

---

## ✅ Benefits of This Architecture

1. **No More Prompt Confusion**
   - Health Mode: Only health instructions
   - General Mode: Only general instructions
   - No mixing, no conflicts

2. **Easy to Extend**
   - Add Way of Dog Mode: Create `WayOfDogChatService`
   - Add Training Mode: Create `TrainingChatService`
   - ~200 lines of code per new mode

3. **Shared Data Access**
   - All modes use same DB
   - All modes use same Pinecone
   - Just different retrieval priorities

4. **Independent Optimization**
   - Tune Health Mode without affecting General
   - Different prompts, different strategies
   - Easier debugging

5. **Better Performance**
   - Smaller, focused prompts
   - Targeted retrieval (only what's needed)
   - Less token usage

---

## 🚀 Future Expansion

To add **Way of Dog Mode**:

```python
# 1. Create wayofdog_chat_service.py (20 mins)
class WayOfDogChatService(BaseChatService):
    def _get_mode_name(self): return "wayofdog"
    def _retrieve_memories(self, ...): return book_memories
    def _generate_system_prompt(self, ...): return book_companion_prompt

# 2. Update routing (5 mins)
elif active_mode == "wayofdog":
    return wayofdog_service

# Done! 🎉
```

---

## 📝 Summary

✅ **Health Mode**: Dedicated service, professional tone, vet report priority  
✅ **General Mode**: Clean service, friendly tone, excludes vet reports  
✅ **Reminder Mode**: Existing agent, stateful conversations  
✅ **All modes**: Share data, formatting, streaming, credits  
✅ **Architecture**: Extensible, maintainable, debuggable

