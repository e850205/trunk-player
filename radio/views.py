import os
import re
import json
import mimetypes
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, FileResponse, HttpResponseBadRequest
from django.views.generic import ListView
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.contrib.auth import authenticate, login
from django.conf import settings
from django.views.generic import ListView, UpdateView
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ImproperlyConfigured
from .models import *
from rest_framework import viewsets, generics
from rest_framework.exceptions import NotFound
from .serializers import TransmissionSerializer, TalkGroupSerializer, ScanListSerializer, MenuScanListSerializer, MenuTalkGroupListSerializer, MessageSerializer
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import mail_admins, send_mail

from django.contrib import messages
import logging

from .forms import *

logger = logging.getLogger(__name__)


def check_anonymous(decorator):
    """
    Decarator used to see if we allow anonymous access
    """
    anonymous = getattr(settings, 'ALLOW_ANONYMOUS', True)
    return decorator if not anonymous else lambda x: x


@login_required
def userScanList(request):
    template = 'radio/userscanlist.html'
    if request.method == "POST":
        form = UserScanForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            tgs = form.cleaned_data['talkgroups']
            sl = ScanList()
            sl.created_by = request.user
            sl.name = name
            sl.description = name
            sl.save()
            sl.talkgroups.add(*tgs)
            return redirect('user_profile')
    else:
        form = UserScanForm()
    return render(request, template, {'form': form})

@login_required
def userProfile(request):
    template = 'radio/profile.html'
    if request.method == "POST":
        profile_form = UserForm(request.POST, instance=request.user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Profile updated')
            return redirect('user_profile')
    else:
        profile_form = UserForm(instance=request.user)
    profile = Profile.objects.get(user=request.user)
    scan_lists = ScanList.objects.filter(created_by=request.user)
    return render(request, template, {'profile_form': profile_form, 'profile': profile, 'scan_lists': scan_lists} )

def agencyList(request):
    template = 'radio/agency_list.html'
    query_data = Agency.objects.exclude(short='_DEF_').order_by('name')

    return render(request, template, {'agency': query_data})


def cityListView(request):
    template = 'radio/city_list.html'
    query_data = City.objects.filter(visible=True)

    return render(request, template, {'cities': query_data})


def cityDetailView(request, slug):
    template = 'radio/city_detail.html'
    query_data = get_object_or_404(City, slug=slug)

    return render(request, template, {'object': query_data})
    

def TransDetailView(request, slug):
    template = 'radio/transmission_detail.html'
    query_data = Transmission.objects.filter(slug=slug)
    restricted, new_query = restrict_talkgroups(request, query_data)
    if not new_query:
        raise Http404
    return render(request, template, {'object': new_query[0]})

def transDownloadView(request, slug):
    import requests
    query_data = Transmission.objects.filter(slug=slug)
    restricted, new_query = restrict_talkgroups(request, query_data)
    if not new_query: raise Http404

    trans = new_query[0]
    file_type = trans.audio_file_type or 'mp3'
    audio_type = 'audio/mp4' if file_type == 'm4a' else 'audio/mpeg'
    start_time = timezone.localtime(trans.start_datetime).strftime('%Y%m%d_%H%M%S')
    filename = '{}_{}.{}'.format(start_time, trans.talkgroup_info.slug, file_type)
    audio_name = '{}.{}'.format(trans.audio_file, file_type)

    # Serve the file straight off the disk when we have it
    media_root = os.path.realpath(settings.MEDIA_ROOT)
    local_file = os.path.realpath(os.path.join(media_root, trans.audio_file_url_path.lstrip('/'), audio_name))
    if local_file.startswith(media_root + os.sep) and os.path.isfile(local_file):
        return FileResponse(open(local_file, 'rb'), as_attachment=True, filename=filename, content_type=audio_type)

    # Otherwise fetch it from where the browser would play it from (S3, ...)
    audio_url = trans.audio_url + audio_name
    if audio_url.startswith('//'):
        url = 'https:' + audio_url
    elif audio_url.startswith(('http://', 'https://')):
        url = audio_url
    else:
        url = request.build_absolute_uri(audio_url)
    try:
        data = requests.get(url, timeout=30)
        data.raise_for_status()
    except requests.RequestException as e:
        logger.error('Unable to download audio file %s: %s', url, e)
        raise Http404

    response = HttpResponse(data.content, content_type=audio_type)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return response


class TransmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Placeholder, use the /api_v1/tg/ /api_v1/scan/ ... endpoints
    """
    queryset = Transmission.objects.none()
    serializer_class = TransmissionSerializer

    def get_serializer_context(self):
        return {'request': self.request}


class ScanListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScanList.objects.all().prefetch_related('talkgroups')
    serializer_class = ScanListSerializer


class TalkGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that lists the talkgroups the user can see
    """
    serializer_class = TalkGroupSerializer

    def get_queryset(self):
        if settings.ACCESS_TG_RESTRICT:
            tg = allowed_tg_list(self.request.user)
        else:
            tg = TalkGroup.objects.filter(public=True)
        return tg



# Open to anyone
def Generic(request, page_name):
    template = 'radio/generic.html'
    query_data = get_object_or_404(WebHtml, name=page_name)
    return render(request, template, {'html_object': query_data})

def get_user_profile(user):
    if user.is_authenticated:
        user_profile = Profile.objects.get(user=user)
    else:
        try:
            anon_user = User.objects.get(username='ANONYMOUS_USER')
        except User.DoesNotExist:
            raise ImproperlyConfigured('ANONYMOUS_USER is missing from User table, was "./manage.py migrations" not run?')
        user_profile = Profile.objects.get(user=anon_user)
    return user_profile



def allowed_tg_list(user):
    user_profile = get_user_profile(user)
    tg_list = None
    for group in user_profile.talkgroup_access.all():
       if tg_list is None:
           tg_list = group.talkgroups.all()
       else:
           tg_list = tg_list | group.talkgroups.all()
    if tg_list:
        tg_list = tg_list.distinct()
    else:
        # Set blank talkgroup queryset
        tg_list = TalkGroup.objects.none()
    return tg_list


def restrict_talkgroups(request, query_data):
    ''' Checks to make sure the user can view
        each of the talkgroups in the query_data
        returns ( was_restricted, new query_data )
    '''
    if not settings.ACCESS_TG_RESTRICT:
        return False, query_data
    tg_list = allowed_tg_list(request.user)
    query_data = query_data.filter(talkgroup_info__in=tg_list)
    return None, query_data
    

class ScanViewSet(generics.ListAPIView):
    serializer_class = TransmissionSerializer

    def get_queryset(self):
        scanlist = self.kwargs['filter_val']
        try:
            sl = ScanList.objects.get(slug__iexact=scanlist)
        except ScanList.DoesNotExist:
            if scanlist == 'default':
                tg = TalkGroup.objects.all()
            else:
                raise NotFound('Scan list {} does not exist'.format(scanlist))
        else:
            tg = sl.talkgroups.all()
        rc_data = Transmission.objects.filter(talkgroup_info__in=tg).prefetch_related('units').prefetch_related('talkgroup_info')
        restricted, rc_data = restrict_talkgroups(self.request, rc_data) 
        return rc_data


class IncViewSet(generics.ListAPIView):
    serializer_class = TransmissionSerializer

    def get_queryset(self):
        inc = self.kwargs['filter_val']
        try:
            if self.request.user.is_staff:
                rc_data = Incident.objects.get(slug__iexact=inc).transmissions.all()
            else:
                rc_data = Incident.objects.get(slug__iexact=inc, public=True).transmissions.all()
        except Incident.DoesNotExist:
            raise NotFound('Incident {} does not exist'.format(inc))
        restricted, rc_data = restrict_talkgroups(self.request, rc_data)
        return rc_data


class MessagePopUpViewSet(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        return MessagePopUp.objects.filter(active=True)


class TalkGroupFilterViewSet(generics.ListAPIView):
    serializer_class = TransmissionSerializer

    def get_queryset(self):
        tg_var = self.kwargs['filter_val']
        search_tgs = re.split('[\+]', tg_var)
        q = Q()
        for stg in search_tgs:
            q |= Q(common_name__iexact=stg)
            q |= Q(slug__iexact=stg)
        tg = TalkGroup.objects.filter(q)
        rc_data = Transmission.objects.filter(talkgroup_info__in=tg).prefetch_related('units')
        restricted, rc_data = restrict_talkgroups(self.request, rc_data)
        return rc_data


class UnitFilterViewSet(generics.ListAPIView):
    serializer_class = TransmissionSerializer

    def get_queryset(self):
        unit_var = self.kwargs['filter_val']
        search_unit = re.split('[\+]', unit_var)
        q = Q()
        for s_unit in search_unit:
            q |= Q(slug__iexact=s_unit)
        units = Unit.objects.filter(q)
        rc_data = Transmission.objects.filter(units__in=units).filter(talkgroup_info__public=True).prefetch_related('units').distinct()
        restricted, rc_data = restrict_talkgroups(self.request, rc_data)
        return rc_data


class TalkGroupList(ListView):
    model = TalkGroup
    context_object_name = 'talkgroups'
    template_name = 'radio/talkgroup_list.html'

    #queryset = TalkGroup.objects.filter(public=True)
    def get_queryset(self):
        if settings.ACCESS_TG_RESTRICT:
            tg = allowed_tg_list(self.request.user)
        else:
            tg = TalkGroup.objects.filter(public=True)
        if self.request.GET.get('recent', None):
            tg = tg.order_by('-recent_usage', '-last_transmission')
        return tg



@csrf_protect
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password1'],
            email=form.cleaned_data['email']
            )
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            new_user = authenticate(username=username, password=password)
            if new_user is not None:
                if new_user.is_active:
                    login(request, new_user)
                    return HttpResponseRedirect('/scan/default/')
                else:
                    # this would be weird to get here
                    return HttpResponseRedirect('/register/success/')
            else:
                return HttpResponseRedirect('/register/success/')
    else:
        form = RegistrationForm()
 
    return render(
    request,
    'registration/register.html',
    { 'form': form },
    )

def register_success(request):
    return render(
    request,
    'registration/success.html', {},
    )


class MenuScanListViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MenuScanListSerializer
    queryset = MenuScanList.objects.all()


class MenuTalkGroupListViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MenuTalkGroupListSerializer
    queryset = MenuTalkGroupList.objects.all()


class UnitUpdateView(PermissionRequiredMixin, UpdateView):
    model = Unit
    form_class = UnitEditForm
    success_url = '/unitupdategood/'
    permission_required = ('radio.change_unit')

    def form_valid(self, form):
        try:
            update_unit_email = SiteOption.objects.get(name='SEND_ADMIN_EMAIL_ON_UNIT_NAME')
            if update_unit_email.value_boolean_or_string() == True:
                Unit = form.save()
                send_mail(
                  'Unit ID Change',
                  'User {} updated unit ID {} Now {}'.format(self.request.user, Unit.dec_id, Unit.description),
                  settings.SERVER_EMAIL,
                  [ mail for name, mail in settings.ADMINS],
                  fail_silently=False,
                )
        except SiteOption.DoesNotExist:
            pass
        return super().form_valid(form)


def ScanDetailsList(request, name):
    template = 'radio/scandetaillist.html'
    scanlist = None
    try:
        scanlist = ScanList.objects.get(name=name)
    except ScanList.DoesNotExist:
        if name == 'default':
            query_data = TalkGroup.objects.all()
        else:
            raise Http404
    if scanlist:
        query_data = scanlist.talkgroups.all()
    return render(request, template, {'object_list': query_data, 'scanlist': scanlist, 'request': request})


def incident(request, inc_slug):
    template = 'radio/player_main.html'
    try:
        if request.user.is_staff:
            inc = Incident.objects.get(slug=inc_slug)
        else:
            inc = Incident.objects.get(slug=inc_slug, public=True)
    except Incident.DoesNotExist:
        raise Http404
    return render(request, template, {'inc':inc})


@csrf_exempt
def import_transmission(request):
    """Add a new transmission, used by trunk-recorder upload scripts

    POST a json body, see docs/config_local.rst for the fields
    """
    if request.method != "POST":
        return HttpResponse(status=405)
    settings_auth_token = getattr(settings, 'ADD_TRANS_AUTH_TOKEN', None)
    if not settings_auth_token or settings_auth_token == '7cf5857c61284': # Check is default is still set
        return HttpResponse('Unauthorized, ADD_TRANS_AUTH_TOKEN is not set on the server (or is still the default).', status=401)
    try:
        request_data = json.loads(request.body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        return HttpResponseBadRequest('Body must be json')
    if not isinstance(request_data, dict):
        return HttpResponseBadRequest('Body must be a json object')
    auth_token = request_data.get('auth_token')
    if auth_token != settings_auth_token:
        return HttpResponse('Unauthorized, check auth_token', status=401)

    for field in ('system', 'source', 'talkgroup', 'start_time', 'audio_filename'):
        if request_data.get(field) in (None, ''):
            return HttpResponseBadRequest('{} is missing'.format(field))
    try:
        tg_dec = int(request_data['talkgroup'])
        epoc_ts = float(request_data['start_time'])
        epoc_end_ts = float(request_data.get('stop_time') or epoc_ts)
        freq = int(float(request_data.get('freq') or 0))
        play_length = float(request_data.get('audio_file_play_length', epoc_end_ts - epoc_ts))
        units = [unit['src'] if isinstance(unit, dict) else unit for unit in request_data.get('srcList') or []]
        units = [int(unit) for unit in units]
    except (TypeError, ValueError, KeyError) as e:
        return HttpResponseBadRequest('Invalid value: {}'.format(e))

    system, created = System.objects.get_or_create(name=request_data['system'])
    source, created = Source.objects.get_or_create(description=request_data['source'])
    try:
        tg = TalkGroup.objects.get(dec_id=tg_dec, system=system)
    except TalkGroup.DoesNotExist:
        name = '#{}'.format(tg_dec)
        tg = TalkGroup.objects.create(dec_id=tg_dec, system=system, alpha_tag=name, description='TalkGroup {}'.format(name))

    t = Transmission(start_datetime=datetime.fromtimestamp(epoc_ts, dt_timezone.utc),
                     end_datetime=datetime.fromtimestamp(epoc_end_ts, dt_timezone.utc),
                     audio_file=request_data['audio_filename'],
                     talkgroup=tg_dec,
                     talkgroup_info=tg,
                     freq=freq,
                     emergency=bool(request_data.get('emergency', False)),
                     source=source,
                     system=system,
                     audio_file_url_path=request_data.get('audio_file_url_path') or '/',
                     audio_file_type=request_data.get('audio_file_type') or 'mp3',
                     play_length=play_length,
                     has_audio=request_data.get('has_audio', True),
                   )
    t.save()

    for count, trans_unit in enumerate(units):
        u, created = Unit.objects.get_or_create(dec_id=trans_unit, system=t.system)
        TranmissionUnit.objects.create(transmission=t, unit=u, order=count)

    return HttpResponse("Transmission added [{}]".format(t.pk))
