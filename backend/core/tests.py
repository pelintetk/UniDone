
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import (
    ProjectGroup, GroupMember, Project, Meeting,
    Task, TaskAssignment, Submission, Feedback
)


User = get_user_model()


class BusinessRuleTests(TestCase):

    def setUp(self):
        self.student1 = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            password="TestPass123!",
            role="STUDENT"
        )
        self.student2 = User.objects.create_user(
            username="student2",
            email="student2@example.com",
            password="TestPass123!",
            role="STUDENT"
        )
        self.student3 = User.objects.create_user(
            username="student3",
            email="student3@example.com",
            password="TestPass123!",
            role="STUDENT"
        )
        self.advisor = User.objects.create_user(
            username="advisor",
            email="advisor@example.com",
            password="TestPass123!",
            role="ADVISOR"
        )

    def create_group(self, name):
        return ProjectGroup.objects.create(
            group_name=name,
            created_by=self.student1
        )

    def create_project(self, group, advisor=None):
        return Project.objects.create(
            group=group,
            advisor=advisor,
            title="Test Project",
            description="Automated test"
        )

    def test_br01_one_active_group_per_student(self):
        group1 = self.create_group("Group A")
        group2 = self.create_group("Group B")

        GroupMember.objects.create(
            group=group1,
            student=self.student1
        )

        with self.assertRaises(ValidationError):
            GroupMember.objects.create(
                group=group2,
                student=self.student1
            )

    def test_br02_max_two_active_members(self):
        group = self.create_group("Group A")

        GroupMember.objects.create(
            group=group,
            student=self.student1
        )
        GroupMember.objects.create(
            group=group,
            student=self.student2
        )

        with self.assertRaises(ValidationError):
            GroupMember.objects.create(
                group=group,
                student=self.student3
            )

    def test_br03_one_active_project_per_group(self):
        group = self.create_group("Group A")
        project = self.create_project(group)

        with self.assertRaises(ValidationError):
            self.create_project(group)

        project.status = Project.Status.COMPLETED
        project.save()

        new_project = self.create_project(group)
        self.assertEqual(
            new_project.status,
            Project.Status.PROPOSED
        )

    def test_br04_only_advisors_can_supervise(self):
        group1 = self.create_group("Group A")
        group2 = self.create_group("Group B")

        with self.assertRaises(ValidationError):
            self.create_project(
                group1,
                advisor=self.student1
            )

        self.create_project(
            group1,
            advisor=self.advisor
        )
        self.create_project(
            group2,
            advisor=self.advisor
        )

        self.assertEqual(
            Project.objects.filter(
                advisor=self.advisor
            ).count(),
            2
        )

    def test_br05_meeting_approval(self):
        group = self.create_group("Group A")
        project = self.create_project(
            group,
            advisor=self.advisor
        )

        meeting = Meeting.objects.create(
            project=project,
            requested_by=self.student1,
            meeting_date=timezone.now() + timedelta(days=7)
        )

        with self.assertRaises(ValidationError):
            meeting.decide(
                self.student1,
                Meeting.Status.APPROVED
            )

        meeting.decide(
            self.advisor,
            Meeting.Status.APPROVED
        )

        self.assertEqual(
            meeting.status,
            Meeting.Status.APPROVED
        )

        with self.assertRaises(ValidationError):
            meeting.decide(
                self.advisor,
                Meeting.Status.REJECTED
            )

    def test_br06_submission_revision(self):
        group = self.create_group("Group A")
        project = self.create_project(
            group,
            advisor=self.advisor
        )

        task = Task.objects.create(
            project=project,
            assigned_by=self.advisor,
            title="Test Task",
            description="Automated test",
            due_date=timezone.localdate() + timedelta(days=7)
        )

        assignment = TaskAssignment.objects.create(
            task=task,
            student=self.student1
        )

        v1 = Submission.submit_version(
            assignment,
            "https://example.com/v1.pdf"
        )
        self.assertEqual(v1.version_number, 1)

        with self.assertRaises(ValidationError):
            Submission.submit_version(
                assignment,
                "https://example.com/v2.pdf"
            )

        with self.assertRaises(ValidationError):
            Feedback.give_feedback(
                v1,
                self.student1,
                "Please revise",
                Feedback.Decision.REVISION_REQUIRED
            )

        Feedback.give_feedback(
            v1,
            self.advisor,
            "Please revise",
            Feedback.Decision.REVISION_REQUIRED
        )

        v2 = Submission.submit_version(
            assignment,
            "https://example.com/v2.pdf"
        )
        self.assertEqual(v2.version_number, 2)

        Feedback.give_feedback(
            v2,
            self.advisor,
            "Approved",
            Feedback.Decision.APPROVED
        )

        self.assertEqual(
            v2.feedbacks.first().decision,
            Feedback.Decision.APPROVED
        )
