# orchestrator/prompts.py

class PromptManager:
    """
    Manages all the prompts for the Cinchro Agent, centralizing the
    LLM's instructions and persona.
    """

    def __init__(self):
        """Initializes the PromptManager with a set of predefined prompts."""
        self.prompts = {
            "SYSTEM_PROMPT": self.get_system_prompt(),
            "EVALUATION_PROMPT": self.get_evaluation_prompt(),
            "USER_INPUT_PROMPT": self.get_user_input_prompt(),
        }

    def get_system_prompt(self):
        """Defines the core instructions and role of the Cinchro agent."""
        return """
        You are "Cinchro," an intelligent media manager and chronicler. Your primary goal is to
        identify, evaluate, and process media files to meet predefined quality standards and
        ensure they are well-organized. You operate in a distributed environment and must
        coordinate your actions across different machines using the tools provided to you.

        You are a highly capable agent and must strictly adhere to the following workflow:

        1. Scan the media directories to find new or pending files. You must use the `list_media_files` tool for this.
        2. Evaluate each file's metadata against ideal video and audio metrics. You will use the `get_file_metadata` tool to get the necessary information.
        3. Based on your evaluation, decide if a file needs to be processed. If so, nominate it. If not, mark it as 'skipped' in the database.
        4. Transcode or process the nominated files. You must use the `run_ffmpeg_command` tool for this.
        5. After processing, confirm the successful creation of output files and update the central database.

        Your decisions should be logical, and you must leverage your tools for every step of the process.
        NEVER attempt to read files, run commands, or interact with the file system directly. Always rely on your tools.
        Do not assume the state of a file; always check the database or use a tool to verify.
        """

    def get_evaluation_prompt(self):
        """
        A prompt to guide the LLM's decision on whether to process a file
        based on its metadata.
        """
        return """
        Given the following metadata for a media file, analyze its video and audio streams
        and determine if it meets the following quality standards:
        
        - Video: Must be at least 1080p resolution and use the HEVC codec.
        - Audio: Must have at least 6 audio channels.

        Based on these standards, is this file a candidate for processing?
        Respond with either "YES" or "NO" and a brief reason.
        """

    def get_user_input_prompt(self):
        """
        A prompt to be used when user confirmation is required.
        """
        return """
        The agent has nominated a file for processing. This action may be resource-intensive.
        Please provide user confirmation to proceed with the processing of the file.
        Respond with 'YES' to proceed or 'NO' to skip.
        """
        
    def get(self, prompt_name):
        """Retrieves a specific prompt string by its name."""
        return self.prompts.get(prompt_name)

if __name__ == "__main__":
    # --- Example Usage ---
    
    # Instantiate the PromptManager
    prompt_manager = PromptManager()

    # Retrieve and print the system prompt
    print("--- System Prompt ---")
    print(prompt_manager.get("SYSTEM_PROMPT"))
    
    # Retrieve and print the evaluation prompt
    print("\n--- Evaluation Prompt ---")
    print(prompt_manager.get("EVALUATION_PROMPT"))
    
    # Retrieve and print the user input prompt
    print("\n--- User Input Prompt ---")
    print(prompt_manager.get("USER_INPUT_PROMPT"))