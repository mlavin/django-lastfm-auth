from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponse
from django.test import TestCase


def test_404(request):
    return HttpResponseNotFound()


def test_500(request):
    return HttpResponseServerError()


def default(request):
    return HttpResponse('Default Redirect')


def new(request):
    return HttpResponse('New User Redirect')


def error(request):
    return HttpResponse('Error Redirect')
