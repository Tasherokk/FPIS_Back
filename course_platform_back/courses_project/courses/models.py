from django.db import models
from django.contrib.auth.models import AbstractUser

# --------------------------------------

class User(AbstractUser):
    ROLE_CHOICES = (
        ('curator', 'Curator'),
        ('student', 'Student'),
        ('seller', 'Seller'),
    )
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    curator = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='students'
    )

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return f"{self.username} ({self.name})"

# --------------------------------------

class Course(models.Model):
    TYPE_CHOICES = (
        ('student', 'For Students'),
        ('teacher', 'For Teachers'),
    )
    SUB_TYPE_CHOICES = (
        ('grade1', 'For 1st Grade'),
        ('grade2', 'For 2nd Grade'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    course_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=None,
        blank=True,
        null=True,
    )
    sub_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default=None,
        choices=SUB_TYPE_CHOICES
    )

    img = models.ImageField(
        upload_to='courses/images/',
        null=True,
        blank=True,
        help_text='Обложка курса или иконка'
    )

    def __str__(self):
        return self.title

# --------------------------------------

class Enrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f"{self.user.username} -> {self.course.title}"

# --------------------------------------

class Topic(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField()
    video_url = models.URLField(blank=True, null=True)  # ссылка на видео
    video_title = models.CharField(max_length=255)

    duration_in_minutes = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Продолжительность видео (в минутах)'
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.order}. {self.title} ({self.course.title})"

# --------------------------------------

class Test(models.Model):
    topic = models.OneToOneField(Topic, on_delete=models.CASCADE, related_name='test')

    def __str__(self):
        return f"Test for topic: {self.topic.title}"

# --------------------------------------

class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()

    def __str__(self):
        return f"Question: {self.text[:50]}..."

# --------------------------------------

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Answer: {self.text[:50]}..."

# --------------------------------------

class UserTestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'test')

    def __str__(self):
        return f"{self.user.username} - {self.test.topic.title} - {self.score} points"

# --------------------------------------

class Registration(models.Model):
    name = models.CharField(max_length=255, verbose_name="Есім")
    phone = models.CharField(max_length=11, verbose_name="Телефон номері")
    selected_pair = models.CharField(max_length=255, verbose_name="Пәндер жұбы")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Тіркелу күні")

    def __str__(self):
        return f"{self.name} ({self.phone})"
