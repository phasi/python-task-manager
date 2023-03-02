from task_manager import TaskManager

tm = TaskManager()


def task1_rollback():
    return "Rolling back task 1"


def task2_rollback():
    return "Rolling back task 2"


@tm.task(rollback=task1_rollback, uses_output=False, rollback_uses_output=False)
def task1():
    return "hello from task1"


@tm.task(rollback=task2_rollback, rollback_uses_output=False)
def task2(get_output_for):
    # Uncomment below line to test what happens when getting output from an unrun task
    # o = get_output_for("task3")
    return get_output_for("task1") + " hello from task 2"


@tm.task(uses_output=False)
def task3():
    # Uncomment below line to test rollback logic when failing task 3
    # raise Exception("This fails")
    return "hello from task 3"


try:
    tm.run_tasks(["task1", "task2", "task3"])

    print(tm.get_output_for("task2"))

    if tm.tasks["task3"].has_run():
        print(tm.get_output_for("task3"))
except:
    print("Could not run all tasks, aborting...")
    for t in tm._on_rollback:
        if tm.tasks[t].has_run():
            print(tm.get_output_for(t))
    # raise exception and crash program for demonstration purposes
    raise
