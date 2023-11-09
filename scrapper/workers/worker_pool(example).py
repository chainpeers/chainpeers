import concurrent.futures
import queue
import subprocess


def worker(task_queue, result_queue):
    while True:
        try:
            # get task from queue
            task = task_queue.get()
            print_out = None

            if task == 'None':  # Sentinel value to signal worker to stop

                break
            # run command with subprocess
            process = subprocess.Popen(task, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # print out from command in console (optional)
            for line in iter(process.stdout.readline, b''):
                print_out = line.decode()
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


# create queue for tasks
task_queue = queue.Queue()

# create queue for results
result_queue = queue.Queue()

# create pool
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    # create workers
    for _ in range(5):
        executor.submit(worker, task_queue, result_queue)

    # first peer lookup in queue
    task_queue.put("command <peer_address>")

    # adding tasks (good place to send requests to api with peers)
    while True:
        result = result_queue.get()
        if result:
            peer = result[2]
            # put_to_send(peer)
            task_queue.put(f"command {peer}")
