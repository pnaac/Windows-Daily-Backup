from abc import ABC, abstractmethod

class BaseHandler(ABC):
    @abstractmethod
    def execute(self, job_id, job_config, global_config, agent_id, **kwargs):
        """
        Executes the job.
        
        Args:
            job_id (str): The unique ID of the job.
            job_config (dict): The configuration for this specific job.
            global_config (dict): Global agent configuration.
            agent_id (str): The ID of the current agent.
            
        Returns:
            dict: Result dictionary containing 'status', 'detailed_message', and optionally 'data'.
        """
        pass
