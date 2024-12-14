import os
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum

def time_to_str(dt: datetime):
    return dt.strftime(r"%Y-%m-%d %H:%M:%S")

def str_to_time(s: str):
    return datetime.strptime(s, r"%Y-%m-%d %H:%M:%S")

def convert_to_str(obj):
    if type(obj) == datetime:
        return time_to_str(obj)
    elif type(obj) == str:
        return obj
    else:
        raise ValueError(f"Unexpected type: {type(obj)}")


class Status(Enum):
    ACTIVE = "ACTIVE"
    DEFERRED = "DEFERRED"
    COMPLETED = "COMPLETED"

class Task:
    def __init__(self, title, notes=None, due_date=None, urgent=False, repeat_behavior=None, dependencies=None, 
                 completed=False, status=Status.ACTIVE, created_at=None, updated_at=None, id=None):
        self.id = id if id else str(uuid.uuid4())
        self.title = title
        self.notes = notes
        self.due_date = due_date
        self.completed = completed
        self.status = status
        self.urgent = urgent
        self.repeat_behavior = repeat_behavior  # e.g., {"interval": timedelta(days=7), "end_date": None}
        self.dependencies = dependencies if dependencies else []
        self.created_at = created_at if created_at else datetime.now()
        self.updated_at = updated_at if updated_at else datetime.now()

    def complete(self):
        if self.dependencies and not all(dep.completed for dep in self.dependencies):
            raise ValueError("Cannot complete task with incomplete dependencies.")
        self.completed = True
        self.status = Status.COMPLETED
        self.updated_at = datetime.now()

        # Handle repeat behavior
        if self.repeat_behavior:
            next_due_date = self.due_date + self.repeat_behavior["interval"] if self.due_date else None
            if not self.repeat_behavior.get("end_date") or next_due_date <= self.repeat_behavior["end_date"]:
                return Task(
                    title=self.title,
                    notes=self.notes,
                    due_date=next_due_date,
                    urgent=self.urgent,
                    repeat_behavior=self.repeat_behavior,
                    dependencies=[]  # Repeated tasks don’t inherit dependencies
                )
        return None

    def defer(self):
        if any(not dep.completed for dep in self.dependencies):
            self.status = Status.DEFERRED
        else:
            self.status = Status.ACTIVE
        self.updated_at = datetime.now()


    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "notes": self.notes,
            "due_date": convert_to_str(self.due_date) if self.due_date else None,
            "completed": self.completed,
            "status": self.status.value,
            "urgent": self.urgent,
            "repeat_behavior": self.repeat_behavior,
            "dependencies": [dep.id for dep in self.dependencies],
            "created_at": convert_to_str(self.created_at),
            "updated_at": convert_to_str(self.updated_at)
        }

    def __repr__(self):
        return (
            f"Task(id={self.id}, title='{self.title}', completed={self.completed}, status={self.status}, "
            f"due_date={self.due_date}, urgent={self.urgent})"
        )

class Project:
    def __init__(self, title, description=None, tasks=None,
                 id=None, completed=False, created_at=None, updated_at=None):
        self.id = id if id else str(uuid.uuid4())
        self.title = title
        self.description = description
        self.tasks = tasks if tasks else []
        self.completed = completed if completed else False
        self.created_at = created_at if created_at else datetime.now()
        self.updated_at = updated_at if updated_at else datetime.now()

    def add_task(self, task):
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def complete(self):
        if all(task.completed for task in self.tasks):
            print(f"Project '{self.title}' is complete!")
        else:
            raise ValueError("Cannot complete project with incomplete tasks.")
        
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "tasks": [task.id for task in self.tasks],
            "completed": self.completed,
            "created_at": convert_to_str(self.created_at),
            "updated_at": convert_to_str(self.updated_at)
        }

    def __repr__(self):
        return f"Project(id={self.id}, title='{self.title}', tasks={len(self.tasks)})"


class DataBase:
    def __init__(self):
        self.tasks = []
        self.projects = []
        # Create the default Inbox project
        self.inbox = Project(title="Inbox", description="Default project for unassigned tasks.")
        self.projects.append(self.inbox)

    def add_task(self, task, project_title=None):
        """
        Add a task to the database and optionally associate it with a project.
        
        If no project is specified, the task is added to the Inbox.
        """
        self.tasks.append(task)

        # Assign to the specified project or the Inbox if no project title is provided
        if project_title:
            project = self.find_project_by_title(project_title)
            if project:
                project.add_task(task)
            else:
                print(f"Warning: Project with title '{project_title}' does not exist. Task added to Inbox.")
                self.inbox.add_task(task)
        else:
            self.inbox.add_task(task)

    def add_project(self, project):
        if any(proj.title == project.title for proj in self.projects):
            raise ValueError(f"A project with the title '{project.title}' already exists. Please use a unique title.")
        self.projects.append(project)


    # Helper methods to find tasks and projects by ID or title

    def find_project_by_id(self, project_id):
        for project in self.projects:
            if str(project.id) == project_id:
                return project
        return None

    def find_project_by_title(self, title):
        for project in self.projects:
            if project.title == title:
                return project
        return None


    # Save and load database to/from disk

    def save(self, db_path='my_database'):
        os.makedirs(db_path, exist_ok=True)
        try:
            with open(os.path.join(db_path, 'tasks.json'), 'w') as f:
                json.dump([task.to_dict() for task in self.tasks], f, indent=4)

            with open(os.path.join(db_path, 'projects.json'), 'w') as f:
                json.dump([project.to_dict() for project in self.projects], f, indent=4)
        except IOError as e:
            print(f"Error saving database: {e}")

    def load(self, db_path='my_database'):
        try:
            with open(os.path.join(db_path, 'tasks.json'), 'r') as f:
                tasks = json.load(f)
                for task in tasks:
                    self.add_task(Task(**task))
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading tasks: {e}")

        try:
            with open(os.path.join(db_path, 'projects.json'), 'r') as f:
                projects = json.load(f)
                for project in projects:
                    self.add_project(Project(**project))
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading projects: {e}")

    def __repr__(self):
        return f"TaskManager(tasks={len(self.tasks)}, projects={len(self.projects)})"
