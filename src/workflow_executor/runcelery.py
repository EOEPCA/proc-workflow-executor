# import worker
# argv = [
#     'worker',
#     '--loglevel=DEBUG',
# ]
# worker.celery.worker_main(argv)
import celery


##################
from celery import Celery
taskapp = Celery("tasks", broker='redis://localhost:6379/0', backend='redis://localhost')
@taskapp.task
def add(x, y):
    return x + y


#################
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    result = taskapp.task.add.delay(2, 2)
    return {"2+2": result.get()}

#################3

import uvicorn

original_callback = uvicorn.main.callback

def callback(**kwargs):
    from celery.contrib.testing.worker import start_worker
    with start_worker(taskapp, perform_ping_check=False, loglevel="info"):
        original_callback(**kwargs)

uvicorn.main.callback = callback


if __name__ == "__main__":
    uvicorn.main()