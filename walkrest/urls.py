from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls import include, url
from rest_framework import routers
from control import views
from rest_framework_simplejwt.views import (TokenObtainPairView,TokenRefreshView, TokenVerifyView)

from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static
from walkrest.settings import MEDIA_URL, MEDIA_ROOT

from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_yasg import openapi
from drf_yasg.views import get_schema_view as swagger_get_schema_view
from control.views import (CustomOpenAPISchemaGenerator)
from django.contrib.auth.decorators import login_required

schema_view = swagger_get_schema_view(
    openapi.Info(
        title="Walkability Rest API",
        default_version='1.0.0',
        description="API documentation of Walkability App and Site",
        contact = openapi.Contact(email=settings.DEFAULT_FROM_EMAIL)
    ),
    public=False,
    permission_classes=[IsAdminUser],  
    generator_class=CustomOpenAPISchemaGenerator,  
)


router = routers.DefaultRouter()
router.register(r'user', views.WalkUserViewSet)
router.register(r'group', views.GroupViewSet)
router.register(r'usercontext', views.UserContextViewSet)
router.register(r'walkcontext', views.WalkContextViewSet)
router.register(r'version', views.VersionViewSet)
router.register(r'data', views.DataViewSet)
router.register(r'datavalue', views.DataValueViewSet)
router.register(r'button', views.ButtonViewSet)
router.register(r'dataimage', views.DataImageViewSet)
router.register(r'country', views.CountryViewSet)
router.register(r'state', views.StateViewSet)
router.register(r'city', views.CityViewSet)
router.register(r'gpscity', views.GPSCityViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('login/', views.LoginViewSet.as_view(), name="api_login"),
    path('api/loginweb/', views.LoginwebViewSet.as_view(), name="api_loginweb"),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/logout/', views.LogoutAPIView.as_view(), name="api_logout"),

    url(r'^status/$', views.status),
    url(r'^statusNEW/$', views.statusNEW),
    url(r'^perception_report/$', views.perception_report),
    url(r'^ranking_icon/$', views.ranking_icon),     
    url(r'^dataset/$',views.get_dataset),
    url(r'^datasetNew/$',views.get_datasetNew),   
    url(r'^dataset_public/$',views.get_dataset_public), 
    url(r'^datawalk_range/$', views.getDataWalk_range),   
    url(r'username_check/', views.checkUsername, name='username-check'), 
    url(r'^point_check/$',views.checkPointStatus), 
    url(r'^countries/$',views.get_countries),
    url(r'^infoReport/$',views.getItemReports),
    url(r'^infoReport2/$',views.getItemReports_new),
    url(r'^clusters/$',views.get_clusters),
    url(r'^lastpoint/$',views.getLastPoint),

    path('password/change-password/', views.ChangePasswordView.as_view(), name='change-password'),   
    path('req-reset-password/', views.ResetPasswordView.as_view(), name='req-reset-password'),
    path('api/v1/reset-password/<uidb64>/<token>/', views.PasswordTokenCheckView_old.as_view()),
    path('api/v2/reset-password/<uidb64>/<token>/', views.PasswordTokenCheckView.as_view(), name='reset-password-confirm'),
    path('reset-password-complete/', views.SetNewPasswordView.as_view(), name='reset-password-complete'),   

   #path('deleteinfo/', views.DeleteAllInfoView.as_view()),       
    path('deleteinfo/', views.DeleteUserInfoView.as_view()), 
    path('delete_datawalk/', views.DeleteDataWalkView.as_view()), 
    path('finish_walk/', views.FinishWalkViewset.as_view()),
    path('data_insert/', views.InsertDataView.as_view()),
    url(r'^disable_auto_add/$', views.disable_auto_add),
    url(r'^fill_countrycode/$', views.fillcodeCountry),
    url(r'^sendmail/$', views.sendMail),
    url(r'^getusers/$',views.get_users), 

    #PENDIENTES
    #url(r'^cities/$',views.get_cities),
    #url(r'^fill_gpsname/$', views.fillGPSname),
    #url(r'^fill/$', views.fillGeopyName),
    #url(r'^get_json/$', views.get_json_file),
    
    #template + functions
    url(r'table/', login_required(views.DataTable), name='datatable'),
    url(r'csv/', views.csvResponse, name='csv_file'),
    url(r'geticons/$', views.getIcons, name='geticons'),
    url(r'reset_pass/$', views.ResetPass, name='reset_pass'),
    url(r'set-pass-complete/', views.setNewPass, name='set_pass_complete'),
    url(r'email/', views.Email, name='format_email'),
    url(r'validate_login/', views.validateLogin, name='validate_login'),
    url(r'data_list/', login_required(views.DataSection), name='data_list'),
    url(r'data_delete/', views.DataDelete, name='data_delete'),
    url(r'user_list/', login_required(views.UserSection), name='user_list'),
    url(r'user_form/', login_required(views.UserForm), name='user_form'),
    url(r'user_create/', login_required(views.UserCreate), name='user_create'),
    url(r'user_update/', login_required(views.UserUpdate), name='user_update'),
    url(r'user_delete/', views.UserDelete, name='user_delete'),

    #complement
    url(r'csv_webreport/', views.csvWebReport, name='csv_webreport'),
    url(r'csv_webreportL/', views.csvWebReportL, name='csv_webreportL'),
    url(r'statusSR/', views.status_stats_rank, name='status_sr'),
    url(r'pointPolygon/', views.validatePointPolygon, name='point_poly'),

    #personal use
    url(r'^multidisable_auto_add/$', views.multidisable_auto_add),
    url(r'^check_walks/$', views.check_unfinish_walks),
    url(r'duplicate/$', views.showIconsDuplicate),
    url(r'checkNewDistance/$', views.checkNewDistance),
    url(r'fillNewDistance/$', views.fillNewDistance),
    url(r'fillPColor/$', views.fillPerceptionColor),
    url(r'pi/', views.getPointsInside, name='pi'), 
    url(r'statusP/', views.status_data_polygon, name='status_poly'),

    #function that must delete or no use
    url(r'getmail/', views.getEmail, name='getmail'),

    #documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', login_required(schema_view.without_ui(cache_timeout=0)), name='schema-json'),
    path('swagger/', login_required(schema_view.with_ui('swagger', cache_timeout=0)), name='schema-swagger-ui'),
    path('redoc/', login_required(schema_view.with_ui('redoc', cache_timeout=0)), name='schema-redoc'),
    
    #additional for required_login
    path("accounts/", include("django.contrib.auth.urls"))
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)
