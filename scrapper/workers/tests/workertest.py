import unittest
import concurrent.futures
import queue
import subprocess
from time import sleep

def worker(task_queue, result_queue):
    while True:
        try:
            # get task from queue
            print_out = None
            task = task_queue.get()
            print(task)
            if task == 'None':  # Sentinel value to signal worker to stop
                print('here')
                break
            # run command with subprocess
            process = subprocess.Popen(task, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # print out from command in console (optional)
            for line in iter(process.stdout.readline, b''):
                print_out = line.decode().strip('\n')
                print(line.decode(), end='')

            # print error out from command (optional)
            for line in iter(process.stderr.readline, b''):
                print(line.decode(), end='')

            # add result to result queue
            process.communicate()
            result_queue.put((task, process.returncode, print_out))

        except queue.Empty:
            # if task queue is empty - wait for new tasks

            continue

        except Exception as e:
            # shutdown worker if error
            print(f"Worker encountered an error: {e}")
            break


class TestCommandRunner(unittest.TestCase):
    def test_add_and_get_tasks(self):
        task_amount = 21
        more_tasks = 3
        total = task_amount + more_tasks
        results = 0
        added = 0
        task_queue = queue.Queue()
        result_queue = queue.Queue()

        # create pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # create workers
            for _ in range(5):
                executor.submit(worker, task_queue, result_queue)
            for _ in range(task_amount):
                task_queue.put(["python3", "./test_task.py"])

            while results != task_amount:
                result = result_queue.get()
                if result:
                    with self.subTest("Check Additional Task Result"):
                        self.assertEqual(3, len(eval(result[2])))
                    results += 1
            with self.subTest("Check Task Count"):
                self.assertEqual(task_amount, results)
            while results != total:
                if added < more_tasks:
                    sleep(1)
                    task_queue.put(["python3", "./test_task.py"])
                    added += 1
                    result = result_queue.get()
                    if result:
                        with self.subTest("Check Additional Task Result"):
                            self.assertEqual(3, len(eval(result[2])))
                    results += 1
                else:
                    break
            with self.subTest("Check Additional Task Result"):
                self.assertEqual(total, results)
            for _ in range(5):
                task_queue.put('None')


if __name__ == '__main__':
    unittest.main()
