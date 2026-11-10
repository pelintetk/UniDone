
from django.conf import settings
from django.db import models


class ProjectGroup(models.Model):
    group_id = models.AutoField(primary_key=True)
    group_name = models.CharField(max_length=150)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_groups"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.group_name


class GroupMember(models.Model):
    membership_id = models.AutoField(primary_key=True)
    group = models.ForeignKey(
        ProjectGroup,
        on_delete=models.CASCADE,
        related_name="members"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="group_memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.group.group_name}"


class Project(models.Model):
    project_id = models.AutoField(primary_key=True)
    group = models.ForeignKey(
        ProjectGroup,
        on_delete=models.PROTECT,
        related_name="projects"
    )
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="advised_projects",
        null=True,
        blank=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=30, default="PROPOSED")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Meeting(models.Model):
    meeting_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="meetings"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_meetings"
    )
    meeting_date = models.DateTimeField()
    status = models.CharField(max_length=30, default="PENDING")
    meeting_notes = models.TextField(blank=True)

    def __str__(self):
        return f"Meeting {self.meeting_id}"


class Task(models.Model):
    task_id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_tasks"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    status = models.CharField(max_length=30, default="TODO")

    def __str__(self):
        return self.title


class TaskAssignment(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="task_assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.title} - {self.student.username}"


class Submission(models.Model):
    submission_id = models.AutoField(primary_key=True)
    assignment = models.ForeignKey(
        TaskAssignment,
        on_delete=models.CASCADE,
        related_name="submissions"
    )
    file_url = models.URLField(max_length=500)
    version_number = models.PositiveIntegerField(default=1)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, default="SUBMITTED")

    def __str__(self):
        return f"Submission {self.submission_id} - v{self.version_number}"


class Feedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)
    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="feedbacks"
    )
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="given_feedbacks"
    )
    comment = models.TextField()
    decision = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback {self.feedback_id}"


class Notification(models.Model):
    notification_id = models.AutoField(primary_key=True)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
