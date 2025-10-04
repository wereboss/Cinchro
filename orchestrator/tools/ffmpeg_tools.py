# orchestrator/tools/ffmpeg_tools.py

import json

class FFMPEGGTools:
    """
    A collection of tools for the Cinchro Agent to interact with the
    remote FFMPEG processing service on the Linux machine.
    """

    def __init__(self, api_base_url, use_dummy_data=False):
        """Initializes the tool client with the base URL of the remote API."""
        self.api_base_url = api_base_url
        self.use_dummy_data = use_dummy_data
        print(f"FFMPEGGTools initialized. Use dummy data: {self.use_dummy_data}")

    def run_ffmpeg_command(self, command: str, input_file: str, output_file: str) -> dict:
        """
        Tool: Executes an FFMPEG command on the remote machine.
        
        Args:
            command (str): The FFMPEG command to execute.
            input_file (str): The path of the input file.
            output_file (str): The desired path for the output file.
            
        Returns:
            dict: A dictionary containing the status of the job.
        """
        if self.use_dummy_data:
            print(f"Using dummy data for run_ffmpeg_command for file: {input_file}")
            # Simulating a successful job submission with dummy data
            job_id = "job_" + str(hash(input_file))
            return {
                "status": "Job Submitted",
                "job_id": job_id,
                "input_file": input_file,
                "output_file": output_file
            }
        
        else:
            print(f"Making real API call to {self.api_base_url}/run_ffmpeg with command: {command}")
            # In the future, this is where the real API call logic will go.
            return {}
        
if __name__ == '__main__':
    # Example usage with dummy data
    print("--- Testing with dummy data ---")
    tools = FFMPEGGTools(api_base_url="http://linux_machine_ip:5001", use_dummy_data=True)
    
    job_status = tools.run_ffmpeg_command(
        command="-c:v copy -c:a aac -b:a 192k",
        input_file="/media/movie_1080p_hevc.mkv",
        output_file="/output/movie_1080p_hevc.mp4"
    )
    print(f"Job status: {job_status}")
    
    # Example usage without dummy data (simulating real API)
    print("\n--- Testing with real API (no dummy data) ---")
    real_tools = FFMPEGGTools(api_base_url="http://linux_machine_ip:5001", use_dummy_data=False)
    real_tools.run_ffmpeg_command(
        command="-c:v copy -c:a aac -b:a 192k",
        input_file="/media/movie_1080p_hevc.mkv",
        output_file="/output/movie_1080p_hevc.mp4"
    )