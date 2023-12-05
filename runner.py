import asyncio
import os
import time


class Runner:
    def __init__(
        self,
        config,
        logger,
    ):
        self.config = config
        self.logger = logger
        self.event_loop = asyncio.get_event_loop()

    def run(self):
        self._print_diagnostics()
        failure_times = []
        sleep_time = 10
        while True:
            try:
                asyncio.run(self._looper())
            except:
                self.logger.exception("Encountered exception. Restarting")
            failure_times.append(time.time())
            if len(failure_times) > 5 and (time.time() - failure_times[-5]) < (60 * 20):
                self.logger.error("Failed 5 times in 20 minutes: Aborting.")
                break
            self._cancel_tasks()
            self.logger.info(f"Sleeping for {sleep_time}")
            time.sleep(sleep_time)

    def _print_diagnostics(self):
        version_file = os.path.expanduser("~/VERSION.txt")
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                version = f.read()
            self.logger.info(f"Hoth version={version.strip()}")
        else:
            self.logger.info(f"Unable to determine hoth version information")
        self.logger.info(f"Config file: {self.config}")

    def _cancel_tasks(self):
        # TODO: Fairly sure this doesn't do anything since asyncio.run creates a new task each time
        #     self.event_loop is the loop for the first run, but every subsequent run will be different
        self.logger.warning("Killing all the tasks!")
        for task in asyncio.all_tasks(self.event_loop):
            task.cancel()

    async def _looper(self):
        raise NotImplementedError("Child class must implement _looper function!")
