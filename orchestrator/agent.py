# orchestrator/agent.py

import json
import os
import sys
from typing import TypedDict, Annotated, List, Dict
from datetime import datetime

# Add the parent directory to the path to import sibling modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Cinchro Modules
from orchestrator.config import ConfigManager
from orchestrator.database import DatabaseManager
from orchestrator.prompts import PromptManager
from orchestrator.tools.media_tools import MediaTools
from orchestrator.tools.ffmpeg_tools import FFMPEGGTools

# LangChain and LangGraph Modules
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.graph import CompiledGraph
from langgraph.checkpoint.base import BaseCheckpointSaver

from langchain_community.chat_models import ChatOllama
from langchain.agents import AgentExecutor, ToolCallingAgent
from langchain.agents.format_scratchpad import format_to_ollama_messages
from langchain.agents.output_parsers import ToolsAgentOutputParser

# --- LangGraph State Definition ---
class GraphState(TypedDict):
    """Represents the state of our graph."""
    files_to_scan: List[str]
    current_file: str
    metadata: dict
    status: str
    notes: str
    user_input: str
    output_files: List[str]

# --- Tool Wrappers for LangGraph ---
# We will wrap our tool classes with @tool decorator to make them callable by LangChain
# For a real application, you'd initialize these from the main entry point and pass them in.
# For this example, we'll instantiate them here for simplicity.

# Use a placeholder ConfigManager to get settings
config = ConfigManager(config_path=os.path.join(os.path.dirname(__file__), 'config.json'))
media_tools_instance = MediaTools(
    api_base_url=config.get("media_api_url"),
    use_dummy_data=config.get("use_dummy_tools")
)
ffmpeg_tools_instance = FFMPEGGTools(
    api_base_url=config.get("ffmpeg_api_url"),
    use_dummy_data=config.get("use_dummy_tools")
)

@tool
def list_media_files(location: str):
    """
    Tool to get a list of media files from a specified network location.
    The Cinchro agent must use this tool to discover files.
    """
    return media_tools_instance.list_media_files(location)

@tool
def get_file_metadata(file_path: str):
    """
    Tool to retrieve detailed metadata (e.g., resolution, codec, audio channels) for a file.
    The Cinchro agent must use this tool to evaluate a file's quality.
    """
    return media_tools_instance.get_file_metadata(file_path)

@tool
def run_ffmpeg_command(command: str, input_file: str, output_file: str):
    """
    Tool to execute a media processing command on the remote FFMPEG machine.
    The Cinchro agent must use this tool to transcode or process files.
    """
    return ffmpeg_tools_instance.run_ffmpeg_command(command, input_file, output_file)

tools = [list_media_files, get_file_metadata, run_ffmpeg_command]


class CinchroAgent:
    """
    The core orchestrator agent for Cinchro, built with LangGraph.
    It manages the entire media processing workflow.
    """

    def __init__(self):
        self.config_manager = config
        self.db_manager = DatabaseManager(self.config_manager.get("DATABASE_PATH"))
        self.prompt_manager = PromptManager()
        
        # Initialize LLM with tool use capabilities
        llm = ChatOllama(model=self.config_manager.get("LLM_MODEL")).bind_tools(tools)
        
        # Define agent to handle tool calls
        self.agent = ToolCallingAgent(
            llm=llm,
            tools=tools,
            prompt=self.prompt_manager.get("SYSTEM_PROMPT")
        )

        self.graph = self._define_graph()

    def _define_graph(self):
        """Defines the LangGraph state machine for the workflow."""
        workflow = StateGraph(GraphState)

        # --- Define Nodes ---
        workflow.add_node("scan_media_node", self.scan_media_node)
        workflow.add_node("evaluate_file_node", self.evaluate_file_node)
        workflow.add_node("decide_action_node", self.decide_action_node)
        workflow.add_node("process_file_node", self.process_file_node)
        workflow.add_node("update_db_node", self.update_db_node)

        # --- Define Edges ---
        workflow.set_entry_point("scan_media_node")

        # Scan -> Evaluate
        workflow.add_edge("scan_media_node", "evaluate_file_node")

        # Evaluate -> Decide
        workflow.add_edge("evaluate_file_node", "decide_action_node")
        
        # Conditional decision node
        workflow.add_conditional_edges(
            "decide_action_node",
            self.route_decision,
            {
                "process": "process_file_node",
                "skip": "update_db_node",
                "end": END,
            }
        )

        # Process -> Update DB
        workflow.add_edge("process_file_node", "update_db_node")
        
        # Update DB -> Evaluate (loop for next file)
        workflow.add_edge("update_db_node", "evaluate_file_node")
        
        # Finalize the graph
        return workflow.compile()
    
    # --- Graph Node Functions ---
    def scan_media_node(self, state: GraphState):
        """Node to list and add files to the database."""
        print("--- Node: scan_media_node ---")
        
        # Use the list_media_files tool via the agent
        agent_response = self.agent.invoke(HumanMessage(content="Scan the media directory for new files."))
        files_found = agent_response.get('tool_outputs', [])
        
        # Add files to the database and update state
        new_files = [f for f in files_found if self.db_manager.add_file(f)]
        state['files_to_scan'] = new_files
        
        print(f"Found {len(new_files)} new files to process.")
        return state

    def evaluate_file_node(self, state: GraphState):
        """Node to evaluate a file and decide if it needs processing."""
        print("--- Node: evaluate_file_node ---")

        files = state.get('files_to_scan', [])
        if not files:
            print("No files left to evaluate. Ending.")
            return {"status": "end"}

        current_file = files.pop(0)
        state['current_file'] = current_file
        state['files_to_scan'] = files
        
        # Use the get_file_metadata tool
        metadata = self.agent.invoke(HumanMessage(content=f"Get metadata for file {current_file}"))
        state['metadata'] = metadata.get('tool_outputs', [{}])[0]
        
        # Use LLM to decide based on metadata
        prompt = self.prompt_manager.get("EVALUATION_PROMPT") + f"\nMetadata: {json.dumps(state['metadata'])}"
        llm_decision = self.agent.invoke(HumanMessage(content=prompt))
        
        if "YES" in str(llm_decision).upper():
            print(f"File {current_file} nominated for processing.")
            state['status'] = "evaluation_passed"
        else:
            print(f"File {current_file} does not meet standards.")
            state['status'] = "evaluation_skipped"
            state['notes'] = "Does not meet quality standards."
        
        return state

    def decide_action_node(self, state: GraphState):
        """Node to route the workflow based on evaluation."""
        print("--- Node: decide_action_node ---")
        status = state.get('status')
        if status == "evaluation_passed":
            # For now, we will assume user input is always 'YES'
            # In a future version, this is where we'd ask for user confirmation.
            print("Decision: Process file.")
            return {"decision": "process"}
        
        elif status == "evaluation_skipped":
            print("Decision: Skip and update DB.")
            return {"decision": "skip"}
            
        return {"decision": "end"}

    def process_file_node(self, state: GraphState):
        """Node to call the FFMPEG tool for processing."""
        print("--- Node: process_file_node ---")
        
        file_to_process = state.get('current_file')
        metadata = state.get('metadata')
        
        # Example processing command
        output_file = file_to_process.replace(".mkv", ".mp4")
        command = f"-c:v copy -c:a aac -b:a 192k"
        
        # Use the run_ffmpeg_command tool
        job_status = self.agent.invoke(HumanMessage(content=f"Run ffmpeg command: {command} on {file_to_process} to output to {output_file}"))
        
        state['status'] = "processing"
        state['notes'] = f"Job submitted: {job_status}"
        
        # This is a simplification; in a real app, we'd poll for job completion
        state['output_files'] = [output_file]
        
        print(f"File {file_to_process} sent for processing.")
        return state

    def update_db_node(self, state: GraphState):
        """Node to update the database after a file is processed or skipped."""
        print("--- Node: update_db_node ---")
        
        self.db_manager.update_file_status(
            file_path=state.get('current_file'),
            status=state.get('status'),
            processing_path=state.get('current_file'),
            output_files=state.get('output_files'),
            notes=state.get('notes')
        )
        print(f"Database updated for {state.get('current_file')} with status: {state.get('status')}")
        
        return state

    # --- Router Function for Conditional Edges ---
    def route_decision(self, state: GraphState):
        """Routes the graph based on the decision node's output."""
        decision = state.get('decision')
        print(f"Routing based on decision: {decision}")
        return decision

    def run(self):
        """Runs the agent workflow."""
        initial_state = {
            "files_to_scan": [],
            "current_file": "",
            "metadata": {},
            "status": "",
            "notes": "",
            "user_input": "",
            "output_files": [],
        }
        
        for s in self.graph.stream(initial_state):
            print(s)
            
if __name__ == "__main__":
    # --- Example Usage ---
    # Create dummy config files for demonstration
    with open("config.json", "w") as f:
        json.dump({
            "LLM_MODEL": "llama3",
            "media_api_url": "http://media-tools:5000",
            "ffmpeg_api_url": "http://ffmpeg-tools:5001",
            "use_dummy_tools": True
        }, f)
    with open(".env", "w") as f:
        f.write("DATABASE_PATH=./cinchro.db\n")
    
    # Instantiate and run the agent
    print("Initializing Cinchro Agent...")
    agent = CinchroAgent()
    print("Starting agent workflow...")
    agent.run()
    
    # Clean up dummy files
    os.remove("config.json")
    os.remove(".env")
    os.remove("cinchro.db")