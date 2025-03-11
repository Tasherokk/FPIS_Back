# courses/serializers.py
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import (
    User, Course, Enrollment, Topic,
    Test, Question, Answer, UserTestResult, Registration
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'role', 'curator', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.password = make_password(password)
            user.save()
        return user



class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'course_type', 'sub_type', 'img',]



class TopicSerializer(serializers.ModelSerializer):
    # Булево поле, не связанное напрямую с моделью
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ['id', 'title', 'order', 'video_url', 'video_title', 'duration_in_minutes', 'is_unlocked']

    def get_is_unlocked(self, obj):
        """
        Логика определения, разблокирована ли тема для текущего пользователя.
        Обсудим детальнее в части про View.
        Пока просто заглушка (например, вернём True):
        """
        return True



class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ['id', 'text', 'is_correct']

class QuestionSerializer(serializers.ModelSerializer):
    answers = AnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'answers']

class TestSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = ['id', 'questions']



class UserTestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTestResult
        fields = ['id', 'user', 'test', 'score', 'passed', 'created_at']
        read_only_fields = ['user', 'test', 'score', 'passed', 'created_at']



class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['id', 'user', 'course']



class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        fields = ['name', 'phone', 'selected_pair']



