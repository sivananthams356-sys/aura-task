"""Business rules for tasks: assignment, progress, status transitions, review, history."""
from app.errors import ApiError
from app.extensions import db
from app.models import Project, Task, TaskHistory, User, utcnow

# (from_status, to_status) -> who may do it
TRANSITIONS = {
    ("Pending", "In Progress"): {"assignee", "manager", "admin"},
    ("In Progress", "Blocked"): {"assignee", "manager"},
    ("Blocked", "In Progress"): {"assignee", "manager"},
}
SUBMIT_MIN_PROGRESS = 90


def _roles(user, task):
    roles = set()
    if task.assignee_id == user.id:
        roles.add("assignee")
    if user.role == "manager" and task.manager_id == user.id:
        roles.add("manager")
    if user.role == "admin":
        roles.add("admin")
    return roles


def _forbid():
    return ApiError(403, "FORBIDDEN", "You do not have permission to perform this action")


def _conflict(message, code="INVALID_TRANSITION"):
    return ApiError(409, code, message)


def log(task, actor, action, field=None, old=None, new=None):
    db.session.add(TaskHistory(
        task_id=task.id, actor_id=actor.id, action=action, field=field,
        old_value=None if old is None else str(old), new_value=None if new is None else str(new)))


def _check_assignment(user, assignee_id, project_id):
    project = db.session.get(Project, project_id)
    if project is None or project.is_archived:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"project_id": "Must be an active project"})
    assignee = db.session.get(User, assignee_id)
    if assignee is None or assignee.role != "employee" or not assignee.is_active:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"assignee_id": "Must be an active employee"})
    if user.role == "manager":
        if assignee.manager_id != user.id:
            raise ApiError(403, "FORBIDDEN", "You can only assign tasks to your own team members")
        if user not in project.members:
            raise ApiError(403, "FORBIDDEN", "You are not a member of this project")
    if assignee not in project.members:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed",
                       {"assignee_id": "Assignee must be a member of the project"})
    if assignee.manager_id is None:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed",
                       {"assignee_id": "Assignee has no manager; assign a manager first"})
    return assignee


def create_task(user, d):
    assignee = _check_assignment(user, d["assignee_id"], d["project_id"])
    start = d["start_date"] or utcnow().date()
    if d["deadline"] < start:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"deadline": "Must not be before the start date"})
    task = Task(title=d["title"], description=d["description"], project_id=d["project_id"],
                assignee_id=assignee.id, manager_id=assignee.manager_id if user.role == "admin" else user.id,
                priority=d["priority"], status="Pending", progress=0, start_date=start, deadline=d["deadline"],
                estimated_hours=d["estimated_hours"], created_by=user.id)
    db.session.add(task)
    db.session.flush()
    log(task, user, "created", "title", None, task.title)
    log(task, user, "assigned", "assignee_id", None, assignee.id)
    db.session.commit()
    return task


def update_task(user, task, d):
    if user.role == "manager" and task.manager_id != user.id:
        raise _forbid()
    if task.status == "Completed":
        raise _conflict("Completed tasks cannot be edited; reopen the task first", "TASK_COMPLETED")
    new_assignee = d.get("assignee_id", task.assignee_id)
    if new_assignee != task.assignee_id:
        assignee = _check_assignment(user, new_assignee, task.project_id)
        log(task, user, "assigned", "assignee_id", task.assignee_id, assignee.id)
        task.assignee_id = assignee.id
        task.manager_id = assignee.manager_id if user.role == "admin" else user.id
    for field in ("title", "description", "priority", "start_date", "deadline", "estimated_hours"):
        if field in d and d[field] != getattr(task, field):
            log(task, user, "updated", field, getattr(task, field), d[field])
            setattr(task, field, d[field])
    if task.start_date and task.deadline < task.start_date:
        db.session.rollback()
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"deadline": "Must not be before the start date"})
    db.session.commit()
    return task


def archive_task(user, task):
    if user.role == "manager" and task.manager_id != user.id:
        raise _forbid()
    task.is_archived = True
    log(task, user, "archived")
    db.session.commit()
    return task


def update_progress(user, task, progress, actual_hours, note):
    if task.assignee_id != user.id:
        raise _forbid()
    if task.status != "In Progress":
        raise _conflict("Progress can only be updated while the task is In Progress", "INVALID_STATE")
    if progress > 99:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed",
                       {"progress": "Progress reaches 100 only after manager approval"})
    log(task, user, "progress_updated", "progress", task.progress, progress)
    task.progress = progress
    if actual_hours is not None:
        task.actual_hours = actual_hours
    task.last_progress_update = utcnow()
    if note:
        from app.models import TaskComment
        db.session.add(TaskComment(task_id=task.id, author_id=user.id, body=note))
    db.session.commit()
    return task


def change_status(user, task, new_status, reason):
    allowed = TRANSITIONS.get((task.status, new_status))
    if allowed is None:
        raise _conflict(f"Cannot change status from {task.status} to {new_status} this way")
    if not (_roles(user, task) & allowed):
        raise _forbid()
    if new_status == "Blocked" and not reason:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"reason": "A reason is required when blocking"})
    log(task, user, "status_changed", "status", task.status, new_status)
    if reason:
        log(task, user, "status_changed", "reason", None, reason)
    task.status = new_status
    task.last_progress_update = utcnow()
    db.session.commit()
    return task


def submit_for_review(user, task, note):
    if task.assignee_id != user.id:
        raise _forbid()
    if task.status != "In Progress":
        raise _conflict("Only tasks that are In Progress can be submitted", "INVALID_STATE")
    if task.progress < SUBMIT_MIN_PROGRESS:
        raise ApiError(422, "VALIDATION_ERROR", "Validation failed",
                       {"progress": f"Progress must be at least {SUBMIT_MIN_PROGRESS}% before submitting"})
    log(task, user, "submitted", "status", task.status, "Under Review")
    task.status = "Under Review"
    task.last_progress_update = utcnow()
    if note:
        from app.models import TaskComment
        db.session.add(TaskComment(task_id=task.id, author_id=user.id, body=note))
    db.session.commit()
    return task


def review_task(user, task, decision, feedback):
    if user.role != "manager" or task.manager_id != user.id:
        raise _forbid()
    if task.status != "Under Review":
        raise _conflict("Only tasks that are Under Review can be reviewed", "INVALID_STATE")
    if decision == "approve":
        log(task, user, "approved", "status", task.status, "Completed")
        task.status, task.progress, task.completed_at = "Completed", 100, utcnow()
        task.review_feedback = feedback
    else:
        if not feedback:
            raise ApiError(422, "VALIDATION_ERROR", "Validation failed", {"feedback": "Feedback is required when rejecting"})
        log(task, user, "rejected", "status", task.status, "In Progress")
        task.status = "In Progress"
        task.rejection_count += 1
        task.review_feedback = feedback
        task.last_progress_update = utcnow()
    db.session.commit()
    return task


def reopen_task(user, task, reason):
    if user.role == "manager" and task.manager_id != user.id:
        raise _forbid()
    if task.status != "Completed":
        raise _conflict("Only Completed tasks can be reopened", "INVALID_STATE")
    log(task, user, "reopened", "status", "Completed", "In Progress")
    task.status, task.progress, task.completed_at = "In Progress", 90, None
    task.reopen_count += 1
    task.review_feedback = reason
    task.last_progress_update = utcnow()
    db.session.commit()
    return task
