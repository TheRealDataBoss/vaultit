"""DRF serializers for projects."""

from rest_framework import serializers

from apps.projects.models import Handoff, Project, Session


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "id", "project_id", "name", "backend",
            "coordination", "created_at",
        ]
        read_only_fields = ["id", "project_id", "created_at"]


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    coordination = serializers.CharField(max_length=50, default="sequential")


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = [
            "id", "session_id", "agent", "created_at", "closed_at",
        ]
        read_only_fields = ["id", "session_id", "created_at"]


class SessionCreateSerializer(serializers.Serializer):
    agent = serializers.CharField(max_length=100, default="custom")


class HandoffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Handoff
        fields = [
            "id", "handoff_id", "version", "agent", "agent_version",
            "tasks", "decisions", "open_questions", "next_steps",
            "raw_notes", "metadata", "created_at",
        ]
        read_only_fields = ["id", "handoff_id", "created_at"]


class HandoffCreateSerializer(serializers.Serializer):
    notes = serializers.CharField(default="", allow_blank=True)
    agent = serializers.CharField(max_length=100, default="custom")
    agent_version = serializers.CharField(max_length=100, default="", allow_blank=True)
    tasks = serializers.ListField(child=serializers.DictField(), default=list)
    decisions = serializers.ListField(child=serializers.DictField(), default=list)
    open_questions = serializers.ListField(child=serializers.CharField(), default=list)
    next_steps = serializers.ListField(child=serializers.CharField(), default=list)


class TaskCreateSerializer(serializers.Serializer):
    task_id = serializers.CharField(max_length=20)
    title = serializers.CharField(max_length=200)
    status = serializers.CharField(max_length=50, default="pending")
    owner = serializers.CharField(max_length=100, default="human")


class TaskUpdateSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=50)


class DecisionCreateSerializer(serializers.Serializer):
    decision_id = serializers.CharField(max_length=20)
    summary = serializers.CharField(max_length=500)
    rationale = serializers.CharField(default="", allow_blank=True)
    made_by = serializers.CharField(max_length=100, default="human")
