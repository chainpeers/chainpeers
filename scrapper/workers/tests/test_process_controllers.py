import unittest
from ..process_controllers import TaskQueue, CommandRunner, AsyncExecutor


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
