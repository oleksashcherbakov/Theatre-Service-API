from django.contrib import admin

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Reservation,
    Ticket,
)


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    inlines = (TicketInline,)


@admin.register(Actor)
class ActorAdmin(admin.ModelAdmin):
    list_display = ["id", "first_name", "last_name"]
    list_filter = ["first_name", "last_name"]
    search_fields = ["last_name"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["id", "name"]
    list_filter = ["name"]
    search_fields = ["name"]


@admin.register(Play)
class PlayAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "description"]
    list_filter = ["title"]
    search_fields = ["title"]


@admin.register(TheatreHall)
class TheatreHallAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "rows", "seats_in_row"]
    list_filter = ["name"]
    search_fields = ["name"]


@admin.register(Performance)
class PerformanceAdmin(admin.ModelAdmin):
    list_display = ["id", "play", "theatre_hall", "show_time"]
    list_filter = ["play", "theatre_hall", "show_time"]


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["id", "row", "seat", "performance"]
