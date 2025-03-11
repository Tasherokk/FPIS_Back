import nested_admin
from django.contrib import admin, messages
from django.contrib.admin import DateFieldListFilter
from django.contrib.admin.widgets import AutocompleteSelect
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from .models import User, Course, Enrollment, Topic, Test, Question, Answer, UserTestResult, Registration
from django import forms
from django_summernote.widgets import SummernoteWidget



class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = '__all__'
        widgets = {
            'text': SummernoteWidget(),  # Используем Summernote для редактирования текста
        }


class AnswerInline(nested_admin.NestedTabularInline):
    model = Answer
    extra = 0
    max_num = 6
    form = AnswerForm


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = '__all__'
        widgets = {
            'text': SummernoteWidget(),  # Используем Summernote для редактирования текста
        }


class QuestionInline(nested_admin.NestedStackedInline):
    model = Question
    extra = 0
    max_num = 40
    inlines = [AnswerInline]
    form = QuestionForm


class TestForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = '__all__'


class TestInline(nested_admin.NestedStackedInline):
    model = Test
    extra = 1
    max_num = 1
    inlines = [QuestionInline]
    form = TestForm


class TopicForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = '__all__'


class TopicInline(nested_admin.NestedStackedInline):
    model = Topic
    extra = 0
    max_num = 33
    inlines = [TestInline]
    form = TopicForm


class CustomUserCreationForm(forms.ModelForm):
    password = forms.CharField(label="Password")
    curator = forms.ModelChoiceField(
        queryset=User.objects.filter(role='curator'),
        required=False,
        label="Curator"
    )

    class Meta:
        model = User
        fields = ('username', 'name', 'password', 'curator')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class CustomUserChangeForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        widget=forms.TextInput(attrs={'readonly': 'readonly'})
    )
    curator = forms.ModelChoiceField(
        queryset=User.objects.filter(role='curator'),
        required=False,
        label="Curator"
    )

    class Meta:
        model = User
        fields = ('username', 'name', 'password', 'curator')




# --------------------------------------
@admin.register(User)
class UserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    model = User
    change_password_form = AdminPasswordChangeForm
    list_display = ('username', 'name', 'role', 'curator')
    list_filter = ('role', 'curator')
    search_fields = ('name', 'username')
    ordering = ('name',)

    fieldsets = (
        (None, {'fields': ('username', 'password', 'password_link')}),
        ('Personal info', {'fields': ('name', 'role', 'curator')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'name', 'password', 'role', 'is_active', 'is_staff', 'is_superuser'),
        }),
    )

    readonly_fields = ['password_link']

    def password_link(self, obj):
        """Добавляем ссылку для смены пароля."""
        if obj.id:
            url = reverse('admin:auth_user_password_change', args=[obj.id])
            return format_html('<a href="{}">{}</a>', url, _('Сменить пароль'))
        return _("Пароль ещё не задан")
    password_link.short_description = "Изменить пароль"


# --------------------------------------
@admin.register(Course)
class CourseAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'description')
    list_filter = ('title',)
    inlines = [TopicInline]



# --------------------------------------
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    autocomplete_fields = ['user']

    date_hierarchy = 'enrolled_at'
    list_display = ('user_username', 'user_full_name', 'course_title', 'enrolled_at', 'refresh_enrolled_at_button', 'delete_button')
    list_filter = ('user', 'course', ('enrolled_at', DateFieldListFilter),)
    ordering = ['-enrolled_at', 'user__name']

    search_fields = ['user__username', 'user__name', 'course__title']

    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Юзернейм'

    def user_full_name(self, obj):
        return obj.user.name
    user_full_name.short_description = 'ФИО'

    def course_title(self, obj):
        return obj.course.title
    course_title.short_description = 'Название Курса'

    def refresh_enrolled_at_button(self, obj):
        url = reverse('admin:refresh_enrolled_at', args=[obj.id])
        return format_html('<a class="button" href="{}">Обновить</a>', url)

    refresh_enrolled_at_button.short_description = 'Обновить Enrolled At'
    refresh_enrolled_at_button.allow_tags = True

    def delete_button(self, obj):
        url = reverse('admin:delete_enrollment', args=[obj.id])
        return format_html('<a class="button" style="color:white; background-color: red;" href="{}">Удалить</a>', url)
    delete_button.short_description = 'Удалить'
    delete_button.allow_tags = True

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('refresh-enrolled-at/<int:pk>/', self.admin_site.admin_view(self.refresh_enrolled_at),
                 name='refresh_enrolled_at'),
            path('delete-enrollment/<int:pk>/', self.admin_site.admin_view(self.delete_enrollment),
                 name='delete_enrollment'),
        ]
        return custom_urls + urls

    def refresh_enrolled_at(self, request, pk):
        from .models import Enrollment
        try:
            enrollment = Enrollment.objects.get(pk=pk)
            enrollment.enrolled_at = now()
            enrollment.save()
            messages.success(request, f"Дата {enrollment.user.name} успешно обновлена на текущее время.")
        except Enrollment.DoesNotExist:
            messages.error(request, "Запись не найдена.")
        return redirect(request.META.get('HTTP_REFERER', 'admin:app_enrollment_changelist'))

    def delete_enrollment(self, request, pk):
        from .models import Enrollment
        try:
            enrollment = Enrollment.objects.get(pk=pk)
            enrollment.delete()
            messages.success(request, f"Запись для {enrollment.user.name} успешно удалена.")
        except Enrollment.DoesNotExist:
            messages.error(request, "Запись не найдена.")
        return redirect(request.META.get('HTTP_REFERER', 'admin:app_enrollment_changelist'))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":  # Поле user
            kwargs["queryset"] = User.objects.filter(role="student")  # Фильтруем только студентов
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# --------------------------------------
@admin.register(Topic)
class TopicAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title', 'course', 'order', 'video_url', 'video_title')
    list_filter = ('course',)
    inlines = [TestInline]



# --------------------------------------
@admin.register(Test)
class TestAdmin(nested_admin.NestedModelAdmin):
    inlines = [QuestionInline]
    list_display = ('topic',)
    list_filter = ('topic__course',)



# --------------------------------------
@admin.register(Question)
class QuestionAdmin(nested_admin.NestedModelAdmin):
    list_display = ('test', 'text',)
    list_filter = ('test__topic__course',)
    inlines = [AnswerInline]
    form = QuestionForm



# --------------------------------------
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'text', 'is_correct')
    list_filter = ('is_correct',)
    form = AnswerForm



# --------------------------------------
@admin.register(UserTestResult)
class UserTestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'score', 'passed', 'created_at')
    list_filter = ('test__topic__course', 'user', 'passed')



# --------------------------------------
@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    ordering = ['-created_at', 'name']
    list_display = ('name', 'phone', 'selected_pair', 'created_at')
    search_fields = ('name', 'phone', 'selected_pair')
    list_filter = ('selected_pair', ('created_at', DateFieldListFilter))

