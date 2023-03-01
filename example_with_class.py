from task_manager import TaskManager


class MyClass:
    def __init__(self):
        self.task_manager = TaskManager()

        self.task_manager.register_task(self.method1, uses_output=False)
        self.task_manager.register_task(self.method2, uses_output=False)

    def _run(self):
        self.task_manager.run_tasks(["method1", "method2"])
        for t in self.task_manager.tasks.keys():
            task = self.task_manager.tasks[t]
            if task.has_run() and task.is_success():
                print(
                    task.get_output()
                )  # or print(self.task_manager.get_output_for(t))

    def run(self):
        try:
            self._run()
        except:
            # Possibly do something on error
            raise

    def method1(self):
        return "Hello 1"

    def method2(self):
        return "Hello 2"


mc = MyClass()

mc.run()
