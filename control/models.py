from django.db import models
#from django.contrib.gis.db import models
from django.contrib.auth.models import User
from datetime import datetime, timezone
from control.choices import (GROUP_TYPES, PROFILE_LIST, COUNTRY_LIST,GENDER_TYPES, ABILITY_TYPES, AGE_TYPES, DECISION_TYPES,PURPOSE_TYPES,GROUPSIZE_TYPES,FAMILIARITY_TYPES,PERCEPTION_TYPES,BUTTON_TIPOS)
from django.utils.text import slugify
from haversine import haversine, Unit
from django.db.models import Sum

def get_deleted_user_instance():
    user = WalkUser.objects.get_or_create(username='user_deleted')
    user[0].set_password('Walkability.app2022!')
    user[0].save()
    return user[0].id

def get_deleted_group_instance():
    group = Group.objects.get_or_create(tag='no_group')    
    return group[0].id

def get_deleted_version_instance():
    version = Version.objects.get_or_create(country='global', number_ver = 'xxxx-xx-xx', name='version_deleted')
    return version[0].id

class Group(models.Model):
    tag = models.CharField(max_length=30)
    group_type = models.CharField(max_length=30, null=True, blank=True, choices=GROUP_TYPES)
    name = models.CharField(max_length=300, null=True, default='N/N')

    def __str__(self):
        return f'{self.group_type} - {self.name} - {self.tag}'


class WalkUser(User):
    walkgroup = models.ForeignKey(Group, on_delete=models.SET(get_deleted_group_instance), null=True)
    celphone = models.CharField(max_length=15, null=True)
    profile = models.CharField(max_length=20, null=True, blank=True, choices=PROFILE_LIST, default="contributor")
    country = models.CharField(max_length=50, null=True, default="N/C")
    countryCode = models.CharField(max_length=7, null=True, default='N/C')

    def __str__(self):
        return f'{self.username} - {self.email}'


class Version(models.Model):
    country = models.CharField(max_length=30, null=True, blank=True, choices=COUNTRY_LIST)
    number_ver = models.CharField(max_length=10, null=True, blank=True)
    name = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f'{self.country} - {self.number_ver}'


class UserContext(models.Model):
    user = models.ForeignKey(WalkUser, on_delete=models.SET(get_deleted_user_instance), null=True)
    gender = models.CharField(max_length=10, blank=True, choices=GENDER_TYPES) 
    ability = models.CharField(max_length=10, blank=True, choices=ABILITY_TYPES)
    age = models.CharField(max_length=10, blank=True, choices=AGE_TYPES)
    created_date = models.DateTimeField(auto_now_add=True, null=True)
    
    def __str__(self):
        return f'{self.user.username} - {self.gender} - {self.ability} - {self.age}'


class WalkContext(models.Model):
    user = models.ForeignKey(WalkUser, on_delete=models.SET(get_deleted_user_instance), null=True)
    version = models.ForeignKey(Version, on_delete=models.SET(get_deleted_version_instance), null=True)
    decision = models.CharField(max_length=15, blank=True, choices=DECISION_TYPES)
    purpose = models.CharField(max_length=15, blank=True, choices=PURPOSE_TYPES)
    group_size = models.CharField(max_length=20, blank=True, choices=GROUPSIZE_TYPES)
    familiarity = models.CharField(max_length=10, blank=True, choices=FAMILIARITY_TYPES)
    date_start = models.DateTimeField(auto_now_add=True, null=True)
    latitude_start = models.DecimalField(max_digits=16, decimal_places=12, null=True)
    longitude_start = models.DecimalField(max_digits=16, decimal_places=12, null=True)
    gpsaccuracy_start  = models.DecimalField(max_digits=16, decimal_places=12, null=True)
    date_end = models.DateTimeField(auto_now=False, auto_now_add=False, null=True, editable = False)
    latitude_end = models.DecimalField(max_digits=16, decimal_places=12, null=True)
    longitude_end = models.DecimalField(max_digits=16, decimal_places=12, null=True)
    gpsaccuracy_end  = models.DecimalField(max_digits=16, decimal_places=12, null=True)
    weather_code = models.CharField(max_length=150, blank=True, null=True)
    weather_codition = models.CharField(max_length=50, blank=True, null=True)
    weather_text = models.CharField(max_length=180, blank=True, null=True)
    temperature = models.CharField(max_length=5, blank=True, null=True)
    city = models.CharField(max_length=60, blank=True, null=True)
    city_tableid = models.PositiveIntegerField(default=0) 
    countryCode = models.CharField(max_length=7, null=True, default='N/C')
    postalCode = models.CharField(max_length=10, null=True, blank=True)
    disable_date_auto_now = models.BooleanField(default=False, blank=True, null=True)
    distance_new = models.DecimalField(max_digits=16, decimal_places=5, null=True)

    def __str__(self):
        return f'{self.user} - {self.decision} - {self.purpose} - {self.group_size} - {self.familiarity}'
    
    def calc_distance(self):
        total_distance = 0
        dataset = Data.objects.filter(walk_context=self.id).values('id','latitude','longitude').order_by('id')

        if len(dataset)>0:
            if self.latitude_start and self.longitude_start and self.latitude_end and self.longitude_end:
                coords = [(self.latitude_start, self.longitude_start)] + [(p['latitude'], p['longitude']) for p in dataset] + [(self.latitude_end, self.longitude_end)]
                distancias = [haversine(coords[i - 1], coords[i], unit='km') for i in range(1, len(coords))]
                total_distance = sum(distancias)
        
        self.distance_new = total_distance
        self.save() 
    '''
    def calc_distance(self):
        sections = list()
        list_a = list()
        list_b = list()
        total_distance = 0
        dataset = Data.objects.filter(walk_context=self.id).order_by('id')
        
        if len(dataset)>0:
        
            if self.latitude_start and self.longitude_start and self.latitude_end and self.longitude_end:
                list_a.append(list([self.latitude_start, self.longitude_start]))
                list_b.append(list([dataset[0].latitude, dataset[0].longitude]))

            for i, point in enumerate(dataset, start=0):
                if i < len(dataset)-1:
                    list_a.append(list([point.latitude, point.longitude]))
                if i > 0:
                    list_b.append(list([point.latitude, point.longitude]))
        
            if self.latitude_start and self.longitude_start and self.latitude_end and self.longitude_end:        
                list_b.append(list([self.latitude_end, self.longitude_end]))
                list_a.append(list([dataset[len(dataset)-1].latitude, dataset[len(dataset)-1].longitude]))

            for p_start, p_end in zip(list_a, list_b):           
                sections.append({'start': p_start, 'end': p_end})
        
            for section in sections:
                total_distance = total_distance + haversine(section['start'], section['end'], unit='km')  

        self.distance_new = round(total_distance,5)
        self.save()
    '''
    def save(self, *args, **kwargs):
        if self.disable_date_auto_now == False:
            self.date_end = datetime.now(timezone.utc)
        super(WalkContext, self).save(*args, **kwargs)


class Data(models.Model):
    user = models.ForeignKey(WalkUser, on_delete=models.SET(get_deleted_user_instance), null=True)
    context = models.ForeignKey(UserContext, on_delete=models.SET_NULL, null=True)
    walk_context = models.ForeignKey(WalkContext, on_delete=models.CASCADE, null=True)
    latitude = models.DecimalField(max_digits=16, decimal_places=12)
    longitude = models.DecimalField(max_digits=16, decimal_places=12)
    datetime = models.DateField(auto_now_add=True)
    datetime_new = models.DateTimeField(auto_now_add=True, blank=True)
    comments = models.TextField(null=True)
    gpsaccuracy  = models.DecimalField(max_digits=16, decimal_places=12, null=True) # cuality of precision
    perception = models.CharField(max_length=10, null= True, blank=True, choices=PERCEPTION_TYPES)
    
    def __str__(self):
        return f'{self.user} - {self.latitude} - {self.longitude} - {self.gpsaccuracy} - {self.datetime}'


class Button(models.Model):
    tag = models.CharField(max_length=50)
    description = models.CharField(max_length=250)
    clasification = models.CharField(max_length=10, null=True, blank=True, choices=BUTTON_TIPOS)
    image = models.FileField(null=True,blank=True)
    active = models.BooleanField(default=False)
    position = models.IntegerField(null=True, blank=True)
    version = models.ForeignKey(Version, on_delete=models.SET(get_deleted_version_instance), null=True)

    def __str__(self):
        return f'{self.tag} - {self.clasification} - {self.active} - {self.version}'


class DataValue(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE)
    value = models.ForeignKey(Button, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['data','value']

    def __str__(self):
        return f'{self.data.latitude} - {self.data.longitude} - {self.data.gpsaccuracy} - {self.value.tag}'

    def save(self, *args, **kwargs):
        if not self.data.perception:
            self.data.perception = self.value.clasification
            self.data.save()
        super(DataValue, self).save(*args, **kwargs)


class DataImage(models.Model):
    data = models.ForeignKey(Data, on_delete=models.CASCADE)
    image = models.ImageField(null=True)
    
    def __str__(self):
        return f'{self.data.latitude} - {self.data.longitude} - {self.data.gpsaccuracy} - {self.image}'


class Country(models.Model):
    name = models.CharField(max_length=50)
    slug = models.CharField(max_length=100, null=True, blank=True)
    iso3 = models.CharField(max_length=6)
    iso2 = models.CharField(max_length=6)
    numeric_code = models.CharField(max_length=6)
    phone_code = models.CharField(max_length=18)
    capital = models.CharField(max_length=30)
    currency = models.CharField(max_length=20)
    native = models.CharField(max_length=50, null=True, blank=True)
    region = models.CharField(max_length=30)
    subregion = models.CharField(max_length=30)
    latitude = models.DecimalField(max_digits=16, decimal_places=12)
    longitude = models.DecimalField(max_digits=16, decimal_places=12)
    emojiU = models.CharField(max_length=25)

    def __str__(self):
        return f'{self.name}'

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(Country, self).save(*args, **kwargs)


class State(models.Model):
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    state_code = models.CharField(max_length=6)
    state_type = models.CharField(max_length=80, null=True, blank=True)
    latitude = models.DecimalField(max_digits=16, decimal_places=12, null=True)
    longitude = models.DecimalField(max_digits=16, decimal_places=12, null=True)

    def __str__(self):
        return f'{self.name}'

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(State, self).save(*args, **kwargs)



class City(models.Model):
    name = models.CharField(max_length=100)
    slug = models.CharField(max_length=100, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    wikiDataId = models.CharField(max_length=10, null=True)
    latitude = models.DecimalField(max_digits=16, decimal_places=12)
    longitude = models.DecimalField(max_digits=16, decimal_places=12)
    postalCode = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f'{self.name}'

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super(City, self).save(*args, **kwargs)



class GPSCity(models.Model):
    name = models.CharField(max_length=600)
    city = models.ForeignKey(City, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['name','city']

    def __str__(self):
        return f'{self.city.name} - {self.name}'
