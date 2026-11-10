
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import (
    ProjectGroup, GroupMember, Project, Meeting,
    Task, TaskAssignment, Submission, Feedback, Notification
)


class Command(BaseCommand):
    help = "Create sample UniDone development data"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Seed data can only be created in development mode."
            )

        User = get_user_model()

        with transaction.atomic():
            users = []

            for number in (1, 2):
                username = f"seed_student_{number}"

                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": f"{username}@example.com",
                        "role": "STUDENT",
                    }
                )

                if created:
                    user.set_unusable_password()
                    user.save(update_fields=["password"])

                if user.role != "STUDENT":
                    raise CommandError(
                        f"{username} does not have the STUDENT role."
                    )

                users.append(user)

            advisor, created = User.objects.get_or_create(
                username="seed_advisor",
                defaults={
                    "email": "seed_advisor@example.com",
                    "role": "ADVISOR",
                }
            )

            if created:
                advisor.set_unusable_password()
                advisor.save(update_fields=["password"])

            if advisor.role != "ADVISOR":
                raise CommandError(
                    "seed_advisor does not have the ADVISOR role."
                )

            group, _ = ProjectGroup.objects.get_or_create(
                group_name="UniDone Demo Group",
                created_by=users[0]
            )

            for student in users:
                if not GroupMember.objects.filter(
                    group=group,
                    student=student,
                    left_at__isnull=True
                ).exists():
                    GroupMember.objects.create(
                        group=group,
                        student=student
                    )

            project, _ = Project.objects.get_or_create(
                group=group,
                title="UniDone Demo Project",
                defaults={
                    "advisor": advisor,
                    "description": "Sample project for API testing",
                    "status": Project.Status.IN_PROGRESS,
                }
            )

            meeting, _ = Meeting.objects.get_or_create(
                project=project,
                requested_by=users[0],
                meeting_notes="UniDone demo meeting",
                defaults={
                    "meeting_date": timezone.now() + timedelta(days=7),
                    "status": Meeting.Status.PENDING,
                }
            )

            task, _ = Task.objects.get_or_create(
                project=project,
                title="Prepare project requirements",
                defaults={
                    "assigned_by": advisor,
                    "description": "Prepare the requirements document",
                    "due_date": timezone.localdate() + timedelta(days=14),
                    "status": "TODO",
                }
            )

            assignments = []

            for student in users:
                assignment, _ = TaskAssignment.objects.get_or_create(
                    task=task,
                    student=student
                )
                assignments.append(assignment)

            assignment = assignments[0]

            submission = Submission.objects.filter(
                assignment=assignment,
                version_number=1
            ).first()

            if submission is None:
                submission = Submission.submit_version(
                    assignment,
                    "https://example.com/demo-submission.pdf"
                )

            if not submission.feedbacks.exists():
                Feedback.give_feedback(
                    submission=submission,
                    advisor=advisor,
                    comment="Please improve the requirements document.",
                    decision=Feedback.Decision.REVISION_REQUIRED
                )

            Notification.objects.get_or_create(
                recipient=users[0],
                title="Revision requested",
                message="Your project submission needs revision.",
            )

        self.stdout.write(
            self.style.SUCCESS(
                "UniDone sample data created successfully!"
            )
        )
