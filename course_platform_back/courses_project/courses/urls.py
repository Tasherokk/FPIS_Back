# courses/urls.py
from django.urls import path
from .views import (
    CourseListView,
    MyCoursesListView,
    CourseTopicsView,
    TopicDetailView,
    SubmitTestView,
    CuratorStudentsProgressView, CourseFirstTopicView, CurrentUserView, CourseDetailView, RegistrationView,
    TodayRegistrationsView,
)

urlpatterns = [

    path('user/me/', CurrentUserView.as_view(), name='user-me'),

    # Публичные
    path('register/', RegistrationView.as_view(), name='register'),
    path('public-courses/', CourseListView.as_view(), name='public-courses'),
    path('public-courses/<int:course_id>/first-topic/', CourseFirstTopicView.as_view(), name='course-first-topic'),
    path('public-courses/<int:course_id>/', CourseDetailView.as_view(), name='course-detail'),
    # path('topics/<int:topic_id>/check-test/', CheckTestView.as_view(), name='topic-check-test'),



    # Для студентов
    path('my-courses/', MyCoursesListView.as_view(), name='my-courses'),
    path('my-courses/<int:course_id>/topics/', CourseTopicsView.as_view(), name='course-topics'),
    path('topics/<int:topic_id>/', TopicDetailView.as_view(), name='topic-detail'),
    path('topics/<int:topic_id>/submit-test/', SubmitTestView.as_view(), name='topic-submit-test'),

    # Для кураторов
    path('curator/progress/', CuratorStudentsProgressView.as_view(), name='curator-progress'),

    # Для продавцов
    path('seller/today-registrations/', TodayRegistrationsView.as_view(), name='today-registrations'),
]
