from unittest.mock import patch

from django.test import TestCase

from food.services.osm_food_service import (
    _parse_element,
    _pick_settlement_centres,
    geocode_place,
    radius_for_place,
)


class ParseElementTests(TestCase):
    """
    OSM element parsing.

    Coordinates and categories are where the bad data actually is: a `0.0`
    coordinate is falsy, and any string not in the choice list is an invalid
    category that Django then refuses to save.
    """

    def node(self, **tags):
        return {'type': 'node', 'id': 1, 'lat': 26.9, 'lon': 80.9, 'tags': tags}

    def test_accepts_zero_coordinates(self):
        # `if not lat or not lon` treated the equator and prime meridian as
        # missing, which is how a whole place vanished.
        parsed = _parse_element({
            'type': 'node', 'id': 1, 'lat': 0.0, 'lon': 0.0,
            'tags': {'name': 'Null Island Cafe', 'amenity': 'cafe'},
        })
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed['latitude'], 0.0)
        self.assertEqual(parsed['longitude'], 0.0)

    def test_rejects_element_without_coordinates(self):
        self.assertIsNone(_parse_element({
            'type': 'node', 'id': 1,
            'tags': {'name': 'Nowhere Cafe', 'amenity': 'cafe'},
        }))

    def test_unknown_cuisine_falls_back_to_multi(self):
        # `fast_food` is a category, not a cuisine, so it was written into the
        # cuisine column and failed validation on save.
        parsed = _parse_element(self.node(name='X', amenity='fast_food', cuisine='fast_food'))
        self.assertEqual(parsed['category'], 'fast_food')
        self.assertEqual(parsed['cuisine'], 'multi')

    def test_arbitrary_cuisine_is_normalised(self):
        parsed = _parse_element(self.node(name='X', amenity='restaurant', cuisine='Tibetan Food!'))
        self.assertTrue(parsed['cuisine'].replace('_', '').isalpha())

    def test_maps_amenities_to_categories(self):
        cases = {
            'cafe': 'cafe', 'restaurant': 'restaurant', 'fast_food': 'fast_food',
            'ice_cream': 'juice_bar', 'confectionery': 'sweet_shop', 'bbq': 'dhaba',
        }
        for amenity, expected in cases.items():
            parsed = _parse_element(self.node(name='X', amenity=amenity))
            self.assertEqual(parsed['category'], expected, amenity)

    def test_maps_shops_to_categories(self):
        self.assertEqual(
            _parse_element(self.node(name='X', shop='bakery'))['category'], 'bakery'
        )
        self.assertEqual(
            _parse_element(self.node(name='X', shop='coffee'))['category'], 'cafe'
        )

    def test_ignores_nodes_that_are_not_food(self):
        self.assertIsNone(_parse_element(self.node(name='Post Office', amenity='post_office')))

    def test_ignores_a_node_with_no_useful_tags(self):
        self.assertIsNone(_parse_element({'type': 'node', 'id': 1, 'lat': 26.9, 'lon': 80.9, 'tags': {'name': 'Nothing'}}))

    def test_extracts_the_osm_image_tag_family(self):
        # Cafes use image, image:url or image:2, and only the first was read.
        for key in ('image', 'image:url', 'image:2', 'image:1'):
            parsed = _parse_element(self.node(name='X', amenity='cafe', **{key: 'https://e.org/p.jpg'}))
            self.assertEqual(parsed['image_url'], 'https://e.org/p.jpg', key)

    def test_keeps_the_photographer_attribution(self):
        parsed = _parse_element(self.node(
            name='X', amenity='cafe',
            image='https://e.org/p.jpg',
            artist='Jane Doe',
            license='CC BY-SA 4.0',
        ))
        self.assertTrue(parsed['image_credit'])

    def test_records_osm_identity(self):
        # Dedupe keyed on the name collapsed every branch of a chain into one
        # row, so one Domino's came back for the whole city.
        parsed = _parse_element(self.node(name='Dominos Pizza', amenity='restaurant'))
        self.assertEqual(parsed['osm_id'], 'node/1')
        self.assertEqual(parsed['osm_type'], 'node')


class RadiusTests(TestCase):
    def test_small_places_get_a_wider_net(self):
        # Every cafe in a hamlet is within a couple of km, so the old fixed 8 km
        # was not the issue, but a wider radius is what makes a village import
        # return anything at all.
        self.assertGreater(radius_for_place('village'), radius_for_place('city'))
        self.assertGreater(radius_for_place('hamlet'), radius_for_place('city'))
        self.assertGreater(radius_for_place('town'), radius_for_place('city'))


class GeocodeTests(TestCase):
    def test_returns_none_for_blank_input(self):
        self.assertIsNone(geocode_place(''))
        self.assertIsNone(geocode_place('   '))

    def test_returns_none_when_nothing_matches(self):
        with patch('food.services.osm_food_service.requests.get') as get:
            get.return_value.json.return_value = []
            get.return_value.raise_for_status.return_value = None
            self.assertIsNone(geocode_place('Nowhereville'))

    def test_resolves_a_village_and_reports_its_type(self):
        # A village is the case a hard-coded city list could never serve.
        with patch('food.services.osm_food_service.requests.get') as get:
            get.return_value.json.return_value = [{
                'lat': '27.0', 'lon': '83.8',
                'display_name': 'Kushinagar, Kushinagar Nagar, Uttar Pradesh',
                'name': 'Kushinagar',
                'addresstype': 'village',
                'address': {'state': 'Uttar Pradesh'},
            }]
            get.return_value.raise_for_status.return_value = None
            place = geocode_place('Kushinagar')

        self.assertEqual(place['addresstype'], 'village')
        self.assertEqual(place['city'], 'Kushinagar')
        self.assertEqual(place['state'], 'Uttar Pradesh')
        self.assertEqual(place['lat'], 27.0)

    def test_survives_a_malformed_response(self):
        with patch('food.services.osm_food_service.requests.get') as get:
            get.return_value.json.return_value = [{'lat': None, 'lon': None}]
            get.return_value.raise_for_status.return_value = None
            self.assertIsNone(geocode_place('Broken'))


class SettlementCentreTests(TestCase):
    def setUp(self):
        from core.models import Settlement

        for i, (name, population) in enumerate(
            [('Metropolis', 5_000_000), ('Midtown', 400_000), ('Smalltown', 40_000), ('Village', 900)]
        ):
            # osm_id is unique, so each fixture row needs a distinct value.
            Settlement.objects.create(
                name=name, latitude=26.0 + i, longitude=80.0 + i,
                population=population, osm_id=f'node/{9000 + i}',
            )

    def test_includes_small_settlements(self):
        # The lookup used to raise KeyError on s['pk'] because .values() did not
        # include it, which fell back to the built-in metro list every time, so
        # small locations never actually got picked.
        chosen = {row['name'] for row in _pick_settlement_centres(4)}
        self.assertIn('Smalltown', chosen)
        self.assertIn('Village', chosen)

    def test_returns_seed_points_with_a_radius(self):
        rows = _pick_settlement_centres(4)
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertIn('lat', row)
            self.assertIn('lon', row)
            self.assertGreater(row['radius_km'], 0)

    def test_small_settlements_get_a_wider_radius(self):
        rows = {row['name']: row for row in _pick_settlement_centres(4)}
        self.assertGreater(rows['Village']['radius_km'], rows['Metropolis']['radius_km'])

    def test_does_not_repeat_a_settlement(self):
        names = [row['name'] for row in _pick_settlement_centres(4)]
        self.assertEqual(len(names), len(set(names)))