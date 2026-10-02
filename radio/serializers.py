from django.contrib.auth.models import User, Group
from rest_framework import serializers
from .models import Transmission, TalkGroup, Unit, ScanList, MenuScanList, MenuTalkGroupList, MessagePopUp
from rest_framework.fields import CurrentUserDefault, SerializerMethodField


class TalkGroupSerializer(serializers.HyperlinkedModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name="talkgroups-detail")
    # Service type name (Fire, Law, EMS, ...), the player colours calls by it
    service = SerializerMethodField()

    class Meta:
        model = TalkGroup
        fields = ('url', 'dec_id', 'alpha_tag', 'description', 'slug', 'service')

    def get_service(self, obj):
        return obj._service_type.name if obj._service_type_id else None

class UnitListField(serializers.RelatedField):

    def to_representation(self, value):
        return { "pk": value.pk, "dec_id": value.dec_id, "description": value.description }

class TransmissionSerializer(serializers.ModelSerializer):
    talkgroup_info = TalkGroupSerializer()
    # Just the file name, the player adds audio_url and the extension
    audio_file = SerializerMethodField()
    units = UnitListField(many=True, read_only=True)

    class Meta:
        model = Transmission
        fields = ('pk', 'url', 'start_datetime', 'local_start_datetime', 'audio_file', 'talkgroup', 'talkgroup_info', 'freq', 'emergency', 'units', 'play_length', 'print_play_length', 'slug', 'freq_mhz', 'tg_name', 'source', 'audio_url', 'system', 'audio_file_type')

    def get_audio_file(self, obj):
        return str(obj.audio_file)

class ScanListSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ScanList
        fields = ('pk', 'name', 'description', 'slug')

class MenuScanListSerializer(serializers.ModelSerializer):

    class Meta:
        model = MenuScanList
        fields = ('pk', 'name', 'scan_name', 'scan_description', 'scan_slug', 'section')

class MenuTalkGroupListSerializer(serializers.ModelSerializer):

    class Meta:
        model = MenuTalkGroupList
        fields = ('pk', 'name', 'tg_name', 'tg_slug')

class MessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = MessagePopUp
        fields = ('pk', 'mesg_type', 'mesg_html' )
