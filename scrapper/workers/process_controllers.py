import subprocess
import asyncio


class CommandRunner:
    def __init__(self, cmd):
        self.cmd = cmd

    def run(self):
        process = subprocess.Popen(
            self.cmd, shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # wait for the process to terminate
        out, err = process.communicate()
        errcode = process.returncode

        return out, err, errcode


class TaskQueue:
    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def get_tasks(self):
        return self.tasks


class AsyncExecutor:
    def __init__(self, task_queue, max_concurrent_tasks):
        self.task_queue = task_queue
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.results = []

    async def execute(self):
        tasks = []
        for task in self.task_queue.get_tasks():
            tasks.append(self._wrap_task(task))
        await asyncio.gather(*tasks)
        return self.results

    async def _wrap_task(self, task):
        async with self.semaphore:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, task.run)
            self.results.append(result)
