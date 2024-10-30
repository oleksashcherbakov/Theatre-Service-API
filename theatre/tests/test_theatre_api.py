from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models import F, Count
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient

from theatre.models import (
    Play,
    TheatreHall,
    Performance,
    Genre,
    Actor,
    Reservation,
    Ticket,
)
from theatre.serializers import (
    PlayListSerializer,
    PerformanceListSerializer,
    PlayRetrieveSerializer,
    PerformanceRetrieveSerializer,
    TicketListSerializer,
    TicketRetrieveSerializer,
)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_theatre_hall(**params):
    defaults = {"name": "George", "rows": 10, "seats_in_row": 10}
    defaults.update(params)

    return TheatreHall.objects.create(**defaults)


def sample_play(**params):
    defaults = {
        "title": "Sample play",
        "description": "Sample description",
    }
    defaults.update(params)

    return Play.objects.create(**defaults)


def sample_performance(**params):
    theatre_hall = sample_theatre_hall()
    play = sample_play()
    defaults = {
        "play": play,
        "theatre_hall": theatre_hall,
        "show_time": "2024-10-22 14:00:00",
    }
    defaults.update(params)

    return Performance.objects.create(**defaults)


def sample_reservation(**params):
    user = get_user_model().objects.create(
        email="test@test.com",
        password="PASSWORD"
    )
    defaults = {
        "user": user,
        "created_at": datetime.now(),
    }
    defaults.update(params)

    return Reservation.objects.create(**defaults)


def sample_ticket(**params):
    defaults = {
        "row": 1,
        "seat": 1,
        "performance": sample_performance(),
        "reservation": sample_reservation(),
    }
    defaults.update(params)
    return Ticket.objects.create(**defaults)


def play_detail_url(play_id):
    return reverse("theatre:play-detail", args=(play_id,))


def performance_detail_url(performance_id):
    return reverse("theatre:performance-detail", args=(performance_id,))


def ticket_detail_url(ticket_id):
    return reverse("theatre:ticket-detail", args=(ticket_id,))


PLAY_URL = reverse("theatre:play-list")
PERFORMANCE_URL = reverse("theatre:performance-list")
TICKET_URL = reverse("theatre:ticket-list")


class UnauthenticatedTheatreApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_theatre_api_play(self):
        res = self.client.get(PLAY_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_theatre_api_performance(self):
        res = self.client.get(PERFORMANCE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_theatre_api_tickets(self):
        res = self.client.get(TICKET_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedUserPlaysTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_plays_list(self):
        sample_play()
        play_with_actors = sample_play()
        play_with_genre = sample_play()

        actor_1 = sample_actor()
        genre_1 = sample_genre()

        play_with_actors.actors.add(actor_1)
        play_with_genre.genres.add(genre_1)

        response = self.client.get(PLAY_URL)

        plays = Play.objects.all()
        serializer = PlayListSerializer(plays, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_plays_by_actors(self):
        actor_1 = sample_actor(first_name="name_1")
        actor_2 = sample_actor(first_name="name_2")

        play_without_actors = sample_play()
        play_with_actor_1 = sample_play()
        play_with_actor_2 = sample_play()

        play_with_actor_1.actors.add(actor_1)
        play_with_actor_2.actors.add(actor_2)

        response = self.client.get(
            PLAY_URL,
            {"actors": f"{actor_1.id}, {actor_2.id}"},
        )

        serializer_without_actors = PlayListSerializer(play_without_actors)
        serializer_with_actor_1 = PlayListSerializer(play_with_actor_1)
        serializer_with_actor_2 = PlayListSerializer(play_with_actor_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_actor_1.data, response.data)
        self.assertIn(serializer_with_actor_2.data, response.data)
        self.assertNotIn(serializer_without_actors.data, response.data)

    def test_filter_plays_by_genres(self):
        genre_1 = sample_genre(name="genre_1")

        play_without_genres = sample_play()
        play_with_genre_1 = sample_play()

        play_with_genre_1.genres.add(genre_1)

        response = self.client.get(PLAY_URL, {"genres": f"{genre_1.id}"})

        serializer_without_genres = PlayListSerializer(play_without_genres)
        serializer_with_genre_1 = PlayListSerializer(play_with_genre_1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_with_genre_1.data, response.data)
        self.assertNotIn(serializer_without_genres.data, response.data)

    def test_retrieve_play_detail(self):
        play = sample_play()
        play.genres.add(sample_genre())
        play.actors.add(sample_actor())

        url = play_detail_url(play.id)

        response = self.client.get(url)

        serializer = PlayRetrieveSerializer(play)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_play_forbidden(self):
        payload = {"title": "Title_test", "description": "Description_test"}

        response = self.client.post(PLAY_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminPlayTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_play(self):
        payload = {"title": "Title_test",
                   "description": "Description_test"
                   }

        response = self.client.post(PLAY_URL, payload)
        play = Play.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(play, key))

    def test_create_play_with_actor_and_genre(self):
        actor_1 = sample_actor(first_name="name_1")
        genre_1 = sample_genre(name="genre_1")
        payload = {
            "title": "Title_test",
            "description": "Description_test",
            "actors": [actor_1.id],
            "genres": [genre_1.id],
        }

        response = self.client.post(PLAY_URL, payload)
        play = Play.objects.get(id=response.data["id"])
        actors = play.actors.all()
        genres = play.genres.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(actor_1, actors)
        self.assertIn(genre_1, genres)
        self.assertEqual(actors.count(), 1)
        self.assertEqual(genres.count(), 1)


class AuthenticatedUserPerformancesTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

        self.play = Play.objects.create(
            title="Hamlet", description="A tragedy by Shakespeare"
        )
        self.theatre_hall = TheatreHall.objects.create(
            name="Main Hall", rows=10, seats_in_row=10
        )
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.theatre_hall,
            show_time=datetime.now()
        )

    def test_performances_list(self):
        response = self.client.get(PERFORMANCE_URL)

        performances = Performance.objects.annotate(
            tickets_available=F("theatre_hall__rows") *
            F("theatre_hall__seats_in_row")
            - Count("tickets")
        ).order_by("id")
        serializer = PerformanceListSerializer(performances, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_filter_performances_by_plays(self):
        response = self.client.get(
            PERFORMANCE_URL,
            {"plays": f"{self.play.id}"},
        )
        performances = (
            Performance.objects.filter(play_id=self.play.id)
            .annotate(
                tickets_available=F("theatre_hall__rows")
                * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
            .order_by("id")
        )
        serializer_with_plays = PerformanceListSerializer(
            performances,
            many=True
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer_with_plays.data, response.data)

    def test_filter_performances_by_theatre_halls(self):
        response = self.client.get(
            PERFORMANCE_URL,
            {"theatre_halls": f"{self.theatre_hall.id}"},
        )
        performances = (
            Performance.objects.filter(theatre_hall_id=self.theatre_hall.id)
            .annotate(
                tickets_available=F("theatre_hall__rows")
                * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
            .order_by("id")
        )
        serializer_with_theatre_halls = PerformanceListSerializer(
            performances, many=True
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer_with_theatre_halls.data, response.data)

    def test_filter_performances_by_date(self):
        date = self.performance.show_time.date()
        response = self.client.get(
            PERFORMANCE_URL,
            {"date": date},
        )
        performances = (
            Performance.objects.filter(show_time__date=date)
            .annotate(
                tickets_available=F("theatre_hall__rows")
                * F("theatre_hall__seats_in_row")
                - Count("tickets")
            )
            .order_by("id")
        )
        serializer_with_theatre_halls = PerformanceListSerializer(
            performances, many=True
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer_with_theatre_halls.data, response.data)

    def test_retrieve_performance_detail(self):
        url = performance_detail_url(self.performance.id)

        response = self.client.get(url)

        serializer = PerformanceRetrieveSerializer(self.performance)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_play_forbidden(self):
        payload = {
            "play": self.play.title,
            "theatre_hall": self.theatre_hall.name,
            "show_time": self.performance.show_time,
        }

        response = self.client.post(PERFORMANCE_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminPerformanceTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

        self.play = Play.objects.create(
            title="Hamlet", description="A tragedy by Shakespeare"
        )
        self.theatre_hall = TheatreHall.objects.create(
            name="Main Hall", rows=10, seats_in_row=10
        )
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.theatre_hall,
            show_time=datetime.now()
        )

    def test_create_performance(self):
        payload = {
            "play": [self.play.id],
            "theatre_hall": [self.theatre_hall.id],
            "show_time": self.performance.show_time,
        }

        response = self.client.post(PERFORMANCE_URL, payload)
        print(response.data)
        performance = Performance.objects.get(id=response.data["id"])
        print(performance)
        print(performance.theatre_hall.id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class AuthenticatedUserTicketTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="testpassword",
        )
        self.client.force_authenticate(self.user)

        self.reservation = Reservation.objects.create(user=self.user)

        self.theatre_hall = TheatreHall.objects.create(
            name="TestHall", rows=10, seats_in_row=10
        )
        self.play = Play.objects.create(
            title="Test_Play", description="Test_description"
        )
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.theatre_hall,
            show_time=datetime.now()
        )
        self.ticket = Ticket.objects.create(
            row=2,
            seat=3,
            performance=self.performance,
            reservation=self.reservation
        )

    def test_tickets_list(self):
        response = self.client.get(TICKET_URL)
        serializer = TicketListSerializer(self.ticket)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer.data, response.data)
        self.assertEqual(len(response.data), 1)

    def test_retrieve_ticket_detail(self):
        url = ticket_detail_url(self.ticket.id)

        response = self.client.get(url)

        serializer = TicketRetrieveSerializer(self.ticket)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_ticket_forbidden(self):
        payload = {
            "row": 3,
            "seat": 3,
            "performance": self.performance.id,
            "reservation": self.reservation.id,
        }

        response = self.client.post(TICKET_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminTicketTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.com",
            password="adminpassword",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

        self.reservation = Reservation.objects.create(user=self.user)

        self.theatre_hall = TheatreHall.objects.create(
            name="TestHall", rows=10, seats_in_row=10
        )
        self.play = Play.objects.create(
            title="Test_Play", description="Test_description"
        )
        self.performance = Performance.objects.create(
            play=self.play,
            theatre_hall=self.theatre_hall,
            show_time=datetime.now()
        )
        self.ticket = Ticket.objects.create(
            row=2,
            seat=3,
            performance=self.performance,
            reservation=self.reservation
        )

    def test_create_ticket(self):
        payload = {
            "row": 3,
            "seat": 3,
            "performance": self.performance.id,
            "reservation": self.reservation.id,
        }

        response = self.client.post(TICKET_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_delete_ticket_as_staff_user(self):
        url = reverse("theatre:ticket-detail", args=[self.ticket.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ticket.objects.filter(id=self.ticket.id).exists())
