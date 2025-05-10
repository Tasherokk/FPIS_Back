# courses/views.py
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Course, Topic, Enrollment, UserTestResult, Test, Answer, Question, Registration
from .serializers import CourseSerializer, TopicSerializer, TestSerializer, RegistrationSerializer
import logging

logger = logging.getLogger(__name__)

# --------------------------------------


class CourseListView(APIView):
    permission_classes = [permissions.AllowAny]
    logger.info("Course list requested")
    def get(self, request):
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CourseDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        serializer = CourseSerializer(course)
        return Response(serializer.data, status=status.HTTP_200_OK)


# --------------------------------------


class MyCoursesListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Для студентов: список курсов, где он заэнроллен
        # Для кураторов: можно возвращать пустой или по желанию - все курсы, которые ведут его студенты
        if user.role == 'student':
            enrollments = user.enrollment_set.select_related('course')
            courses = [en.course for en in enrollments]
        else:
            courses = []

        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# --------------------------------------


class CourseTopicsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        user = request.user

        # 1. Проверяем, что user зачислен на курс
        enrolled = user.enrollment_set.filter(course_id=course_id).exists()
        if not enrolled:
            return Response({"detail": "Вы не записаны на этот курс."},
                            status=status.HTTP_403_FORBIDDEN)

        # 2. Получаем все темы данного курса, отсортированные по order
        topics = Topic.objects.filter(course_id=course_id).order_by('order')

        # 3. Для каждой темы определяем is_unlocked
        unlocked_topic_ids = set()
        passed_previous = True  # Флаг, прошёл ли пользователь предыдущую тему
        prev_topic_id = None

        # Перед тем как итерироваться, подготовим словарь:
        # topic_id -> test_id (если у темы есть тест)
        topic_test_map = {t.id: t.test.id for t in topics if hasattr(t, 'test')}

        # Для каждой темы по порядку:
        for topic in topics:
            if passed_previous:
                # Тема считается открытой
                unlocked_topic_ids.add(topic.id)
            else:
                break
            # Если у темы есть тест, проверим проходил ли пользователь его
            test_id = topic_test_map.get(topic.id)
            if test_id:
                user_result = UserTestResult.objects.filter(
                    user=user, test_id=test_id, passed=True
                ).exists()
                # passed_previous станет True только если есть запись о passed=True
                passed_previous = user_result
            else:
                # Если теста нет, то автоматически считаем её пройденной
                passed_previous = True

        # 4. Сериализуем результат
        serializer = TopicSerializer(topics, many=True, context={'request': request})
        data = serializer.data

        # 5. Подменяем значение is_unlocked для каждой темы в финальном output
        # (мы можем сделать это и внутри get_is_unlocked, передавая контекст)
        for item in data:
            topic_id = item['id']
            is_unlocked = topic_id in unlocked_topic_ids

            if is_unlocked:
                # Тема разблокирована – показываем все поля
                item['is_unlocked'] = True
            else:
                # Сохраняем нужные поля, прежде чем чистить словарь
                locked_title = item['title']
                locked_duration = item['duration_in_minutes']
                locked_order = item['order']# или item.get('duration_in_minutes')

                item.clear()
                item.update({
                    'id': topic_id,
                    'title': locked_title,
                    'duration_in_minutes': locked_duration,
                    'order': locked_order,
                    'is_unlocked': False
                })

        return Response(data, status=status.HTTP_200_OK)



class CourseFirstTopicView(APIView):
    permission_classes = [permissions.AllowAny]  # публичный эндпоинт

    def get(self, request, course_id):
        # 1. Проверяем, существует ли курс
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"detail": "Курс не найден."},
                            status=status.HTTP_404_NOT_FOUND)

        # 2. Получаем все темы, отсортированные по order
        topics_qs = Topic.objects.filter(course=course).order_by('order')
        if not topics_qs.exists():
            return Response({"detail": "В курсе нет тем."},
                            status=status.HTTP_404_NOT_FOUND)

        # 3. Сериализуем все темы
        serializer = TopicSerializer(topics_qs, many=True)
        data = serializer.data  # это список словарей

        # 4. Обрабатываем так, что "первая" тема остаётся полной,
        #    а все остальные темы — "сокращённые" (закрытые).
        for i, topic_item in enumerate(data):
            if i == 0:
                # Первая тема (индекс 0): оставляем все поля
                topic_item['is_unlocked'] = True
            else:
                # Остальные темы: "урезаем" поля
                locked_data = {
                    'id': topic_item['id'],
                    'title': topic_item['title'],
                    'duration_in_minutes': topic_item.get('duration_in_minutes'),
                    'is_unlocked': False
                }
                data[i] = locked_data

        return Response(data, status=status.HTTP_200_OK)


# --------------------------------------


class TopicDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, topic_id):
        user = request.user
        logger.info(f"User {user.id} requested topic {topic_id}")
        # Получаем тему
        try:
            topic = Topic.objects.select_related('course').get(id=topic_id)
        except Topic.DoesNotExist:
            return Response({"detail": "Тема не найдена."},
                            status=status.HTTP_404_NOT_FOUND)

        # Проверяем, что пользователь зачислен на курс
        enrolled = user.enrollment_set.filter(course=topic.course).exists()
        if not enrolled:
            return Response({"detail": "Вы не записаны на этот курс."},
                            status=status.HTTP_403_FORBIDDEN)

        # Проверяем, разблокирована ли тема
        # Логика та же, что в CourseTopicsView, но можно вынести в отдельную функцию
        # или переиспользовать. Здесь, для краткости, сделаем “упрощённую” проверку:
        topics = Topic.objects.filter(course=topic.course).order_by('order')
        # собираем их в список, чтобы понять, какие прошёл пользователь
        passed_previous = True
        unlocked_topic_ids = set()
        topic_test_map = {t.id: t.test.id for t in topics if hasattr(t, 'test')}

        for t in topics:
            if passed_previous:
                unlocked_topic_ids.add(t.id)
            else:
                break
            test_id = topic_test_map.get(t.id)
            if test_id:
                user_result = UserTestResult.objects.filter(
                    user=user, test_id=test_id, passed=True
                ).exists()
                passed_previous = user_result
            else:
                passed_previous = True

        if topic_id not in unlocked_topic_ids:
            return Response({"detail": "Тема ещё не разблокирована."},
                            status=status.HTTP_403_FORBIDDEN)

        # Если тема разблокирована, возвращаем сериализованные данные
        # Можно использовать TopicSerializer, но нам ещё нужен тест
        topic_data = {
            "id": topic.id,
            "title": topic.title,
            "video_url": topic.video_url,
            "video_title": topic.video_title,
            "duration_in_minutes": topic.duration_in_minutes,
        }

        if hasattr(topic, 'test'):
            test_serializer = TestSerializer(topic.test)
            topic_data["test"] = test_serializer.data
        else:
            topic_data["test"] = None

        return Response(topic_data, status=status.HTTP_200_OK)



# --------------------------------------


class SubmitTestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, topic_id):
        user = request.user
        logger.info(f"User {user.id} submitted test for topic {topic_id}")

        # Проверяем, есть ли такой topic и test
        try:
            topic = Topic.objects.get(id=topic_id)
            test = topic.test  # Ошибка AttributeError, если у темы нет теста
        except (Topic.DoesNotExist, AttributeError):
            return Response({"detail": "Тест для данной темы не найден."},
                            status=status.HTTP_404_NOT_FOUND)

        # Проверяем, что пользователь зачислен
        enrolled = user.enrollment_set.filter(course=topic.course).exists()
        if not enrolled:
            return Response({"detail": "Вы не записаны на этот курс."},
                            status=status.HTTP_403_FORBIDDEN)

        # Получаем ответы
        user_answers = request.data.get('answers', [])
        logger.debug(f"Submitted answers: {user_answers}")
        if not user_answers:
            return Response({"detail": "Необходимо указать ответы."},
                            status=status.HTTP_400_BAD_REQUEST)

        score = 0
        answers_detail = []  # Тут будем хранить {question_id, answered_correctly}

        # Сопоставляем ответы с базой
        for ua in user_answers:
            q_id = ua.get('question_id')
            a_id = ua.get('answer_id')

            # Ищем вопрос
            try:
                question = test.questions.get(id=q_id)
            except Question.DoesNotExist:
                # Если вопрос не найден, можем добавить запись, что он “неверный”
                answers_detail.append({
                    "question_id": q_id,
                    "answered_correctly": False,
                })
                continue

            # Ищем ответ
            try:
                answer = question.answers.get(id=a_id)
            except Answer.DoesNotExist:
                # Аналогично, если не нашли ответ
                answers_detail.append({
                    "question_id": q_id,
                    "answered_correctly": False,
                })
                continue

            # Проверяем, правильный ли ответ
            answered_correctly = answer.is_correct
            if answered_correctly:
                score += 1

            answers_detail.append({
                "question_id": q_id,
                "answered_correctly": answered_correctly,
            })

        passed = (score >= 9)
        logger.info(f"User {user.id} scored {score}, passed: {passed}")
        # Проверяем, есть ли у пользователя старая запись (UserTestResult)
        # Если да – не затираем, а только обновляем, если новая попытка лучше
        utr, created = UserTestResult.objects.get_or_create(
            user=user,
            test=test,
            defaults={'score': score, 'passed': passed}
        )
        if not created:
            # если запись уже была, сравниваем
            if passed and not utr.passed:
                # если ранее был не пройден, а теперь пройден – обновляем
                utr.score = score
                utr.passed = True
                utr.save()
            else:
                # если уже был пройден (passed=True), то ничего не меняем
                # или если у нас сейчас неудачная попытка, но раньше было passed=True, то оставляем как есть
                if score > utr.score:
                    utr.score = score
                    utr.save()

        data = {
            "score": score,
            "passed": passed,
            "answers_detail": answers_detail,  # <-- тут детальная инфа по каждому вопросу
        }
        return Response(data, status=status.HTTP_200_OK)



# class CheckTestView(APIView):
#     permission_classes = [permissions.AllowAny]  # или IsAuthenticated, если нужно
#
#     def post(self, request, topic_id):
#         # Пытаемся найти тему и тест
#         try:
#             topic = Topic.objects.get(id=topic_id)
#             test = topic.test
#         except (Topic.DoesNotExist, AttributeError):
#             return Response({"detail": "Тест для данной темы не найден."},
#                             status=status.HTTP_404_NOT_FOUND)
#
#         # Получаем массив ответов
#         user_answers = request.data.get('answers', [])
#         if not user_answers:
#             return Response({"detail": "Необходимо указать ответы."},
#                             status=status.HTTP_400_BAD_REQUEST)
#
#         score = 0
#         answers_detail = []  # Чтобы вернуть, какие вопросы правильные/неправильные
#
#         for ua in user_answers:
#             q_id = ua.get('question_id')
#             a_id = ua.get('answer_id')
#
#             # Ищем вопрос
#             try:
#                 question = test.questions.get(id=q_id)
#             except:
#                 answers_detail.append({
#                     "question_id": q_id,
#                     "answered_correctly": False
#                 })
#                 continue
#
#             # Ищем ответ
#             try:
#                 answer = question.answers.get(id=a_id)
#             except:
#                 answers_detail.append({
#                     "question_id": q_id,
#                     "answered_correctly": False
#                 })
#                 continue
#
#             # Проверяем правильность
#             answered_correctly = answer.is_correct
#             if answered_correctly:
#                 score += 1
#
#             answers_detail.append({
#                 "question_id": q_id,
#                 "answered_correctly": answered_correctly
#             })
#
#         passed = (score >= 9)
#
#         data = {
#             "score": score,
#             "passed": passed,
#             "answers_detail": answers_detail
#         }
#         # ВАЖНО: Мы не записываем результат в БД (не создаём UserTestResult)
#
#         return Response(data, status=status.HTTP_200_OK)


# --------------------------------------


class CuratorStudentsProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        logger.info(f"Curator {user.id} requested student progress")
        if user.role != 'curator':
            return Response({"detail": "Доступно только кураторам."},
                            status=status.HTTP_403_FORBIDDEN)

        students = user.students.all()  # related_name='students' у поля curator
        data_out = []

        for student in students:
            # Список курсов, на которые записан данный студент
            enrollments = student.enrollment_set.select_related('course')
            courses_progress = []

            for en in enrollments:
                course = en.course
                # Общее число тем
                topics = course.topics.all()
                total_topics = topics.count()

                # Считаем, сколько тем прошло = количество тестов, где passed=True
                # но нужно понимать, что если у темы нет теста, считаем её автоматически пройденной
                total_passed = 0
                for t in topics:
                    if hasattr(t, 'test'):
                        # проверяем UserTestResult
                        if UserTestResult.objects.filter(user=student, test=t.test, passed=True).exists():
                            total_passed += 1
                        else:
                            break
                    else:
                        # если у темы нет теста, считаем пройденной
                        total_passed += 1

                courses_progress.append({
                    "course_id": course.id,
                    "course_title": course.title,
                    "passed_topics": total_passed,
                    "total_topics": total_topics,
                })

            data_out.append({
                "student_id": student.id,
                "student_name": student.name,
                "courses": courses_progress
            })

        return Response(data_out, status=status.HTTP_200_OK)


# --------------------------------------




class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user  # текущий пользователь, полученный из JWT
        data = {
            'id': user.id,
            'username': user.username,
            'name': user.name,     # если у вас есть поле name
            'role': user.role,     # student / curator, и т.д.
            # Можно добавлять и другие поля по желанию
        }
        return Response(data)


# --------------------------------------



class RegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        logger.info(f"Registration attempt with data: {request.data}")
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Registration successful!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TodayRegistrationsView(APIView):
    def get(self, request):
        today = now().date()
        registrations = Registration.objects.filter(created_at__date=today)
        serializer = RegistrationSerializer(registrations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)