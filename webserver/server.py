import os
from fastapi import FastAPI, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime
import json
import lg_db
import asyncio
from pydantic import BaseModel, Field
from contextvars import ContextVar

# Context to store current client_id during a request
current_client_id = ContextVar("client_id", default=None)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

ws_manager = ConnectionManager()

# Global list of queues for connected SSE clients
connections = []

class DeviceRegistration(BaseModel):
    client_id: str
    secret: str

class ChatInput(BaseModel):
    question: str
    client_id: str
    secret: str

class CalendarEventInput(BaseModel):
    title: str
    start_time: str = Field(description="ISO 8601 format: YYYY-MM-DDTHH:MM:SS")
    end_time: str = Field(description="ISO 8601 format: YYYY-MM-DDTHH:MM:SS")

class CalendarEventRemovalInput(BaseModel):
    title: str = Field(description="Title of the event to remove")

class ObjectiveInput(BaseModel):
    title: str
    description: str = ""
    client_id: str
    secret: str

class TaskInput(BaseModel):
    title: str
    objective_id: int
    weight: int = 1
    client_id: str
    secret: str

class RemoveItemInput(BaseModel):
    id: int
    client_id: str
    secret: str

load_dotenv()

@tool
def get_server_time():
     """Get the current server time. ALWAYS call this tool first before scheduling any events to ensure you are using the correct reference date (Year 2026)."""
     current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
     return f"The current server time is {current_time}."


@tool
def my_server_function():
    """Execute a simple local test function."""
    print("   [Server] Executing local python code...")
    return "SUCCESS: The local code ran!"

@tool("add_calendar_event", args_schema=CalendarEventInput)
def add_calendar_event(title: str, start_time: str, end_time: str):
    """Add an event to the calendar. Use strict ISO format."""
    
    client_id = current_client_id.get()
    
    # 1. Save to DB
    lg_db.add_calendar_event(client_id, title, start_time, end_time)
    
    # 2. Push to frontend via SSE (Best effort sync-to-async bridge)
    # Since this runs in a thread, we need to schedule the update on the main loop
    payload = {
        "command": "add_event",
        "parameters": [title, start_time, end_time]
    }
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop:
        for q in connections:
             loop.call_soon_threadsafe(q.put_nowait, payload)
    
    return f"Event '{title}' scheduled for {start_time}"

@tool("get_calendar_events", args_schema=None)
def get_calendar_events_tool():
    """Retrieve all calendar events for the current client. Use this to find event titles before removing them."""
    client_id = current_client_id.get()
    events = lg_db.get_all_events(client_id)
    return json.dumps(events)

@tool("remove_calendar_event", args_schema=CalendarEventRemovalInput)
def remove_calendar_event(title: str):
    """Remove an event from the calendar by title."""
    
    client_id = current_client_id.get()
    
    # 1. Remove from DB
    lg_db.remove_calendar_event(client_id, title)
    
    # 2. Push to frontend via SSE (Best effort sync-to-async bridge)
    payload = {
        "command": "remove_event",
        "parameters": [title]
    }
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop:
        for q in connections:
             loop.call_soon_threadsafe(q.put_nowait, payload)
    
    return f"Event '{title}' removed from calendar."

# --- Objective & Task Tools ---

@tool
def get_objectives_tool():
    """Get all objectives and their tasks for the current user. Returns a list of dictionaries.
    Use this to find IDs of objectives or tasks before adding/removing them."""
    client_id = current_client_id.get()
    if not client_id: return "Error: No client context."
    return json.dumps(lg_db.get_client_objectives(client_id))

class AddObjectiveSchema(BaseModel):
    title: str
    description: str = ""

@tool("add_objective", args_schema=AddObjectiveSchema)
def add_objective_tool(title: str, description: str = ""):
    """Create a new objective. Returns the result string."""
    client_id = current_client_id.get()
    if not client_id: return "Error: No client context."
    obj_id = lg_db.add_objective(client_id, title, description)
    return f"Objective '{title}' created with ID {obj_id}."

class AddTaskSchema(BaseModel):
    objective_id: int = Field(description="The ID of the objective to add this task to.")
    title: str = Field(description="The task content.")
    weight: int = Field(description="Importance weight of the task (default 1).", default=1)

@tool("add_task", args_schema=AddTaskSchema)
def add_task_tool(objective_id: int, title: str, weight: int = 1):
    """Add a task to a specific objective. Requires knowing the objective_id first."""
    client_id = current_client_id.get()
    if not client_id: return "Error: No client context."
    task_id = lg_db.add_task(objective_id, title, weight)
    return f"Task '{title}' (weight {weight}) added to objective {objective_id}."

class RemoveTaskSchema(BaseModel):
    task_id: int

@tool("remove_task", args_schema=RemoveTaskSchema)
def remove_task_tool(task_id: int):
    """Remove a task by ID."""
    client_id = current_client_id.get()
    if not client_id: return "Error: No client context."
    lg_db.remove_task(client_id, task_id)
    return f"Task {task_id} removed."

class RemoveObjectiveSchema(BaseModel):
    objective_id: int

@tool("remove_objective", args_schema=RemoveObjectiveSchema)
def remove_objective_tool(objective_id: int):
    """Remove an objective by ID. This also removes all tasks under it."""
    client_id = current_client_id.get()
    if not client_id: return "Error: No client context."
    lg_db.remove_objective(client_id, objective_id)
    return f"Objective {objective_id} removed."

class CompleteTaskSchema(BaseModel):
    task_id: int

@tool("complete_task", args_schema=CompleteTaskSchema)
def complete_task_tool(task_id: int):
    """Mark a task as completed. This updates the user's XP score."""
    client_id = current_client_id.get()
    if not client_id: return "Error: No client context."
    res = lg_db.complete_task(client_id, task_id)
    return f"Task {task_id} completed. Success: {res}"

class CompleteObjectiveSchema(BaseModel):
    objective_id: int

@tool("complete_objective", args_schema=CompleteObjectiveSchema)
def complete_objective_tool(objective_id: int):
    """Mark an entire objective as completed. This updates the user's completed objectives count."""
    client_id = current_client_id.get()
    if not client_id: return "Error: No client context."
    res = lg_db.complete_objective(client_id, objective_id)
    return f"Objective {objective_id} completed. Success: {res}"

@tool("get_user_stats", args_schema=None)
def get_user_stats_tool():
    """Retrieve the current user's gamification stats: XP score, task completion count, and objective completion count."""
    client_id = current_client_id.get()
    if not client_id: return "Error: No client context."
    stats = lg_db.get_client_stats(client_id)
    return json.dumps(stats)

class Assistant:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_base="https://api.deepseek.com",
            temperature=1.3,
        )

        # Updated Persona: Genie
        self.system_message = SystemMessage(
            content=(
                "You are 'Genie', a friendly and helpful Strategic AI Assistant.\n\n"
                
                "MISSION:\n"
                "Your purpose is to help the user achieve their goals. You guide, encourage, and provide structure. You function as a supportive partner for the user's life planning.\n\n"
                
                "CORE STRATEGY (THE 5 Ws):\n"
                "When analyzing objectives or tasks, you must process them through this tactical lens to help the user:\n"
                "1. **WHEN (Timing & Agenda)**: Don't just list tasks. Use `read_calendar` (via `get_calendar_events`) to find gaps. Proactively suggest: 'Your Tuesday morning is open; that is the optimal time for this work.' Pick the best date available.\n"
                "2. **WHERE (Environment)**: Suggest the optimal physical setting to achieve the objective. 'This task requires focus; try a quiet place.' vs 'This is routine; do it while commuting.'\n"
                "3. **WHO (Resources)**: Is this a solo effort or a team effort? Suggest looking for help if a task looks overwhelming.\n"
                "4. **WHAT (Critical Path)**: Identify the most important task. Which task blocks the others? Suggest subdivision if a task seems too heavy. 'This task is critical; dividing it into smaller chunks will make it manageable.'\n"
                "5. **WHY (Value)**: Explain the value. 'It is good to do this NOW because it helps you progress on your main goal.'\n\n"
                
                "PERSONALITY:\n"
                "1. **Supportive**: Do not scare. Influence positively. Use logic to show why action is better than inaction.\n"
                "2. **Organized**: Help structure the user's plans efficiently. Frame task completion as positive progress.\n"
                "3. **Friendly & Motivating**: Be polite, witty, giving praise where due. Mention the user's current XP or completion stats to motivate them.\n\n"
                
                "RULES OF ENGAGEMENT:\n"
                "1. **CRITICAL: Direct Orders = Immediate Action**: If the user specifically asks to ADD, REMOVE, MODIFY, or FINISH a task or objective, YOU MUST EXECUTE THE TOOL IMMEDIATELY. Do not ask for confirmation. Do not discuss it. Tool usage (e.g., `remove_task`, `complete_objective`) has PRIORITY over conversation.\n"
                "2. **Analyze Dependencies**: Check dependencies. If a user tries to skip a step, explain logically why the foundation must be built first.\n"
                "3. **Encouragement**: Instead of demanding, suggest kindly why completing a task is beneficial.\n"
                "4. **Scheduler**: Always try to ground abstract plans into concrete time slots using `add_calendar_event`. IMPORTANT: The current year is 2026. Always schedule events in the future relative to the current server time, which you should check first.\n"
                "5. **Missing Objectives**: If the user wants to schedule a task but it has no parent Objective, CREATE IT. Use `add_objective` to build the structure first, then schedule the tasks.\n"
                "6. **Modifications**: For vague ideas, ask confirmation. For specific commands, ACT IMMEDIATELY."
            )
        )

        # Add the calendar tool to the list
        self.tools = [
            my_server_function, get_server_time, 
            add_calendar_event, get_calendar_events_tool, remove_calendar_event,
            get_objectives_tool, add_objective_tool, remove_objective_tool,
            add_task_tool, remove_task_tool,
            complete_task_tool, complete_objective_tool,
            get_user_stats_tool
        ]

        # create_react_agent expects (model, tools, ...)
        self.agent = create_react_agent(self.llm, self.tools, prompt=self.system_message)
        self.config = {}

app = FastAPI()

@app.on_event("startup")
def on_startup():
    try:
        lg_db.init_db()
        print("Database initialized.")
    except Exception as e:
        print(f"DB init failed: {e}")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_index():
    return FileResponse("html/index.html")

@app.get("/chat")
def chat_page():
    return FileResponse("html/chat.html")
@app.get("/agenda")
def agenda_page():
    return FileResponse("html/agenda.html")

@app.get("/objectives")
def objectives_page():
    return FileResponse("html/objectives.html")

@app.get("/robots.txt")
def robots_txt():
    return FileResponse("static/robots.txt")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    print(f"WS Connected: {websocket.client}")
    try:
        while True:
            data = await websocket.receive_text()
            # Optional: handle incoming WS messages if you want to support WS-only chat
            # await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        print(f"WS Disconnected: {websocket.client}")
        ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WS Error: {e}")
        ws_manager.disconnect(websocket)

@app.get("/api/chat/history")
def get_history(client_id: str = Query(...), secret: str = Query(...)):
    if not lg_db.get_client(client_id, secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    
    history = lg_db.get_chat_history(client_id)
    return history

@app.post("/api/chat")
async def chat(input_data: ChatInput):
    print(f"DEBUG: Chat request: {input_data.question} from {input_data.client_id}")
    question = input_data.question
    client_id = input_data.client_id
    secret = input_data.secret
    
    # Verify client
    if not lg_db.get_client(client_id, secret):
         print("DEBUG: Client verification failed")
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    
    current_client_id.set(client_id)
    
    # Save User Context
    lg_db.add_chat_message(client_id, "user", question)
    
    # Fetch Context (History) to give the assistant memory
    # We fetch the last 20 messages to provide enough context
    history_records = lg_db.get_chat_history(client_id, limit=20)
    
    # Convert DB records to LangGraph message format
    # Note: The current question we just added is included in 'history_records'
    # because get_chat_history sorts by timestamp.
    messages_payload = []
    for record in history_records:
        # Map DB roles to LangChain roles just in case, though they match (user/assistant)
        role = record["role"]
        messages_payload.append({"role": role, "content": record["content"]})
    
    assistant = Assistant()
    try:
        # create_react_agent expects input like: {"messages": [{"role":"user","content": ...}]}
        # Run blocking agent in a thread to keep async loop responsive for WS
        # Increased recursion_limit to 100 to handle complex multi-step plans (e.g. creating multiple objectives/tasks)
        response = await asyncio.to_thread(
            assistant.agent.invoke, 
            {"messages": messages_payload},
            {"recursion_limit": 100}
        )
        print(f"DEBUG: Agent response: {response}")
        
        # Normalize different possible response shapes
        messages = None
        if isinstance(response, dict):
            messages = response.get("messages") or response.get("output") or response.get("outputs")
        if messages is None:
            final = str(response)
        else:
            last = messages[-1]
            if hasattr(last, "content"):
                final = last.content
            elif isinstance(last, dict) and "content" in last:
                final = last["content"]
            else:
                final = str(last)
        
        print(f"DEBUG: Final text: {final}")

        # Save Assistant Response
        lg_db.add_chat_message(client_id, "assistant", final)

        # Broadcast response to WebSockets
        print(f"DEBUG: Broadcasting to {len(ws_manager.active_connections)} clients")
        await ws_manager.broadcast(json.dumps({
            "type": "chat_response",
            "content": final
        }))

        return JSONResponse(content={"response": final})
    except Exception as e:
        print(f"ERROR: Chat exception: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/calendar/events")
def get_calendar_events(client_id: str = Query(...), secret: str = Query(...)):
    """Fetch all events from the database for FullCalendar"""
    if not lg_db.get_client(client_id, secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
         
    events = lg_db.get_all_events(client_id)
    return events


@app.get("/api/objectives")
def get_objectives(client_id: str = Query(...), secret: str = Query(...)):
    if not lg_db.get_client(client_id, secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    return lg_db.get_client_objectives(client_id)

@app.post("/api/objectives")
def add_objective(data: ObjectiveInput):
    if not lg_db.get_client(data.client_id, data.secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    
    obj_id = lg_db.add_objective(data.client_id, data.title, data.description)
    return {"id": obj_id, "status": "success"}

@app.delete("/api/objectives")
def delete_objective(data: RemoveItemInput):
    if not lg_db.get_client(data.client_id, data.secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    
    lg_db.remove_objective(data.client_id, data.id)
    return {"status": "success"}

@app.post("/api/objectives/complete")
def complete_objective_endpoint(data: RemoveItemInput): # Reusing RemoveItemInput (id, client_id, secret)
    if not lg_db.get_client(data.client_id, data.secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    
    success = lg_db.complete_objective(data.client_id, data.id)
    return {"status": "success" if success else "failed"}

@app.post("/api/tasks")
def add_task(data: TaskInput):
    if not lg_db.get_client(data.client_id, data.secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    
    # Optional: Verify objective belongs to client? (lg_db.add_task doesn't check owner of obj, 
    # but since objectives are scoped, it's somewhat safe provided ID is valid)
    task_id = lg_db.add_task(data.objective_id, data.title, data.weight)
    return {"id": task_id, "status": "success"}

@app.delete("/api/tasks")
def delete_task(data: RemoveItemInput):
    if not lg_db.get_client(data.client_id, data.secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    
    lg_db.remove_task(data.client_id, data.id)
    return {"status": "success"}

@app.post("/api/tasks/complete")
def complete_task_endpoint(data: RemoveItemInput): # Reusing RemoveItemInput (id, client_id, secret)
    if not lg_db.get_client(data.client_id, data.secret):
         return JSONResponse(content={"error": "Invalid client_id or secret"}, status_code=403)
    
    success = lg_db.complete_task(data.client_id, data.id)
    return {"status": "success" if success else "failed"}


@app.get("/api/hello_db")
def hello_db():
    raw = lg_db.lg_hello_db()  
    try:
        parsed = json.loads(raw)  
    except Exception:
        return JSONResponse(content={"message": raw})
    return JSONResponse(content={"message": parsed})

@app.post("/api/uuid_secret_count")
def uuid_secret_count(device: DeviceRegistration):
    count = lg_db.get_uuid_secret_count(device.client_id, device.secret)
    return {"count": count}

@app.post("/api/register_device")
def register_device_api(device: DeviceRegistration):
    """
    Register a client device (UUID+Secret).
    The client generates a UUID and a secret (e.g. random bytes), 
    and sends them here for initial pairing.
    """
    lg_db.register_device(device.client_id, device.secret)
    
    # Example: Notify all connected SSE clients about this event
    # Note: Since this function is synchronous, we'd use a thread-safe way in production,
    # or make this route 'async def'. For now, this is a conceptual example:
    # for q in connections:
    #     q.put_nowait({"event": "device_registered", "id": device.client_id})

    return {"status": "registered", "client_id": device.client_id}

# events SSE endpoint
@app.get("/sse")
async def calendar_events(request: Request):
    print("SSE endpoint called")
    
    # Create a queue for this specific client
    queue = asyncio.Queue()
    connections.append(queue)
    
    async def event_generator():
        try:
            while True:
                # Wait lazily for new data. This blocks without consuming CPU
                # until something calls queue.put()
                data = await queue.get()
                
                # If connection closes, the loop breaks via CancelledError
                yield f"data: {json.dumps(data)}\n\n"
        except asyncio.CancelledError:
            print("SSE client disconnected")
        finally:
            connections.remove(queue)

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.get("/api/trigger_sse")
async def trigger_test(text: str = "hello", parms: list[str] = Query(default=[])):
    """
    Trigger SSE event.
    Usage: /api/trigger_sse?text=hello&parms=arg1&parms=arg2
    """
    # parms is now a real list: ['arg1', 'arg2']
    message = {"command": text, "parameters": parms}
    
    for q in connections:
        await q.put(message)
    return {"status": "sent", "message": message, "receivers": len(connections)}
