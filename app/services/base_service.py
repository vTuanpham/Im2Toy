import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
from ..core.prompt_manager import PromptManager


class BaseService(ABC):
    def __init__(
        self,
        config: Dict[str, Any],
        prompt_manager: PromptManager,
        prompt_type: str,
        max_concurrency: int = 1,
        max_total_tasks: int = 1,
        max_retries: int = 3,
    ):
        self.config = config
        self.prompt_manager = prompt_manager
        self.prompt_type = prompt_type

        self.max_concurrency = max_concurrency
        self.max_total_tasks = max_total_tasks
        self.max_retries = max_retries
        self.completed_tasks = 0
        self.semaphore = asyncio.Semaphore(max_concurrency)

        logging.log(
            logging.INFO, f"BaseService initialized with prompt type: {prompt_type}"
        )

    def _get_prompt_sequence(
        self,
        prompt_type: Union[str, None] = None,
        exclude_keys: Union[List[str], None, str] = None,
    ):
        """
        Retrieves a prompt sequence for the given prompt type, excluding specified keys.
        """

        logging.log(logging.INFO, f"Getting prompt sequence: {prompt_type}")

        if prompt_type:
            return self.prompt_manager.get_prompt_sequence(prompt_type, exclude_keys)
        return self.prompt_manager.get_prompt_sequence(self.prompt_type, exclude_keys)

    def _get_prompt_key(self, prompt_key: str, prompt_type: Union[str, None] = None):
        """
        Retrieves a specific prompt key for the given prompt type.
        """

        logging.log(logging.INFO, f"Getting prompt key: {prompt_key}")

        if prompt_type:
            return self.prompt_manager.get_prompt_key(prompt_type, prompt_key)
        return self.prompt_manager.get_prompt_key(self.prompt_type, prompt_key)

    @abstractmethod
    async def forward(self, *args, **kwargs):
        """
        Abstract method that each subclass must implement to process each task.
        """
        raise NotImplementedError("The forward method must be implemented.")

    @abstractmethod
    def process_results(self, results) -> Any:
        """
        Abstract method to define how to handle the results returned from each task.
        """
        raise NotImplementedError("The process_results method must be implemented.")

    async def __call__(self, *args, **kwargs) -> Any:
        """
        Runs tasks in parallel with a concurrency and retry mechanism.
        """

        logging.log(
            logging.INFO,
            f"Processing {self.max_total_tasks} tasks in {self.prompt_type}",
        )

        async def limited_task(*args, **kwargs):
            if (
                self.max_total_tasks is not None
                and self.completed_tasks >= self.max_total_tasks
            ):
                return None

            logging.log(
                logging.INFO, f"Processing task with args {args}, kwargs {kwargs}"
            )

            async with self.semaphore:
                for attempt in range(1, self.max_retries + 1):
                    try:
                        # Pass original arguments directly to `forward`
                        results = await self.forward(*args, **kwargs)
                        self.completed_tasks += 1
                        return results
                    except Exception as e:
                        logging.error(logging.ERROR, f"Error processing task: {e}")
                        if attempt == self.max_retries:
                            logging.error(
                                logging.ERROR,
                                f"Max retries reached for task with args {args}, kwargs {kwargs}",
                            )
                            return None
                        await asyncio.sleep(2 ** (attempt - 1))  # Exponential backoff

        # Run each task with the original arguments in parallel
        tasks = [limited_task(*args, **kwargs) for _ in range(self.max_total_tasks)]
        results = await asyncio.gather(*tasks)

        # Filter out any None results from tasks that failed all retries
        results = [result for result in results if result is not None]

        logging.log(logging.INFO, f"Completed {len(results)} tasks")

        self.completed_tasks = 0
        logging.log(
            logging.INFO, f"Setting completed tasks back to {self.completed_tasks}"
        )

        return self.process_results(results)
