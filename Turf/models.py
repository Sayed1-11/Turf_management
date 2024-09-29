from django.db import models,transaction
from datetime import datetime, timedelta, time
from Offers.models import Coupon
from User.models import UserModel
from django.core.validators import MinValueValidator, MaxValueValidator
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum

class Sports(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Facility(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name

class Turf(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    image = models.ImageField(upload_to='turf_images/')
    facilities = models.ManyToManyField(Facility)
    rating = models.FloatField(default=0.0)  
    availble_offers = models.ManyToManyField(Coupon,null=True)
    sports = models.ManyToManyField(Sports, null=True, blank=True)
    def __str__(self):
        return self.name

    def calculate_average_rating(self):
        ratings = self.ratings.all()  
        if ratings.exists():
            average_rating = ratings.aggregate(models.Avg('rating'))['rating__avg']
            return round(average_rating, 1)  # Round to 1 decimal place
        return 0.0

    def update_rating(self):
        self.rating = self.calculate_average_rating()
        self.save()


class TurfRating(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    turf = models.ForeignKey(Turf, related_name='ratings', on_delete=models.CASCADE)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)] 
    )
    comment = models.TextField(blank=True, null=True)  
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating by {self.user} for {self.turf} - {self.rating}/5"

    class Meta:
        unique_together = ('user', 'turf')  

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.turf.update_rating()


class FieldSize(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

Sports_CHOICE = [
    ('Cricket', 'Cricket'),
    ('Football', 'Football'),
   
]


class TurfSlot(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, null=True)
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE)
    field_size = models.ForeignKey(FieldSize, on_delete=models.CASCADE)
    start_time = models.TimeField()
    sports = models.CharField(max_length=256, choices=Sports_CHOICE, null=True, blank=True)
    end_time = models.TimeField()
    date = models.DateField()
    is_booked = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=2000)
    advance_price = models.DecimalField(max_digits=6, decimal_places=2, default=500)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.turf.name} ({self.field_size.name}) - {self.date} {self.start_time} to {self.end_time}"

    class Meta:
        unique_together = ('turf', 'date', 'start_time', 'end_time')

    # Method to calculate the dynamic price of the slot
    def calculate_price(self):
        start_datetime = datetime.combine(self.date, self.start_time)
        end_datetime = datetime.combine(self.date, self.end_time)
        duration = (end_datetime - start_datetime).total_seconds() / 3600  # Convert to hours

        # Calculate the base price based on slot duration
        total_price = self.price * duration

        # Apply coupon discount if available
        if self.coupon:
            total_price -= total_price * (self.coupon.discount_percentage / 100)

        return total_price
 
# Swimming Session Model
class SwimmingSession(models.Model):
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=20)
    price_per_person = models.DecimalField(max_digits=6, decimal_places=2, default=200.00)

    def __str__(self):
        return f"Session from {self.start_time} to {self.end_time}"

    class Meta:
        unique_together = ('start_time', 'end_time')
        ordering = ['start_time']

    def clean(self):
        super().clean()
        if self.end_time <= self.start_time:
            if not (self.start_time.hour == 23 and self.end_time == time(0, 0)):
                raise ValidationError("End time must be after start time.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def remaining_capacity(self, date):
        """
        Calculates the remaining capacity for the session on a given date.
        """
        total_people = SwimmingSlot.objects.filter(session=self, date=date).aggregate(
            Sum('number_of_people')
        )['number_of_people__sum'] or 0
        return self.capacity - total_people


# Swimming Slot Model
class SwimmingSlot(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, null=True)
    turf = models.ForeignKey('Turf', on_delete=models.CASCADE)
    field_size = models.ForeignKey('FieldSize', on_delete=models.CASCADE, null=True)
    date = models.DateField()
    session = models.ForeignKey(SwimmingSession, on_delete=models.CASCADE, null=True)
    number_of_people = models.PositiveIntegerField()

    def available_capacity(self):
        """
        Check the remaining capacity for the session.
        """
        return self.session.remaining_capacity(self.date)

    def book_slot(self, number_of_people):
        """
        Book a slot for a given number of people, updating the capacity.
        """
        if number_of_people <= 0:
            raise ValueError("Number of people must be greater than zero.")
        
        if self.available_capacity() < number_of_people:
            raise ValueError("Not enough capacity to book the slot.")

        self.number_of_people += number_of_people
        self.save()

    def total_price(self):
        """
        Calculate the total price based on the number of people.
        """
        return self.number_of_people * self.session.price_per_person


# Atomic Slot Booking Function
def book_slot_atomic(slot, people_count):
    """
    Atomically book a slot to prevent race conditions.
    """
    with transaction.atomic():
        # Lock the slot to avoid race conditions
        slot = SwimmingSlot.objects.select_for_update().get(id=slot.id)
        if slot.available_capacity() < people_count:
            raise ValueError("Cannot book. Slot capacity exceeded.")

        # Book the slot and update the number of people
        slot.book_slot(people_count)

class BadmintonSlot(models.Model):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, null=True)
    turf = models.ForeignKey(Turf, on_delete=models.CASCADE)
    field_size = models.ForeignKey(FieldSize, on_delete=models.CASCADE)
    start_time = models.TimeField()
    end_time = models.TimeField()
    date = models.DateField()
    is_booked = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=2000)
    advance_price = models.DecimalField(max_digits=6, decimal_places=2, default=500)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.turf.name} ({self.field_size.name}) - {self.date} {self.start_time} to {self.end_time}"

    class Meta:
        unique_together = ('turf', 'date', 'start_time', 'end_time')

    # Method to calculate the dynamic price of the slot
    def calculate_price(self):
        start_datetime = datetime.combine(self.date, self.start_time)
        end_datetime = datetime.combine(self.date, self.end_time)
        duration = (end_datetime - start_datetime).total_seconds() / 3600  # Convert to hours

        # Calculate the base price based on slot duration
        total_price = self.price * duration

        # Apply coupon discount if available
        if self.coupon:
            total_price -= self.coupon.discount_amount  


        return total_price