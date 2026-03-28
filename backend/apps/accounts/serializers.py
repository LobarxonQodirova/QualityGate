"""
Serializers for accounts app.
"""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Inspector, QualityTeam, User


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight user serializer for list views and nested references."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name",
            "full_name", "role", "employee_id", "department",
            "is_active", "is_certified_inspector",
        ]
        read_only_fields = ["id"]


class UserDetailSerializer(serializers.ModelSerializer):
    """Full user serializer for detail views."""

    full_name = serializers.CharField(read_only=True)
    is_quality_staff = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name",
            "full_name", "role", "employee_id", "department", "phone",
            "avatar", "is_active", "is_certified_inspector",
            "certification_expiry", "is_quality_staff",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id", "email", "username", "first_name", "last_name",
            "password", "password_confirm", "role", "employee_id",
            "department", "phone",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        return attrs


class InspectorSerializer(serializers.ModelSerializer):
    """Serializer for Inspector profile."""

    user = UserListSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)
    is_certification_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inspector
        fields = [
            "id", "user", "user_id", "certification_level",
            "certification_number", "certified_date", "certification_expiry",
            "specializations", "qualified_standards", "total_inspections",
            "is_active", "is_certification_valid", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "total_inspections", "created_at", "updated_at"]


class QualityTeamSerializer(serializers.ModelSerializer):
    """Serializer for QualityTeam."""

    leader = UserListSerializer(read_only=True)
    leader_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    members = UserListSerializer(many=True, read_only=True)
    member_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
    )
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = QualityTeam
        fields = [
            "id", "name", "description", "leader", "leader_id",
            "members", "member_ids", "member_count", "production_area",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", [])
        leader_id = validated_data.pop("leader_id", None)
        if leader_id:
            validated_data["leader_id"] = leader_id
        team = QualityTeam.objects.create(**validated_data)
        if member_ids:
            team.members.set(User.objects.filter(id__in=member_ids))
        return team

    def update(self, instance, validated_data):
        member_ids = validated_data.pop("member_ids", None)
        leader_id = validated_data.pop("leader_id", None)
        if leader_id is not None:
            instance.leader_id = leader_id
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if member_ids is not None:
            instance.members.set(User.objects.filter(id__in=member_ids))
        return instance
