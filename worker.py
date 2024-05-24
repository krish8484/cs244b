import signal
import sys
import uuid
from scheduler_client import SchedulerClient
from worker_client import WorkerClient
from Data.future import Future
from Data.task import Task
from Data.WorkerInfo import WorkerInfo
from logging_provider import logging
import threading
from random import randrange
import grpc
import json
import time
from operations import Operations
import constants
from exceptions import WorkerUnableToExecuteTaskError


class Worker:
    def __init__(
            self,
            scheduler_host,
            scheduler_port,
            worker_host,
            worker_port,
            add_delay,
            max_thread_count,
            gpu_enabled):
        self.scheduler_host = scheduler_host
        self.scheduler_port = scheduler_port
        self.worker_host = worker_host
        self.worker_port = worker_port
        self.scheduler_client = SchedulerClient(self.scheduler_host, self.scheduler_port)
        self.add_delay = add_delay
        self.max_thread_count = max_thread_count
        self.gpu_enabled = gpu_enabled

        self.add_random_delay()
        workerInfo = WorkerInfo(
            self.worker_host,
            self.worker_port,
            self.max_thread_count,
            self.gpu_enabled)
        
        try:
            self.worker_id = self.scheduler_client.RegisterWorker(workerInfo)
            logging.info(f"Registered worker - WorkerId assigned from scheduler is {self.worker_id}")
        except grpc.RpcError as rpc_error:
            if rpc_error.code() == grpc.StatusCode.CANCELLED:
                logging.error(f"RegisterWorker: RPC Cancelled. RPC Error: code={rpc_error.code()} message={rpc_error.details()}")
            elif rpc_error.code() == grpc.StatusCode.UNAVAILABLE:
                logging.error(f"RegisterWorker: Scheduler Unavailable. RPC Error: code={rpc_error.code()} message={rpc_error.details()}")
            else:
                logging.error(f"RegisterWorker: Unhandled RPC error: code={rpc_error.code()} message={rpc_error.details()}")

        # Datastore for storing task result in memory. CREATED FOR TESTING FLOW -> NEED TO CHANGE TO FILE BASED SYSTEM LATER (Swarnim's PR)
        self.dummyFileStore = {}
        self.operations = Operations(self)
        signal.signal(signal.SIGINT, self.sigterm_handler)

    def submit_task(self, task: Task) -> Future:
        self.add_random_delay()
        resultLocation = str(uuid.uuid4())
        self.dummyFileStore[resultLocation] = constants.NOTCOMPLETED
        future = Future(resultLocation=resultLocation, hostName=self.worker_host, port=self.worker_port)
        threading.Thread(target=self.execute_task, args=(task, future)).start()
        logging.info(f"submitted task {task} to worker {self.worker_id}")
        return future

    def execute_task(self, task: Task, future: Future):
        logging.info(f"executing task {task}")
        self.add_random_delay()
        function_name = task.taskDefintion
        if function_name in self.operations.operationsMapping:
            result = self.operations.operationsMapping[function_name](*task.taskData)
            self.dummyFileStore[future.resultLocation] = json.dumps(result).encode()
        else:
            logging.info("Unknown function:", function_name)

    def get_result(self, future: Future) -> bytes:
        self.add_random_delay()
        return self.dummyFileStore[future.resultLocation]

    def notify_task_completion(self, task):
        self.add_random_delay()
        pass

    def get_result_from_worker(self, future: Future) -> bytes:
        if (future.hostName == self.worker_host and future.port == self.worker_port):
            return self.get_result(future)
        workerClient = WorkerClient(future.hostName, future.port)
        while True:
            result = workerClient.GetResult(future=future)
            if result == constants.NOTCOMPLETED:
                time.sleep(constants.WAITTIMEFORPOLLINGRESULT)
                continue
            elif result == constants.ERROR:
                raise WorkerUnableToExecuteTaskError(future)
            else:
                return result

    def sigterm_handler(self, signum, frame):
        logging.info("Exiting gracefully.")
        sys.exit(0)

    def add_random_delay(self):
        if self.add_delay:
            if randrange(100) > 50:
                delayVal = randrange(10)
                logging.info(f"AddDelay is true - Adding delay of {delayVal} seconds.")
                time.sleep(delayVal)
            else:
                logging.info(f"AddDelay is true but not adding any delay.")
