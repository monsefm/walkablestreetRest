from control.models import WalkUser, Group, UserContext, WalkContext, Version, Data, Button, DataValue, DataImage, Country, State, City, GPSCity
from rest_framework import serializers
from haversine import haversine, Unit
from django.db.models import Count
import datetime
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.exceptions import AuthenticationFailed, NotFound, ValidationError
from control.utils import Util
from walkrest.settings import SUPPORT_TEAM
from django.shortcuts import render
from django.conf import settings
from django.template import loader
from django.core.mail import EmailMessage
from control.choices import (TABLE_NAME)


class WalkUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalkUser
        fields = ['id','username', 'email', 'password', 'celphone','date_joined', 'profile','country', 'countryCode', 'walkgroup']

    def create(self, validated_data):
        walkuser = WalkUser(**validated_data)
        walkuser.set_password(validated_data['password'])
        walkuser.save()
        return walkuser

    def update(self, instance, validated_data):
        update_user = super().update(instance,validated_data)
        update_user.set_password(validated_data['password'])
        update_user.save()
        return update_user


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = '__all__'


class UserContextSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    class Meta:
        model = UserContext
        fields = ['id', 'gender', 'ability','age', 'created_date','user','username']
    
    def get_username(self,obj):
        if obj.user:
            return obj.user.username
        else:
            return None


class WalkContextSerializer(serializers.ModelSerializer):
    duration_walk = serializers.SerializerMethodField() 
    distance = serializers.SerializerMethodField()
    dataset = serializers.SerializerMethodField()   
    cant_points = serializers.SerializerMethodField()
    #distance_new = serializers.SerializerMethodField()

    class Meta:
        model = WalkContext
        fields = ['id','user','decision','purpose','group_size','familiarity','date_start','latitude_start','longitude_start','gpsaccuracy_start','date_end','latitude_end','longitude_end','gpsaccuracy_end','version','weather_code','weather_codition','weather_text','weather_text','temperature','city', 'city_tableid', 'countryCode', 'postalCode','disable_date_auto_now', 'duration_walk', 'distance','distance_new','cant_points', 'dataset']
        read_only_fields = ['date_end']

    def get_duration_walk(self,obj):
        if obj.date_end and obj.date_start and obj.date_end > obj.date_start:     
            duration = datetime.datetime.strptime(datetime.datetime.strftime(obj.date_end,"%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(datetime.datetime.strftime(obj.date_start,"%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")         
            return str(duration)
        return 0

    '''
    def get_distance(self, obj):
        sections = list()
        list_a = list()
        list_b = list()
        total_distance = 0
        dataset = Data.objects.filter(walk_context=obj.id).order_by('id')
        
        if len(dataset)>0:
        
            if obj.latitude_start and obj.longitude_start and obj.latitude_end and obj.longitude_end:
                list_a.append(list([obj.latitude_start, obj.longitude_start]))
                list_b.append(list([dataset[0].latitude, dataset[0].longitude]))

            for i, point in enumerate(dataset, start=0):
                if i < len(dataset)-1:
                    list_a.append(list([point.latitude, point.longitude]))
                if i > 0:
                    list_b.append(list([point.latitude, point.longitude]))
        
            if obj.latitude_start and obj.longitude_start and obj.latitude_end and obj.longitude_end:        
                list_b.append(list([obj.latitude_end, obj.longitude_end]))
                list_a.append(list([dataset[len(dataset)-1].latitude, dataset[len(dataset)-1].longitude]))

            for p_start, p_end in zip(list_a, list_b):           
                sections.append({'start': p_start, 'end': p_end})
        
            for section in sections:
                total_distance = total_distance + haversine(section['start'], section['end'], unit='km')  
            
        return round(total_distance,4)
    '''
    def get_distance(self,obj):
        total_distance = 0
        dataset = Data.objects.filter(walk_context=obj.id).values('id','latitude','longitude').order_by('id')    
        
        if len(dataset)>0:
            if obj.latitude_start and obj.longitude_start and obj.latitude_end and obj.longitude_end:
                coords = [(obj.latitude_start, obj.longitude_start)] + [(p['latitude'], p['longitude']) for p in dataset] + [(obj.latitude_end, obj.longitude_end)]
                distancias = [haversine(coords[i - 1], coords[i], unit='km') for i in range(1, len(coords))]   
                total_distance = sum(distancias)

        return (total_distance)



    def get_dataset(self, obj):
        request = self.context.get('request') 
        dataset = Data.objects.filter(walk_context=obj)
        response = list()
        for x in dataset:
            icon_data = list() 
            data_value = DataValue.objects.filter(data=x.id)            

            for b in data_value:                
                button = Button.objects.get(pk=b.value.id)    
                icon_data.append({'id': b.value.id, 'id_datavalue': b.id, 'tag': button.tag, 'description': button.description, 'clasification': button.clasification, 'image': (request.build_absolute_uri(button.image.url) if button.image.name else None)})        

            response.append({
                'id': x.id, 'latitude': x.latitude, 'longitude': x.longitude, 'datetime': x.datetime, 'comments': x.comments, 'gpsaccuracy': x.gpsaccuracy, 'perception': x.perception, 'icon_data': icon_data 
            })
        return response
        #return [{'id': x.id, 'latitude': x.latitude, 'longitude': x.longitude, 'datetime': x.datetime, 'comments': x.comments, 'gpsaccuracy': x.gpsaccuracy, 'perception': x.perception } for x in dataset]
    

    def get_cant_points(self,obj):
        return len(Data.objects.filter(walk_context=obj))

    #def get_distance_new(self,obj):
    #    d =  round(obj.distance_new,3) if obj.distance_new else None
    #    return obj.distance_new


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = '__all__'


class DataSerializer(serializers.ModelSerializer):
    icon_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Data
        fields = ['id','latitude','longitude','datetime','datetime_new', 'comments','gpsaccuracy','perception','user','context','walk_context', 'icon_data']

    def get_icon_data(self,obj):
        request = self.context.get('request')
        icon_data = list()    
       
        data_value_full = DataValue.objects.filter(data=obj.id)
        #data_value = data_value_full.values('value').annotate(bcount = Count('value'))
        data_value = DataValue.objects.filter(data=obj.id).values('value').annotate(bcount = Count('value'))
        
        for b in data_value:
            button = Button.objects.get(pk=b['value'])
            current_data_value = data_value_full.filter(value=b['value']).first()
            icon_data.append({ 'id': b['value'], 'id_datavalue': current_data_value.id, 'bcount': b['bcount'], 'tag': button.tag, 'description': button.description, 'clasification': button.clasification, 'image': (request.build_absolute_uri(button.image.url) if button.image.name else None)})        

        return icon_data

class ButtonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Button
        fields = '__all__'


class DataValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataValue
        fields = '__all__'


class DataImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataImage
        fields = '__all__'


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = '__all__'


class StateSerializer(serializers.ModelSerializer):
    country_code = serializers.SerializerMethodField() 
    country_name = serializers.SerializerMethodField()
    class Meta:
        model = State
        fields = ['id','name','slug','country','country_code','country_name','state_code','state_type','latitude','longitude']
    
    def get_country_code(self,obj):  
        return obj.country.iso2
    
    def get_country_name(self,obj):  
        return obj.country.name


class CitySerializer(serializers.ModelSerializer):
    country_code = serializers.SerializerMethodField() 
    country_name = serializers.SerializerMethodField()
    state_code = serializers.SerializerMethodField() 
    state_name = serializers.SerializerMethodField()
    class Meta:
        model = City
        fields = ['id','name','slug','country','country_code','country_name','state','state_code','state_name','latitude','longitude','wikiDataId', 'postalCode']

    def get_country_code(self,obj):  
        return obj.country.iso2
    
    def get_country_name(self,obj):  
        return obj.country.name
    
    def get_state_code(self,obj):  
        return obj.state.state_code
    
    def get_state_name(self,obj):  
        return obj.state.name


class GPSCitySerializer(serializers.ModelSerializer):
    city_name = serializers.SerializerMethodField()
    city_slug = serializers.SerializerMethodField()
    class Meta:
        model = GPSCity
        fields = ['id', 'name','city','city_name','city_slug']

    def get_city_name(self,obj):
        return obj.city.name

    def get_city_slug(self,obj):
        return obj.city.slug


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    default_error_message = {
        'bad_token': ('Token is expired or invalid')
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs
    def save(self, **kwargs):
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('bad_token')


class LoginSerializer(TokenObtainPairSerializer):   
    pass


class LoginwebSerializer(TokenObtainPairSerializer):
    model = WalkUser
    profile = serializers.CharField(max_length=12, required=True)
    pass


class ChangePasswordSerializer(serializers.Serializer):
    model = WalkUser
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    redirect_url = serializers.CharField(max_length=500, required=False)

    class Meta:
        fields = ['username']


class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=True, write_only=True)
    token = serializers.CharField(required=True, min_length=1, write_only=True)
    uidb64 = serializers.CharField(required=True, min_length=1, write_only=True)

    class Meta:
        fields = ['password', 'token', 'uidb64']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            token = attrs.get('token')
            uidb64 = attrs.get('uidb64')

            id = smart_str(urlsafe_base64_decode(uidb64))
            user = WalkUser.objects.get(id=int(id))
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed('The reset link is invalid', 401)

            user.set_password(password)
            user.save()

            #Original
            #email_body = 'Dear ' +user.username+ '\n \nYour password has been changed!\n \nThanks for using our site! \n \n'+SUPPORT_TEAM
            #data = {    'email_body': email_body,
            #            'to_email': user.email,
            #            'email_subject': '[WalkableStreet] Your password has been successfully changed!'
            #        }
            #Util.send_mail(data)
            
            #NEW
            data_email = {
                    'title': "Password changed successfully!",
                    'link': None,
                    'greeting': 'Hi ' + user.username + '!',
                    'text': 'Your password has been changed successfully.\nPlease use your new password to log in.',
                    'support_team': SUPPORT_TEAM,
                    'opt': 2,
            }
            template = loader.get_template('email/email.html')
            email_menssage = template.render(data_email)

            my_email2 = EmailMessage('[WalkableStreet] Your password has been successfully changed!',email_menssage,settings.DEFAULT_FROM_EMAIL,[user.email])
            my_email2.content_subtype = 'html'
            my_email2.send()

            return (user)
        except Exception as e:
            raise AuthenticationFailed('The reset link is invalid', 401)

        return super().validate(attrs)

#Resp
class DeleteAllInfoSerializer(serializers.Serializer):
    user = serializers.IntegerField(required=True)
    option = serializers.CharField(required=True)

    class Meta:
        fields = ['user', 'option']


class DeleteUserInfoSerializer(serializers.Serializer):
    user = serializers.IntegerField(required=True)
    option = serializers.CharField(required=True)
    keep_data = serializers.CharField(required=True)
    feedback = serializers.CharField(allow_null=True, allow_blank=True)

    class Meta:
        fields = ['user', 'option', 'keep_data','feedback']


class DeleteDataWalkSerializer(serializers.Serializer):
    data = serializers.IntegerField(required = True)

    class Meta:
        fields = ['data']


class FinishWalkSerializer(serializers.Serializer):
    model = WalkContext
    id = serializers.IntegerField(required = True)
    latitude_end = serializers.DecimalField(max_digits=16, decimal_places=12,required = True)
    longitude_end = serializers.DecimalField(max_digits=16, decimal_places=12, required = True)
    gpsaccuracy_end = serializers.DecimalField(max_digits=16, decimal_places=12, required = True)

    class Meta:
        fields = ['id', 'latitude_end', 'longitude_end', 'gpsaccuracy_end']

    def validate(self, attrs):
        id = attrs.get('id')
        latitude_end = attrs.get('latitude_end')
        longitude_end = attrs.get('longitude_end')
        gpsaccuracy_end = attrs.get('gpsaccuracy_end')

        if WalkContext.objects.filter(id=id).exists():
            try:
                walk_object = WalkContext.objects.get(id=id)
                walk_object.latitude_end = latitude_end
                walk_object.longitude_end = longitude_end
                walk_object.gpsaccuracy_end = gpsaccuracy_end
                walk_object.save()

                return walk_object
                #super().validate(attrs)
            except Exception as e:
                raise ValidationError('Error in operation', 400)
        raise NotFound('Walk no found',404)


class InsertDataSerializer(serializers.Serializer):
    table = serializers.ChoiceField(choices=TABLE_NAME, required = True)

    class Meta:
        fields = ['table']
