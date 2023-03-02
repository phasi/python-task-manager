"""
Library for safe and easy execution of functions
"""  # pylint: disable=too-many-lines
import typing


class Task:
    """
    Task object containing function and its output
    """

    def __init__(
        self,
        action: typing.Optional[typing.Callable],
        rollback: typing.Optional[typing.Callable] = None,
        uses_output=True,
        rollback_uses_output=True,
    ):
        self._action = action
        self._success = None
        self._has_run = False
        self._output = None
        self.rollback = rollback
        self._uses_output = uses_output
        self._rollback_uses_output = rollback_uses_output
        self._input = None

    @classmethod
    def make_backup(cls, task):
        """
        makes a clone/backup of tasks
        """
        backup_task = cls(action=task.action)
        backup_task._success = task.is_success()
        backup_task._has_run = task.has_run()
        backup_task._output = task.get_output()
        backup_task.rollback = task.rollback
        backup_task._uses_output = task.uses_output()
        backup_task._rollback_uses_output = task.rollback_uses_output()
        backup_task._input = task.get_input()
        return backup_task

    @property
    def action(self):
        return self._action

    # Flush methods should be used if task manager is a global instance
    # to avoid two subsequent operations from accessing the same instance's
    # data in computer's memory

    def _flush_output(self):
        """
        flushes outputs
        """
        self._output = None

    def _flush_status(self):
        """
        flushes statuses
        """
        self._success = None
        self._has_run = False

    def flush(self):
        """flushes outputs and statuses"""
        self._flush_output()
        self._flush_status()

    def run(self, **kwargs):
        """
                runs task and save the output
                Args:
                    get_output_for: Callable - a method to access other tasks' outputs
                    rollback:       Callable - a function to be registered as a rollback task for this task
        "
                Returns:
                    N/A

                Raises:
                    Re-raises the original exception"
        """
        try:
            # save keyword arguments (input)
            self._input = kwargs
            # run task function/action and save output
            self._output = self._action(**kwargs)
            self._success = True
            self._has_run = True
        except:
            self._success = False
            self._has_run = True
            raise

    def get_output(self) -> typing.Any:
        """
        returns task's output
        """
        return self._output

    def has_run(self):
        """
        check if this task has been executed
        """
        return self._has_run

    def is_success(self):
        """
        check if the execution of this task was successful
        """
        return self._success

    def uses_output(self):
        """
        check if this task needs to access outputs from other tasks.
        defaults to True.
        """
        return self._uses_output

    def rollback_uses_output(self):
        """
        check if rollback needs access to outputs from other tasks.
        Defaults to True.
        """
        return self._rollback_uses_output

    def get_input(self):
        """
        Returns input as dictionary (what was sent as input to the task)
        """
        return self._input


class TaskFailedError(Exception):
    """
    this exception should be raised when
    executed task was a failure
    """


class OutputNotAvailableError(Exception):
    """
    this exception should be raised when
    task output is not available because
    the task has not run.
    """


class TaskManager:
    """
    A safe way to manage, execute and revert/rollback
    functions (tasks).

    Upon failures TaskManager has the ability to rollback
    all tasks to the point before the operations started,
    you just need to defined a rollback action.

    Usage example:

    # global task manager
    tm = TaskManager()

    @tm.task()
    def example1():
        return "foo"

    # Run task and print output
    tm.run_tasks(["example1"])
    print(tm.get_output_for("example1"))

    # lets flush tasks because our TaskManager() is a global instance
    # after flushing we can start over with all the task outputs cleared
    tm.flush_tasks()
    """

    def __init__(self):
        # Task store for registered tasks
        self.tasks: typing.Dict[str, Task] = {}
        # Store for rollback actions in case we need to use them
        self._on_rollback: typing.List[str] = []

    def _register(self, task_name: str, task: Task):
        self.tasks[task_name] = task

    def flush_tasks(self):
        """
        flush_tasks should be used if task manager is a global instance
        to avoid two subsequent operations from accessing the same instance's
        data in computer's memory.

        Example:

        tm = TaskManager()
        ...running tasks...and then...
        tm.flush_tasks()
        """
        for task in self.tasks.items():
            task.flush()

    def register_task(self, function: typing.Callable, **kwargs):
        """
        Method to register tasks.

        Arguments:
        function: typing.Callable[] - function to be used as a task
        **kwargs - keyword arguments to be passed to the Task() on __init__()
        """
        self._register(
            task_name=function.__name__, task=Task(action=function, **kwargs)
        )

    def task(self, **kwargs):
        """
        This method is like register_task() but it is used
        only when using decorators. It receives a function
        and registers it as a task.

        Usage example:

        task_manager = TaskManager()

        # Decorator to register task with TaskManager
        @task_manager.task(**kwargs)
        def my_task(get_output_for, **kwargs):
            print("Task executed")

        """

        def wrapper(func):
            self.register_task(function=func, **kwargs)
            return func

        return wrapper

    def _get_output_for(self, task_name: str) -> typing.Any:
        """
        Returns output from the selected task.

        Arguments:
            task_name: str - Name/Identifier of the task

        Returns:
            typing.Any (Output can be anything)

        Raises:
            Re-raises the original exception
            KeyError when task cannot be find in registered tasks
        """
        try:
            selected = self.tasks[task_name]
            if not selected.has_run():
                raise OutputNotAvailableError(
                    f"{task_name} has not run therefore its output is not available."
                )
            return selected.get_output()
        except KeyError as e:
            raise Exception(
                f"_get_output_for could not find '{task_name}' from registered tasks"
            ) from e

    def get_output_for(self, task_name: str) -> typing.Any:
        """
        public method for _get_output_for()
        """
        return self._get_output_for(task_name)

    def _register_rollback_task(
        self, function: typing.Callable, rollback_uses_output, **kwargs
    ):
        """
        Registers a rollback task.
        """
        self.register_task(function, uses_output=rollback_uses_output, **kwargs)
        # add unique (by name) rollback tasks only
        if not function.__name__ in self._on_rollback:
            self._on_rollback.insert(0, function.__name__)

    def _rollback_dependencies(self, **kwargs):
        """
        Rollback dependency tasks
        """
        self._run_tasks(self._on_rollback, **kwargs)

    def _run_tasks(self, tasks: typing.List[str], **kwargs):
        """
        Runs tasks and registers their rollback tasks.

        Arguments:
            tasks: Callable[str] - list of task names

        Returns:
            N/A

        Raises:
            Re-raises the original exception
            KeyError when task cannot be find in registered tasks
        """
        # current_task = None
        # Validate task names first
        for t in tasks:
            try:
                self.tasks[t]
            except KeyError as e:
                raise Exception(f"Unknown task '{t}'. Check registered tasks") from e
        # Run tasks
        for t in tasks:
            try:
                current_task = self.tasks[t]
                if current_task.has_run() and current_task.is_success():
                    continue
                if current_task.uses_output():
                    current_task.run(get_output_for=self._get_output_for, **kwargs)
                else:
                    current_task.run(**kwargs)
                if not current_task.is_success():
                    raise TaskFailedError(f"Task '{t}' has been tagged non successful")
                # Register rollback task only if current task was run succesfully
                # we dont need to rollback the current task because it failed
                if current_task.rollback:
                    self._register_rollback_task(
                        function=current_task.rollback,
                        rollback_uses_output=current_task._rollback_uses_output,
                    )
            except Exception as e:
                raise TaskFailedError(f"Task '{t}' failed") from e

    def run_tasks(self, tasks: typing.List[str], **kwargs):
        """
        Public method for running tasks. Read docs from _run_tasks
        for more information.
        """
        try:
            self._run_tasks(tasks, **kwargs)
        except Exception:
            self._rollback_dependencies(**kwargs)
            raise
