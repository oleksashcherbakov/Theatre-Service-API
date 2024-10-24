from datetime import datetime

from django.db.models import Count, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from theatre.models import (
    Actor,
    Genre,
    Play,
    TheatreHall,
    Performance,
    Ticket,
    Reservation,
)

from theatre.serializers import (
    ActorSerializer,
    GenreSerializer,
    PlaySerializer,
    TheatreHallSerializer,
    PerformanceSerializer,
    PerformanceListSerializer,
    TicketSerializer,
    ReservationSerializer,
    PlayListSerializer,
    PlayRetrieveSerializer,
    PerformanceRetrieveSerializer,
    TicketListSerializer,
    TicketRetrieveSerializer,
    ReservationListSerializer,
    ReservationRetrieveSerializer,
    PlayImageSerializer,
)


class ActorViewSet(viewsets.ModelViewSet):
    queryset = Actor.objects.all()
    serializer_class = ActorSerializer


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class PlayViewSet(viewsets.ModelViewSet):
    queryset = Play.objects.all()

    @staticmethod
    def _params_to_ints(query_string):
        return [int(str_id) for str_id in query_string.split(",")]

    def get_queryset(self):
        queryset = self.queryset

        actors = self.request.query_params.get("actors")
        genres = self.request.query_params.get("genres")

        if actors:
            actors_ids = self._params_to_ints(actors)
            queryset = queryset.filter(actors__in=actors_ids)

        if genres:
            genres_ids = self._params_to_ints(genres)
            queryset = queryset.filter(genres__in=genres_ids)

        if self.action in ("list", "retrieve"):
            return queryset.prefetch_related("actors", "genres")
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return PlayListSerializer
        if self.action == "retrieve":
            return PlayRetrieveSerializer
        if self.action == "upload_image":
            return PlayImageSerializer
        return PlaySerializer

    @action(
        methods=["post"],
        detail=True,
        url_path="upload-image",
    )
    def upload_image(self, request, pk=None):
        serializer = self.get_serializer(Play, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "genres",
                type=OpenApiTypes.NUMBER,
                description="Filter by genres (ex. ?genres=2,1)",
                many=True,
            ),
            OpenApiParameter(
                "actors",
                type=OpenApiTypes.NUMBER,
                description="Filter by actors id (ex. ?actors=2,3)",
                many=True,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TheatreHallViewSet(viewsets.ModelViewSet):
    queryset = TheatreHall.objects.all()
    serializer_class = TheatreHallSerializer


class PerformanceViewSet(viewsets.ModelViewSet):
    queryset = Performance.objects.all()

    @staticmethod
    def _params_to_ints(query_string):
        return [int(str_id) for str_id in query_string.split(",")]

    def get_queryset(self):
        queryset = self.queryset

        if self.action == "list":
            queryset = (
                queryset.select_related()
                .prefetch_related("play__actors", "play__genres")
                .annotate(
                    tickets_available=F("theatre_hall__rows")
                    * F("theatre_hall__seats_in_row")
                    - Count("tickets")
                )
                .order_by("id")
            )
        if self.action == "retrieve":
            queryset = queryset.select_related().prefetch_related(
                "play__actors", "play__genres"
            )

        plays = self.request.query_params.get("play")
        theatre_halls = self.request.query_params.get("theatre_hall")
        date = self.request.query_params.get("date")

        if plays:
            plays_ids = self._params_to_ints(plays)
            queryset = queryset.filter(play__in=plays_ids)

        if theatre_halls:
            theatre_halls_ids = self._params_to_ints(theatre_halls)
            queryset = queryset.filter(theatre_hall__in=theatre_halls_ids)

        if date:
            date = datetime.strptime(date, "%Y-%m-%d").date()
            queryset = queryset.filter(show_time__date=date)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return PerformanceListSerializer
        if self.action == "retrieve":
            return PerformanceRetrieveSerializer
        return PerformanceSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "plays",
                type=OpenApiTypes.NUMBER,
                description="Filter by plays (ex. ?plays=2,1)",
                many=True,
            ),
            OpenApiParameter(
                "theatre_halls",
                type=OpenApiTypes.NUMBER,
                description="Filter by theatre halls id "
                            "(ex. ?theatre_halls=2,3)",
                many=True,
            ),
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Filter by date (ex. ?date=2024-01-12)",
                many=True,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects

    def get_serializer_class(self):
        if self.action == "list":
            return ReservationListSerializer
        if self.action == "retrieve":
            return ReservationRetrieveSerializer
        return ReservationSerializer

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)

        if self.action == "list":
            queryset = queryset.prefetch_related(
                "tickets__performance__play",
                "tickets__performance__theatre_hall"
            )
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("tickets")
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketsViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all().select_related(
        "performance__play", "performance__theatre_hall", "reservation__user"
    )

    def get_serializer_class(self):
        if self.action == "list":
            return TicketListSerializer
        if self.action == "retrieve":
            return TicketRetrieveSerializer
        return TicketSerializer
