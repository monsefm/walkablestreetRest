from django.shortcuts import render, redirect
from control.models import WalkUser, Group, UserContext, WalkContext, Version, Data, Button, DataValue, DataImage, Country, State, City, GPSCity
from rest_framework import viewsets, filters, generics, permissions
from rest_framework import status as Response_status
from rest_framework.response import Response
from control.serializers import ButtonSerializer, WalkUserSerializer, GroupSerializer, UserContextSerializer, WalkContextSerializer, VersionSerializer, DataSerializer, ButtonSerializer, DataValueSerializer, DataImageSerializer, CountrySerializer, StateSerializer, CitySerializer, GPSCitySerializer, LogoutSerializer, LoginSerializer, LoginwebSerializer, ChangePasswordSerializer, ResetPasswordSerializer,SetNewPasswordSerializer, DeleteAllInfoSerializer, DeleteUserInfoSerializer, DeleteDataWalkSerializer, FinishWalkSerializer, InsertDataSerializer
from django.db import models
import django_filters.rest_framework
from django.db.models import Q, Sum, F, Count, Value, Case, When, DecimalField
from django.db.models.functions import ExtractMonth, TruncDate, ExtractYear, Lower, Concat, Coalesce, Cast
from django.http import HttpResponse, JsonResponse, HttpResponsePermanentRedirect
import datetime
import calendar
from haversine import haversine, Unit
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
import csv
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from walkrest.settings import MAIL, SUPPORT_TEAM, ADMIN_EMAIL, BIGDATA_KEY
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import authenticate
from django.utils.encoding import smart_str, smart_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from control.utils import Util
from django.conf import settings
from django.template import loader
from django.core.mail import EmailMessage
from django.contrib import messages
from django.utils.text import slugify

from rest_framework.decorators import api_view
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.generators import OpenAPISchemaGenerator
import os
import requests
import json

from functools import partial
from geopy.geocoders import Nominatim
#from django.contrib.gis.geos import Polygon, Point
#from shapely.geometry import Point, Polygon


#Geopy configuration
geolocator = Nominatim(user_agent="control")
reverse_2 = partial(geolocator.reverse, language="en", addressdetails=True)


def getaddress(lat, lng, opt):
    city = ''           
    coordinates = str(lat) + ',' +str(lng)         
    
    try:          
        location = reverse_2(coordinates) 
        print(location)
        display_city = location.raw['display_name'].split(',')           
        city_aux = [dc for dc in display_city if (dc.lower()).find('city') != -1 ]          
        
        if opt == 'city':        
            if not city_aux:
                dict_key = location.raw['address'].keys()
                if 'city' in dict_key:
                    city = location.raw['address']['city'] 
                elif 'town' in dict_key: 
                    city = location.raw['address']['town']            
                else:
                    #support api                 
                    resp_bigdata = requests.get('https://api.bigdatacloud.net/data/reverse-geocode?latitude='+str(lat)+'&longitude='+str(lng)+'&localityLanguage=en&key='+BIGDATA_KEY)
                    resp_city = resp_bigdata.json()
                    city = resp_city['city']
            else:
                city = (city_aux[0].replace(' City','')).lstrip()  

        data = dict({
            'place_id': location.raw['place_id'],
            'lat': location.raw['lat'],
            'lon': location.raw['lon'],
            'display_name': location.raw['display_name'],
            'display_city': city,
            'address': dict(location.raw['address'])
        })
        
    except:
        #support api                 
        #resp_bigdata = requests.get('https://api.bigdatacloud.net/data/reverse-geocode?latitude='+str(lat)+'&longitude='+str(lng)+'&localityLanguage=en&key='+BIGDATA_KEY)
        #data = resp_bigdata.json()
        #dict_key = data.keys()
        #if not 'countryCode' in dict_key:
        data = str("Error")    
    return data


#Tags Documentation
class CustomOpenAPISchemaGenerator(OpenAPISchemaGenerator):
  def get_schema(self, request=None, public=False):

    swagger = super().get_schema(request, public)
    swagger.tags = [
        { "name": "api", "description": "Everything about authentication, get tokens, login in and login out for app and web site" },
        { "name": "button", "description": "Everything about button (icons)" },
        { "name": "data", "description": "Everything about point (data)" },
        { "name": "dataimage", "description": "Everything about image(s) attached to point (data)" },
        { "name": "datavalue", "description": "Everything about relation between a data and button(s) value" },
        { "name": "group", "description": "Everything about user groups" },
        { "name": "others", "description": "Different functions for validation, get information or do important tasks" },
        { "name": "password", "description": "Functions focus in work with password" },
        { "name": "reports", "description": "Everything about stats in the web site or app" },
        { "name": "user", "description": "Everything about your users. Important note: The search term is for put user id and username" },
        { "name": "usercontext", "description": "Everything about user context" },
        { "name": "version", "description": "Everything about app version and button version" },
        { "name": "walkcontext", "description": "Everything about walk context" },

    ]

    return swagger


#New permission for allow post
class IsPostOrIsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        # allow all POST requests
        if request.method == 'POST':
            return True
        return request.user and request.user.is_authenticated

#Redirect function
class CustomRedirect(HttpResponsePermanentRedirect):
    allowed_schemes = [os.environ.get('APP_SCHEME'), 'http', 'https']


class WalkUserViewSet(viewsets.ModelViewSet):
    permission_classes = (IsPostOrIsAuthenticated,)
   # authentication_classes = (JWTAuthentication,)
    queryset = WalkUser.objects.all()
    serializer_class = WalkUserSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter]  
    search_fields = ['id','username']

    def get_queryset(self):
        queryset = WalkUser.objects.all()
        username = self.request.query_params.get('username')
        user = self.request.query_params.get('user')        
        if username:
            queryset = queryset.filter(username=username)
        if user:
            queryset = queryset.filter(id=int(user))
        return queryset


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter]


class UserContextViewSet(viewsets.ModelViewSet):
    #swagger manual paramenters assignment
    username = openapi.Parameter('username', openapi.IN_QUERY, "Insert username", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)
    user = openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER)   
      
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,) 
    queryset = UserContext.objects.all()
    serializer_class = UserContextSerializer

    def get_queryset(self):
        queryset = UserContext.objects.all()
        username = self.request.query_params.get('username')
        user = self.request.query_params.get('user')
        if username or user:
            if username:
                user_object = WalkUser.objects.filter(username=username)
                if len(user_object)>0:
                    queryset = queryset.filter(user=user_object[0].id).order_by('created_date','-id')
                else:
                    queryset = None
            if user:
                queryset = queryset.filter(user=user).order_by('created_date','-id')
        return queryset

    @swagger_auto_schema(operation_description="## Parameter filters:\n- **username** \n- **user id** \n \n**You can use username or user id or none with the other filters**",
    manual_parameters=[username,user])
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserContextSerializer(queryset, many=True)
        return Response(serializer.data)


class WalkContextViewSet(viewsets.ModelViewSet):
    #swagger manual paramenters assignment
    username = openapi.Parameter('username', openapi.IN_QUERY, "Insert username", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)
    user = openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER)
    
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    queryset = WalkContext.objects.all().order_by('id')
    serializer_class = WalkContextSerializer  

    def get_queryset(self):
        queryset = WalkContext.objects.prefetch_related().all().order_by('id')
        username = self.request.query_params.get('username')
        user = self.request.query_params.get('user')
        if username:
            user_object = WalkUser.objects.filter(username=username)
            if (len(user_object)>0):
                queryset = queryset.filter(user=user_object[0].id).order_by('id')
            else:
                queryset = None  
        if user:
            queryset = queryset.filter(user=user).order_by('id')
        return queryset
    
    def get_serializer_context(self):
        context = super(WalkContextViewSet, self).get_serializer_context()
        context.update({"request": self.request})
        return context

    @swagger_auto_schema(operation_description="## Parameter filters:\n- **username** \n- **user id** \n \n**You can use username or user id or none with the other filters**",
    manual_parameters=[username,user])
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = WalkContextSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class VersionViewSet(viewsets.ModelViewSet):
    #swagger manual paramenters assignment
    country = openapi.Parameter('country', openapi.IN_QUERY, "Insert country", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)
    
    queryset = Version.objects.all()
    serializer_class = VersionSerializer    

    def get_queryset(self):
        queryset = Version.objects.all()
        country = self.request.query_params.get('country')
        if country:
            queryset = queryset.filter(country=country).order_by('-id')    
        return queryset

    @swagger_auto_schema(operation_description="## Parameter filters:\n- **country name**",
    manual_parameters=[country])
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = VersionSerializer(queryset, many=True)
        return Response(serializer.data)


class DataViewSet(viewsets.ModelViewSet):
    #swagger manual paramenters assignment  
    username = openapi.Parameter('username', openapi.IN_QUERY, "Insert username", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)
    user = openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER)
    walkcontext = openapi.Parameter('walkcontext', openapi.IN_QUERY, "Insert walk id", type=openapi.TYPE_INTEGER)   
    
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    queryset = Data.objects.all()
    serializer_class = DataSerializer

    def get_queryset(self):
        queryset = Data.objects.all()
        walkcontext = self.request.query_params.get('walkcontext')
        username = self.request.query_params.get('username')
        user = self.request.query_params.get('user')
        if walkcontext:
            queryset = queryset.filter(walk_context=walkcontext).order_by('-id')
        if username:
            user_object = WalkUser.objects.filter(username=username)
            if(len(user_object)>0):
                queryset = queryset.filter(user=user_object[0].id).order_by('-walk_context','-id',)
        if user:
            queryset = queryset.filter(user=int(user)).order_by('-walk_context','-id')
        return queryset

    def get_serializer_context(self):
        context = super(DataViewSet, self).get_serializer_context()
        context.update({"request": self.request})
        return context

    @swagger_auto_schema(operation_description="## Parameter filters:\n- **username** \n- **user id** \n - **walk context = walk id** \n \n**You can use username or user id or none with the other filters**",
    manual_parameters=[username,user,walkcontext])
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()       
        serializer = DataSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)  


class ButtonViewSet(viewsets.ModelViewSet):
    #swagger manual paramenters assignment
    clasification = openapi.Parameter('clasification', openapi.IN_QUERY, "Insert clasification", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)
    country = openapi.Parameter('country', openapi.IN_QUERY, "Insert country", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)
    
    queryset = Button.objects.all()
    serializer_class = ButtonSerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend,filters.SearchFilter]
    lookup_field = 'clasification'

    def get_queryset(self):
        queryset = Button.objects.all()
        clasification = self.request.query_params.get('clasification')
        country = self.request.query_params.get('country')
        if clasification:
            queryset =  queryset.filter(clasification=clasification)
        if country:
            version_object = Version.objects.filter(country=country).order_by('-id')
            if(len(version_object)>0):
                queryset = queryset.filter(version=int(version_object[0].id))
        return queryset

    @swagger_auto_schema(operation_description="## Parameter filters:\n- **clasification** \n- **country name** \n - **walk context = walk id** \n \n**The search term can be used for clasification**",
    manual_parameters=[clasification,country])
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = ButtonSerializer(queryset, many=True)
        return Response(serializer.data)


class DataValueViewSet(viewsets.ModelViewSet):
    #swagger manual paramenters assignment
    data = openapi.Parameter('data', openapi.IN_QUERY, "Insert data id", type=openapi.TYPE_INTEGER)
    value = openapi.Parameter('value', openapi.IN_QUERY, "Insert value id", type=openapi.TYPE_INTEGER)
    queryset = DataValue.objects.all()
    serializer_class = DataValueSerializer

    def get_queryset(self):
        queryset = DataValue.objects.all()
        data = self.request.query_params.get('data')
        value = self.request.query_params.get('value')
        if data:
            queryset = queryset.filter(data=data)
        if value:
            queryset = queryset.filter(value=value)
        return queryset

    @swagger_auto_schema(operation_description="## Parameter filters:\n- **id data** \n- **id value** (It is the id button)",
    manual_parameters=[data,value])
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = DataValueSerializer(queryset, many=True)
        return Response(serializer.data)


class DataImageViewSet(viewsets.ModelViewSet):
    queryset = DataImage.objects.all()
    serializer_class = DataImageSerializer


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = Country.objects.all()
        iso2 = self.request.query_params.get('iso2')

        if iso2:
            iso2_upper = iso2.upper()
            queryset = queryset.filter(iso2=iso2_upper)
        return queryset


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer

    def get_queryset(self):
        queryset = State.objects.all().order_by('slug')
        country_code = self.request.query_params.get('country_code')
        state_code = self.request.query_params.get('state_code')
        slug = self.request.query_params.get('slug')

        if country_code:
            country_code = country_code.upper()
            country = Country.objects.get(Q(iso2=country_code)| Q(iso3=country_code))
            if country:
                queryset = queryset.filter(country=country)
        if state_code:
            state_code = state_code.upper()
            state = State.objects.filter(state_code = state_code)
            if len(state) > 0:
                queryset = queryset.filter(state__in=state)
        if slug:
            queryset = queryset.filter(slug=slug)
        return queryset


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer

    def get_queryset(self):
        queryset = City.objects.all().order_by('country','slug')
        country_code = self.request.query_params.get('country_code')
        state_code = self.request.query_params.get('state_code')
        slug = self.request.query_params.get('slug')
        
        if country_code:
            country_code = country_code.upper()
            country = Country.objects.get(Q(iso2=country_code)| Q(iso3=country_code))                       
            if country:                
                queryset = queryset.filter(country=country)  
        if state_code:
            state_code = state_code.upper()  
            state = State.objects.filter(state_code = state_code)
            if len(state) > 0:
                queryset = queryset.filter(state__in=state)    
        if slug:
            queryset = queryset.filter(slug=slug)
        return queryset


class GPSCityViewSet(viewsets.ModelViewSet):
    queryset = GPSCity.objects.all()
    serializer_class = GPSCitySerializer
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend, filters.SearchFilter]


#Paulaversion
class LogoutAPIView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=Response_status.HTTP_204_NO_CONTENT)

#Monseversion
class LoginViewSet(TokenObtainPairView):
    serializer_class = LoginSerializer

    @swagger_auto_schema(tags=['api'])
    def post(self, request, *args, **kwargs):
        username = request.data.get('username','')
        password = request.data.get('password','')
        user = authenticate(
            username=username,
            password=password
        )
        if user:
            login_serializer = self.serializer_class(data=request.data)
            if login_serializer.is_valid():
                user_serializer = WalkUserSerializer(user)
                walkuser = WalkUser.objects.get(id=user_serializer.data['id'])
                usercontext = UserContext.objects.filter(user=user_serializer.data['id']).order_by("-id").first()
                walkcontext = WalkContext.objects.filter(user=user_serializer.data['id']).order_by("-id").first()
                
                return Response({
                     'access': login_serializer.validated_data.get('access'),
                     'refresh': login_serializer.validated_data.get('refresh'),
                     'user': {'id': walkuser.id, 'username': walkuser.username, 'email': walkuser.email, 'password': walkuser.password, 'celphone': walkuser.celphone, 'walkgroup': walkuser.walkgroup.id if walkuser.walkgroup else None},
                     'last_usercontext': usercontext.id if usercontext else None,
                     'last_walkcontext': walkcontext.id if walkcontext else None,
                     'message': 'success'
                 }, status=Response_status.HTTP_200_OK)
            return Response({'error': 'Wrong password or username'}, status=Response_status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Wrong password or username'}, status=Response_status.HTTP_400_BAD_REQUEST) 


class LoginwebViewSet(TokenObtainPairView):
    serializer_class = LoginwebSerializer

    @swagger_auto_schema(tags=['api'])
    def post(self, request, *args, **kwargs):
        username = request.data.get('username','')
        password = request.data.get('password','')
        profile = request.data.get('profile','')

        cast_username = username.lower()
        cast_profile = profile.lower()
        query = WalkUser.objects.all().annotate(username_lower=Lower('username'))  
        validate_user = query.filter(username_lower = cast_username).first()

        if validate_user:           
            if query.filter(username_lower = cast_username,profile = cast_profile).first() and validate_user.check_password(password):               
                user = authenticate(
                    username=username,
                    password=password
                )
                if user:
                    login_serializer = self.serializer_class(data=request.data)
                    if login_serializer.is_valid():
                        user_serializer = WalkUserSerializer(user)
                        walkuser = WalkUser.objects.get(id=user_serializer.data['id'])
                        usercontext = UserContext.objects.filter(user=user_serializer.data['id']).order_by("-id").first()
                        walkcontext = WalkContext.objects.filter(user=user_serializer.data['id']).order_by("-id").first()
                        
                        dataids = Data.objects.all().values_list('id', flat=True)  
                        dv = DataValue.objects.all().select_related('data','value').values('id','data','value').annotate(
                                                            dv = models.ExpressionWrapper(Concat(F('data'),F('value')),
                                                            output_field=models.CharField())
                                                            )                        
                        datavalue = dv.values_list('id','dv').order_by('data','value')

                        return Response({
                            'access': login_serializer.validated_data.get('access'),
                            'refresh': login_serializer.validated_data.get('refresh'),
                            'user': {'id': walkuser.id, 'username': walkuser.username, 'email': walkuser.email, 'password': walkuser.password, 'celphone': walkuser.celphone, 'profile': walkuser.profile, 'countryCode':walkuser.countryCode, 'country': walkuser.country, 'walkgroup': walkuser.walkgroup.id if walkuser.walkgroup else None},
                            'last_usercontext': usercontext.id if usercontext else None,
                            'last_walkcontext': walkcontext.id if walkcontext else None,
                            'point_status': {
                                                'data_cant': str(len(dataids)), 'data_firstID': dataids.first(), 'data_lastID':dataids.last(),
                                                'dv_cant': str(len(datavalue)), 'dv_firstID': datavalue.first()[0], 'dv_first': datavalue.first()[1], 'dv_lastID': datavalue.last()[0], 'dv_last': datavalue.last()[1]
                                             },
                            'message': 'success'
                        }, status=Response_status.HTTP_200_OK)                           
                    return JsonResponse({ 'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': login_serializer.errors})
                return JsonResponse({'status': 'error','code': Response_status.HTTP_400_BAD_REQUEST, 'message': "User credentials aren't valid"})
            else:
               
                error_message = 'Wrong '
                v_error = list()                
                if validate_user.check_password(password) == False:    
                    v_error.append('password')
                if not query.filter(username_lower = cast_username,profile = cast_profile).first():
                    v_error.append('profile')     
                
                if len(v_error) == 2:
                    error_message = error_message + v_error[0] +' and '+ v_error[1]
                elif len(v_error) == 1:
                    error_message = error_message + v_error[0]
               
                return JsonResponse({'status': 'error','code': Response_status.HTTP_400_BAD_REQUEST, 'message': error_message})
        return JsonResponse({'status': 'error','code': Response_status.HTTP_404_NOT_FOUND, 'message': "Your username doesn't exist"})


class ChangePasswordView(generics.UpdateAPIView):    
    serializer_class = ChangePasswordSerializer
    model = WalkUser
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def get_object(self, queryset=None):
        obj = self.request.user
        return obj

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=Response_status.HTTP_400_BAD_REQUEST)            
            
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            response = {
                'status': 'success',
                'code': Response_status.HTTP_200_OK,
                'message': 'Password updated successfully'                
            }

            return Response(response)
        return Response(serializer.errors, status=Response_status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    @swagger_auto_schema(tags=['password'])
    def post(self, request):        
        serializer = self.serializer_class(data=request.data)
        username = request.data['username']  
        redirect_url = request.data.get('redirect_url', '')   
               
        if serializer.is_valid() and WalkUser.objects.filter(username=username).exists():
            
            user = WalkUser.objects.get(username=username)

            email_subject = ''
            email_body = ''
            status = ''
            code =''
            message = ''
            data = dict()

            if user.email and not user.email == '':
                uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
                token = PasswordResetTokenGenerator().make_token(user)
                current_site = get_current_site(request = request).domain
                relativeLink = reverse('reset-password-confirm', kwargs={'uidb64':uidb64, 'token': token})
                 
                absurl = 'https://' + current_site + relativeLink

                data_email = {
                    'title': "Reset your Password",
                    'link': absurl + "?redirect_url=" + redirect_url,
                    'greeting': 'Hi ' + user.username + '!',
                    'text': "You're receiving this email because you requested a password reset for your user account at WalkableStreet app or site.\n\nPlease press the button for go to the following page and choose a new password:",
                    'support_team': SUPPORT_TEAM,
                    'opt': 1,
                }  
                    
                email_subject = '[WalkableStreet] Reset your password'

                email_body = "Hi " + user.username + "!\n\nYou're receiving this email because you requested a password reset for your user account at WalkableStreet app or site.\n\n";
                email_body = email_body + "Please use link for go to the following page and choose a new password:\n\n" + absurl + "?redirect_url=" + redirect_url +"\n\n";
                email_body = email_body + "Thanks for using our app and site!\n\n" + SUPPORT_TEAM
               
                status = 'success'
                code = Response_status.HTTP_200_OK
                message = 'We sent you a link to reset your password'

                #Original
                #data = {'email_body': email_body,'to_email': user.email,'email_subject': email_subject  }
                #Util.send_mail(data)

                #NEW
                template = loader.get_template('email/email.html')
                email_menssage = template.render(data_email)

                my_email2 = EmailMessage(email_subject,email_menssage,settings.DEFAULT_FROM_EMAIL,[user.email])
                my_email2.content_subtype = 'html'
                my_email2.send()
                
            else:
                email_body = 'Hi ' + user.username + '!\n \nThe inserted email has not been found \n\nPlease contact us by email: '+MAIL
                email_subject = '[WalkableStreet] Email not found'                
               
                status = 'error'
                code = Response_status.HTTP_404_NOT_FOUND
                message = 'Email not found. Please contact us by email: ' + MAIL                
            
            response = {
                    'status': status,
                    'code': code,
                    'message': message                
            }  

            return Response(response)
        return Response(serializer.errors, status=Response_status.HTTP_400_BAD_REQUEST)


class PasswordTokenCheckView_old(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer
    
    @swagger_auto_schema(tags=['password'])
    def get(self, request, uidb64,token):   
        try:
            id = smart_str(urlsafe_base64_decode(uidb64))
            user = WalkUser.objects.get(id=int(id))  
            if PasswordResetTokenGenerator().check_token(user, token):        
                response = {
                    'status': 'success',
                    'code': Response_status.HTTP_200_OK,
                    'message': 'Credentials Valid' ,
                    'data':{'uidf64':uidb64, 'token':token}               
                }            
                return Response(response)
            else:
                return Response({'error': 'Token is not valid, please request a new one'}, status=Response_status.HTTP_401_UNAUTHORIZED)
        except DjangoUnicodeDecodeError as identifier:
            return Response({'error': 'Token is not valid, please request a new one'}, status=Response_status.HTTP_401_UNAUTHORIZED)


class PasswordTokenCheckView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    @swagger_auto_schema(tags=['password'])
    def get(self, request, uidb64, token):
        redirect_url = request.GET.get('redirect_url')     
        try:
            id = smart_str(urlsafe_base64_decode(uidb64))
            user = WalkUser.objects.get(id=int(id))

            if not PasswordResetTokenGenerator().check_token(user, token):
                if len(redirect_url) > 3:
                    return CustomRedirect(redirect_url+'?token_valid=False')
                else:
                    return CustomRedirect(os.environ.get('FRONTEND_URL', '')+'?token_valid=False')

            if redirect_url and len(redirect_url) > 3:
                return CustomRedirect(redirect_url+'?token_valid=True&message=Credentials Valid&uidb64='+uidb64+'&token='+token)
            else:
                return CustomRedirect(os.environ.get('FRONTEND_URL', '')+'?token_valid=False')

        except DjangoUnicodeDecodeError as identifier:
            try:
                if not PasswordResetTokenGenerator().check_token(user):
                    return CustomRedirect(redirect_url+'?token_valid=False')
                    
            except UnboundLocalError as e:
                return Response({'error': 'Token is not valid, please request a new one'}, status=status.HTTP_400_BAD_REQUEST)
     

class SetNewPasswordView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer
    
    @swagger_auto_schema(tags=['password'])
    def patch(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid(raise_exception=True):
            id = smart_str(urlsafe_base64_decode(request.data['uidb64']))
            user = WalkUser.objects.get(id=int(id))

            response = {
                'status': 'success',
                'code': Response_status.HTTP_200_OK,
                'message': 'Password reset successfully',
                'profile': user.profile
            }            
            return Response(response)
        return Response(serializer.errors, status=Response_status.HTTP_400_BAD_REQUEST)

#RESP
class DeleteAllInfoView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    serializer_class = DeleteAllInfoSerializer
    
    @swagger_auto_schema(tags=['others'])
    def post(self, request):
        """
        This function delete all the information about a user (user data, walks data, user context and points). It must be careful when you use it.

        ## Parameter filters:
        - **user id**
        - **option = special string of activation**

        **You can use username or user id or none with the other filters**
        """
        serializer = self.serializer_class(data=request.data)
        id_user = request.data['user']
        option = request.data['option']
        response = {'data':dict(), 'usercontext':dict(), 'walkcontext':dict(), 'user': dict()}

        if serializer.is_valid():           
            if WalkUser.objects.filter(id=id_user).exists() and option == 'delete':        
                user_object = WalkUser.objects.get(id=id_user)  
                cant_data = 0
                cant_context=0
                cant_walk=0 
                check_d = False
                check_c = False
                check_w = False 
               
                if Data.objects.filter(user=user_object).exists():    
                    try:
                        data_object = Data.objects.filter(user=user_object)                  
                        cant_data = data_object.delete() 
                        response['data'] = { 'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "All data deleted", 'count':cant_data[0]}     
                        check_d = True            
                    except:  
                        response['data'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No data deleted."}
                        check_d = False
                else:
                    response['data'] = {'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No data found." }  
                    check_d = True
                
                if UserContext.objects.filter(user=user_object).exists():
                    try:
                        usercontext = UserContext.objects.filter(user=user_object)
                        cant_context = usercontext.delete()
                        response['usercontext'] = { 'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "All usercontext deleted", 'count':cant_context[0]}                            
                        check_c = True
                    except:
                        response['usercontext'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No usercontext deleted."}
                        check_c = False
                else:
                    response['usercontext'] = {'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No usercontext found." }
                    check_c = True
                
                if WalkContext.objects.filter(user=user_object).exists():
                    try:
                        walkcontext = WalkContext.objects.filter(user=user_object)  
                        cant_walk = walkcontext.delete()
                        response['walkcontext'] = { 'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "All walkcontext deleted", 'count':cant_walk[0]} 
                        check_w = True
                    except:
                        response['walkcontext'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No walkcontext deleted."}
                        check_w = False
                else:
                    response['walkcontext'] = {'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No usercontext found." }
                    check_w = True
                     
                if check_d == True and check_c == True and check_w == True:
                    try:
                        user_object.delete()
                        response['user'] = { 'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "User deleted"} 
                    except:
                        response['user'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No user deleted."}  
                else:
                    response['user'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "User cannot be deleted because a problem in related information."}  
                
                return Response(response)

            return Response({'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No user found or right key in option" })      
        return Response({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "User id and Option required" } ) 


class DeleteUserInfoView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    serializer_class = DeleteUserInfoSerializer
    
    @swagger_auto_schema(tags=['others'])
    def post(self, request):
        """
        This function delete all the information about a user (user data, walks data, user context and points) or just the user account keeping their information. After delete account the system send a notification to the administrator and the user if their have mail. It must be careful when you use it.

        ## Parameter filters:
        - **user id**
        - **option = special string of activation**

        **You can use username or user id or none with the other filters**
        """
        serializer = self.serializer_class(data=request.data)        
        id_user = request.data['user']
        option = request.data['option']
        keep = request.data['keep_data']
        feed = request.data['feedback']

        response = {'data':dict(), 'usercontext':dict(), 'walkcontext':dict(), 'user': dict()}       

        if serializer.is_valid():           
            if WalkUser.objects.filter(id=id_user).exists() and option == 'delete':        
                user_object = WalkUser.objects.get(id=id_user)  
                username = user_object.username
                email = user_object.email                
                cant_data = 0
                cant_context=0
                cant_walk=0 
                check_d = False
                check_c = False
                check_w = False 

                email_content = dict()
                email_subject = ""
                email_list = []
                

                if keep == 'false':               
                    if Data.objects.filter(user=user_object).exists():    
                        try:
                            data_object = Data.objects.filter(user=user_object)                  
                            cant_data = data_object.delete() 
                            response['data'] = { 'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "All data deleted", 'count':cant_data[0]}     
                            check_d = True            
                        except:  
                            response['data'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No data deleted."}
                            check_d = False
                    else:
                        response['data'] = {'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No data found." }  
                        check_d = True
                    
                    if UserContext.objects.filter(user=user_object).exists():
                        try:
                            usercontext = UserContext.objects.filter(user=user_object)
                            cant_context = usercontext.delete()
                            response['usercontext'] = { 'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "All usercontext deleted", 'count':cant_context[0]}                            
                            check_c = True
                        except:
                            response['usercontext'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No usercontext deleted."}
                            check_c = False
                    else:
                        response['usercontext'] = {'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No usercontext found." }
                        check_c = True
                    
                    if WalkContext.objects.filter(user=user_object).exists():
                        try:
                            walkcontext = WalkContext.objects.filter(user=user_object)  
                            cant_walk = walkcontext.delete()
                            response['walkcontext'] = { 'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "All walkcontext deleted", 'count':cant_walk[0]} 
                            check_w = True
                        except:
                            response['walkcontext'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No walkcontext deleted."}
                            check_w = False
                    else:
                        response['walkcontext'] = {'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No usercontext found." }
                        check_w = True
                     
                if (keep == 'false' and check_d == True and check_c == True and check_w == True) or (keep == 'true'):
                    try:
                        user_object.delete()                       
                        #response['user'] = { 'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "User deleted"} 
                    except:
                        response['user'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No user deleted."}  
                    else:
                        #Send Email
                        template = loader.get_template('email/email.html')
                        email_subject = '[WalkableStreet] Account Deleted Notification'
                        
                        
                        try:
                            #Mail Administrator
                            feedback = 'has left the following feedback: <<' +  feed +'>>'  if feed and not feed == 'null' else "hasn't left feedback"
                            about = 'not deleted' if keep == 'true' else 'to delete'
                            
                            email_content = {
                                    'title': "Account Deleted",
                                    'link': None,
                                    'greeting': 'Hi Administrator!',
                                    'text': "This message is because user '" + username + "' has deleted their account. The user " + feedback + " and decided " + about + " their data in the platform." ,'support_team': SUPPORT_TEAM,
                                    'opt': 6,
                                    'admin_footer': 1
                            }
                            
                            email_list = [ADMIN_EMAIL, 'monse.fm@gmail.com']
                            email_menssage = template.render(email_content)
                            my_email = EmailMessage(email_subject,email_menssage,settings.DEFAULT_FROM_EMAIL, email_list)
                            my_email.content_subtype = 'html'
                            my_email.send()

                            #Mail User
                            #print(email)
                            if email:
                                user_feedback = 'you have left the following feedback: <<' +  feed +'>>'  if feed and not feed == 'null' else "you haven't left feedback"
                                user_about = 'not deleted' if keep == 'true' else 'to delete'

                                email_content_user = {
                                        'title': "Account Deleted",
                                        'link': None,
                                        'greeting': 'Hi '+ username +'!',
                                        'text': "Thank you for your interest in using Walkbaility.App. We are sad to see you leave and delete your account. Anyway, " + user_feedback + " and you decided " + user_about + " your data in the platform.",'support_team': SUPPORT_TEAM,
                                        'opt': 6,
                                        'admin_footer': 0
                                }
                            
                                email_list_user = [email]
                                email_menssage_user = template.render(email_content_user)
                                my_email_user = EmailMessage(email_subject,email_menssage_user,settings.DEFAULT_FROM_EMAIL, email_list_user)
                                my_email_user.content_subtype = 'html'
                                my_email_user.send()
                        except:
                             response = {
                                    'status': 'error',
                                    'code': Response_status.HTTP_400_BAD_REQUEST,
                                    'message': "Account deleted but an error occurred while sending the message."
                            }
                        else:
                            response = {
                                    'status': 'success',
                                    'code': Response_status.HTTP_200_OK,
                                    'message': 'Account deleted successfully. Notification has been sent'
                            }
                else:
                    response['user'] = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "User cannot be deleted because a problem in related information."}  
                
                return Response(response)

            return Response({'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No user found or right key in option" })      
        return Response({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "User id and Option required" } ) 






class DeleteDataWalkView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    serializer_class = DeleteDataWalkSerializer
    
    @swagger_auto_schema(tags=['others'])
    def post(self, request):
        """
        This function for special delete in case you delete points in walks. If you delete all the points you' re gonna delete the walk too.

        ## Parameter filters:
        - **data id**
        """
        serializer = self.serializer_class(data=request.data)
        id_data = request.data['data']

        if serializer.is_valid():
            if Data.objects.filter(id=id_data).exists():
                data_object = Data.objects.get(id=id_data)
                walkcontext = data_object.walk_context                
                try:
                   data_object.delete()
                except:
                    return Response({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "No data deleted."} )
                else:
                    cant_data = Data.objects.filter(walk_context=walkcontext).count()                    
                    if cant_data > 0:                 
                        return Response({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "Data deleted."} ) 
                    else:
                        try:                            
                            walkcontext.delete()
                            return Response({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "Data deleted and walkcontext is empty. In this case, the walkcontext is removed too."} ) 
                        except:
                            return Response({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "Walkcontext is empty, but it cannot be deleted because a problem in database."} )
        
            return Response({'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No data found" })   
        return Response({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "Data id required" } ) 


class FinishWalkViewset(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    serializer_class = FinishWalkSerializer

    @swagger_auto_schema(tags=['others'])
    def patch(self, request):
        """
        This function is for insert the information for finish the walk (latitude, longitude, gps accuracy) and deactivate the automatic updaing in date end.

        ## Parameter filters:
        - **walk id**
        - **latitude end**
        - **longitude end**
        - **gpsaccuracy end**
        """
        serializer = self.serializer_class(data=request.data) 
        if serializer.is_valid(raise_exception=True):
            #activar disabled                
            WalkContext.objects.filter(id=serializer.data['id']).update(disable_date_auto_now=True) 
            
            response = {
                'status': 'success',
                'code': Response_status.HTTP_200_OK,
                'message': 'Walk finished successfully'      
            }            
            return Response(response)
        return Response(serializer.errors, status=Response_status.HTTP_400_BAD_REQUEST)


class InsertDataView(generics.GenericAPIView):
    #permission_classes = (IsAuthenticated,)
    #authentication_classes = (JWTAuthentication,)
    serializer_class = InsertDataSerializer
    
    @swagger_auto_schema(tags=['others'])
    def post(self, request):
        """
        This function for insert data of country, state and city tables.

        ## Parameter filters:
        - **table = (table name)**
        """
        serializer = self.serializer_class(data=request.data)
        table_name = request.data['table']

        if serializer.is_valid():
            response = dict({'status':'success', 'code': Response_status.HTTP_200_OK, 'message': 'Data inserted successfully', 'city_problem':list()})
            
            if table_name == 'country':
                country = Country.objects.all()
                country.delete()
                with open('./db_json/countries.json') as content:
                    json_set = json.load(content)   
                    index = 0
                    for c in json_set:   
                        col_latitude    =  c.get('latitude').replace(',','.') 
                        col_longitude   =  c.get('longitude').replace(',','.') 
                       
                        Country(name=c.get('name'), slug = slugify(c.get('name')), iso3=c.get('iso3'), iso2=c.get('iso2'), numeric_code=c.get('numeric_code'), phone_code=c.get('phone_code'), capital=c.get('capital'), currency=c.get('currency'), native=c.get('native'), region=c.get('region'), subregion=c.get('subregion'), latitude=col_latitude, longitude=col_longitude, emojiU=c.get('emojiU')).save()                    
                        index = index + 1
                        print(round((index/len(json_set))*100,4))  
            
            elif table_name == 'state':
                state = State.objects.all()
                state.delete()
                with open('./db_json/states.json') as content:
                    json_set = json.load(content)   
                    index = 0
                    for s in json_set:   
                        country_code = s.get('country_code')
                        col_country = Country.objects.get(iso2=country_code)

                        col_latitude    =  s.get('latitude').replace(',','.') if s.get('latitude') else None
                        col_longitude   =  s.get('longitude').replace(',','.') if s.get('longitude') else None 
                       
                        State(name=s.get('name'), slug = slugify(s.get('name')), country=col_country, state_code=s.get('state_code'), type=s.get('type') if s.get('type') != 'null' else None, latitude=col_latitude, longitude=col_longitude).save()                    
                        index = index + 1
                        print(round((index/len(json_set))*100,4))  

            elif table_name == 'city':
                city = City.objects.all()
                city.delete()
                with open('./db_json/cities.json') as content:
                    json_set = json.load(content)   
                    index = 0                    
                    for c in json_set:   
                        country_code = c.get('country_code')
                        col_country = Country.objects.get(iso2=country_code)

                        state_name = c.get('state_name')
                        col_state = State.objects.filter(name=state_name, country = col_country).first()

                        if col_state:
                            col_latitude    =  c.get('latitude').replace(',','.') 
                            col_longitude   =  c.get('longitude').replace(',','.')  
                        
                            City(name=c.get('name'), slug = slugify(c.get('name')), country=col_country, state=col_state, wikiDataId=c.get('wikiDataId') if c.get('wikiDataId') else None, latitude=col_latitude, longitude=col_longitude).save()                    
                        else:
                            response['city_problem'].append(c.get('id'))
                        index = index + 1
                        print(round((index/len(json_set))*100,4)) 
            else:
                response['status'] = 'error'
                response['code'] = Response_status.HTTP_400_BAD_REQUEST
                response['message'] = 'Table name required'               
            
            return Response(response) 
        return Response({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': "Table name required" } ) 


@swagger_auto_schema(methods=['get'],
    manual_parameters=[
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('iso2', openapi.IN_QUERY, "Insert country code", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date from', openapi.IN_QUERY, "Insert date from", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date to', openapi.IN_QUERY, "Insert date to", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        ], tags=['reports'])
@api_view(['GET'])
def status(request):
    """
    This function get a data resume about total points (data), total distance and sum of duration (with two point or more) by walks.

    ## Parameter filters:
     - **user id**
     - **country code = iso2**
     - **date_from = format MM/DD/YYYY**
     - **date_to = format MM/DD/YYYY**

    **You can use just one variable or none for get data resumen by all users or data filtered**
    """
    id_user = request.GET.get('user',None)
    iso2 = request.GET.get('iso2', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)

    data_list = ''
    data_list = Data.objects.all().order_by('walk_context','id')
    response = {  'cant_points_total': 0,  'distance_total': 0, 'unit': 'Km', 'duration_total': 0, 'duration_total_old': 0  }

    if len(data_list) > 0:
        ids_walk = []
        cant_points = 0
        walkset = WalkContext.objects.all()
        if id_user:
            user_object = WalkUser.objects.get(pk=id_user)
            if user_object:
                if user_object.profile == 'contributor':
                    walkset = walkset.filter(user=user_object).order_by('id')
                elif user_object.profile == 'licensed' and not user_object.country == 'global':
                    walkset = walkset.filter(countryCode=user_object.countryCode).order_by('id')
        if iso2:
            walkset = walkset.filter(countryCode=iso2).order_by('id')
        if date_from and date_to:
            datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
            datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'

            dateto_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY
            next_day = dateto_format + datetime.timedelta(days=1)
            date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD
            
            walkset = walkset.filter(Q(date_start__gte=datefrom_str), Q(date_end__lt=date_str)).order_by('id')

        #Distance calculation
        total_distance = 0

        for wc in walkset:
            sections = list()
            list_a = list()
            list_b = list()
            total_distance_wc = 0
            dataset = data_list.filter(walk_context=wc.id).order_by('id')
            cant_points+=wc.data_set.count()

            if wc.data_set.count() > 1:
                ids_walk.append(wc.id)

            if len(dataset):
                if wc.latitude_start and wc.longitude_start and wc.latitude_end and wc.longitude_end:
                    list_a.append(list([wc.latitude_start, wc.longitude_start]))
                    list_b.append(list([dataset[0].latitude, dataset[0].longitude]))

                for i, point in enumerate(dataset, start=0):
                    if i < len(dataset)-1:
                        list_a.append(list([point.latitude, point.longitude]))
                    if i > 0:
                        list_b.append(list([point.latitude, point.longitude]))

                if wc.latitude_start and wc.longitude_start and wc.latitude_end and wc.longitude_end:
                    list_b.append(list([wc.latitude_end, wc.longitude_end]))
                    list_a.append(list([dataset[len(dataset)-1].latitude, dataset[len(dataset)-1].longitude]))

                for p_start, p_end in zip(list_a, list_b):
                    sections.append({'start': p_start, 'end': p_end})

                for section in sections:
                    total_distance_wc = total_distance_wc + haversine(section['start'], section['end'], unit='km')

            total_distance = total_distance + total_distance_wc

        #Duration calculation
        duration_data = WalkContext.objects.filter(id__in=ids_walk).annotate(duration = (F('date_end')) - (F('date_start'))).aggregate(duration_total = Sum(F('duration')))
        
        if duration_data['duration_total']: 
            duration_data_final  = duration_data['duration_total']              
            duration_str = str(duration_data['duration_total']).split('.')

            second = round(float('0.' + duration_str[1]),0)
            
            if second == 1.0:
                duration_data_final = duration_data_final + datetime.timedelta(seconds=1)
            duration_data_final = duration_data_final - datetime.timedelta(microseconds=duration_data_final.microseconds)  
        else:
            duration_data_final = duration_data['duration_total'] = 0      

        response = {
            'cant_points_total': cant_points,
            'distance_total': round(total_distance,2),
            'unit': 'Km',
            'duration_total': str(duration_data_final),
            'duration_total_old': str(duration_data['duration_total'])
        }
    return JsonResponse(response)


@swagger_auto_schema(methods=['get'],
    manual_parameters=[
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('iso2', openapi.IN_QUERY, "Insert country code", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date from', openapi.IN_QUERY, "Insert date from", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date to', openapi.IN_QUERY, "Insert date to", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        ], tags=['reports'])
@api_view(['GET'])
def statusNEW(request):   
    """
    This function get a data resume about total points (data), total distance and sum of duration (with two point or more) by walks.

    ## Parameter filters:
     - **user id**
     - **country code = iso2**
     - **date_from = format MM/DD/YYYY**
     - **date_to = format MM/DD/YYYY**

    **You can use just one variable or none for get data resumen by all users or data filtered**
    """
    id_user = request.GET.get('user',None)
    iso2 = request.GET.get('iso2', None)
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)   

    data_list = ''    
    response = {  'cant_points_total': 0,  'distance_total': 0, 'unit': 'Km', 'duration_total': 0, 'duration_total_old': 0  }

    data_list = Data.objects.all().select_related('walk_context').order_by('walk_context', 'id')
    cant_points = len(data_list)
    
    if len(data_list) > 0:
        q = Q()     
        walkset = WalkContext.objects.all()
        if id_user:
            user_object = WalkUser.objects.get(pk=id_user)
            if user_object:
                if user_object.profile == 'contributor':
                    q &= Q(user=user_object)                   
                elif user_object.profile == 'licensed' and not user_object.country == 'global':
                    q &= Q(countryCode=user_object.countryCode)
                    
        if iso2:            
            q &= Q(countryCode=iso2)
        if date_from and date_to:
            datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
            datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'

            dateto_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY
            next_day = dateto_format + datetime.timedelta(days=1)
            date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD
            
            q &= Q(date_start__gte=datefrom_str, date_end__lt=date_str)            

        walkset = walkset.filter(q).order_by('id')               
        
        #Distance calculation
        distance_data = walkset.annotate(
                                            adjusted_distance=Case(
                                            When(distance_new__isnull=True, then=Value(0)),
                                            default=F('distance_new'),
                                            output_field=DecimalField()
                                        )
                                    ).aggregate(distancia_total=Sum('adjusted_distance'))
        
        #Duration calculation
        walk = walkset.annotate(data_count=Count('data'))
        walk_filter = walk.filter(data_count__gt=1)
        ids_walk = walk_filter.values_list('id', flat=True)

        duration_data = walkset.filter(id__in=ids_walk).annotate(duration = (F('date_end')) - (F('date_start'))).aggregate(duration_total = Sum(F('duration')))
        
        if duration_data['duration_total']: 
            duration_data_final  = duration_data['duration_total'] 
            if str(duration_data['duration_total']).find('.') != -1:
                duration_str = str(duration_data['duration_total']).split('.')
                second = round(float('0.' + duration_str[1]),0)
                if second == 1.0:
                    duration_data_final = duration_data_final + datetime.timedelta(seconds=1)
                duration_data_final = duration_data_final - datetime.timedelta(microseconds=duration_data_final.microseconds)  
            elif str(duration_data['duration_total']).find('day') != -1:
                duration_data_final = (duration_data['duration_total'])
        else:
            duration_data_final = duration_data['duration_total'] = 0      

        response = {            
            'cant_points_total': cant_points,           
            'distance_total': round(float(distance_data['distancia_total']),2),
            'unit': 'Km',
            'duration_total': str(duration_data_final),
            'duration_total_old': str(duration_data['duration_total'])
        }
   
    return JsonResponse(response)


@swagger_auto_schema(methods=['get'], manual_parameters=[], tags=['others'])
@api_view(['GET'])
def validatePointPolygon(request):
    id_user = request.GET.get('user',None)
    date_from = request.GET.get('date_from',None)
    date_to = request.GET.get('date_to', None)
    coordinates = request.GET.getlist('coor')
    response = dict()
    walkids_time = ''
    ids_list = ''
    user_object = ''
    q = Q()

    if not id_user or len(coordinates)==0:
        return HttpResponse('id user and coors required.',content_type='text/plain')

    data_list = Data.objects.all().select_related('walk_context').order_by('walk_context', 'id')
    walkset = WalkContext.objects.all()

    if len(data_list) > 0:
        user_object = WalkUser.objects.get(pk=id_user)
        if user_object:
            if user_object.profile == 'contributor':
                walkids = walkset.filter(user=user_object).values_list('id', flat=True).order_by('id')
                data_list = data_list.filter(walk_context__in=walkids).order_by('id')
            elif user_object.profile == 'licensed' and not user_object.country == 'global':
                walkids = walkset.filter(countryCode=user_object.countryCode).values_list('id', flat=True).order_by('id')
                data_list = data_list.filter(walk_context__in=walkids).order_by('id')
        if date_from and date_to:
            datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
            datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'

            dateto_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY
            next_day = dateto_format + datetime.timedelta(days=1)
            date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD

            walkids_time = walkset.filter(Q(date_start__gte=datefrom_str), Q(date_end__lt=date_str)).values_list('id', flat=True).order_by('id')
            data_list = data_list.filter(walk_context__in=walkids_time).order_by('id')
        if len(coordinates) > 0:
            polylist = list()
            for coor in coordinates:
                latlng = coor.split(',')
                polylist.append((float(latlng[0]),float(latlng[1])))
            polygon = Polygon((polylist))

            #User licensed No global condition
            point_error = 0
            if user_object.profile == 'licensed' and not user_object.country == 'global':
                for p in polylist:
                    plocation = getaddress(p[0],p[1],'country')
                    if plocation == 'Error' or not plocation['address']['country_code'].upper() == user_object.countryCode:
                        point_error+=1
                if point_error > 0:
                    error_message = 'There is a point outside the country limits' if point_error == 1 else 'There are ' + str(point_error) + ' points outside the country limits'
                    return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': error_message }, safe=False)
            dataset = Data.objects.all().values('id','latitude','longitude').order_by('id')
            ids = [d['id'] for d in dataset if  polygon.contains(Point(float(d['longitude']), float(d['latitude'])))]
            q |= Q(id__in=ids)


        data_list = data_list.filter(q)
        ids_list = data_list.values_list('id', flat=True)

        response = {
            'status': 'success',
            'code': Response_status.HTTP_200_OK,
            'ids': list(ids_list)
        }
    return JsonResponse(response)


@swagger_auto_schema(methods=['get'], manual_parameters=[], tags=['reports'])
@api_view(['GET'])
def status_stats_rank(request):
    id_user = request.GET.get('user',None)
    iso2 = request.GET.get('iso2', None)
    date_from = request.GET.get('date_from',None)
    date_to = request.GET.get('date_to', None)
    coordinates = request.GET.getlist('coor')
    ids_markers = request.GET.getlist('id_marker')
    response = { 'cant_points_total': 0,'distance_total': 0, 'unit': 'Km' }

    data_list = ''
    cant_points = 0
    total_distance = 0
    walkids = ''
    walkids_iso2 = ''
    walkids_time = ''
    ids = ''
    user_object = ''
    q = Q()
    data_list = Data.objects.all().select_related('walk_context').order_by('walk_context', 'id')
    walkset = WalkContext.objects.all()

    if len(data_list) > 0 and id_user:
        user_object = WalkUser.objects.get(pk=id_user)
        if user_object:
            if user_object.profile == 'contributor':
                walkids = walkset.filter(user=user_object).values_list('id', flat=True).order_by('id')
                data_list = data_list.filter(walk_context__in=walkids).order_by('id')
            elif user_object.profile == 'licensed' and not user_object.country == 'global':
                walkids = walkset.filter(countryCode=user_object.countryCode).values_list('id', flat=True).order_by('id')
                data_list = data_list.filter(walk_context__in=walkids).order_by('id')
                iso2 = ''
        if iso2:
            walkids_iso2 = walkset.filter(countryCode=iso2).values_list('id', flat=True).order_by('id')
            q &= Q(walk_context__in=walkids_iso2)
            #data_list = data_list.filter(walk_context__in=walkids_iso2).order_by('id')
        if date_from and date_to:
            datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
            datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'

            dateto_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY
            next_day = dateto_format + datetime.timedelta(days=1)
            date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD

            walkids_time = walkset.filter(Q(date_start__gte=datefrom_str), Q(date_end__lt=date_str)).values_list('id', flat=True).order_by('id')
            data_list = data_list.filter(walk_context__in=walkids_time).order_by('id')
        if len(coordinates) > 0:
            polylist = list()
            #for coor in coordinates:
            #    latlng = coor.split(',')
            #    polylist.append((float(latlng[0]),float(latlng[1])))
            #polygon = Polygon((polylist))
            
            #ids = [d['id'] for d in dataset if  polygon.contains(Point(float(d['longitude']), float(d['latitude'])))]
            #q |= Q(id__in=ids)

            polylist = [tuple(map(float, coor.split(','))) for coor in coordinates]
            polygon = Polygon(polylist)

            dataset = Data.objects.all().values('id','latitude','longitude').order_by('id')
            ids = [d['id'] for d in dataset if  polygon.contains(Point(float(d['longitude']), float(d['latitude'])))]
            q &= Q(id__in=ids)
        if len(ids_markers) > 0:
            q &= Q(id__in=ids_markers)

        data_list = data_list.filter(q).order_by('id')
        ids_walk = data_list.values_list('walk_context',flat=True).distinct().order_by('walk_context')
        walkset = walkset.filter(id__in=ids_walk).values('id','latitude_start','longitude_start','latitude_end','longitude_end').order_by('id')

        cant_points = len(data_list)
        #Distance calculation
        total_distance = 0
        
        #OLD VERSION
        '''
        for wc in walkset:
            sections = list()
            list_a = list()
            list_b = list()
            walk_data = ''
            walk_data = data_list.filter(walk_context=wc['id'])
            if len(walk_data) > 0:
                if wc['latitude_start'] and wc['longitude_start'] and wc['latitude_end'] and wc['longitude_end']:
                    list_a.append(list([wc['latitude_start'], wc['longitude_start']]))
                    list_b.append(list([walk_data[0].latitude, walk_data[0].longitude]))

                for i, point in enumerate(walk_data, start=0):
                    if i < len(walk_data)-1:
                        list_a.append(list([point.latitude, point.longitude]))
                    if i > 0:
                        list_b.append(list([point.latitude, point.longitude]))

                if wc['latitude_start'] and wc['longitude_start'] and wc['latitude_end'] and wc['longitude_end']:
                    list_b.append(list([wc['latitude_end'], wc['longitude_end']]))
                    list_a.append(list([walk_data[len(walk_data)-1].latitude, walk_data[len(walk_data)-1].longitude]))

                for p_start, p_end in zip(list_a, list_b):
                    sections.append({'start': p_start, 'end': p_end})

                total_distance_wc = 0
                for section in sections:
                    total_distance_wc = total_distance_wc + haversine(section['start'], section['end'], unit='km')

                total_distance = total_distance + total_distance_wc
        '''
        distance_data = walkset.annotate(
                                            adjusted_distance=Case(
                                            When(distance_new__isnull=True, then=Value(0)),
                                            default=F('distance_new'),
                                            output_field=DecimalField()
                                        )
                                    ).aggregate(distancia_total=Sum('adjusted_distance'))
                
        total_distance = float(distance_data['distancia_total']) if distance_data['distancia_total'] else 0
        #'''
        response = {
            'cant_points_total': cant_points,
            'distance_total': round(total_distance,2),
            'unit': 'Km',
        }

    return JsonResponse(response)


@swagger_auto_schema(methods=['get'],
    manual_parameters=[], tags=['reports'])
@api_view(['GET'])
def status_data_polygon(request):
    """
    This function get a resume about total points (data) and total distance inside a polygon coordinates.
    """
    id_user = request.GET.get('user',None)
    coordinates = request.GET.getlist('coor')
    response = {    'cant_points_total': 0,  'distance_total': 0, 'unit': 'Km'  }

    data_list = ''
    cant_points = 0
    total_distance = 0
    data_list = Data.objects.all().select_related('walk_context').order_by('walk_context','id')
    if len(data_list):
        ids = []
        ids_walk = []
        walkset = WalkContext.objects.all()
        user_object = WalkUser.objects.get(pk=id_user)

        if len(coordinates) > 0:
            polylist = list()
            for coor in coordinates:
                latlng = coor.split(',')
                polylist.append((float(latlng[0]),float(latlng[1])))
            polygon = Polygon((polylist))

            #User licensed No global condition
            point_error = 0
            if user_object.profile == 'licensed' and not user_object.country == 'global':
                for p in polylist:
                    plocation = getaddress(p[0],p[1],'country')
                    if plocation == 'Error' or not plocation['address']['country_code'].upper() == user_object.countryCode:
                        point_error+=1
                if point_error > 0:
                    error_message = 'There is a point outside the country limits' if point_error == 1 else 'There are ' + str(point_error) + ' points outside the country limits'
                    return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': error_message }, safe=False)


            dataset = Data.objects.all().values('id','latitude','longitude','walk_context').order_by('walk_context','id')
            ids = [d['id'] for d in dataset if  polygon.contains(Point(float(d['longitude']), float(d['latitude'])))]
            data_list = data_list.filter(id__in=ids).order_by('walk_context','id')
            ids_walk = data_list.values_list('walk_context',flat=True).distinct().order_by('walk_context')
            walkset = walkset.filter(id__in=ids_walk).values('id','latitude_start','longitude_start','latitude_end','longitude_end').order_by('id')

            cant_points = len(ids)
            #Distance calculation
            total_distance = 0

            #OLD VERSION
            '''
            for wc in walkset:
                sections = list()
                list_a = list()
                list_b = list()
                walk_data = ''
                walk_data = data_list.filter(walk_context=wc['id'])
                if len(walk_data) > 0:
                    if wc['latitude_start'] and wc['longitude_start'] and wc['latitude_end'] and wc['longitude_end']:
                        list_a.append(list([wc['latitude_start'], wc['longitude_start']]))
                        list_b.append(list([walk_data[0].latitude, walk_data[0].longitude]))

                    for i, point in enumerate(walk_data, start=0):
                        if i < len(walk_data)-1:
                            list_a.append(list([point.latitude, point.longitude]))
                        if i > 0:
                            list_b.append(list([point.latitude, point.longitude]))

                    if wc['latitude_start'] and wc['longitude_start'] and wc['latitude_end'] and wc['longitude_end']:
                        list_b.append(list([wc['latitude_end'], wc['longitude_end']]))
                        list_a.append(list([walk_data[len(walk_data)-1].latitude, walk_data[len(walk_data)-1].longitude]))

                    for p_start, p_end in zip(list_a, list_b):
                        sections.append({'start': p_start, 'end': p_end})

                    total_distance_wc = 0
                    for section in sections:
                        total_distance_wc = total_distance_wc + haversine(section['start'], section['end'], unit='km')


                    total_distance = total_distance + total_distance_wc

            '''
            #Distance calculation
            distance_data = walkset.annotate(
                                            adjusted_distance=Case(
                                            When(distance_new__isnull=True, then=Value(0)),
                                            default=F('distance_new'),
                                            output_field=DecimalField()
                                        )
                                    ).aggregate(distancia_total=Sum('adjusted_distance'))
            response = {
                'cant_points_total': cant_points,
                #'distance_total': round(total_distance,2),
                'distance_total': round(float(distance_data['distancia_total']),2),
                'unit': 'Km',
            }


    return JsonResponse(response)




@swagger_auto_schema(methods=['get'],
    manual_parameters=[
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('walkcontext', openapi.IN_QUERY, "Insert walk id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('iso2', openapi.IN_QUERY, "Insert country code", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date from', openapi.IN_QUERY, "Insert date from", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date to', openapi.IN_QUERY, "Insert date to", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('mode', openapi.IN_QUERY, "Insert mode character", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('opt', openapi.IN_QUERY, "Insert opt", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), uniqueItems=True)
    ], tags=['reports'])
@api_view(['GET'])
def perception_report(request):
    """
    This function get data grouped according their perception color (green = good, yellow = concern, red = problem) or without perception. Also you can change the mode for show the perception information without groups

    ## Parameter filters:
     - **user id**
     - **walk context = walk id**
     - **country code = iso2**
     - **date_from = format MM/DD/YYYY**
     - **date_to = format MM/DD/YYYY**
     - **mode = character for distribute the data for years, months or day (y, m, d)**
     - **opt = option for count data in general without perception division (opt = g)**

    **You can use user id or none with the other filters. Polygon coordinates filters are not activated for this web**
    """
    id_user = request.GET.get('user',None)
    walkcontext = request.GET.get('walkcontext', None)
    iso2 = request.GET.get('iso2', None) 
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    coordinates = request.GET.getlist('coor')
    ids_markers = request.GET.getlist('id_marker')
    mode = request.GET.get('mode', None)
    opt = request.GET.get('opt', None) # if opt =  g no perception slip
    data_list = ''
    response = []
    walkids = ''
    walkids_iso2 = ''
    walkids_time = ''
    ids = ''
    user_object = ''
    q = Q()

    data_list = Data.objects.select_related().all().order_by('walk_context','id')

    if id_user:
        user_object = WalkUser.objects.get(pk=id_user)
        if user_object:
            if user_object.profile == 'contributor':
                walkids = WalkContext.objects.filter(user=user_object).values_list('id', flat=True).order_by('id')
                data_list = data_list.filter(walk_context__in=walkids).order_by('id')
            elif user_object.profile == 'licensed' and not user_object.country == 'global':
                walkids = WalkContext.objects.filter(countryCode=user_object.countryCode).values_list('id', flat=True).order_by('id')
                data_list = data_list.filter(walk_context__in=walkids).order_by('id')
                iso2=''
    if walkcontext:
        data_list = data_list.filter(walk_context=int(walkcontext)).order_by('id')
    if iso2:
        walkids_iso2 = WalkContext.objects.filter(countryCode=iso2).values_list('id', flat=True).order_by('id') 
        q &= Q(walk_context__in=walkids_iso2)
        #data_list = data_list.filter(walk_context__in=walkids).order_by('id')  
    if date_from and date_to: 
        datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
        datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'
    
        dateto_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY 
        next_day = dateto_format + datetime.timedelta(days=1)            
        date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD
        
        walkids = WalkContext.objects.filter(Q(date_start__gte=datefrom_str), Q(date_end__lt=date_str)).values_list('id', flat=True).order_by('id') 
        data_list = data_list.filter(walk_context__in=walkids).order_by('id') 
    if len(coordinates) > 0:
        polylist = list()
        polylist = [tuple(map(float, coor.split(','))) for coor in coordinates]
        polygon = Polygon(polylist)

        dataset = Data.objects.all().values('id','latitude','longitude').order_by('id') 
        ids = [d['id'] for d in dataset if  polygon.contains(Point(float(d['longitude']), float(d['latitude'])))]
        q &= Q(id__in=ids)
    if len(ids_markers) > 0:
            q &= Q(id__in=ids_markers)

    data_list = data_list.filter(q)

    if mode:
        if mode=='y':
            response = []
            if len(data_list) > 0:
                year_set = data_list.annotate(only_year=ExtractYear('datetime')).values('only_year').distinct().order_by('only_year')

                index = year_set[0]['only_year']
                while index <= year_set[len(year_set)-1]['only_year']:
                    response.append({'year': index, 'report':dict()})
                    index += 1

                if opt and opt.lower() == 'g':
                    for resp in response:
                        resp['report']['all'] = {'pcount': 0}
                        resp['report']['n/p'] = {'pcount': 0}

                        resp['report']['all']['pcount'] =  data_list.filter(datetime__year=resp['year'],perception__isnull=False).count()
                        resp['report']['n/p']['pcount'] =  data_list.filter(datetime__year=resp['year'],perception__isnull=True).count()
                else:
                    for resp in response:
                        result = data_list.filter(datetime__year=resp['year']).values('perception').annotate(pcount = Count('perception')).order_by('perception')

                        resp['report']['green'] = {'pcount': 0}
                        resp['report']['yellow'] = {'pcount': 0}
                        resp['report']['red'] = {'pcount': 0}
                        resp['report']['n/p'] = {'pcount': 0}

                        for data in result:
                            if data['perception'] == 'green':
                                resp['report']['green']['pcount'] = data['pcount']
                            elif data['perception'] == 'yellow':
                                resp['report']['yellow']['pcount'] = data['pcount']
                            elif data['perception'] == 'red':
                                resp['report']['red']['pcount'] = data['pcount']
                            elif data['perception'] == None:
                                resp['report']['n/p']['pcount'] = data_list.filter(datetime__year=resp['year'],perception__isnull=True).count()

        if mode=='m':
            response = []

            index = 1
            while index <= 12:
                response.append({'month_id': index, 'month_name': calendar.month_name[index],'report':dict()})
                index += 1

            if opt and opt.lower() == 'g':
                for resp in response:
                    resp['report']['all'] = {'pcount': 0}
                    resp['report']['n/p'] = {'pcount': 0}

                    resp['report']['all']['pcount'] =  data_list.filter(datetime__month=resp['month_id'],perception__isnull=False).count()
                    resp['report']['n/p']['pcount'] =  data_list.filter(datetime__month=resp['month_id'],perception__isnull=True).count()
            else:
                for resp in response:
                    result = data_list.filter(datetime__month=resp['month_id']).values('perception').annotate(pcount = Count('perception')).order_by('perception')
                    resp['report']['green'] = {'pcount': 0}
                    resp['report']['yellow'] = {'pcount': 0}
                    resp['report']['red'] = {'pcount': 0}
                    resp['report']['n/p'] = {'pcount': 0}
                    for data in result:
                        if data['perception'] == 'green':
                            resp['report']['green']['pcount'] = data['pcount']
                        elif data['perception'] == 'yellow':
                            resp['report']['yellow']['pcount'] = data['pcount']
                        elif data['perception'] == 'red':
                            resp['report']['red']['pcount'] = data['pcount']
                        elif data['perception'] == None:
                            resp['report']['n/p']['pcount'] = data_list.filter(datetime__month=resp['month_id'],perception__isnull=True).count()

        if mode == 'd':
            response = []
            index = 0
            while index < 7:
                response.append({'day_id': index, 'day_name': calendar.day_name[index],'report': dict()})
                index += 1

            if opt and opt.lower() == 'g':
                for resp in response:
                    resp['report']['all'] = {'pcount': 0}
                    resp['report']['n/p'] = {'pcount': 0}

                    resp['report']['all']['pcount'] =  data_list.filter(datetime__week_day=resp['day_id'],perception__isnull=False).count()
                    resp['report']['n/p']['pcount'] =  data_list.filter(datetime__week_day=resp['day_id'],perception__isnull=True).count()

            else:
                for resp in response:
                    result = data_list.filter(datetime__week_day=resp['day_id']).values('perception').annotate(pcount = Count('perception')).order_by('perception')
                    resp['report']['green'] = {'pcount': 0}
                    resp['report']['yellow'] = {'pcount': 0}
                    resp['report']['red'] = {'pcount': 0}
                    resp['report']['n/p'] = {'pcount': 0}
                    for data in result:
                        if data['perception'] == 'green':
                            resp['report']['green']['pcount'] = data['pcount']
                        elif data['perception'] == 'yellow':
                            resp['report']['yellow']['pcount'] = data['pcount']
                        elif data['perception'] == 'red':
                            resp['report']['red']['pcount'] = data['pcount']
                        elif data['perception'] == None:
                            resp['report']['n/p']['pcount'] = data_list.filter(datetime__week_day=resp['day_id'],perception__isnull=True).count()


    else:
        response = dict()
        if opt and opt.lower() == 'g':
            response['all'] = {'pcount': 0}
            response['n/p'] = {'pcount': 0}

            response['all']['pcount'] =  data_list.filter(perception__isnull=False).count()
            response['n/p']['pcount'] =  data_list.filter(perception__isnull=True).count()

        else:
            response['green'] = {'pcount': 0}
            response['yellow'] = {'pcount': 0}
            response['red'] = {'pcount': 0}
            response['n/p'] = {'pcount': 0}
            result = data_list.values('perception').annotate(pcount = Count('perception')).order_by('perception')

            for data in result:
                if data['perception'] == 'green':
                    response['green']['pcount'] = data['pcount']
                elif data['perception'] == 'yellow':
                    response['yellow']['pcount'] = data['pcount']
                elif data['perception'] == 'red':
                    response['red']['pcount'] = data['pcount']
                elif data['perception'] == None:
                    response['n/p']['pcount'] = data_list.filter(perception__isnull=True).count()

    return JsonResponse(response, safe=False)



@swagger_auto_schema(methods=['get'], 
    manual_parameters=[ 
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('walkcontext', openapi.IN_QUERY, "Insert walk id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('iso2', openapi.IN_QUERY, "Insert country code", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date from', openapi.IN_QUERY, "Insert date from", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date to', openapi.IN_QUERY, "Insert date to", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('mode', openapi.IN_QUERY, "Insert mode", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
    ], tags=['reports']) 
@api_view(['GET'])
def ranking_icon(request):
    """
    This function get a list with ten most used buttons. This report can generate overall, by user or by walk or you can mix user and walk for get more specific information. If you add the mode parameter the ranking format change for colour.

    ## Parameter filters:     
     - **user id**
     - **walk context = walk id**
     - **country code = iso2**
     - **date_from = format MM/DD/YYYY**
     - **date_to = format MM/DD/YYYY**
     - **mode**

    **You can use user id or none with the other filters. In the mode case you must complete with word sr**
    """    
    id_user = request.GET.get('user',None)  
    walkcontext = request.GET.get('walkcontext', None)
    iso2 = request.GET.get('iso2', None) 
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    mode = request.GET.get('mode', None)  
    walkids = ''
       
    data_list = Data.objects.select_related().all().order_by('walk_context','id')       

    if id_user:
        user_object = WalkUser.objects.get(pk=id_user)
        if user_object:
            if user_object.profile == 'contributor':                
                walkids = WalkContext.objects.filter(user=user_object).values_list('id', flat=True).order_by('id') 
                data_list = data_list.filter(walk_context__in=walkids).order_by('id')  
            elif user_object.profile == 'licensed' and not user_object.country == 'global':                 
                walkids = WalkContext.objects.filter(countryCode=user_object.countryCode).values_list('id', flat=True).order_by('id') 
                data_list = data_list.filter(walk_context__in=walkids).order_by('id')  
    if walkcontext:
        data_list = data_list.filter(walk_context=walkcontext).order_by('id')  
    if iso2:
        walkids = WalkContext.objects.filter(countryCode=iso2).values_list('id', flat=True).order_by('id') 
        data_list = data_list.filter(walk_context__in=walkids).order_by('id') 
    if date_from and date_to: 
        datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
        datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'
    
        dateto_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY 
        next_day = dateto_format + datetime.timedelta(days=1)            
        date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD
        
        walkids = WalkContext.objects.filter(Q(date_start__gte=datefrom_str), Q(date_end__lt=date_str)).values_list('id', flat=True).order_by('id') 
        data_list = data_list.filter(walk_context__in=walkids).order_by('id') 

    data_value = ''
    ids = []
    if mode and mode == 'sr':
        response = dict({'totalgreen': 0, 'totalyellow': 0, 'totalred':0 , 'total': 0, 'green': list(), 'yellow': list(), 'red': list()})  
        for id in data_list:
            ids.append(id.id)
        
        data_value = DataValue.objects.filter(data__in=ids).values('value').annotate(bcount = Count('value')).order_by('-bcount')
        
        index = 0
        for data in data_value:
            button = Button.objects.get(pk=data['value'])  

            response[button.clasification].append({'id': data['value'], 'bcount': data['bcount'], 'tag': button.tag, 'description': button.description, 'clasification': button.clasification, 'image': request.build_absolute_uri(button.image.url)})
            response['total'+(button.clasification if button.clasification == 'green' or button.clasification == 'yellow' or button.clasification == 'red' else '' )] += data['bcount']
    else:
        response = dict({'ranking_list': list(), 'comments': list()})

        for id in data_list:
            ids.append(id.id)
            if id.comments and (id.comments not in response['comments']):
                response['comments'].append(id.comments)

        data_value = DataValue.objects.filter(data__in=ids).values('value').annotate(bcount = Count('value')).order_by('-bcount')[:10]

        for data in data_value:
            button = Button.objects.get(pk=data['value'])
            response['ranking_list'].append({'id': data['value'], 'bcount': data['bcount'], 'tag': button.tag, 'description': button.description, 'clasification': button.clasification, 'image': request.build_absolute_uri(button.image.url)})
        
    return JsonResponse(response,safe=False)




#for points - data
@swagger_auto_schema(methods=['get'],
    manual_parameters=[
        openapi.Parameter('username', openapi.IN_QUERY, "Insert username", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('country', openapi.IN_QUERY, "Insert country code", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('city', openapi.IN_QUERY, "Insert city", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('ability', openapi.IN_QUERY, "Insert ability", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('age', openapi.IN_QUERY, "Insert age", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('gender', openapi.IN_QUERY, "Insert gender", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('decision', openapi.IN_QUERY, "Insert decision", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('familiarity', openapi.IN_QUERY, "Insert familiarity", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('group size', openapi.IN_QUERY, "Insert group size", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('perception', openapi.IN_QUERY, "Insert perception", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('purpose', openapi.IN_QUERY, "Insert purpose", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)
    ], tags=['reports'])
@api_view(['GET'])
def get_dataset(request):  
    """
    This function get a list the points (data) with diferent filters. This report can generate overall, by user, city, user context variables (gender, ability, age) or by walk context variables
    (perception, group_size, decision, purpose, familiarity). Also you can mix the parameters for get more specific information.

    ## Parameter filters:
     - **username**
     - **user id**
     - **country = country code is a two chatacter code. People call it ISO2 code**
     - **city**
     - **ability = can be a list**
     - **age = can be a list**
     - **gender = can be a list**
     - **decision = can be a list**
     - **familiarity = can be a list**
     - **group size = can be a list**
     - **perception = can be a list**
     - **purpose = can be a list**

    **You can use username or user id or none with the other filters**
    """
    username = request.GET.get('username',None)
    id_user = request.GET.get('user',None)  
    city = request.GET.get('city', None) 
    country = request.GET.get('country', None) 
    gender = request.GET.getlist('gender')  
    age = request.GET.getlist('age') 
    ability = request.GET.getlist('ability') 
    perception = request.GET.getlist('color') 
    group_size = request.GET.getlist('group')
    decision = request.GET.getlist('decision')
    purpose = request.GET.getlist('purpose')
    familiarity = request.GET.getlist('familiarity')
  
    response = list()
    user_id = 0

    data_list = Data.objects.select_related('context','walk_context').all().order_by('-id')
    walk_list = WalkContext.objects.all()
    usercontext_list = UserContext.objects.all()
    datavalue_list = DataValue.objects.select_related('data','value').all()
       
    if username or id_user:
        if username and not id_user: 
            user_object = WalkUser.objects.get(username=username)  
            if user_object:
                user_id = user_object.id
                data_list = data_list.filter(user=user_object.id)
                
        elif id_user and not username:
            data_list = data_list.filter(user=id_user)
            user_id = id_user
        else:
            return HttpResponse('username or id user required (just one variable).',content_type='text/plain')
    
    if country:  
        iso2_upper = country.upper() 
        walkcontext_object = walk_list.filter(countryCode=iso2_upper)           
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))        
            
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)  

    if city: 
        walkcontext_object = walk_list.filter(city=city) 
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))
        
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)  

    
    if len(gender) > 0:  
        usercontext_object = usercontext_list.filter(gender__in=gender)      
        if int(user_id) > 0:
            usercontext_object = usercontext_object.filter(user=int(user_id)) 

        ids = [i.id for i in usercontext_object]
        data_list = data_list.filter(context__in=ids)

    if len(age) > 0:       
        usercontext_object = usercontext_list.filter(age__in=age) 
        if int(user_id) > 0:
            usercontext_object = usercontext_object.filter(user=int(user_id))
           
        ids = [i.id for i in usercontext_object]
        data_list = data_list.filter(context__in=ids)

    if len(ability) > 0:  
        usercontext_object = usercontext_list.filter(ability__in=ability)              
        if int(user_id) > 0:
            usercontext_object = usercontext_object.filter(user=int(user_id),ability__in=ability)
              
        ids = [i.id for i in usercontext_object]
        data_list = data_list.filter(context__in=ids)


    if len(perception) > 0:   
        data_list = data_list.filter(perception__in=perception)     
        if int(user_id) > 0:
            data_list = data_list.filter(user=int(user_id))
        

    if len(group_size) > 0:   
        walkcontext_object = walk_list.filter(group_size__in=group_size)       
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))        
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)    


    if len(decision) > 0: 
        walkcontext_object = walk_list.filter(decision__in=decision)            
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))       
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)


    if len(purpose) > 0:
        walkcontext_object = walk_list.filter(purpose__in=purpose)              
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))   
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)

    if len(familiarity) > 0: 
        walkcontext_object = walk_list.filter(familiarity__in=familiarity)             
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))       
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)  
    
    noicon_b = Button.objects.get(tag='NoIcon')
    index = 0
    for d in data_list:        
        if index == 5000:
            break
        
        icon_data = list() 
       
        currentdata_value  = datavalue_list.filter(data=d.id).select_related('value')

        if len(currentdata_value) > 0:
            for b in currentdata_value:
                icon_data.append({'id': b.value.id, 'id_datavalue': b.id, 'tag': b.value.tag, 'description': b.value.description, 'clasification': b.value.clasification, 'image': request.build_absolute_uri(b.value.image.url)})
        else:
            icon_data.append({'id': noicon_b.id, 'id_datavalue': 0, 'tag': noicon_b.tag, 'description': noicon_b.description, 'clasification': noicon_b.clasification, 'image': request.build_absolute_uri(noicon_b.image.url)})
                
        response.append({
        "id":          d.id,
        "latitude":    d.latitude,
        "longitude":   d.longitude,
        "datetime":    d.datetime,
        "comments":    d.comments,
        "gpsaccuracy": d.gpsaccuracy,
        "perception":  d.perception,
        "user":        d.user.id,
        "context":     d.context.id,
        "context_data": dict({'id': d.context.id, 'gender': d.context.gender, 'age': d.context.age, 'ability':d.context.ability}),
        "walk_context": d.walk_context.id,
        'walk_context_data': dict({'id': d.walk_context.id, 'group_size': d.walk_context.group_size, 'decision': d.walk_context.decision, 'purpose':d.walk_context.purpose, 'familiarity': d.walk_context.familiarity}),
        'city': d.walk_context.city,
        'country': d.walk_context.countryCode,
        "icon_data": icon_data
        })   
        index+=1
    return JsonResponse(response, safe=False)
    
    
@swagger_auto_schema(methods=['get'],
    manual_parameters=[
        openapi.Parameter('username', openapi.IN_QUERY, "Insert username", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('country', openapi.IN_QUERY, "Insert country code", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('city', openapi.IN_QUERY, "Insert city", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('ability', openapi.IN_QUERY, "Insert ability", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('age', openapi.IN_QUERY, "Insert age", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('gender', openapi.IN_QUERY, "Insert gender", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('decision', openapi.IN_QUERY, "Insert decision", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('familiarity', openapi.IN_QUERY, "Insert familiarity", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('group size', openapi.IN_QUERY, "Insert group size", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('perception', openapi.IN_QUERY, "Insert perception", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('purpose', openapi.IN_QUERY, "Insert purpose", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)
    ], tags=['reports'])
@api_view(['GET'])
def get_datasetNew(request):  
    """
    This function get a list the points (data) with diferent filters. This report can generate overall, by user, city, user context variables (gender, ability, age) or by walk context variables
    (perception, group_size, decision, purpose, familiarity). Also you can mix the parameters for get more specific information.

    ## Parameter filters:
     - **username**
     - **user id**
     - **country = country code is a two chatacter code. People call it ISO2 code**
     - **city**
     - **ability = can be a list**
     - **age = can be a list**
     - **gender = can be a list**
     - **decision = can be a list**
     - **familiarity = can be a list**
     - **group size = can be a list**
     - **perception = can be a list**
     - **purpose = can be a list**

    **You can use username or user id or none with the other filters**
    """
    username = request.GET.get('username',None)
    id_user = request.GET.get('user',None)  
    city = request.GET.get('city', None) 
    country = request.GET.get('country', None) 
    gender = request.GET.getlist('gender')  
    age = request.GET.getlist('age') 
    ability = request.GET.getlist('ability') 
    perception = request.GET.getlist('color') 
    group_size = request.GET.getlist('group')
    decision = request.GET.getlist('decision')
    purpose = request.GET.getlist('purpose')
    familiarity = request.GET.getlist('familiarity')
    id_user_profile = request.GET.get('user_profile', None)
  
    response = list()
    user_id = 0    

    data_list = Data.objects.only('id', 'latitude', 'longitude', 'datetime', 'comments', 'gpsaccuracy', 'perception', 'user', 'context__id', 'context__gender', 'context__age', 'context__ability', 'walk_context__id', 'walk_context__group_size', 'walk_context__decision', 'walk_context__purpose', 'walk_context__familiarity', 'walk_context__city', 'walk_context__countryCode').select_related('context', 'walk_context').all().order_by('-id')
    data_list = data_list.prefetch_related('datavalue_set__value')
    walk_list = WalkContext.objects.all()
    usercontext_list = UserContext.objects.all()

    user_profile = WalkUser.objects.get(pk=id_user_profile)
    if user_profile.profile == 'licensed' and (user_profile.countryCode and user_profile.countryCode != 'global'): 
        country = user_profile.countryCode
          
    if username or id_user:
        if username and not id_user: 
            user_object = WalkUser.objects.get(username=username)  
            if user_object:
                user_id = user_object.id
                data_list = data_list.filter(user=user_object.id)
                
        elif id_user and not username:
            data_list = data_list.filter(user=id_user)
            user_id = id_user
        else:
            return HttpResponse('username or id user required (just one variable).',content_type='text/plain')
    
    if country:  
        iso2_upper = country.upper() 
        walkcontext_object = walk_list.filter(countryCode=iso2_upper)           
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))        
            
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)  

    if city: 
        walkcontext_object = walk_list.filter(city=city) 
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))
        
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)  

    
    if len(gender) > 0:  
        usercontext_object = usercontext_list.filter(gender__in=gender)      
        if int(user_id) > 0:
            usercontext_object = usercontext_object.filter(user=int(user_id)) 

        ids = [i.id for i in usercontext_object]
        data_list = data_list.filter(context__in=ids)

    if len(age) > 0:       
        usercontext_object = usercontext_list.filter(age__in=age) 
        if int(user_id) > 0:
            usercontext_object = usercontext_object.filter(user=int(user_id))
           
        ids = [i.id for i in usercontext_object]
        data_list = data_list.filter(context__in=ids)

    if len(ability) > 0:  
        usercontext_object = usercontext_list.filter(ability__in=ability)              
        if int(user_id) > 0:
            usercontext_object = usercontext_object.filter(user=int(user_id),ability__in=ability)
              
        ids = [i.id for i in usercontext_object]
        data_list = data_list.filter(context__in=ids)


    if len(perception) > 0:   
        data_list = data_list.filter(perception__in=perception)     
        if int(user_id) > 0:
            data_list = data_list.filter(user=int(user_id))
        

    if len(group_size) > 0:   
        walkcontext_object = walk_list.filter(group_size__in=group_size)       
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))        
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)    


    if len(decision) > 0: 
        walkcontext_object = walk_list.filter(decision__in=decision)            
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))       
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)


    if len(purpose) > 0:
        walkcontext_object = walk_list.filter(purpose__in=purpose)              
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))   
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)

    if len(familiarity) > 0: 
        walkcontext_object = walk_list.filter(familiarity__in=familiarity)             
        if int(user_id) > 0:
            walkcontext_object = walkcontext_object.filter(user=int(user_id))       
        ids = [i.id for i in walkcontext_object]
        data_list = data_list.filter(walk_context__in=ids)  
     
    noicon_b = Button.objects.get(tag='NoIcon')
    context_dict = {context.id: {'gender': context.gender, 'age': context.age, 'ability': context.ability} for context in usercontext_list}
    walk_context_dict = {walk_context.id: {'group_size': walk_context.group_size, 'decision': walk_context.decision, 'purpose': walk_context.purpose, 'familiarity': walk_context.familiarity, 'city': walk_context.city, 'countryCode': walk_context.countryCode} for walk_context in walk_list}
    value_dict = {value.id: {'tag': value.tag, 'description': value.description, 'clasification': value.clasification, 'image': request.build_absolute_uri(value.image.url)} for value in Button.objects.all()}

    if user_profile.profile == 'licensed' and user_profile.countryCode == 'global': 
        data_list = data_list[:4000] 
    elif user_profile.profile == 'contributor':
        data_list = data_list[:3500] 
    
    for d in data_list:        
        icon_data = list() 
       
        currentdata_value = d.datavalue_set.all()
        if len(currentdata_value) > 0:
            for b in currentdata_value:
                icon_data.append({'id': b.value.id, 'id_datavalue': b.id, 'tag': value_dict[b.value.id]['tag'], 'description': value_dict[b.value.id]['description'], 'clasification': value_dict[b.value.id]['clasification'], 'image': value_dict[b.value.id]['image']})
        else:
            icon_data.append({'id': noicon_b.id, 'id_datavalue': 0, 'tag': noicon_b.tag, 'description': noicon_b.description, 'clasification': noicon_b.clasification, 'image': request.build_absolute_uri(noicon_b.image.url)})
        
        response.append({
        "id":          d.id,
        "latitude":    d.latitude,
        "longitude":   d.longitude,
        "datetime":    d.datetime,
        "comments":    d.comments,
        "gpsaccuracy": d.gpsaccuracy,
        "perception":  d.perception,
        "user":        d.user.id,        
        "context_data": dict({'id': d.context.id, 'gender': context_dict[d.context.id]['gender'], 'age': context_dict[d.context.id]['age'], 'ability': context_dict[d.context.id]['ability']}),
        "walk_context_data": dict({'id': d.walk_context.id, 'group_size': walk_context_dict[d.walk_context.id]['group_size'], 'decision': walk_context_dict[d.walk_context.id]['decision'], 'purpose': walk_context_dict[d.walk_context.id]['purpose'], 'familiarity': walk_context_dict[d.walk_context.id]['familiarity'], 'city': walk_context_dict[d.walk_context.id]['city'], 'countryCode': walk_context_dict[d.walk_context.id]['countryCode']}),        
        "icon_data": icon_data
        })   
    return JsonResponse(response, safe=False)


@swagger_auto_schema(methods=['get'], tags=['reports'])
@api_view(['GET'])
def get_dataset_public(request):  
    """
    This function get a list the points without buttons (data) for public users.   
    """  
    response = list()  
  
    data_list = Data.objects.only('id', 'latitude', 'longitude', 'datetime', 'comments', 'gpsaccuracy', 'perception', 'user', 'context__id', 'context__gender', 'context__age', 'context__ability', 'walk_context__id', 'walk_context__group_size', 'walk_context__decision', 'walk_context__purpose', 'walk_context__familiarity', 'walk_context__city', 'walk_context__countryCode').select_related('context', 'walk_context').all().order_by('-id')
    walk_list = WalkContext.objects.all()
    usercontext_list = UserContext.objects.all()    
    
    data_list = data_list[:3500]
    context_dict = {context.id: {'gender': context.gender, 'age': context.age, 'ability': context.ability} for context in usercontext_list}
    walk_context_dict = {walk_context.id: {'group_size': walk_context.group_size, 'decision': walk_context.decision, 'purpose': walk_context.purpose, 'familiarity': walk_context.familiarity, 'city': walk_context.city, 'countryCode': walk_context.countryCode} for walk_context in walk_list}
    for d in data_list:   
        response.append({
        "id":          d.id,
        "latitude":    d.latitude,
        "longitude":   d.longitude,
        "datetime":    d.datetime,
        "comments":    d.comments,
        "gpsaccuracy": d.gpsaccuracy,
        "perception":  d.perception,
        "user":        d.user.id,        
        "context_data": dict({'id': d.context.id, 'gender': context_dict[d.context.id]['gender'], 'age': context_dict[d.context.id]['age'], 'ability': context_dict[d.context.id]['ability']}),        
        "walk_context_data": dict({'id': d.walk_context.id, 'group_size': walk_context_dict[d.walk_context.id]['group_size'], 'decision': walk_context_dict[d.walk_context.id]['decision'], 'purpose': walk_context_dict[d.walk_context.id]['purpose'], 'familiarity': walk_context_dict[d.walk_context.id]['familiarity'], 'city': walk_context_dict[d.walk_context.id]['city'], 'countryCode': walk_context_dict[d.walk_context.id]['countryCode']}),
        "city": d.walk_context.city,
        "country": d.walk_context.countryCode   
    })

    return JsonResponse(response, safe=False)


from django.db import connection
import re
def get_clusters(request):
    grid = request.GET.get('grid',None)

    if not grid:
        return HttpResponse('Grid size required', content_type='text/plain' )
    
    grid_size = float(grid)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ST_AsText(ST_SnapToGrid(ST_MakePoint(longitude, latitude), %s)) AS cluster,
                    COUNT(*) AS count,
                    ARRAY_AGG(id) AS point_ids
            FROM control_data
            GROUP BY cluster
        """, [grid_size])

        result = cursor.fetchall()

        clusters = []
        for cluster, count, point_ids, in result:
            coords = re.match(r'POINT\(([-\d.]+) ([-\d.]+)\)', cluster)
            clusters.append({'geometry': cluster, 'latitude': coords[2], 'longitude': coords[1], 'point_count': count, 'point_list': point_ids})

    return JsonResponse(clusters, safe=False)



def getLastPoint(request):
    user = request.GET.get('user', None)
    response = dict()

    if not user:
        return HttpResponse('user id required', content_type='text/plain')

    user_object = WalkUser.objects.get(pk=user)
    if user_object.profile == 'licensed' and not user_object.countryCode == 'global':
        country = Country.objects.get(iso2=user_object.countryCode)
        response = {'id': 0, 'user': user_object.id, 'latitude': country.latitude, 'longitude': country.longitude}
    
    else:    
        userinfo = Data.objects.filter(user=int(user)).order_by('-id').first()
        response = {'id': userinfo.id, 'user': userinfo.user.id, 'latitude': userinfo.latitude, 'longitude': userinfo.longitude}

    return JsonResponse(response)


def showIconsDuplicate(request):
    response = dict({'cant_duplicate': 0, 'detail':list()})
    query = DataValue.objects.all().order_by('id')
    data_value = query.values('data','value').annotate(bcount = Count('value')).order_by('-data')

    for dv in data_value:
        if dv['bcount'] > 1:
            response['detail'].append({'data': dv['data'], 'value':dv['value'], 'bcount':dv['bcount'], 'id_list': list(), 'delete_list':list()})

    for resp in response['detail']:
        ids = []
        ids_delete = []
        data_value_id = query.filter(data=resp['data'], value=resp['value'])
        i=0
        for dv_id in data_value_id:
            if i>0:
                ids_delete.append(dv_id.id)
            ids.append(dv_id.id)
            i=i+1
        resp['id_list'] = ids
        resp['delete_list'] = ids_delete

    response['cant_duplicate'] = len(response['detail'])
    return JsonResponse(response,safe=False)


def getEmail(request):
    username = request.GET.get('username', None)
    response = dict()

    if not username:
        return HttpResponse('username is required.', content_type='text/plain')
    else:
        user_object= User.objects.get(username=username)
        if not user_object:
            response = dict({'status': 'error', 'message': "user isn't exist."})
        else:
            response = dict({'status': 'success', 'message': 'user exists, getting email.', 'data':{'id': user_object.id, 'username': user_object.username  , 'email': user_object.email if user_object.email else None} })
    return JsonResponse(response)



@swagger_auto_schema(methods=['get'],
    manual_parameters=[
        openapi.Parameter('walk id', openapi.IN_QUERY, "Insert walk id", type=openapi.TYPE_INTEGER)
    ], tags=['others'])
@api_view(['GET'])
def disable_auto_add(request):
    """
    This function is for deactivate the automatic updating in the date end quickly and calculate distance new. Don't use here.

    ## Parameter filters:
     - **walk id**
    """
    walk_id = request.GET.get('walk', None)

    if not walk_id:
        return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Walkcontext id required'})

    if WalkContext.objects.filter(id=int(walk_id)).exists():
        try:
            '''
            walk = WalkContext.objects.get(id=int(walk_id))
            sections = list()
            list_a = list()
            list_b = list()
            total_distance = 0
            dataset = Data.objects.filter(walk_context=walk.id).order_by('id')

            if len(dataset)>0:

                if walk.latitude_start and walk.longitude_start and walk.latitude_end and walk.longitude_end:
                    list_a.append(list([walk.latitude_start, walk.longitude_start]))
                    list_b.append(list([dataset[0].latitude, dataset[0].longitude]))

                for i, point in enumerate(dataset, start=0):
                    if i < len(dataset)-1:
                        list_a.append(list([point.latitude, point.longitude]))
                    if i > 0:
                        list_b.append(list([point.latitude, point.longitude]))

                if walk.latitude_start and walk.longitude_start and walk.latitude_end and walk.longitude_end:
                    list_b.append(list([walk.latitude_end, walk.longitude_end]))
                    list_a.append(list([dataset[len(dataset)-1].latitude, dataset[len(dataset)-1].longitude]))

                for p_start, p_end in zip(list_a, list_b):
                    sections.append({'start': p_start, 'end': p_end})

                for section in sections:
                    total_distance = total_distance + haversine(section['start'], section['end'], unit='km')
            
            '''
            total_distance = 0
            walkset = WalkContext.objects.get(id=int(walk_id))
            dataset = Data.objects.filter(walk_context=walkset.id).values('id','latitude','longitude').order_by('id')
            if len(dataset)>0:
                if walkset.latitude_start and walkset.longitude_start and walkset.latitude_end and walkset.longitude_end:
                    coords = [(walkset.latitude_start, walkset.longitude_start)] + [(p['latitude'], p['longitude']) for p in dataset] + [(walkset.latitude_end, walkset.longitude_end)]
                    distancias = [haversine(coords[i - 1], coords[i], unit='km') for i in range(1, len(coords))]
                    total_distance = sum(distancias)
            
            WalkContext.objects.filter(id=int(walk_id)).update(disable_date_auto_now=True,distance_new=total_distance)
            

            return JsonResponse({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': 'Walkcontext field updated!'})
        except:
            return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Walkcontext field not updated'})
    return JsonResponse({'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No walkcontext found" })



def multidisable_auto_add(request):

    if WalkContext.objects.filter(Q(disable_date_auto_now=False),Q(latitude_end__isnull=False),Q(longitude_end__isnull=False)).exists():
        try:
            update_data = WalkContext.objects.filter(Q(disable_date_auto_now=False),Q(latitude_end__isnull=False),Q(longitude_end__isnull=False)).update(disable_date_auto_now=True)
            return JsonResponse({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': 'Walkcontext field updated!', 'pcount': update_data})
        except:
            return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Walkcontext field not updated'})
    return JsonResponse({'status': 'error', 'code': Response_status.HTTP_404_NOT_FOUND, 'message': "No walkcontext found" })



def check_unfinish_walks(request):
    walkset = WalkContext.objects.filter(Q(disable_date_auto_now=False),Q(latitude_end__isnull=False),Q(longitude_end__isnull=False)).order_by('-id')

    if len(walkset) > 0:
        #walk_ids = walkset.values_list('id', flat=True).order_by('-id')
        walks = [{'id': w.id, 'latitude_end': w.latitude_end, 'longitude_end': w.longitude_end, 'disable_date_auto_now': w.disable_date_auto_now} for w in walkset]
        return JsonResponse({'unfinish_walks': str(len(walkset)), 'walks': walks})
    return JsonResponse({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "All walkcontext finish" })



@swagger_auto_schema(methods=['get'],
    manual_parameters=[ openapi.Parameter('username', openapi.IN_QUERY, "Insert username", type=openapi.TYPE_ARRAY,
                      items=openapi.Items(type=openapi.TYPE_STRING), required=True, collection_format='multi', uniqueItems=True),
    ], tags=['others'])
@api_view(['GET'])
def checkUsername(request):
    """
    This function is for test the existence of the username in the database. If the username exists, the function notify you for avoid duplication.

    ## Parameter filters:
     - **username**
     - **old_username**
    **The input old username is used when you wanna update the username, for a correct searching, ommiting your actual username**
    """
    username = request.GET.get('username', None)
    old_username = request.GET.get('old_username', None)

    
    if not username:
        return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Username required'})

    cast_username = username.lower()
    query = User.objects.all().annotate(username_lower=Lower('username'))
   
    if old_username:        
        cast_old = old_username.lower()
        check = query.filter(username_lower = cast_username).exclude(username_lower=cast_old).exists()
    else:
        check = query.filter(username_lower = cast_username).exists()
    
    if check:
        return JsonResponse({'status': 'error', 'code': Response_status.HTTP_302_FOUND, 'message': "The username exists" })
    return JsonResponse({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "The username can be created" })



#for walks
@swagger_auto_schema(methods=['get'],
    manual_parameters=[
        openapi.Parameter('date from', openapi.IN_QUERY, "Insert date from", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date to', openapi.IN_QUERY, "Insert date to", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('city', openapi.IN_QUERY, "Insert city", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),

    ], tags=['reports'])
@api_view(['GET'])
def getDataWalk_range(request):
    """
    This function get a list the walks with diferent filters. This report can generate overall, by two dates, city and user. Also you can mix the parameters for get more specific information.

    ## Parameter filters:
     - **date_from = format MM/DD/YYYY**
     - **date_to = format MM/DD/YYYY**
     - **user id**
     - **city**
     - **country**

    **You have to use date from and date to together**
    """
    date_from = request.GET.get('date_from', None)
    date_to = request.GET.get('date_to', None)
    user = request. GET.get('user', None)
    city = request.GET.get('city', None)
    country = request.GET.get('country',None)
    response = dict({'cant_walks': 0, 'walkset': list()})
    
    if not date_from and not date_to:
        return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Date from and date to required'})
    
    walkset = WalkContext.objects.all()
    data_list = Data.objects.select_related('context','walk_context').all().order_by('walk_context','id')
    datavalue_list = DataValue.objects.select_related('data','value').all()

    datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
    datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'
   
    date_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY 
    next_day = date_format + datetime.timedelta(days=1)            
    date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD

    if user:
        walkset = walkset.filter(user=int(user))
    if city:
        cast_city = city.lower()
        walkset = walkset.annotate(city_lower=Lower('city'))   
        walkset = walkset.filter(city_lower = cast_city)
    if country:
        cast_country = country.upper()
        walkset = walkset.filter(countryCode = cast_country)
    
    walkset = walkset.filter(Q(date_start__gte=datefrom_str), Q(date_end__lt=date_str))
    response['cant_walks'] = len(walkset)

    for w in walkset:
        
        response['walkset'].append({
            'id': w.id,
            'user': w.user.id if w.user else None,
            'version': w.version.id if w.version else None,
            'decision': w.decision,
            'purpose': w.purpose,
            'group_size': w.group_size,
            'familiarity': w.familiarity,
            'date_start': w.date_start.strftime('%Y-%m-%d %H:%M:%S'),            
            'latitude_start': w.latitude_start,
            'longitude_start': w.longitude_start,
            'gpsaccuracy_start': w.gpsaccuracy_start,
            'date_end': w.date_end.strftime('%Y-%m-%d %H:%M:%S'),
            'latitude_end': w.latitude_end,
            'longitude_end': w.longitude_end,
            'gpsaccuracy_end': w.gpsaccuracy_end,
            'weather_code': w.weather_code,
            'weather_codition': w.weather_codition,
            'weather_text': w.weather_text,
            'temperature': w.temperature,
            'city': w.city,
            'countryCode': w.countryCode,
            'cant_points': 0,
            'dataset': list()
        })
    
    noicon_b = Button.objects.get(tag='NoIcon')
    for resp in response['walkset']:
        dataset = data_list.filter(walk_context=resp['id']).select_related('walk_context').order_by('id')
        resp['cant_points'] = len(dataset)

        if len(dataset) > 0:
            for d in dataset:
                icon_data = list()   
                currentdata_value  = datavalue_list.filter(data=d.id)

                if len(currentdata_value) > 0:
                    for b in currentdata_value:                    
                        icon_data.append({'id': b.value.id, 'tag': b.value.tag, 'description': b.value.description, 'clasification': b.value.clasification, 'image': request.build_absolute_uri(b.value.image.url)})        
                else:
                    icon_data.append({'id': noicon_b.id, 'id_datavalue': 0, 'tag': noicon_b.tag, 'description': noicon_b.description, 'clasification': noicon_b.clasification, 'image': request.build_absolute_uri(noicon_b.image.url)})

                resp['dataset'].append({
                    'id': d.id,
                    'user': d.user.id,
                    'context': d.context.id,
                    'walk_context': d.walk_context.id,
                    'latitude': d.latitude,
                    'longitude': d.longitude,
                    'datetime': d.datetime,
                    'comments': d.comments,
                    'gpsaccuracy': d.gpsaccuracy,
                    'perception': d.perception,
                    'icon_data': icon_data
                
                })

    return JsonResponse(response, safe=False)



@swagger_auto_schema(methods=['get'],
        manual_parameters=[
            openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
            openapi.Parameter('mode', openapi.IN_QUERY, "Insert mode", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        ], tags=['others'])
@api_view(['GET'])
def get_countries(request):
    """
    This function get a list of countries  save in database in each walk. You can filter for user. 
    
    ## Parameter filters:
     - **user id**
     - **mode = mode for country list  with points (mode = cd)**
    """
    id_user = request.GET.get('user',None)
    mode = request.GET.get('mode','')
    response = list()
    walk = ''

    if id_user:
        user_object = WalkUser.objects.get(pk=id_user)
        if user_object:
            if user_object.profile == 'contributor':
                walk =  WalkContext.objects.filter(user=user_object).values('countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('countryCode')   
            elif user_object.profile == 'licensed' and not user_object.country == 'global': 
                walk =  WalkContext.objects.filter(countryCode=user_object.countryCode).values('countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('countryCode')   
            else:
                walk =  WalkContext.objects.values('countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('countryCode')     
                
    else:
        walk =  WalkContext.objects.values('countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('countryCode')     
    if mode == 'cd':
        walk_data = walk.filter(num_data__gt=0).order_by('countryCode')
    else:
        walk_data =  walk.filter(num_data__gte=0).order_by('countryCode')
    
    id_countries = walk_data.values_list('countryCode', flat=True).distinct()

    list_country = Country.objects.filter(iso2__in=id_countries).order_by('slug')    
    [response.append({'name':c.name, 'slug': c.slug,'iso2':c.iso2})  for c in list_country ]
    return JsonResponse(response, safe=False)




#@swagger_auto_schema(methods=['get'], tags=['others'])
#@api_view(['GET'])
def fillcodeCountry(request):
  #  """
  #  This function fill codeCountry variable depending its city or coordinates. No need input parameters 
  #  """
    response = dict()
    try:
        walk = WalkContext.objects.filter(Q(countryCode__isnull=True)|Q(countryCode='N/C')).order_by('id')

        if len(walk) > 0:
            cant_code = 0
            error_id = ''
            index = 0           
            for w in walk: 
                if len(walk) == 1 and w.id == 300:
                    cant_code = 1
                    break
                resp = getaddress(w.latitude_start,w.longitude_start,'country')                 
                if not resp == 'Error':
                    country_code = resp['address']['country_code'].upper()
                    country = Country.objects.get(iso2=country_code)              
                    w.countryCode = country.iso2
                    w.save()
                    cant_code = cant_code+1
                else:
                    error_id = error_id + str(w.id) + ', '
                index = index + 1
                print(round((index/len(walk))*100,4))
                    
            if cant_code == len(walk):
                response = {    'status': 'success',  'code': Response_status.HTTP_200_OK,   'message': "countryCode filled sucessfully" }
            else:
                return JsonResponse({'status': 'error',  'code': Response_status.HTTP_400_BAD_REQUEST,   'message': "Error in Walk ("+error_id[:-2]+")"})
        else:
            response = {    'status': 'success',  'code': Response_status.HTTP_200_OK,   'message': "Walkcontext with empty countryCode no found" }
    except:
        response = {    'status': 'error',  'code': Response_status.HTTP_400_BAD_REQUEST,   'message': "Error getting walkcontext" }
    return JsonResponse(response)


#PENDIENTE
#@swagger_auto_schema(methods=['get'],
#        manual_parameters=[openapi.Parameter('mode', openapi.IN_QUERY, "Insert mode", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
#        ], tags=['others'])
#@api_view(['GET'])
def get_cities(request):
#    """
#    This function get a list of cities save in database in each walk. Filtering the none city and deleted the duplicate one.
#    
#    ## Parameter filters:
#     - **mode = mode for list cities with points (mode = cd)**
#    """
    mode = request.GET.get('mode','')
    response = list()
    walk_data = WalkContext.objects.filter(city_tableid__gt = 0).exclude(Q(city=None),Q(city='')).order_by('city')
    walk =  walk_data.annotate(
                                num_data = models.ExpressionWrapper(Count(F('data')),
                                output_field=models.IntegerField())
                            )
    
    walk_datasc = WalkContext.objects.filter(city_tableid = 0).order_by('city')    
   
    #for i in walk_datasc:
    #    print(i.id,i.city,sep=',')

    cityset = City.objects.all().order_by('country')  
    old_cant_city = len(cityset)
    new_cant_city = 0    
    txt_new_cities = ''
    aux_city = list()

    
    if mode == 'cd':
        walkset = walk.filter(num_data__gt=0).order_by('city')        
    else:
        walkset = walk.filter(num_data__gte=0).order_by('city') 
    
    #walkcontext with city_tableid > 0
    if len(walkset) > 0:
        for w in walkset:
            gps_city = w.city
            slug = slugify(gps_city)
            city = gps_city
                    
            #search in city table
            current_city = cityset.filter(id=w.city_tableid) 

            if len(current_city) == 1:
                city = current_city[0].name
            slug = slugify(city)      
            
            if not city in aux_city:
                aux_city.append(city)
                response.append({'city': city, 'slug': slug, 'gps_city': gps_city if gps_city else city })    
    
    #walkcontext without city_tableid == 0
    if len(walk_datasc) > 0:
        walk_sc =  walk_datasc.annotate(
                                num_data = models.ExpressionWrapper(Count(F('data')),
                                output_field=models.IntegerField())
                            )
        if mode == 'cd':            
            walkset_sc = walk_sc.filter(num_data__gt=0).order_by('city')
        else:           
            walkset_sc = walk_sc.filter(num_data__gte=0).order_by('city') 
        

        for w in walkset_sc:
            gps_city = w.city
            slug = slugify(gps_city)
            city = gps_city

            if city:
                #search in gpscity table
                print(w.city)
                #current_gpscity =  GPSCity.objects.filter(Q(name__contains=w.city)) 

                #if len(current_city) == 1:
                    #city = current_gpscity[0].city.name
                #else:
                    #search for location
                    #resp = getaddress(w.latitude_start,w.longitude_start, 'city') 
                    #if not resp == 'Error':
                        #if len(current_city) == 0:
                        #    city = resp['display_city']                    
                        #dict_key = resp['address'].keys()

                        #country_code = resp['address']['country_code'].upper()
                        #col_country = Country.objects.get(iso2=country_code)
                        #state_name = resp['address']['state'].upper() if 'state' in dict_key  else ''
                        #state_code = resp['address']['ISO3166-2-lvl4'][3:]
                        #col_state = State.objects.filter(Q(name=state_name)|Q(state_code=state_code), country = col_country).first()

                        #current_city = cityset.filter(name=city,country=col_country,state=col_state)
                        
                        #if len(current_city) > 0:
                        #    current_city.update(gpsname=gps_city,postalCode = resp['address']['postcode'])
                        #else:          
                            #Add new city 
                            #if col_state:
                            #    col_latitude    =  resp['lat'].replace(',','.') 
                            #    col_longitude   =  resp['lon'].replace(',','.') 
                            #                            
                            #    City(name=city,gpsname=gps_city, slug = slugify(city), country=col_country, state=col_state, wikiDataId=None, latitude=col_latitude, longitude=col_longitude,postalCode = resp['address']['postcode']).save()                 
                            #    txt_new_cities = txt_new_cities + slugify(city) + ', '
            else:
                #search for location
                resp = getaddress(w.latitude_start,w.longitude_start, 'city') 
                if not resp == 'Error':
                    city = resp['display_city']                    
                    dict_key = resp['address'].keys()

                    country_code = resp['address']['country_code'].upper()
                    col_country = Country.objects.get(iso2=country_code)
                    state_name = resp['address']['state'].upper() if 'state' in dict_key  else ''
                    state_code = resp['address']['ISO3166-2-lvl4'][3:]
                    col_state = State.objects.filter(Q(name=state_name)|Q(state_code=state_code), country = col_country).first()

                    current_city = cityset.filter(name=city,country=col_country,state=col_state)
                        
                    if len(current_city) > 0:
                        current_city.update(gpsname=gps_city,postalCode = resp['address']['postcode'])
                    else:          
                        #Add new city 
                        if col_state:
                            col_latitude    =  resp['lat'].replace(',','.') 
                            col_longitude   =  resp['lon'].replace(',','.') 
                                                    
                            City(name=city,gpsname=gps_city, slug = slugify(city), country=col_country, state=col_state, wikiDataId=None, latitude=col_latitude, longitude=col_longitude,postalCode = resp['address']['postcode']).save()                 
                            txt_new_cities = txt_new_cities + slugify(city) + ', '
                else:
                    #api support
                    pass
            if not city in aux_city:
                aux_city.append(city)
                response.append({'city': city, 'slug': slug, 'gps_city': gps_city if gps_city else city })   
            slug = slugify(city)              
            
    response = sorted(response, key=lambda city:city['slug'])
    
    new_cant_city = City.objects.all().count()    
    if int(old_cant_city) < int(new_cant_city) and txt_new_cities:    
        #send email for admin
        title = 'New city inserted!' if int(new_cant_city)-int(old_cant_city) == 1 else 'New cities inserted!'
        city_text = 'city' if int(new_cant_city)-int(old_cant_city) == 1 else 'cities'
        data_email = {
                    'title': title,                    
                    'greeting': 'Hi administrator!',
                    'text': 'You must check the new ' + city_text + ' inserted and fix in case of error: '+txt_new_cities[:-2],
                    'support_team': SUPPORT_TEAM,
                    'opt': 4,
                }
        
        template = loader.get_template('email/email.html')
        email_menssage = template.render(data_email)

        my_email2 = EmailMessage(title,email_menssage,settings.DEFAULT_FROM_EMAIL,[ADMIN_EMAIL])
        my_email2.content_subtype = 'html'
        my_email2.send()        
    return JsonResponse(response, safe=False)


#PENDIENTE
def fillGeopyName(request):    
    response = dict()
    #try:
    citycheck =  City.objects.annotate(
                            num_data = models.ExpressionWrapper(Count(F('gpscity')),
                            output_field=models.IntegerField())
                        )
    cityset = citycheck.filter(num_data=0)

    v_cities = ""
    for c in cityset:
        #if c.id == 493018:
            #GPSCity(name='Antarctica',city=c).save()
        v_cities = v_cities + str(c.id) + ','
    #print(cityset[0].id)

   
    test = getaddress(-30.025642700000,-82.051920800000, 'city')      
    print(test)
    #print(v_cities)
    return JsonResponse({'num_total': len(cityset)})

    #cityset = City.objects.filter()
    if len(cityset) > 0:
        cant_code = 0
        error_id = ''
        index = 0  
        v_yes = 0
        v_no =0         
        for c in cityset: 
            if c.latitude and c.longitude:                 

                location = getaddress(c.latitude,c.longitude, 'city')                                      
                                
                if  not location == 'Error':
                    #print('ID: '+str(c.id),' &&& city_name: '+c.name)
                    #print(coordinates)
                    #print(location.raw['display_name']) 
                    #print(location.raw['address']) 


                    if  c.name.strip() in location['display_name']:
                        #print('yes')
                        v_yes = v_yes +1
                    else:
                        #print('nope') 
                        v_no = v_no +1     
                    GPSCity(name=location['display_name'],city=c).save()
                    cant_code = cant_code+1                    
                else:
                    error_id = error_id + str(c.id) + ', '
            else:
                error_id = error_id + str(c.id) + ', '
            index = index + 1
            print(round((index/len(cityset))*100,4), end='\n\n')
        print('FROM: '+str(index),' &&& YES: '+str(v_yes),' &&& NO: '+str(v_no) )       
        if cant_code == len(cityset):
            response = {    'status': 'success',  'code': Response_status.HTTP_200_OK,   'message': "geopyname filled sucessfully" }
        else:
            return JsonResponse({'status': 'error',  'code': Response_status.HTTP_400_BAD_REQUEST,   'message': "Error in City ("+error_id[:-2]+")"})
    else:
        response = {    'status': 'success',  'code': Response_status.HTTP_200_OK,   'message': "City with empty geopyname no found" }
    #except:
    #    response = {    'status': 'error',  'code': Response_status.HTTP_400_BAD_REQUEST,   'message': "Error" }
    return JsonResponse(response)


#PENDIENTE
def get_json_file(request):
    geopyset = GPSCity.objects.all()
    response = list()
    
    index=0
    for g in geopyset:           
        response.append({
            'id':g.id,
            'name':g.name,
            'city':g.city.id,
            'city_name': g.city.name,
            'city_slug': g.city.slug,
            'country_code': g.city.country.iso2,
            'state_code': g.city.state.state_code
        })
        index = index + 1
        print(round((index/len(geopyset))*100,4))
       
    
    json_string = json.dumps(response, ensure_ascii=False, indent=4)
    #print(json_string)   

    with open('db_json/gpscity.json', 'w') as outfile:
        #json.dump(json_string, outfile)
        outfile.write(json_string)

    return JsonResponse(response, safe=False)


#PENDIENTE
#def fillGPSname(request):

@swagger_auto_schema(methods=['get'],
    manual_parameters=[        
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER)
    ], tags=['reports'])
@api_view(['GET'])
def csvWebReport_old(request):
    """
    This function get a walk report in overall or by user.

    ## Parameter filters:     
     - **user id**       
    """

    user = request.GET.get('user', '')
    response = dict()
    if request.method == 'GET' and user:       
        walkset = WalkContext.objects.all()

        if user:
            walkset = walkset.filter(user=user).order_by('-id')

        perception_text = ""
        header_csv = [  'user', 'walk_name', 'walk_code', 'walk_decision','walk_purpose','walk_group_size','walk_familiarity', 'n_reports',
                        'walk_weather_code','walk_weather_codition','walk_weather_text','walk_temperature', 'walk_country', 'walk_city',
                        'pedestrian_gender','pedestrian_ability','pedestrian_age',
                        'rep_datetime', 'rep_latitude', 'rep_longitude', 'rep_perception', 'rep_comments',
                        'button_name', 'button_code', 'button_counter', 'button_description',
                        'version_name','version_number','version_country'
                    ]

        filename = 'Reports-{}.csv'.format(datetime.datetime.today().strftime("%Y-%m-%dT%H-%M-%S"))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(header_csv)

        for w in walkset:
            dataset = Data.objects.filter(walk_context=w.id).order_by('-datetime','-id')
            country = Country.objects.filter(iso2=w.countryCode)

            if len(dataset) > 0:
                noicon_b = Button.objects.get(tag='NoIcon')
                for d in dataset:
                    perception_text = "None"

                    if d.perception == 'yellow':
                        perception_text = "Concern"
                    elif d.perception == 'red':
                        perception_text = "Problem"
                    elif d.perception == "green":
                        perception_text = "Good"

                    dvset = DataValue.objects.filter(data=d.id)
                    counter = 1
                    if len(dvset)>0:
                        for dv in dvset:
                            new_row = [ w.user.username,
                                        'Walk'+str(w.id) if w.id else 'None', str(w.id) if w.id else 'None', w.decision if w.id else 'None',w.purpose if w.id else 'None', w.group_size if w.id else 'None',w.familiarity if w.id else 'None', str(w.data_set.count()),
                                        w.weather_code if w.id else 'None',w.weather_codition if w.id else 'None',w.weather_text if w.id else 'N/W', w.temperature if w.id else 'None', country[0].name if len(country) > 0 else 'N/C', w.city if w.id else 'None',      
                                        d.context.gender if d.context.id else 'None',d.context.ability if d.context.id else 'None',d.context.age if d.context.id else 'None',
                                        d.datetime, d.latitude, d.longitude, perception_text, d.comments,
                                        dv.value.tag,dv.value.id, str(counter),dv.value.description,
                                        w.version.name if w.version else 'None', w.version.number_ver if w.version else 'None', w.version.country if w.version else 'None'
                                    ]
                            new_row_selected = [str(x) for x in new_row]
                            writer.writerow(new_row_selected)
                            counter = counter + 1

                    else:
                        new_row = [ w.user.username,
                            'Walk'+str(w.id) if w.id else 'None', str(w.id) if w.id else 'None', w.decision if w.id else 'None',w.purpose if w.id else 'None', w.group_size if w.id else 'None',w.familiarity if w.id else 'None', str(w.data_set.count()),
                            w.weather_code if w.id else 'None',w.weather_codition if w.id else 'None',w.weather_text if w.id else 'N/W', w.temperature if w.id else 'None', country[0].name if len(country) > 0 else 'N/C', w.city if w.id else 'None',                  
                            d.context.gender if d.context.id else 'None',d.context.ability if d.context.id else 'None',d.context.age if d.context.id else 'None',
                            d.datetime, d.latitude, d.longitude, perception_text, d.comments,
                            noicon_b.tag,noicon_b.id, str(counter),noicon_b.description,
                            w.version.name if w.version else 'None', w.version.number_ver if w.version else 'None', w.version.country if w.version else 'None'
                        ]
                        new_row_selected = [str(x) for x in new_row]
                        writer.writerow(new_row_selected)
                        counter = counter + 1

            else:
                new_row = [ w.user.username,
                            'Walk'+str(w.id) if w.id else 'None', str(w.id) if w.id else 'None', w.decision if w.id else 'None',w.purpose if w.id else 'None', w.group_size if w.id else 'None',w.familiarity if w.id else 'None', str(0),
                             w.weather_code if w.id else 'None',w.weather_codition if w.id else 'None',w.weather_text if w.id else 'N/W', w.temperature if w.id else 'None', country[0].name if len(country) > 0 else 'N/C', w.city if w.id else 'None',
                            'None', 'None', 'None',
                            'None', 'None', 'None', 'None', 'None',
                            'None','None','None','None',
                            w.version.name if w.version else 'None', w.version.number_ver if w.version else 'None', w.version.country if w.version else 'None'
                        ]
                new_row_selected = [str(x) for x in new_row]
                writer.writerow(new_row_selected)
        return response
    else:
        return HttpResponse("wrong method and you need user id @admin will punish you", content_type="text/plain")
                        


@swagger_auto_schema(methods=['get'],
    manual_parameters=[        
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('iso2', openapi.IN_QUERY, "Insert country code", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date from', openapi.IN_QUERY, "Insert date from", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date to', openapi.IN_QUERY, "Insert date to", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        
    ], tags=['reports'])
@api_view(['GET'])
def csvWebReport(request):
    """
    This function get a walk report in overall or by user, country code and a set period.

    ## Parameter filters:     
     - **user id**  
     - **country code = iso2**
     - **date_from = format MM/DD/YYYY**
     - **date_to = format MM/DD/YYYY**      
    """

    user = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    iso2 = request.GET.get('iso2', '')     

    response = dict()
    if request.method == 'GET':       
        walkset = WalkContext.objects.all().order_by('-id')           

        if user:
            user_object = WalkUser.objects.get(pk=user)
            if user_object:
                walkset = walkset.filter(user=user_object).order_by('-id')                                   
        if iso2:
            walkset = walkset.filter(countryCode=iso2).order_by('-id')                
        if date_from and date_to: 
            datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
            datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'
        
            dateto_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY 
            next_day = dateto_format + datetime.timedelta(days=1)            
            dateto_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD
            
            walkset = walkset.filter(Q(date_start__gte=datefrom_str), Q(date_end__lt=dateto_str)).order_by('-id')              

        perception_text = ""
        header_csv = [  'user', 'walk_name', 'walk_code', 'walk_decision','walk_purpose','walk_group_size','walk_familiarity', 'n_reports',
                        'walk_weather_code','walk_weather_codition','walk_weather_text','walk_temperature', 'walk_country', 'walk_city',
                        'pedestrian_gender','pedestrian_ability','pedestrian_age',
                        'rep_datetime', 'rep_latitude', 'rep_longitude', 'rep_perception', 'rep_comments',
                        'button_name', 'button_code', 'button_counter', 'button_description',
                        'version_name','version_number','version_country'
                    ]

        filename = 'Reports-{}.csv'.format(datetime.datetime.today().strftime("%Y-%m-%dT%H-%M-%S"))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(header_csv)
        
        for w in walkset:           
            dataset = Data.objects.filter(walk_context=w.id).order_by('-datetime','-id')
            country = Country.objects.filter(iso2=w.countryCode)

            if len(dataset) > 0:
                noicon_b = Button.objects.get(tag='NoIcon')
                for d in dataset:
                    perception_text = "None"

                    if d.perception == 'yellow':
                        perception_text = "Concern"
                    elif d.perception == 'red':
                        perception_text = "Problem"
                    elif d.perception == "green":
                        perception_text = "Good"

                    dvset = DataValue.objects.filter(data=d.id)
                    counter = 1
                    if len(dvset)>0:
                        for dv in dvset:
                            new_row = [ w.user.username,
                                        'Walk'+str(w.id) if w.id else 'None', str(w.id) if w.id else 'None', w.decision if w.id else 'None',w.purpose if w.id else 'None', w.group_size if w.id else 'None',w.familiarity if w.id else 'None', str(w.data_set.count()),
                                        w.weather_code if w.id else 'None',w.weather_codition if w.id else 'None',w.weather_text if w.id else 'N/W', w.temperature if w.id else 'None', country[0].name if len(country) > 0 else 'N/C', w.city if w.id else 'None',      
                                        d.context.gender if d.context.id else 'None',d.context.ability if d.context.id else 'None',d.context.age if d.context.id else 'None',
                                        d.datetime, d.latitude, d.longitude, perception_text, d.comments,
                                        dv.value.tag,dv.value.id, str(counter),dv.value.description,
                                        w.version.name if w.version else 'None', w.version.number_ver if w.version else 'None', w.version.country if w.version else 'None'
                                    ]
                            new_row_selected = [str(x) for x in new_row]
                            writer.writerow(new_row_selected)
                            counter = counter + 1

                    else:
                        new_row = [ w.user.username,
                            'Walk'+str(w.id) if w.id else 'None', str(w.id) if w.id else 'None', w.decision if w.id else 'None',w.purpose if w.id else 'None', w.group_size if w.id else 'None',w.familiarity if w.id else 'None', str(w.data_set.count()),
                            w.weather_code if w.id else 'None',w.weather_codition if w.id else 'None',w.weather_text if w.id else 'N/W', w.temperature if w.id else 'None', country[0].name if len(country) > 0 else 'N/C', w.city if w.id else 'None',                  
                            d.context.gender if d.context.id else 'None',d.context.ability if d.context.id else 'None',d.context.age if d.context.id else 'None',
                            d.datetime, d.latitude, d.longitude, perception_text, d.comments,
                            noicon_b.tag,noicon_b.id, str(counter),noicon_b.description,
                            w.version.name if w.version else 'None', w.version.number_ver if w.version else 'None', w.version.country if w.version else 'None'
                        ]
                        new_row_selected = [str(x) for x in new_row]
                        writer.writerow(new_row_selected)
                        counter = counter + 1

            else:
                new_row = [ w.user.username,
                            'Walk'+str(w.id) if w.id else 'None', str(w.id) if w.id else 'None', w.decision if w.id else 'None',w.purpose if w.id else 'None', w.group_size if w.id else 'None',w.familiarity if w.id else 'None', str(0),
                             w.weather_code if w.id else 'None',w.weather_codition if w.id else 'None',w.weather_text if w.id else 'N/W', w.temperature if w.id else 'None', country[0].name if len(country) > 0 else 'N/C', w.city if w.id else 'None',
                            'None', 'None', 'None',
                            'None', 'None', 'None', 'None', 'None',
                            'None','None','None','None',
                            w.version.name if w.version else 'None', w.version.number_ver if w.version else 'None', w.version.country if w.version else 'None'
                        ]
                new_row_selected = [str(x) for x in new_row]
                writer.writerow(new_row_selected)
        return response
    else:
        return HttpResponse("wrong method and you need user id @admin will punish you", content_type="text/plain")


@swagger_auto_schema(methods=['get'],
    manual_parameters=[
        openapi.Parameter('user_profile', openapi.IN_QUERY, "Insert user profile id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
        openapi.Parameter('iso2', openapi.IN_QUERY, "Insert country code", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date from', openapi.IN_QUERY, "Insert date from", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        openapi.Parameter('date to', openapi.IN_QUERY, "Insert date to", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),

    ], tags=['reports'])
@api_view(['GET'])
def csvWebReportL(request):
    """
    This function get a walk report in overall or by user, country code and a set period for user with licensed profile.

    ## Parameter filters:
     - **user profile**
     - **user id**
     - **country code = iso2**
     - **date_from = format MM/DD/YYYY**
     - **date_to = format MM/DD/YYYY**
    """

    user_profile = request.GET.get('userp', '')
    user = request.GET.get('user', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    iso2 = request.GET.get('iso2', '')

    response = dict()
    walkset = ''
    if request.method == 'GET' and user_profile:
        walkset = WalkContext.objects.all().order_by('-id')
        u_profile_obj = WalkUser.objects.filter(pk=user_profile)

        if u_profile_obj[0].profile == 'licensed' and not u_profile_obj[0].country == 'global':
            walkset = walkset.filter(countryCode=u_profile_obj[0].countryCode)

        if user:
            user_object = WalkUser.objects.get(pk=user)
            if user_object:
                walkset = walkset.filter(user=user_object).order_by('-id')
        if iso2:
            walkset = walkset.filter(countryCode=iso2).order_by('-id')
        if date_from and date_to:
            datefrom_format = datetime.datetime.strptime(date_from, "%m/%d/%Y") #MM/DD/YYYY
            datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD     #'%Y-%m-%d %H:%M:%S.%f'

            dateto_format = datetime.datetime.strptime(date_to, "%m/%d/%Y") #MM/DD/YYYY
            next_day = dateto_format + datetime.timedelta(days=1)
            dateto_str = datetime.datetime.strftime(next_day, '%Y-%m-%d %H:%M:%S.%f') #YYYY-MM-DD

            walkset = walkset.filter(Q(date_start__gte=datefrom_str), Q(date_end__lt=dateto_str)).order_by('-id')

        perception_text = ""
        header_csv = [  'user', 'data_id', 'data_datetime', 'data_latitude', 'data_longitude', 'data_perception', 'data_comments',
                        'user_context_id','user_context_gender','user_context_ability','user_context_age','user_context_created_date',
                        'walk_id','walk_decision','walk_purpose','walk_group_size','walk_familiarity','walk_date_start','walk_latitude_start','walk_longitude_start',
                        'walk_date_end','walk_latitude_end','walk_longitude_end','walk_weather_code','walk_weather_codition','walk_weather_text','walk_temperature','walk_code_country','walk_country','walk_city',
                        'button_id', 'button_tag', 'button_counter', 'button_description',
                        'version_id','version_name','version_number','version_country'
                     ]

        filename = 'Reports-{}.csv'.format(datetime.datetime.today().strftime("%Y-%m-%dT%H-%M-%S"))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
        writer = csv.writer(response)
        writer.writerow(header_csv)

        noicon_b = Button.objects.get(tag='NoIcon')
        for w in walkset:
            dataset = Data.objects.filter(walk_context=w.id).order_by('-datetime','-id')
            country = Country.objects.filter(iso2=w.countryCode)

            if len(dataset) > 0:
                for d in dataset:
                    perception_text = "None"

                    if d.perception == 'yellow':
                        perception_text = "Concern"
                    elif d.perception == 'red':
                        perception_text = "Problem"
                    elif d.perception == "green":
                        perception_text = "Good"

                    dvset = DataValue.objects.filter(data=d.id)
                    counter = 1
                    if len(dvset)>0:
                        for dv in dvset:
                            new_row = [ d.user.username, str(d.id), d.datetime, d.latitude, d.longitude, perception_text, d.comments,
                                d.context.id if d.context.id else 'None', d.context.gender if d.context.id else 'None',d.context.ability if d.context.id else 'None',d.context.age if d.context.id else 'None', d.context.created_date if d.context.id else 'None',
                                d.walk_context.id if d.walk_context.id else 'None', d.walk_context.decision if d.walk_context.id else 'None',d.walk_context.purpose if d.walk_context.id else 'None', d.walk_context.group_size if d.walk_context.id else 'None',d.walk_context.familiarity if d.walk_context.id else 'None', d.walk_context.date_start,d.walk_context.latitude_start, d.walk_context.longitude_start,
                                d.walk_context.date_end if d.walk_context.id else 'None', d.walk_context.latitude_end if d.walk_context.id else 'None',d.walk_context.longitude_end if d.walk_context.id else 'None',d.walk_context.weather_code if d.walk_context.id else 'None', d.walk_context.weather_codition if d.walk_context.id else 'None',d.walk_context.weather_text if d.walk_context.id else 'None', d.walk_context.temperature if d.walk_context.id else 'None', d.walk_context.countryCode, country[0].name if len(country) > 0 else 'N/C', d.walk_context.city if d.walk_context.id else 'None',
                                dv.value.id, dv.value.tag, str(counter), dv.value.description,
                                d.walk_context.version.id if d.walk_context.version else 'None', d.walk_context.version.name if d.walk_context.version else 'None', d.walk_context.version.number_ver if d.walk_context.version else 'None', d.walk_context.version.country if d.walk_context.version else 'None'
                                ]
                            new_row_selected = [str(x) for x in new_row]
                            writer.writerow(new_row_selected)
                            counter = counter + 1

                    else:
                        new_row =   [   d.user.username, str(d.id), d.datetime, d.latitude, d.longitude, perception_text, d.comments,
                                d.context.id if d.context.id else 'None',d.context.gender if d.context.id else 'None',d.context.ability if d.context.id else 'None', d.context.age if d.context.id else 'None',d.context.created_date if d.context.id else 'None',
                                d.walk_context.id if d.walk_context.id else 'None', d.walk_context.decision if d.walk_context.id else 'None',d.walk_context.purpose if d.walk_context.id else 'None', d.walk_context.group_size if d.walk_context.id else 'None',d.walk_context.familiarity if d.walk_context.id else 'None', d.walk_context.date_start,d.walk_context.latitude_start, d.walk_context.longitude_start,
                                d.walk_context.date_end if d.walk_context.id else 'None', d.walk_context.latitude_end if d.walk_context.id else 'None',d.walk_context.longitude_end if d.walk_context.id else 'None',d.walk_context.weather_code if d.walk_context.id else 'None', d.walk_context.weather_codition if d.walk_context.id else 'None',d.walk_context.weather_text if d.walk_context.id else 'None', d.walk_context.temperature if d.walk_context.id else 'None', d.walk_context.countryCode, country[0].name if len(country) > 0 else 'N/C', d.walk_context.city if d.walk_context.id else 'None',
                                noicon_b.id, noicon_b.tag, str(counter),noicon_b.description,
                                d.walk_context.version.id if d.walk_context.version else 'None', d.walk_context.version.name if d.walk_context.version else 'None', d.walk_context.version.number_ver if d.walk_context.version else 'None', d.walk_context.version.country if d.walk_context.version else 'None'
                        ]
                        new_row_selected = [str(x) for x in new_row]
                        writer.writerow(new_row_selected)
                        counter = counter + 1

            else:
                new_row =   [   w.user.username if w.user else str(0), 'None', 'None', 'None', 'None', 'None', 'None',
                                'None', 'None', 'None', 'None', 'None',
                                str(w.id), w.decision if w.id else 'None',w.purpose if w.id else 'None', w.group_size if w.id else 'None',w.familiarity if w.id else 'None', w.date_start,w.latitude_start, w.longitude_start,
                                w.date_end if w.id else 'None', w.latitude_end if w.id else 'None',w.longitude_end if w.id else 'None',w.weather_code if w.id else 'None', w.weather_codition if w.id else 'None',w.weather_text if w.id else 'None', w.temperature if w.id else 'None', w.countryCode, country[0].name if len(country) > 0 else 'N/C', w.city if w.id else 'None',
                                'None', 'None', str(0),'None',
                                w.version.id if w.version else 'None', w.version.name if w.version else 'None', w.version.number_ver if w.version else 'None', w.version.country if w.version else 'None'
                        ]
                new_row_selected = [str(x) for x in new_row]
                writer.writerow(new_row_selected)
        return response
    else:
        return HttpResponse("wrong method and you need user profile id @admin will punish you", content_type="text/plain")


@swagger_auto_schema(methods=['get'],
    manual_parameters=[openapi.Parameter('check', openapi.IN_QUERY, "Insert checklist item", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True)], tags=['others'])
@api_view(['GET'])
def checkPointStatus(request):
    """
    This function validate current state of data and datavalue in base of 8 item: data cant, data first ID, data last ID, datavalue cant, datavalue first ID and value concadenate and datavalue last ID and value concadenate.

    ## Parameter filters:  
     - **check list = List with 8 parameters**    

    **All parameters are required**
    """
    checklist = request.GET.getlist('check')
    response = dict() 

    if len(checklist) < 8:
        return JsonResponse({'status': 'error','code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'data list, user id and datavalue list required'})

    dataids = Data.objects.all().values_list('id', flat=True)
    dv = DataValue.objects.all().select_related('data','value').values('id','data','value').annotate(
                                                            dv = models.ExpressionWrapper(Concat(F('data'),F('value')),
                                                            output_field=models.CharField())
                                                            )  
    datavalue = dv.values_list('id','dv').order_by('data','value')
    current_check = list([str(len(dataids)),str(dataids.first()),str(dataids.last()),str(len(datavalue)),str(datavalue.first()[0]),str(datavalue.first()[1]),str(datavalue.last()[0]),str(datavalue.last()[1])])

    #check model data and datavalue
    if len(list(set(current_check) - set(checklist))) == 0:            
        response = {
                    'status': 'success',
                    'code': Response_status.HTTP_200_OK,
                    'message': 'No change'
                    }
        
    else: 
        response = {
                        'status': 'error',
                        'code': Response_status.HTTP_400_BAD_REQUEST,
                        'message': "Need change point data",
                        'point_status': {
                                            'data_cant': (len(dataids)), 'data_firstID': dataids.first(), 'data_lastID':dataids.last(),
                                            'dv_cant': (len(datavalue)), 'dv_firstID': datavalue.first()[0], 'dv_first': datavalue.first()[1], 'dv_lastID': datavalue.last()[0], 'dv_last': datavalue.last()[1]
                                        }
                    }       
        
    return JsonResponse(response, safe=False)


def getItemReports(request):
    user = request.GET.get('user',None)
    response = list()

    if not user:
        return JsonResponse({'status': 'error','code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'user id required'})
    user_info = WalkUser.objects.filter(pk=user)
    if len(user_info) < 1:
        return JsonResponse({'status': 'error','code': Response_status.HTTP_404_NOT_FOUND, 'message': 'user not found'})
    
    #walkset = WalkContext.objects.all().order_by('-id')   
    #if user_info[0].profile == 'contributor':
    #    walkset = walkset.filter(user=user_info[0].id).order_by('-id')
    #elif user_info[0].profile == 'licensed' and not user_info[0].country == 'global': 
    #    walkset = walkset.filter(countryCode=user_info[0].countryCode).order_by('-id')

    walkset=''
    if user_info[0].profile == 'contributor':        
        walkset = WalkContext.objects.filter(user=user_info[0].id).values('id','distance_new','date_start','date_end','weather_codition','countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('-id')
    elif user_info[0].profile == 'licensed' and not user_info[0].country == 'global':         
        walkset = WalkContext.objects.filter(countryCode=user_info[0].countryCode).values('id','distance_new','date_start','date_end','weather_codition','countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('-id')
    else:       
        walkset = WalkContext.objects.all().values('id','distance_new','date_start','date_end','weather_codition','countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('-id')

    index = 0   
    for w in walkset:
        duration = 0
        country = Country.objects.filter(iso2=w['countryCode'])       
        if w['date_end'] and w['date_start'] and w['date_end'] > w['date_start']:     
            duration = datetime.datetime.strptime(datetime.datetime.strftime(w['date_end'],"%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(datetime.datetime.strftime(w['date_start'],"%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")         

        #w.calc_distance()
        
        distance = round(w['distance_new'],2) if w['distance_new'] else 0
        response.append({
            'index': int(index) + 1,
            'pos': int(index),
            'name': w['id'],
            'distance': 0 if distance == 0.00 else distance,
            'time': str(duration) if duration and w['date_start'] and w['date_end'] else str(0),
            'reports': w['num_data'],
            'weather': (w['weather_codition']) if w['weather_codition'] else 'N/W',
            'country': country[0].name if len(country) > 0 else 'N/C'

        })
        index = index + 1
    
    return JsonResponse(response, safe=False)



from django.core.paginator import Paginator
def getItemReports_new(request):
    user = request.GET.get('user',None)
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 100)
    response = list()

    if not user:
        return JsonResponse({'status': 'error','code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'user id required'})
    user_info = WalkUser.objects.filter(pk=user)
    if len(user_info) < 1:
        return JsonResponse({'status': 'error','code': Response_status.HTTP_404_NOT_FOUND, 'message': 'user not found'})

    walkset=''
    if user_info[0].profile == 'contributor':        
        walkset = WalkContext.objects.filter(user=user_info[0].id).values('id','distance_new','date_start','date_end','weather_codition','countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('-id')
    elif user_info[0].profile == 'licensed' and not user_info[0].country == 'global':         
        walkset = WalkContext.objects.filter(countryCode=user_info[0].countryCode).values('id','distance_new','date_start','date_end','weather_codition','countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('-id')
    else:       
        walkset = WalkContext.objects.all().values('id','distance_new','date_start','date_end','weather_codition','countryCode').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('-id')

    index = 0
    for w in walkset:
        duration = 0
        country = Country.objects.filter(iso2=w['countryCode'])
        if w['date_end'] and w['date_start'] and w['date_end'] > w['date_start']:
            duration = datetime.datetime.strptime(datetime.datetime.strftime(w['date_end'],"%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(datetime.datetime.strftime(w['date_start'],"%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

        #w.calc_distance()

        distance = round(w['distance_new'],2) if w['distance_new'] else 0
        response.append({		
            'index': int(index) + 1,
            'pos': int(index),
            'name': w['id'],
            'distance': 0 if distance == 0.00 else distance,
            'time': str(duration) if duration and w['date_start'] and w['date_end'] else str(0),
            'reports': w['num_data'],
            'weather': (w['weather_codition']) if w['weather_codition'] else 'N/W',
            'country': country[0].name if len(country) > 0 else 'N/C'

        })
        index = index + 1
		
    paginator = Paginator(response, per_page)
    page_obj = paginator.get_page(page_number)

    payload = {
        "page": {
            "count": len(response), 
            "current": page_obj.number,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        },

        "result": page_obj.object_list
    }
    return JsonResponse(payload)



def checkNewDistance(request):
    response = dict({'total_walks': 0 , 'countND': 0, 'walks': list()}) 
    walkset = WalkContext.objects.all().order_by('id')  
    cant = 0
    index = 0
    total_walk = len(walkset) 
    for w in walkset:        
        if w.distance_new == None:
            cant = cant + 1 
            response['walks'].append({'id': w.id, 'cant_points': w.data_set.count(), 'new_distance': w.distance_new }) 
        print('index: ',index)
        print(round(float((index/total_walk)*100),3))
        print('Id_walk: ',w.id,' , w.distance_new: ', w.distance_new)
        index = index + 1
    response['total_walks'] = total_walk
    response['countND'] = cant     
    return JsonResponse(response, safe=False)


def checkNewDistance_0(request):
    response = dict({'total_walks': 0 , 'pcount': 0, 'ids': list()}) 
    walkset = WalkContext.objects.all().order_by('id')  
    cant = 0
    index = 0
    total_walk = len(walkset) 
    for w in walkset:        
        if w.distance_new == None:
            cant = cant + 1 
            response['ids'].append(w.id) 
        print('index: ',index)
        print(round(float((index/total_walk)*100),3))
        print('Id_walk: ',w.id,' , w.distance_new: ', w.distance_new)
        index = index + 1
    response['total_walks'] = total_walk
    response['pcount'] = cant     
    return JsonResponse(response, safe=False)


def fillNewDistance(request):
    mode = request.GET.get('mode',None)
    walkset = WalkContext.objects.all()

    #Parameter 'mode' is just for know if fill rows with distance_new empty or all rows from the model (mode=all)
    if not mode:
        if not WalkContext.objects.filter(distance_new__isnull=True).exists():
            return JsonResponse({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "No walk without distance_new empty found" })
        walkset = walkset.filter(distance_new__isnull=True)

    index = 0
    total = len(walkset)
    try:
        for w in walkset:
            w.calc_distance()
            print(round(index/total * 100,3))
            index = index + 1

        return JsonResponse({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': 'Walkcontext field updated!'})
    except:
        return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Walkcontext field not updated'})


def fillPerceptionColor(request):
    mode = request.GET.get('mode',None)
    dataset = Data.objects.all()

    #Parameter 'mode' is just for know if fill rows with distance_new empty or all rows from the model (mode=all)
    if not mode:
        if not dataset.filter(perception__isnull=True).exists():
            return JsonResponse({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': "No data without perception empty found" })
        dataset = dataset.filter(perception__isnull=True)

    index = 0
    total = len(dataset)
    try:
        for d in dataset:
            dv  = DataValue.objects.filter(data=d.id).select_related('value')
            if len(dv) > 0:
                #print('ID DATA: ',d.id,' and first button perception: ',dv[0].value.clasification)           
                d.perception = dv[0].value.clasification
                d.save()

            print(round(index/total * 100,3))
            index = index + 1

        return JsonResponse({'status': 'success', 'code': Response_status.HTTP_200_OK, 'message': 'Data field updated!'})
    except:
        return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Data field not updated'})



@csrf_exempt
@swagger_auto_schema(methods=['post'], tags=['others'])
@api_view(['POST'])
def sendMail(request):
    """
    Send mail to 'walkabilityappinfo@gmail.com' with contact form data.
    No include parameters here for security.   
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'Ups, Admin will punish you'})
   
    name = request.POST.get('name')
    id_user = request.POST.get('user')
    email = request.POST.get('email')
    subject = request.POST.get('subject')
    message = request.POST.get('message')
    opt = request.POST.get('opt')
    
    email_content = dict()
    email_subject = ""
    email_list = []
    response = dict()
    
    template = loader.get_template('email/email.html')
    if opt == 'c':
        username_email = name
        if int(id_user) > 0:
            user = WalkUser.objects.get(id=int(id_user))
            username_email = user.username
    
        email_content = {
                'title': "Contact form question", 
                'link': None,
                'greeting': 'Hi Administrator!',
                'text': 'This message has been sent by ' + username_email + ' from the WalkableStreet web contact form.','support_team': SUPPORT_TEAM,
                'contact_data': { 'name': name, 'email': email, 'subject': subject, 'message':message},
                'opt': 5,
        }
        email_subject = '[WalkableStreet] Contact: '+ subject
        email_list = [ADMIN_EMAIL, 'monse.fm@gmail.com']
    
    
    elif opt == 'req':
        email_content = {
                'title': "Questions & Doubts",
                'link': None,
                'greeting': 'Hi Administrator!',
                'text': "This message is because '"+ name + "' [" + email+ "] send the question: ",
                'question': message,
                'support_team': SUPPORT_TEAM,
                'opt': 7,
        }
        email_subject = '[WalkableStreet] Questions & Doubts Notification'
        email_list = [ADMIN_EMAIL, 'monse.fm@gmail.com']
        
    
    elif opt == 'da':
        
       # feedback = message if message else 'No leave feedback'
       # about = 'Keep their reports data' if name == 'true' else 'No keep reports data'
        feedback = 'have left the following feedback: <<' +  message +'>>'  if message and not message == 'null' else "haven't left feedback"
        about = 'not deleted' if name == 'true' else 'to delete'


        email_content = {
                'title': "Delete Account",
                'link': None,
                'greeting': 'Hi Administrator!',
                'text': "This message is because user '" + id_user + "' has deleted their account. Before go, the user " + feedback + " and decided " + about + " their data in the platform." ,'support_team': SUPPORT_TEAM,
                'opt': 6,
        }
        email_subject = '[Walkability] Delete Account Notification'
        email_list = [ADMIN_EMAIL, 'monse.fm@gmail.com']
        #email_list = ['monse.fm@gmail.com']

        
        #Send email to user
        user_feedback = 'you have left the following feedback: <<' +  message +'>>'  if message and not message == 'null' else "you haven't left feedback"
        user_about = 'not deleted' if name == 'true' else 'to delete'

        email_content_user = {
                'title': "Delete Account",
                'link': None,
                'greeting': 'Hi '+ id_user +'!',
                'text': "Thank you for your interest in using Walkbaility.App. We are sad to see you leave and delete your account. Anyway, " + user_feedback + " and you decided " + user_about + " your data in the platform.",'support_team': SUPPORT_TEAM,
                'opt': 6,
        }
        email_subject = '[Walkability] Delete Account Notification'
        email_list_user = [email]

        email_menssage_user = template.render(email_content_user)
        my_email_user = EmailMessage(email_subject,email_menssage_user,settings.DEFAULT_FROM_EMAIL, email_list_user)
        my_email_user.content_subtype = 'html'
        my_email_user.send()


    #template = loader.get_template('email/email.html')
    email_menssage = template.render(email_content)

    my_email = EmailMessage(email_subject,email_menssage,settings.DEFAULT_FROM_EMAIL, email_list)
    my_email.content_subtype = 'html'
    
    try:
        my_email.send()
        response = {
                'status': 'success',
                'code': Response_status.HTTP_200_OK,
                'message': 'Thanks for your message. Mail has been sent successfully'
        }
    except:
        response = {
                'status': 'error',
                'code': Response_status.HTTP_400_BAD_REQUEST,
                'message': "An error occurred while sending the message." 
        }	

    return JsonResponse(response)



@swagger_auto_schema(methods=['get'],
        manual_parameters=[
            openapi.Parameter('user', openapi.IN_QUERY, "Insert user id", type=openapi.TYPE_INTEGER),
            openapi.Parameter('mode', openapi.IN_QUERY, "Insert mode", type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), collection_format='multi', uniqueItems=True),
        ], tags=['others'])
@api_view(['GET'])
def get_users(request):
    """
    This function get a list of users save in database depending a user with licensed profile. You can use a mode for get the list of users with data points. 
    
    ## Parameter filters:
     - **user id**
     - **mode = mode for list users with points (mode = ud)**
    """
    id_user = request.GET.get('user',None)
    mode = request.GET.get('mode','')
    response = list()
    walk = ''
    list_users = ''

    if id_user:
        user_object = WalkUser.objects.get(pk=id_user)
        if user_object:
            if user_object.profile == 'contributor':
                return JsonResponse({'status': 'error',  'code': Response_status.HTTP_400_BAD_REQUEST,   'message': user_object.username + " hasn't licensed profile"})
            elif user_object.profile == 'licensed' and not user_object.country == 'global': 
                walk =  WalkContext.objects.filter(countryCode=user_object.countryCode).values('user').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('user')   
            else:
                walk =  WalkContext.objects.values('user').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('user')     
                
    else:
        walk =  WalkContext.objects.values('user').annotate(
                                    num_data = models.ExpressionWrapper(Count(F('data')),
                                    output_field=models.IntegerField())
                                ).order_by('user')     
    if mode == 'ud':
        walk_data = walk.filter(num_data__gt=0).order_by('user')
    else:
        walk_data =  walk.filter(num_data__gte=0).order_by('user')
    
    id_users = walk_data.values_list('user', flat=True).distinct()

    list_users = WalkUser.objects.filter(id__in=id_users).order_by('username')    
    [response.append({'id': u.id, 'username':u.username, 'profile': u.profile, 'slug': slugify(u.username)})  for u in list_users ]
    response = sorted(response, key=lambda user:user['slug'])

    return JsonResponse(response, safe=False)


## POINT IN POLYGON TEST
def getPointsInside(request):   
    coordinates = request.GET.getlist('coor') 
    response = dict({'WALK_INFO':list(), 'POINT_INFO':list()})
    polylist = list()

    for coor in coordinates:
        latlng = coor.split(',')
        polylist.append((float(latlng[0]),float(latlng[1])))
        print(getaddress(float(latlng[0]), float(latlng[1]), 'country'))

    polygon = Polygon((polylist))
  
    dataset = Data.objects.all().values('id','latitude','longitude','walk_context').order_by('walk_context','id')
    walk_ids=[]
    data_ids=[]
    for d in dataset:
        point = Point(float(d['longitude']), float(d['latitude']))
        if polygon.contains(point):
            if not d['walk_context'] in walk_ids:
                walk_ids.append(d['walk_context'])            
            data_ids.append(d['id'])
            response['POINT_INFO'].append({'WALK': d['walk_context'], 'id_data': d['id'], 'latitude':d['latitude'], 'longitude': d['longitude']})
    
    response['WALK_INFO'] = {'cant_ids': len(walk_ids), 'detail':list()}
    walkset = WalkContext.objects.filter(id__in=walk_ids).order_by('id')
    for wc in walkset:
        sections = list()
        list_a = list()
        list_b = list()
        total_distance_wc = 0
        dataset_filter = dataset.filter(Q(walk_context=wc.id , id__in=data_ids)).order_by('id')

        if wc.latitude_start and wc.longitude_start and wc.latitude_end and wc.longitude_end:
            list_a.append(list([wc.latitude_start, wc.longitude_start]))
            list_b.append(list([dataset_filter[0]['latitude'], dataset_filter[0]['longitude']]))

        for i, point in enumerate(dataset_filter, start=0):
            if i < len(dataset_filter)-1:
                list_a.append(list([point['latitude'], point['longitude']]))
            if i > 0:
                list_b.append(list([point['latitude'], point['longitude']]))

        if wc.latitude_start and wc.longitude_start and wc.latitude_end and wc.longitude_end:
            list_b.append(list([wc.latitude_end, wc.longitude_end]))
            list_a.append(list([dataset_filter[len(dataset_filter)-1]['latitude'], dataset_filter[len(dataset_filter)-1]['longitude']]))

        for p_start, p_end in zip(list_a, list_b):
            sections.append({'start': p_start, 'end': p_end})

        for section in sections:
            total_distance_wc = total_distance_wc + haversine(section['start'], section['end'], unit='km')

        response['WALK_INFO']['detail'].append({'walk_id':wc.id, 'cant_points': len(dataset_filter), 'distance':total_distance_wc})

    return JsonResponse(response, safe=False)



#####################################

# VIEWS FOR DJANGO APP - TEMPLATES

#####################################

def ResetPass(request):
    token = request.GET.get('token', None)
    token_valid = request.GET.get('token_valid', None)
    uidb64 = request.GET.get('uidb64', None)
    data = {
        'token': token,
        'token_valid' : token_valid,
        'uidb64': uidb64
    }
    return render(request, 'reset_password.html', {'data': data})


def Email(request):
    return render(request, 'email/email.html',{})


def DataTable(request):
    
    opt = request.GET.get("opt", None)
    dataset = Data.objects.all().order_by('-datetime','-id')
    fulldata = dataset.values('user').distinct()
    if not opt:
        dataset = dataset[:100]

    current_site = get_current_site(request = request).domain
    resp_country = requests.get('http://'+current_site+'/countries/?mode=cd')
    countrylist = resp_country.json()

    search_str = request.GET.get("search", None)
    if search_str:
        search = search_str.split('|')
        s_user, s_from, s_to, s_color, s_country = search
        if s_user:
            dataset = dataset.filter(user=int(s_user))
        if s_from:
            datefrom_format = datetime.datetime.strptime(s_from, "%m/%d/%Y") #MM/DD/YYYY
            datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d') #YYYY-MM-DD

            dataset = dataset.filter(Q(datetime__gte=datefrom_str))
        if s_to:
            date_format = datetime.datetime.strptime(s_to, "%m/%d/%Y") #MM/DD/YYYY
            next_day = date_format + datetime.timedelta(days=1)
            date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d') #YYYY-MM-DD
            dataset = dataset.filter(Q(datetime__lt=date_str))
        if s_color:
            dataset = dataset.filter(perception=s_color)
        if s_country:
            walkset = WalkContext.objects.filter(countryCode=s_country).order_by('-id')
            ids_walk_city = [i.id for i in walkset]
            dataset = dataset.filter(walk_context__in=ids_walk_city)

    ids_data = [i.id for i in dataset]
    ids_user = [i['user'] for i in fulldata]

    response = list()
    for d in dataset:
        icon_data = list()
        cant_button = 0
        data_value = DataValue.objects.filter(data=d.id).values('value').annotate(bcount = Count('value'))

        if len(data_value) == 1:
            cant_button = 1
            button = Button.objects.get(pk=data_value[0]['value'])
            icon_data.append({'id': data_value[0]['value'], 'bcount': data_value[0]['bcount'], 'tag': button.tag, 'description': button.description, 'clasification': button.clasification, 'image': (request.build_absolute_uri(button.image.url) if button.image else None)})

        elif len(data_value)>1:
            cant_button = len(data_value)

        response.append({
        "id":          d.id,
        "latitude":    d.latitude,
        "longitude":   d.longitude,
        "datetime":    d.datetime,
        "comments":    d.comments,
        "gpsaccuracy": d.gpsaccuracy,
        "perception":  d.perception,
        "user":        d.user,
        "context":     d.context.id if d.context else None,
        "context_data": (dict({'id': d.context.id, 'gender': d.context.gender, 'age': d.context.age, 'ability':d.context.ability}) if d.context else None),
        "walk_context": d.walk_context.id if d.walk_context else None,
        'walk_context_data': (dict({'id': d.walk_context.id, 'group_size': d.walk_context.group_size, 'decision': d.walk_context.decision, 'purpose':d.walk_context.purpose, 'familiarity': d.walk_context.familiarity}) if d.walk_context else None),
        'city': d.walk_context.city,
        "icon_data": icon_data,
        'cant_button': cant_button
        })


    ids_user_unique = set(ids_user)
    userlist = WalkUser.objects.filter(id__in=ids_user_unique).order_by("username")

    return render(request, 'table.html', {'dataset': response, 'countrylist':countrylist, 'userlist':userlist, 'ids_data': ids_data, 'opt':opt})



@csrf_exempt
def csvResponse_o(request):
    if request.method == 'POST':
        ids = request.POST.get('csv', '')
        ids = ids.split(',') if ids else []
        all_ids = [int(x) for x in ids]
        query = Data.objects.filter(id__in=all_ids).order_by('-datetime','-id')
        opt = request.POST.get('opt', '')
        if not opt == '1':
            query = Data.objects.all().order_by('-datetime','-id')

        perception_text = ""

        header_csv = [  'user', 'data_id', 'data_datetime', 'data_latitude', 'data_longitude', 'data_perception', 'data_comments',
                        'user_context_id','user_context_gender','user_context_ability','user_context_age','user_context_created_date',
                        'walk_id','walk_decision','walk_purpose','walk_group_size','walk_familiarity','walk_date_start','walk_latitude_start','walk_longitude_start',
                        'walk_date_end','walk_latitude_end','walk_longitude_end','walk_weather_code','walk_weather_codition','walk_weather_text','walk_temperature','walk_code_country','walk_country','walk_city',
                        'button_id', 'button_tag', 'button_counter', 'button_description',
                        'version_id','version_name','version_number','version_country'
                     ]
        filename = 'Data-{}.csv'.format(datetime.datetime.today().strftime("%Y-%m-%dT%H-%M-%S"))

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)
        writer.writerow(header_csv)

        noicon_b = Button.objects.get(tag='NoIcon')
        for q in query:
            perception_text = "None"

            if q.perception == 'yellow':
                perception_text = "Concern"
            elif q.perception == 'red':
                perception_text = "Problem"
            elif q.perception == "green":
                perception_text = "Good"

            country = Country.objects.filter(iso2=q.walk_context.countryCode)

            datavalue_set = DataValue.objects.filter(data=q.id)
            counter = 1
            if len(datavalue_set)>0:
                for dv in datavalue_set:
                    new_row = [ q.user.username, str(q.id), q.datetime, q.latitude, q.longitude, perception_text, q.comments,
                                q.context.id if q.context.id else 'None',q.context.gender if q.context.id else 'None',q.context.ability if q.context.id else 'None',q.context.age if q.context.id else 'None',q.context.created_date if q.context.id else 'None',
                                q.walk_context.id if q.walk_context.id else 'None', q.walk_context.decision if q.walk_context.id else 'None',q.walk_context.purpose if q.walk_context.id else 'None', q.walk_context.group_size if q.walk_context.id else 'None',q.walk_context.familiarity if q.walk_context.id else 'None', q.walk_context.date_start,q.walk_context.latitude_start, q.walk_context.longitude_start,
                                q.walk_context.date_end if q.walk_context.id else 'None', q.walk_context.latitude_end if q.walk_context.id else 'None',q.walk_context.longitude_end if q.walk_context.id else 'None',q.walk_context.weather_code if q.walk_context.id else 'None', q.walk_context.weather_codition if q.walk_context.id else 'None',q.walk_context.weather_text if q.walk_context.id else 'None', q.walk_context.temperature if q.walk_context.id else 'None', q.walk_context.countryCode, country[0].name if len(country) > 0 else 'N/C', q.walk_context.city if q.walk_context.id else 'None',
                                dv.value.id, dv.value.tag, str(counter), dv.value.description,
                                q.walk_context.version.id if q.walk_context.version else 'None', q.walk_context.version.name if q.walk_context.version else 'None', q.walk_context.version.number_ver if q.walk_context.version else 'None', q.walk_context.version.country if q.walk_context.version else 'None'
                                ]
                    new_row2 = [str(x) for x in new_row]
                    writer.writerow(new_row2)
                    counter = counter + 1
            else:
                new_row =   [   q.user.username, str(q.id), q.datetime, q.latitude, q.longitude, perception_text, q.comments,
                                q.context.id if q.context.id else 'None',q.context.gender if q.context.id else 'None',q.context.ability if q.context.id else 'None',q.context.age if q.context.id else 'None',q.context.created_date if q.context.id else 'None',
                                q.walk_context.id if q.walk_context.id else 'None', q.walk_context.decision if q.walk_context.id else 'None',q.walk_context.purpose if q.walk_context.id else 'None', q.walk_context.group_size if q.walk_context.id else 'None',q.walk_context.familiarity if q.walk_context.id else 'None', q.walk_context.date_start,q.walk_context.latitude_start, q.walk_context.longitude_start,
                                q.walk_context.date_end if q.walk_context.id else 'None', q.walk_context.latitude_end if q.walk_context.id else 'None',q.walk_context.longitude_end if q.walk_context.id else 'None',q.walk_context.weather_code if q.walk_context.id else 'None', q.walk_context.weather_codition if q.walk_context.id else 'None',q.walk_context.weather_text if q.walk_context.id else 'None', q.walk_context.temperature if q.walk_context.id else 'None', q.walk_context.countryCode, country[0].name if len(country) > 0 else 'N/C', q.walk_context.city if q.walk_context.id else 'None',
                                noicon_b.id, noicon_b.tag, str(counter),noicon_b.description,
                                q.walk_context.version.id if q.walk_context.version else 'None', q.walk_context.version.name if q.walk_context.version else 'None', q.walk_context.version.number_ver if q.walk_context.version else 'None', q.walk_context.version.country if q.walk_context.version else 'None'
                            ]
                new_row2 = [str(x) for x in new_row]
                writer.writerow(new_row2)
                counter = counter + 1

        return response
    else:
        return HttpResponse("GET method not acepted.. @admin will punish you", content_type="text/plain")



@csrf_exempt
def csvResponse(request):
    if request.method == 'POST':
        ids = request.POST.get('csv', '')
        ids = ids.split(',') if ids else []
        all_ids = [int(x) for x in ids]
        query = Data.objects.filter(id__in=all_ids).order_by('-datetime','-id')
        opt = request.POST.get('opt', '')
        if not opt == '1':
            query = Data.objects.all().order_by('-datetime','-id')

        perception_text = ""

        header_csv = [  'user', 'data_id', 'data_datetime', 'data_latitude', 'data_longitude', 'data_perception', 'data_comments',
                        'user_context_id','user_context_gender','user_context_ability','user_context_age','user_context_created_date',
                        'walk_id','walk_decision','walk_purpose','walk_group_size','walk_familiarity','walk_date_start','walk_latitude_start','walk_longitude_start',
                        'walk_date_end','walk_latitude_end','walk_longitude_end','walk_weather_code','walk_weather_codition','walk_weather_text','walk_temperature','walk_code_country','walk_country','walk_city',
                        'button_id', 'button_tag', 'button_cant', 'button_description',
                        'version_id','version_name','version_number','version_country'
                     ]
        filename = 'Data-{}.csv'.format(datetime.datetime.today().strftime("%Y-%m-%dT%H-%M-%S"))

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

        writer = csv.writer(response)
        writer.writerow(header_csv)

        noicon_b = Button.objects.get(tag='NoIcon')
        for q in query:
            perception_text = "None"

            if q.perception == 'yellow':
                perception_text = "Concern"
            elif q.perception == 'red':
                perception_text = "Problem"
            elif q.perception == "green":
                perception_text = "Good"

            country = Country.objects.filter(iso2=q.walk_context.countryCode)
            datavalue_set = DataValue.objects.filter(data=q.id)
                       
            if len(datavalue_set)>0:
                btn_ids = ''
                btn_tags = ''
                btn_cant = len(datavalue_set)
                btn_descriptions = ''

                for dv in datavalue_set:
                    btn_ids = btn_ids + str(dv.value.id) + ' | '
                    btn_tags = btn_tags + dv.value.tag + ' | '                   
                    btn_descriptions = btn_descriptions + dv.value.description + ' | '

                new_row = [ q.user.username, str(q.id), q.datetime, q.latitude, q.longitude, perception_text, q.comments,
                                q.context.id if q.context.id else 'None',q.context.gender if q.context.id else 'None',q.context.ability if q.context.id else 'None',q.context.age if q.context.id else 'None',q.context.created_date if q.context.id else 'None',
                                q.walk_context.id if q.walk_context.id else 'None', q.walk_context.decision if q.walk_context.id else 'None',q.walk_context.purpose if q.walk_context.id else 'None', q.walk_context.group_size if q.walk_context.id else 'None',q.walk_context.familiarity if q.walk_context.id else 'None', q.walk_context.date_start,q.walk_context.latitude_start, q.walk_context.longitude_start,
                                q.walk_context.date_end if q.walk_context.id else 'None', q.walk_context.latitude_end if q.walk_context.id else 'None',q.walk_context.longitude_end if q.walk_context.id else 'None',q.walk_context.weather_code if q.walk_context.id else 'None', q.walk_context.weather_codition if q.walk_context.id else 'None',q.walk_context.weather_text if q.walk_context.id else 'None', q.walk_context.temperature if q.walk_context.id else 'None', q.walk_context.countryCode, country[0].name if len(country) > 0 else 'N/C', q.walk_context.city if q.walk_context.id else 'None',
                                btn_ids[:-3], btn_tags[:-3], str(btn_cant), btn_descriptions[:-3],
                                q.walk_context.version.id if q.walk_context.version else 'None', q.walk_context.version.name if q.walk_context.version else 'None', q.walk_context.version.number_ver if q.walk_context.version else 'None', q.walk_context.version.country if q.walk_context.version else 'None'
                                ]
                new_row2 = [str(x) for x in new_row]
                writer.writerow(new_row2)
            else:
                new_row =   [   q.user.username, str(q.id), q.datetime, q.latitude, q.longitude, perception_text, q.comments,
                                q.context.id if q.context.id else 'None',q.context.gender if q.context.id else 'None',q.context.ability if q.context.id else 'None',q.context.age if q.context.id else 'None',q.context.created_date if q.context.id else 'None',
                                q.walk_context.id if q.walk_context.id else 'None', q.walk_context.decision if q.walk_context.id else 'None',q.walk_context.purpose if q.walk_context.id else 'None', q.walk_context.group_size if q.walk_context.id else 'None',q.walk_context.familiarity if q.walk_context.id else 'None', q.walk_context.date_start,q.walk_context.latitude_start, q.walk_context.longitude_start,
                                q.walk_context.date_end if q.walk_context.id else 'None', q.walk_context.latitude_end if q.walk_context.id else 'None',q.walk_context.longitude_end if q.walk_context.id else 'None',q.walk_context.weather_code if q.walk_context.id else 'None', q.walk_context.weather_codition if q.walk_context.id else 'None',q.walk_context.weather_text if q.walk_context.id else 'None', q.walk_context.temperature if q.walk_context.id else 'None', q.walk_context.countryCode, country[0].name if len(country) > 0 else 'N/C', q.walk_context.city if q.walk_context.id else 'None',
                                noicon_b.id, noicon_b.tag, str(0),noicon_b.description,
                                q.walk_context.version.id if q.walk_context.version else 'None', q.walk_context.version.name if q.walk_context.version else 'None', q.walk_context.version.number_ver if q.walk_context.version else 'None', q.walk_context.version.country if q.walk_context.version else 'None'
                            ]
                new_row2 = [str(x) for x in new_row]
                writer.writerow(new_row2)

        return response
    else:
        return HttpResponse("GET method not acepted.. @admin will punish you", content_type="text/plain")


def getIcons(request):
    if request.is_ajax and request.method == "GET":
        id_data = request.GET.get("id_data", None)
        icon_data = list()
        data_value = DataValue.objects.filter(data= int(id_data)).values('value').annotate(bcount = Count('value'))
        if len(data_value)>0:
            for b in data_value:
                button = Button.objects.get(pk=b['value'])
                icon_data.append({'id': b['value'], 'bcount': b['bcount'], 'tag': button.tag, 'description': button.description, 'clasification': button.clasification, 'image': request.build_absolute_uri(button.image.url)})

            return JsonResponse( {'icon_data': icon_data, 'status':200})

    return JsonResponse({'icon_data': {}, 'status':200})

 
@csrf_exempt
def setNewPass(request):
    if request.method == 'POST':
        password = request.POST.get('password', '')
        token = request.POST.get('token', '')
        uidb64 = request.POST.get('uidb64', '')

        response = dict()

        id = smart_str(urlsafe_base64_decode(uidb64))
        user = WalkUser.objects.get(id=int(id))

        if not PasswordResetTokenGenerator().check_token(user, token):
            response = {
                'status': 'error',
                'code': Response_status.HTTP_400_BAD_REQUEST,
                'message': 'Token not valid'
            }
        else:
            user.set_password(password)
            user.save()
            
            #Original
            #email_body = 'Dear ' +user.username+ '\n\nYour password has been changed!\n \nThanks for using our site! \n \n'+SUPPORT_TEAM
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
                    'text': "Your password has been changed successfully.\nPlease use your new password to log in.",
                    'support_team': SUPPORT_TEAM,
                    'opt': 2,
            }  
            template = loader.get_template('email/email.html')
            email_menssage = template.render(data_email)

            my_email2 = EmailMessage('[WalkableStreet] Your password has been successfully changed!',email_menssage,settings.DEFAULT_FROM_EMAIL,[user.email])
            my_email2.content_subtype = 'html'
            my_email2.send() 

            response = {
                'status': 'success',
                'code': Response_status.HTTP_200_OK,
                'message': 'Password reset successfully'
            }
    return JsonResponse(response)


@csrf_exempt
def validateLogin(request):
    
    if request.method == "POST":
        username = request.POST.get('username', '')              
        password = request.POST.get('password', '')
        next_value = request.POST.get('next', '')
        response = dict()
        
        cast_username = username.lower()
        query = User.objects.annotate(username_lower=Lower('username'))  

        user = query.filter(username_lower = cast_username).first()        

        if user:
            if user.check_password(password):
                if next_value == '/swagger/':
                    if user.is_staff == True:
                        response = {
                        'status': 'success',
                        'code': Response_status.HTTP_200_OK,
                        'message': 'success'
                        }
                    else:
                        response = {
                        'status': 'error',
                        'code': Response_status.HTTP_400_BAD_REQUEST,
                        'message': "Your account doesn't have access to this page. To proceed, please login with an account that has access."
                        }
                else:
                    response = {
                        'status': 'success',
                        'code': Response_status.HTTP_200_OK,
                        'message': 'success'
                        }
            else:
                response = {
                    'status': 'error',
                    'code': Response_status.HTTP_400_BAD_REQUEST,
                    'message': "Your username and password didn't match. Please try again."
                }
        else:

            response = {
                'status': 'error',
                'code': Response_status.HTTP_404_NOT_FOUND,
                'message': "Your username doesn't exist."    
            }
        
    return JsonResponse(response)



@csrf_exempt
def DataSection(request):
    opt = request.GET.get("opt", None)
    dataset = Data.objects.all().order_by('-datetime','-id')
    fulldata = dataset.values('user').distinct()
    if not opt:
        dataset = dataset[:100] 
    
    current_site = get_current_site(request = request).domain
    resp_country = requests.get('http://'+current_site+'/countries/?mode=cd')
    countrylist = resp_country.json()

    search_str = request.GET.get("search", None)
    if search_str:
        search = search_str.split('|')
        s_user, s_from, s_to, s_color, s_country = search
        if s_user:
            dataset = dataset.filter(user=int(s_user))
        if s_from:
            datefrom_format = datetime.datetime.strptime(s_from, "%m/%d/%Y") #MM/DD/YYYY
            datefrom_str = datetime.datetime.strftime(datefrom_format, '%Y-%m-%d') #YYYY-MM-DD

            dataset = dataset.filter(Q(datetime__gte=datefrom_str))
        if s_to:
            date_format = datetime.datetime.strptime(s_to, "%m/%d/%Y") #MM/DD/YYYY
            next_day = date_format + datetime.timedelta(days=1)
            date_str = datetime.datetime.strftime(next_day, '%Y-%m-%d') #YYYY-MM-DD
            dataset = dataset.filter(Q(datetime__lt=date_str))
        if s_color:
            dataset = dataset.filter(perception=s_color)
        if s_country:       
            walkset = WalkContext.objects.filter(countryCode=s_country).order_by('-id')
            ids_walk_city = [i.id for i in walkset]
            dataset = dataset.filter(walk_context__in=ids_walk_city)

    ids_data = [i.id for i in dataset]
    ids_user = [i['user'] for i in fulldata]

    response = list()
    for d in dataset:
        icon_data = list()
        cant_button = 0
        data_value = DataValue.objects.filter(data=d.id).values('value').annotate(bcount = Count('value'))

        if len(data_value) == 1:
            cant_button = 1
            button = Button.objects.get(pk=data_value[0]['value'])
            icon_data.append({'id': data_value[0]['value'], 'bcount': data_value[0]['bcount'], 'tag': button.tag, 'description': button.description, 'clasification': button.clasification, 'image': (request.build_absolute_uri(button.image.url) if button.image else None)})

        elif len(data_value)>1:
            cant_button = len(data_value)


        response.append({
        "id":          d.id,
        "latitude":    d.latitude,
        "longitude":   d.longitude,
        "datetime":    d.datetime,
        "comments":    d.comments,
        "gpsaccuracy": d.gpsaccuracy,
        "perception":  d.perception,
        "user":        d.user,
        "context":     d.context.id if d.context else None,
        "context_data": (dict({'id': d.context.id, 'gender': d.context.gender, 'age': d.context.age, 'ability':d.context.ability}) if d.context else None),
        "walk_context": d.walk_context.id if d.walk_context else None,
        'walk_context_data': (dict({'id': d.walk_context.id, 'group_size': d.walk_context.group_size, 'decision': d.walk_context.decision, 'purpose':d.walk_context.purpose, 'familiarity': d.walk_context.familiarity}) if d.walk_context else None),
        'city': d.walk_context.city,
        'city_bd': d.walk_context.city,
        "icon_data": icon_data,
        'cant_button': cant_button
        })
    ids_user_unique = set(ids_user)
    userlist = WalkUser.objects.filter(id__in=ids_user_unique).order_by("username")
    

    return render(request, 'data_list.html', {'dataset': response, 'countrylist':countrylist, 'userlist':userlist, 'ids_data': ids_data, 'opt':opt, 'entity': 'Data', 'list_url': '/data_list/'})    


@csrf_exempt
def DataDelete(request):
    if request.method == "POST":       
        delete_data = request.POST.get('d', list()) 
        response = dict()
        message = ''

        delete_data = delete_data if isinstance(delete_data, list) else delete_data.split(',') 
        message = 'The data point was deleted successfully.'
        if len(delete_data) > 1:
            message = 'The ' + str(len(delete_data)) + ' data points were deleted successfully.'
            
        walkset = [w.walk_context for w in Data.objects.filter(id__in=delete_data).distinct('walk_context').order_by('walk_context','id')]           
        try:
            Data.objects.filter(id__in=delete_data).delete()  
            
        except:
            message = 'Error, the data point could not be deleted.'
            if len(delete_data) > 1:
                message = 'Error, the '+str(len(delete_data))+' data points could not be deleted.'
            messages.error(request, message)
            return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': message})
        
        else:           
            ids_empty_walk = []
            for w in walkset:
                if w.data_set.count() == 0:                   
                    ids_empty_walk.append(w.id)
            
            if len(ids_empty_walk) == 0:
                messages.success(request, message)
                response = {
                    'status': 'success',
                    'code': Response_status.HTTP_200_OK,
                    'message': message 
                }
            else:
                try:
                    WalkContext.objects.filter(id__in=ids_empty_walk).delete()
                    message = message + ' The empty walk cwas deleted successfully.'
                    if len(ids_empty_walk) > 1:
                        message = message + ' The '+str(len(ids_empty_walk))+' empty walks were deleted successfully.'
                    
                    messages.success(request, message)
                    response = {
                        'status': 'success',
                        'code': Response_status.HTTP_200_OK,
                        'message': message 
                    }
                except:
                    message = message + ' Error, the empty walk could not be deleted.'
                    if len(ids_empty_walk) > 1:
                        message = message + ' Error, the '+str(len(ids_empty_walk))+' empty walks could not be deleted.'
                    messages.warning(request, message)
                    return JsonResponse({'status': 'warning', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': message})
        
    return JsonResponse(response)


@csrf_exempt
def UserSection(request):
    dataset = WalkUser.objects.all().order_by('-date_joined','username')
    response = list()
         
    for d in dataset:
        walks = WalkContext.objects.filter(user=d.id).count()
        points = Data.objects.filter(user=d.id).count()

        response.append({
        "id":           d.id,
        "username":     d.username,
        "email":        d.email,
        "profile":      d.profile,
        "country":      d.country if d.country else 'No country',
        "date_joined":  d.date_joined,
        "walks":        walks,
        "points":       points
        })
    
   
    return render(request, 'user_list.html', {'dataset': response,  'entity': 'Users', 'list_url': '/user_list/'}) 

@csrf_exempt
def UserForm(request):
    id = request.GET.get('id', '')
    action = ''
    title_form = ''
    dataset_group = list()
    response = dict()

    if id:
        action = 'update'
        title_form = 'Update WalkUser'
        walkuser = WalkUser.objects.get(pk=id)

        if walkuser:
            user = User.objects.get(username=walkuser.username)

            dataset_group = list()
        
            response = {
            "id":           walkuser.id,
            "username":     walkuser.username,
            "password":     walkuser.password,
            "email":        walkuser.email,
            "celphone":     walkuser.celphone,
            "profile":      walkuser.profile,
            "country":      walkuser.country if walkuser.country else 'No country',
            "countryCode":  walkuser.countryCode if walkuser.countryCode else 'No code',
            "walkgroup":    walkuser.walkgroup if walkuser.walkgroup else 'No group',
            "is_staff":     user.is_staff,
            "is_superuser": user.is_superuser           
            }
    else:
        action = 'create'
        title_form = 'Create WalkUser'
        

    walkgroup = Group.objects.all().order_by('tag')    
    for wg in walkgroup:
        dataset_group.append({
            "id":           wg.id,
            "tag":          wg.tag,
            "group_type":   wg.group_type,
            "name":         wg.name           
        })

    #add countries
    countries = Country.objects.all().order_by('slug','name')
    #url = "https://countriesnow.space/api/v0.1/countries/iso" 
    #resp = requests.get(url)
    #countries = resp.json() 
   
    return render(request, 'user_form.html', {'action': action,'title_template': title_form ,'wuser': response, 'list_group': dataset_group, 'list_countries': countries, 'entity': 'Users', 'list_url': '/user_list/'}) 

@csrf_exempt
def UserDelete(request):
    if request.method == "POST":
        id = request.POST.get('id', '') 
        delete_data = request.POST.get('d', list()) 
        response = dict()

        if id:        
            user = WalkUser.objects.get(pk=id)
            if WalkUser.objects.filter(pk=id).exists():
                username = user.username
                try:
                    user.delete()
                    messages.success(request, 'The user ' + username +  ' was successfully deleted.')
                    response = {'status': 'success','code': Response_status.HTTP_200_OK,'message': 'The user ' + username +  ' was successfully deleted.' }
                except:
                    messages.error(request, 'Error, the user could not be deleted.')
                    return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Error, the user could not be deleted.'})
            else:
                messages.error(request, "User not found.")
                response = {
                    'status': 'error',
                    'code': Response_status.HTTP_404_NOT_FOUND,
                    'message': "User not found."    
                }
        else:
            delete_data = delete_data if isinstance(delete_data, list) else delete_data.split(',')            
            try:
                message = 'The user was deleted successfully.'
                if len(delete_data) > 1:
                    message = 'The ' + str(len(delete_data)) + ' users were deleted successfully.'

                WalkUser.objects.filter(id__in=delete_data).delete()           
                messages.success(request, message)
                response = {
                    'status': 'success',
                    'code': Response_status.HTTP_200_OK,
                    'message': message 
                }
            except:
                message = 'Error, the user could not be deleted.'
                if len(delete_data) > 1:
                    message = 'Error, the '+str(len(delete_data))+' users could not be deleted.'
                messages.error(request, message)
                return JsonResponse({'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': message})
            
        
    return JsonResponse(response)

@csrf_exempt
def UserCreate(request): 
   
    if request.method == "POST":
      
        username = request.POST.get('username', '') 
        email = request.POST.get('email','')             
        password = request.POST.get('password', '')
        phone = request.POST.get('phone','')
        walkgroup = request.POST.get('walkgroup','')
        profile = request.POST.get('profile', '') 
        country = request.POST.get('country','')             
        countryCode = request.POST.get('countryCode','')
        privileges = request.POST.get('privileges', '')  
        button_send = request.POST.get('send', '')      
        my_group=''
        response = dict() 

        new_walkuser = WalkUser(username=username,email=email,celphone=phone, profile=profile, country=(country if country else 'N/C'), countryCode=(countryCode if countryCode else 'N/C'))
        new_walkuser.set_password(password)

        if walkgroup:
            my_group = Group.objects.get(id=walkgroup)
            new_walkuser.walkgroup = my_group
        new_walkuser.save()  

        if new_walkuser:
            if not privileges:

                if button_send == 'true' and email:
                    data_email = {
                    'title': "Welcome to WalkableStreet",
                    'link': None,
                    'greeting': 'Hi new user!',
                    'text': "We hope you enjoy using our app, sharing your experience in each walk and checking it.\nThis email includes your account details, so please keep it safe!.",
                    'support_team': SUPPORT_TEAM,
                    'username': new_walkuser.username,
                    'password': password,
                    'opt': 3,
                    } 
                    template = loader.get_template('email/email.html')
                    email_menssage = template.render(data_email)

                    my_email = EmailMessage('[WalkableStreet] The user was created successfully!',email_menssage,settings.DEFAULT_FROM_EMAIL,[email])
                    my_email.content_subtype = 'html'
                    my_email.send() 

                messages.success(request, 'The user ' + new_walkuser.username +  ' was successfully created.')
                response = {'status': 'success','code': Response_status.HTTP_201_CREATED,'message': 'The user ' + new_walkuser.username +  ' was successfully created.' }
            else:
                my_user = User.objects.get(pk=new_walkuser.id)
                if privileges == 'staff':
                    my_user.is_staff = True
                elif privileges == 'super_user':
                    my_user.is_staff = True
                    my_user.is_superuser = True                       
                my_user.save()  
                
                if my_user:
                    if button_send == 'true' and email:
                        data_email = {
                        'title': "Welcome to WalkableStreet",
                        'link': None,
                        'greeting': 'Hi new user!',
                        'text': "We hope you enjoy using our app, sharing your experience in each walk and checking it.\nThis email includes your account details, so please keep it safe!.",
                        'support_team': SUPPORT_TEAM,
                        'username': new_walkuser.username,
                        'password': password,
                        'opt': 3,
                        } 
                        template = loader.get_template('email/email.html')
                        email_menssage = template.render(data_email)

                        my_email = EmailMessage('[WalkableStreet] The user was created successfully!',email_menssage,settings.DEFAULT_FROM_EMAIL,[email])
                        my_email.content_subtype = 'html'
                        my_email.send() 
                    messages.success(request, 'The user ' + new_walkuser.username +  ' was successfully created and configured.')
                    response = {'status': 'success','code': Response_status.HTTP_201_CREATED,'message': 'The user ' + new_walkuser.username +  ' was successfully created and configured.' }
                else:
                    messages.error(request, 'Error, the privileges user could not be inserted.')
                    response = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Error, the privileges user could not be inserted.'}

        else:
            messages.error(request, 'Error, the user could not be created.')
            response = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Error, the user could not be created.'}    
        
    return JsonResponse(response)


@csrf_exempt
def UserUpdate(request): 
   
    if request.method == "POST":
      
        id = request.POST.get('id','')
        username = request.POST.get('username', '') 
        email = request.POST.get('email','')             
        password = request.POST.get('password', '')
        phone = request.POST.get('phone','')
        walkgroup = request.POST.get('walkgroup','')
        profile = request.POST.get('profile', '') 
        country = request.POST.get('country','')             
        countryCode = request.POST.get('countryCode','') 
        privileges = request.POST.get('privileges', '')
        pc = request.POST.get('pc','')        
        response = dict()   

        if WalkUser.objects.filter(id=id).exists(): 
           
            try:
                WalkUser.objects.filter(id=id).update(username=username, email=email, celphone=phone, walkgroup=walkgroup, profile=profile, country=country, countryCode=countryCode)
                walkuser = WalkUser.objects.get(id=id)
                if pc == 'true': 
                    try:                  
                        walkuser.set_password(password)
                        walkuser.save()
                    except:
                        messages.error(request, 'Error, the password user could not be updated.')
                        response = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Error, the password user could not be updated.'}
                                
                my_user = User.objects.get(id=id)
                try:
                    if privileges == 'staff':
                        my_user.is_staff = True
                    elif privileges == 'super_user':
                        my_user.is_staff = True
                        my_user.is_superuser = True
                    else:
                        my_user.is_staff = False
                        my_user.is_superuser = False
                    my_user.save()  
                   
                    messages.success(request, 'The user ' + username +  ' was successfully updated.')
                    response = {'status': 'success','code': Response_status.HTTP_200_OK,'message': 'The user ' + username +  ' was successfully updated.' }
                except:
                    messages.error(request, 'Error, the privileges user could not be updated.')
                    response = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Error, the privileges user could not be updated.'}

            except:
                messages.error(request, 'Error, the user could not be updated.')
                response = {'status': 'error', 'code': Response_status.HTTP_400_BAD_REQUEST, 'message': 'Error, the user could not be updated.'}
       
        else:
            messages.error(request, "User not found.")
            response = {
                'status': 'error',
                'code': Response_status.HTTP_404_NOT_FOUND,
                'message': "User not found."    
            }
    
    return JsonResponse(response)



#######################################

# END VIEWS FOR DJANGO APP - TEMPLATES

#######################################



