from django.test import TestCase
from .models import User, Course, Topic, Test, Question, Answer
from .serializers import (
    UserSerializer, CourseSerializer, TopicSerializer,
    TestSerializer, QuestionSerializer, AnswerSerializer
)


class UserSerializerTest(TestCase):
    def setUp(self):
        self.curator = User.objects.create(
            username="curator1",
            name="Curator One",
            role="curator"
        )

        self.user_data = {
            'username': 'newstudent',
            'name': 'New Student',
            'role': 'student',
            'curator': self.curator.id,
            'password': 'testpassword123'
        }

        self.serializer = UserSerializer(data=self.user_data)

    def test_user_serializer_valid(self):
        self.assertTrue(self.serializer.is_valid())
        user = self.serializer.save()
        self.assertEqual(user.username, 'newstudent')
        self.assertEqual(user.name, 'New Student')
        self.assertEqual(user.role, 'student')
        self.assertEqual(user.curator, self.curator)

    def test_password_write_only(self):
        self.assertTrue(self.serializer.is_valid())
        serialized_data = self.serializer.data
        self.assertNotIn('password', serialized_data)


class CourseSerializerTest(TestCase):
    def setUp(self):
        self.course_data = {
            'title': 'Python Advanced',
            'description': 'Learn advanced Python concepts',
            'course_type': 'teacher',
            'sub_type': 'grade2'
        }
        self.serializer = CourseSerializer(data=self.course_data)

    def test_course_serializer_valid(self):
        self.assertTrue(self.serializer.is_valid())
        course = self.serializer.save()
        self.assertEqual(course.title, 'Python Advanced')
        self.assertEqual(course.description, 'Learn advanced Python concepts')
        self.assertEqual(course.course_type, 'teacher')
        self.assertEqual(course.sub_type, 'grade2')


class TopicSerializerTest(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description"
        )
        self.topic = Topic.objects.create(
            course=self.course,
            title="Test Topic",
            order=1,
            video_url="https://example.com/video",
            video_title="Test Video",
            duration_in_minutes=20
        )
        self.serializer = TopicSerializer(instance=self.topic)

    def test_topic_serializer_contains_expected_fields(self):
        data = self.serializer.data
        self.assertIn('id', data)
        self.assertIn('title', data)
        self.assertIn('order', data)
        self.assertIn('video_url', data)
        self.assertIn('video_title', data)
        self.assertIn('duration_in_minutes', data)
        self.assertIn('is_unlocked', data)

    def test_is_unlocked_field_default(self):
        data = self.serializer.data
        self.assertTrue(data['is_unlocked'])


class QuestionAnswerSerializerTest(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Test Course", description="Test")
        self.topic = Topic.objects.create(course=self.course, title="Test Topic", order=1, video_title="Test")
        self.test = Test.objects.create(topic=self.topic)
        self.question = Question.objects.create(test=self.test, text="What is 5+5?")
        self.answer1 = Answer.objects.create(question=self.question, text="10", is_correct=True)
        self.answer2 = Answer.objects.create(question=self.question, text="11", is_correct=False)

    def test_question_serializer(self):
        serializer = QuestionSerializer(instance=self.question)
        data = serializer.data
        self.assertEqual(data['text'], "What is 5+5?")
        self.assertEqual(len(data['answers']), 2)

    def test_answer_serializer(self):
        serializer = AnswerSerializer(instance=self.answer1)
        data = serializer.data
        self.assertEqual(data['text'], "10")
        self.assertIn('id', data)
