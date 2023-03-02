#!/usr/bin/env python3
import unittest

from task_manager import TaskManager


class TaskManagerTests(unittest.TestCase):
    """
    tests for task_manager.py
    """

    def test_initialize_task_manager(self):
        """
        test initialize taskmanager
        """
        task_manager = TaskManager()
