
from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError

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
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student"],
                condition=models.Q(left_at__isnull=True),
                name="unique_active_group_per_student"
            )
        ]

    def clean(self):
        super().clean()

        if self.left_at is not None:
            return

        active_members = GroupMember.objects.filter(
            group=self.group,
            left_at__isnull=True
        ).exclude(pk=self.pk)

        if active_members.count() >= 2:
            raise ValidationError(
                "A project group cannot have more than 2 active students."
            )

    def save(self, *args, **kwargs):
        with transaction.atomic():
            ProjectGroup.objects.select_for_update().get(
                pk=self.group_id
            )
            self.full_clean()
            return super().save(*args, **kwargs)

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
    
    class Status(models.TextChoices):
        PROPOSED = "PROPOSED", "Proposed"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PROPOSED
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group"],
                condition=models.Q(
                    status__in=["PROPOSED", "IN_PROGRESS"]
                ),
                name="unique_active_project_per_group"
            )
        ]

    def clean(self):
        super().clean()

        if self.advisor_id is not None:
            if self.advisor.role != "ADVISOR":
                raise ValidationError(
                    "Only users with the ADVISOR role can be assigned as project advisors."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

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
    
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )

    meeting_notes = models.TextField(blank=True)

    def decide(self, advisor, decision):
        if self.project.advisor_id != advisor.pk:
            raise ValidationError(
                "Only the assigned project advisor can decide on this meeting."
            )

        if advisor.role != "ADVISOR":
            raise ValidationError(
                "Only users with the ADVISOR role can decide on meetings."
            )

        if self.status != self.Status.PENDING:
            raise ValidationError(
                "Only pending meeting requests can be approved or rejected."
            )

        if decision not in [
            self.Status.APPROVED,
            self.Status.REJECTED
        ]:
            raise ValidationError(
                "Decision must be APPROVED or REJECTED."
            )

        self.status = decision
        self.save(update_fields=["status"])

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "version_number"],
                name="unique_submission_version_per_assignment"
            )
        ]

    @classmethod
    def submit_version(cls, assignment, file_url):
        from django.db import transaction

        with transaction.atomic():
            # Aynı görev atamasının teslimlerini sırayla al.
            submissions = cls.objects.filter(
                assignment=assignment
            ).order_by("-version_number")

            latest = submissions.first()

            if latest is None:
                next_version = 1
            else:
                latest_feedback = latest.feedbacks.order_by(
                    "-created_at", "-pk"
                ).first()

                if (
                    latest_feedback is None
                    or latest_feedback.decision != "REVISION_REQUIRED"
                ):
                    raise ValidationError(
                        "A new submission requires a revision request."
                    )

                next_version = latest.version_number + 1

            return cls.objects.create(
                assignment=assignment,
                file_url=file_url,
                version_number=next_version
            )

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
    
    class Decision(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        REVISION_REQUIRED = "REVISION_REQUIRED", "Revision Required"

    decision = models.CharField(
        max_length=30,
        choices=Decision.choices
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def give_feedback(cls, submission, advisor, comment, decision):
        if decision not in cls.Decision.values:
            raise ValidationError("Invalid feedback decision.")

        project = submission.assignment.task.project

        if advisor.role != "ADVISOR" or project.advisor_id != advisor.pk:
            raise ValidationError(
                "Only the assigned project advisor can give feedback."
            )

        if submission.feedbacks.exists():
            raise ValidationError(
                "This submission already has feedback."
            )

        return cls.objects.create(
            submission=submission,
            advisor=advisor,
            comment=comment,
            decision=decision
        )

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
