from django.http import Http404
from django.shortcuts import render
from django.views import View
from . import models


def demo(request):
    courses = models.Course.objects.only('title', 'cover_url','teacher__positional_title','teacher__name').filter(is_delete=False)
    return render(request, 'course/course.html', locals())


class CourseDetail(View):
    def get(self, request, course_id):
        course = models.Course.objects.only('title', 'cover_url', 'video_url', 'profile', 'outline', 'teacher__name',
                                            'teacher__profile', 'teacher__positional_title',
                                            'teacher__avatar_url').select_related('teacher').filter(is_delete=False,
                                                                                                    id=course_id).first()
        if course:
            return render(request, 'course/course_detail.html', locals())
        else:
            raise Http404('page not found')
