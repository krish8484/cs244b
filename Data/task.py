from Data.future import Future
import api_pb2

class Task:
    # self.taskData is a list of future or/and bytes
    def __init__(self, taskId, taskDefintion, taskData):
        self.taskId : str = taskId
        self.taskDefintion : str = taskDefintion
        if len(taskData)!=0 and not isinstance(taskData[0], api_pb2.TaskDataParam):
            self.taskData = taskData
        # Converts list of api_pb2.TaskDataParam to list of future and/or bytes
        else:
            self.taskData = []
            for i in taskData:
                if i.WhichOneof("dataParam") == "future":
                    self.taskData.append(Future(i.future.resultLocation, i.future.hostName, i.future.port))
                else:
                    self.taskData.append(i.data)

    # Converts the current Task object to a protobuf Task message (api_pb2.Task)
    def to_proto(self) -> api_pb2.Task:
        task = api_pb2.Task(taskId = self.taskId, taskDefinition = self.taskDefintion)
        for i in self.taskData:
            if isinstance(i, list):
                for f in i:
                    if isinstance(f, Future):
                        task.taskData.append(api_pb2.TaskDataParam(
                            future=api_pb2.Future(
                                resultLocation=f.resultLocation,
                                hostName=f.hostName,
                                port=f.port
                            )
                        ))
            elif isinstance(i, Future):
                task.taskData.append(api_pb2.TaskDataParam(future = api_pb2.Future(resultLocation = i.resultLocation, hostName = i.hostName, port = i.port)))
            else:
                task.taskData.append(api_pb2.TaskDataParam(data = i))
        return task

    def __str__(self):
        return "[Task ID: {} || Task Definition: {}]".format(self.taskId, self.taskDefintion)
