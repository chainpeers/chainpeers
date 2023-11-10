import unittest
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


class TestTaskQueue(unittest.TestCase):
    def test_add_and_get_tasks(self):
        queue = TaskQueue()
        queue.add_task("task1")
        queue.add_task("task2")
        self.assertEqual(queue.get_tasks(), ["task1", "task2"])


class TestCommandRunner(unittest.TestCase):
    def test_run(self):
        runner = CommandRunner("echo Hello")
        out, err, errcode = runner.run()
        self.assertEqual(out.strip().decode(), "Hello")
        self.assertEqual(err.decode(), "")
        self.assertEqual(errcode, 0)


class TestAsyncExecutor(unittest.IsolatedAsyncioTestCase):
    async def test_execute(self):
        queue = TaskQueue()
        queue.add_task(CommandRunner("echo Hello"))
        queue.add_task(CommandRunner("echo World"))
        executor = AsyncExecutor(queue, 2)
        results = await executor.execute()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0].strip().decode(), "Hello")
        self.assertEqual(results[0][1].decode(), "")
        self.assertEqual(results[0][2], 0)
        self.assertEqual(results[1][0].strip().decode(), "World")
        self.assertEqual(results[1][1].decode(), "")
        self.assertEqual(results[1][2], 0)


if __name__ == '__main__':
    unittest.main()
