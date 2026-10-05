"""
Tests for the food API.

Each test pins down a behaviour that was previously broken: the browser crashing
on a null rating, a broken menu tab, an owner page that 403'd, anyone being able
to edit someone else's outlet, and the small-location import path.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import FoodPlace, MenuItem


def make_place(**overrides):
    defaults = {
        'name': 'Corner Dhaba',
        'category': 'dhaba',
        'cuisine': 'north_indian',
        'latitude': 26.9,
        'longitude': 80.9,
        'city': 'Lucknow',
        'state': 'Uttar Pradesh',
        'rating': 0.0,
        'is_active': True,
    }
    defaults.update(overrides)
    return FoodPlace.objects.create(**defaults)


class FoodListTests(TestCase):
    """The public browse endpoint."""

    def setUp(self):
        self.client = APIClient()
        make_place(name='Tunday Kababi', rating=4.5)
        make_place(name='Blue Palm Cafe', category='cafe', rating=4.0)

    def test_list_returns_paginated_envelope(self):
        response = self.client.get('/api/food/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_garbage_page_does_not_500(self):
        # `int('abc')` used to raise and take down the whole endpoint.
        response = self.client.get('/api/food/?page=abc')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['page'], 1)

    def test_garbage_filters_are_ignored(self):
        response = self.client.get('/api/food/?min_rating=high&price_level=xyz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 2)

    def test_category_filter(self):
        response = self.client.get('/api/food/?category=cafe')
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Blue Palm Cafe')

    def test_category_all_is_not_a_stored_value(self):
        response = self.client.get('/api/food/?category=all')
        self.assertEqual(response.data['total'], 2)

    def test_location_filter_and_distance(self):
        response = self.client.get('/api/food/?lat=26.91&lon=80.91&radius=50')
        self.assertEqual(response.data['total'], 2)
        self.assertTrue(response.data['has_location'])
        self.assertIsNotNone(response.data['results'][0]['distance_km'])

    def test_invalid_coordinates_are_ignored_rather_than_crashing(self):
        # A NaN latitude makes every comparison below False, which emptied the
        # page instead of falling back to a plain browse.
        response = self.client.get('/api/food/?lat=abc&lon=abc')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['has_location'])
        self.assertEqual(response.data['total'], 2)

    def test_out_of_range_coordinates_are_rejected(self):
        response = self.client.get('/api/food/?lat=999&lon=999')
        self.assertFalse(response.data['has_location'])

    def test_sparse_flag_signals_thin_coverage(self):
        response = self.client.get('/api/food/')
        self.assertTrue(response.data['sparse'])

        make_place(name='Third Place', rating=3.0)
        make_place(name='Fourth Place', rating=3.0)
        make_place(name='Fifth Place', rating=3.0)
        response = self.client.get('/api/food/')
        self.assertFalse(response.data['sparse'])

    def test_non_veg_filter_includes_places_with_unknown_diet(self):
        # OSM rows often have no diet tag at all; filtering on `is_veg=False`
        # alone hid all of them.
        make_place(name='Untagged Cafe', category='cafe', is_veg=None)
        response = self.client.get('/api/food/?is_veg=false')
        names = [r['name'] for r in response.data['results']]
        self.assertIn('Untagged Cafe', names)


class FoodDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_menu_items_key_always_present(self):
        # The tab rendered off `menu_items?.length === 0`, which is false when
        # the key is absent, so the empty state never appeared.
        place = make_place()
        response = self.client.get(f'/api/food/{place.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('menu_items', response.data)
        self.assertEqual(response.data['menu_items'], [])

    def test_unrated_place_serialises_with_a_zero_rating(self):
        # OSM rows have no rating, so this is the common case. It has to come
        # back as a number the card can render, not a null that breaks `.toFixed`.
        place = make_place(rating=0.0, review_count=0)
        response = self.client.get(f'/api/food/{place.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['rating'], 0.0)
        self.assertEqual(response.data['review_count'], 0)

    def test_image_credit_is_returned(self):
        place = make_place(image_url='https://example.org/a.jpg', image_credit='Wikimedia / CC BY-SA 4.0')
        response = self.client.get(f'/api/food/{place.id}/')
        self.assertEqual(response.data['image_credit'], 'Wikimedia / CC BY-SA 4.0')

    def test_missing_place_is_404(self):
        self.assertEqual(self.client.get('/api/food/999999/').status_code, 404)


class OwnerWriteTests(TestCase):
    """
    Owner registration and listing.

    RegisterFoodPage used to fake the submission with a setTimeout, so nothing
    was ever persisted and MyFoodPlacesPage had nothing to show.
    """

    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.owner = User.objects.create_user(
            username='owner', email='owner@example.com', password='pw12345!'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='pw12345!'
        )

    def test_anonymous_cannot_create(self):
        self.assertEqual(self.client.post('/api/food/', {'name': 'X'}, format='json').status_code, 401)

    def test_owner_can_register_and_owner_is_set_server_side(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post('/api/food/', {
            'name': 'Royal Punjabi Dhaba',
            'category': 'dhaba',
            'cuisine': 'north_indian',
            'latitude': 26.9,
            'longitude': 80.9,
            'city': 'Lucknow',
            # A client claiming ownership or verification must be ignored.
            'owner': self.other.id,
            'is_verified': True,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)

        place = FoodPlace.objects.get(id=response.data['id'])
        self.assertEqual(place.owner, self.owner)
        self.assertFalse(place.is_verified)

    def test_mine_returns_only_own_listings(self):
        mine = make_place(name='Mine', owner=self.owner)
        make_place(name='Theirs', owner=self.other)
        make_place(name='OSM Import')  # owner is NULL

        self.client.force_authenticate(self.owner)
        response = self.client.get('/api/food/?mine=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['results'][0]['id'], mine.id)

    def test_mine_is_empty_for_anonymous(self):
        make_place(name='Mine', owner=self.owner)
        response = self.client.get('/api/food/?mine=true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], 0)

    def test_owner_can_edit_own_listing(self):
        place = make_place(name='Mine', owner=self.owner)
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f'/api/food/{place.id}/', {'description': 'Great value'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        place.refresh_from_db()
        self.assertEqual(place.description, 'Great value')

    def test_owner_cannot_edit_someone_elses_listing(self):
        # `IsAuthenticatedOrReadOnly` only proves someone is signed in, so any
        # authenticated user could rewrite any outlet.
        place = make_place(name='Theirs', owner=self.other)
        self.client.force_authenticate(self.owner)
        response = self.client.patch(f'/api/food/{place.id}/', {'name': 'Hijacked'}, format='json')
        self.assertEqual(response.status_code, 403)
        place.refresh_from_db()
        self.assertEqual(place.name, 'Theirs')

    def test_owner_cannot_edit_an_osm_imported_row(self):
        place = make_place(name='From OSM', owner=None)
        self.client.force_authenticate(self.owner)
        response = self.client.patch(f'/api/food/{place.id}/', {'name': 'Hijacked'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_owner_can_delete_own_listing(self):
        place = make_place(name='Mine', owner=self.owner)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.delete(f'/api/food/{place.id}/').status_code, 204)
        self.assertFalse(FoodPlace.objects.filter(pk=place.pk).exists())

    def test_out_of_range_coordinates_are_rejected(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post('/api/food/', {
            'name': 'Nowhere', 'latitude': 999, 'longitude': 80.9, 'city': 'X',
        }, format='json')
        self.assertEqual(response.status_code, 400)


class MenuItemTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.owner = User.objects.create_user(
            username='chef', email='chef@example.com', password='pw12345!'
        )
        self.other = User.objects.create_user(
            username='critic', email='critic@example.com', password='pw12345!'
        )
        self.place = make_place(name='Mine', owner=self.owner)

    def test_owner_can_add_and_remove_a_dish(self):
        self.client.force_authenticate(self.owner)

        created = self.client.post(
            f'/api/food/{self.place.id}/menu-items/',
            {'name': 'Butter Chicken', 'price': 320, 'is_veg': False},
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.data)
        # MenuItemCard reads `image`; the model field is `image_url`.
        self.assertIn('image', created.data)

        item_id = created.data['id']
        self.assertEqual(MenuItem.objects.filter(food_place=self.place).count(), 1)

        removed = self.client.delete(f'/api/food/{self.place.id}/menu-items/{item_id}/')
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(MenuItem.objects.filter(food_place=self.place).count(), 0)

    def test_menu_read_is_public(self):
        MenuItem.objects.create(food_place=self.place, name='Samosa', price=20)
        response = self.client.get(f'/api/food/{self.place.id}/menu-items/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_cannot_edit_menu_of_another_outlet(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(
            f'/api/food/{self.place.id}/menu-items/', {'name': 'Free Food'}, format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_edit_menu_of_an_osm_row(self):
        place = make_place(name='From OSM')
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f'/api/food/{place.id}/menu-items/', {'name': 'Free Food'}, format='json'
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_delete_a_dish_through_another_outlet(self):
        other_place = make_place(name='Theirs', owner=self.other)
        item = MenuItem.objects.create(food_place=self.place, name='Samosa', price=20)
        self.client.force_authenticate(self.other)
        # Item id belongs to a different outlet: must not resolve.
        response = self.client.delete(f'/api/food/{other_place.id}/menu-items/{item.id}/')
        self.assertEqual(response.status_code, 404)


class ImportTests(TestCase):
    """
    OSM import. These are the only routes that hit Overpass, so they must stay
    explicit: browse requests used to fire a blocking upstream call whenever an
    area came back thin.
    """

    def setUp(self):
        self.client = APIClient()
        # Import is a write and it costs an upstream call, so it is authenticated.
        User = get_user_model()
        self.user = User.objects.create_user(
            username='importer', email='importer@example.com', password='pw12345!'
        )
        self.client.force_authenticate(self.user)

    def test_anonymous_cannot_trigger_an_import(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            '/api/food/import-area/', {'lat': 26.9, 'lon': 80.9}, format='json'
        )
        self.assertEqual(response.status_code, 401)

    def test_browse_endpoints_never_call_overpass(self):
        with patch('food.views.fetch_food_near') as fetch, \
             patch('food.views.search_food_by_location') as search:
            self.client.get('/api/food/')
            self.client.get('/api/food/nearby/?lat=26.9&lon=80.9')
            self.client.get('/api/food/random/')
            fetch.assert_not_called()
            search.assert_not_called()

    def test_import_area_requires_coordinates(self):
        response = self.client.post('/api/food/import-area/', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_import_city_requires_a_query(self):
        response = self.client.post('/api/food/import-city/?q=', {}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_import_city_saves_places_for_a_small_town(self):
        # A village is the case the hard-coded metro list could never serve.
        payload = [{
            'osm_id': 'node/1', 'osm_type': 'node', 'name': 'Kushingarh Tea Stall',
            'category': 'cafe', 'cuisine': 'multi',
            'latitude': 27.0, 'longitude': 83.8,
            'city': '', 'state': '', 'address': 'Main Bazaar',
            'image_url': '', 'image_credit': '', 'price_level': 1,
        }]
        with patch('food.views.search_food_by_location', return_value=payload):
            response = self.client.post('/api/food/import-city/?q=Kushinagar', {}, format='json')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['saved'], 1)
        # The queried name fills in the city, since OSM rarely carries addr:city.
        self.assertEqual(FoodPlace.objects.get().city, 'Kushinagar')

    def test_import_does_not_overwrite_ratings(self):
        # Overpass carries no ratings; a hardcoded 0.0 wiped real ones on re-sync.
        place = make_place(osm_id='node/9', rating=4.7, review_count=210)
        payload = [{
            'osm_id': 'node/9', 'osm_type': 'node', 'name': place.name,
            'category': 'dhaba', 'cuisine': 'north_indian',
            'latitude': 26.9, 'longitude': 80.9,
        }]
        with patch('food.views.fetch_food_near', return_value=payload):
            self.client.post(
                '/api/food/import-area/', {'lat': 26.9, 'lon': 80.9, 'radius': 5}, format='json'
            )

        place.refresh_from_db()
        self.assertEqual(place.rating, 4.7)
        self.assertEqual(place.review_count, 210)


class CategoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_categories_include_all_with_counts(self):
        make_place(name='A', category='cafe')
        make_place(name='B', category='cafe')
        data = self.client.get('/api/food/categories/').data
        by_key = {row['key']: row for row in data}
        self.assertEqual(by_key['all']['count'], 2)
        self.assertEqual(by_key['cafe']['count'], 2)
        # 'all' is a filter value, never a stored category.
        self.assertNotIn('all', FoodPlace.objects.values_list('category', flat=True))

    def test_cuisines_list(self):
        response = self.client.get('/api/food/cuisines/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(row['key'] == 'multi' for row in response.data))

    def test_nearby_requires_coordinates(self):
        self.assertEqual(self.client.get('/api/food/nearby/').status_code, 400)

    def test_nearby_reports_sparse(self):
        make_place(name='Only One')
        response = self.client.get('/api/food/nearby/?lat=26.9&lon=80.9')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['sparse'])