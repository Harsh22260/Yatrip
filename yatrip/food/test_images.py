from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch

from food.models import FoodPlace
from food.services import images as food_images


def make_place(**overrides):
    defaults = {
        'name': 'Blue Palm Cafe',
        'category': 'cafe',
        'cuisine': 'multi',
        'latitude': 26.9,
        'longitude': 80.9,
        'city': 'Lucknow',
    }
    defaults.update(overrides)
    return FoodPlace.objects.create(**defaults)


class FindPhotoTests(TestCase):
    """
    Photos for cafes.

    Cafes are the category that looked worst: they almost never carry an OSM
    ``image`` tag, so nearly every card fell back to plain artwork. This is the
    name-based lookup that fills the gap where Wikimedia actually has a photo.
    """

    def test_strips_generic_words_from_the_query(self):
        # "Cafe Coffee Day" must not match anything merely coffee-shaped.
        self.assertEqual(food_images._tokens('Cafe Coffee Day'), ['day'])

    def test_returns_none_when_name_is_only_generic_words(self):
        self.assertIsNone(food_images.find_food_photo('The Cafe'))
        self.assertIsNone(food_images.find_food_photo(''))

    def test_uses_city_to_disambiguate_then_falls_back(self):
        found_photo = {'url': 'https://x/a.jpg', 'credit': 'CC BY'}
        with patch.object(food_images, 'search_photo', return_value=None) as search, \
             patch.object(food_images, '_wikipedia_photo') as wiki:
            # Nothing for "Blue Palm Cafe Lucknow"; found on the bare name.
            wiki.side_effect = [None, found_photo]
            found = food_images.find_food_photo('Blue Palm Cafe', city='Lucknow')

        self.assertEqual(found, found_photo)
        self.assertEqual(search.call_count, 2)
        self.assertEqual(wiki.call_count, 2)
        self.assertEqual(search.call_args_list[0].args[0], 'Blue Palm Cafe Lucknow')

    def test_discards_over_long_urls(self):
        with patch.object(food_images, 'search_photo', return_value={
            'url': 'https://commons.example/' + 'a' * 400 + '.jpg',
            'credit': 'CC BY',
        }):
            # A truncated URL would 404 in the browser, so it is dropped whole and
            # the row keeps its empty image for the artwork fallback.
            self.assertIsNone(food_images.find_food_photo('Blue Palm Cafe'))


class BackfillTests(TestCase):
    def setUp(self):
        self.with_photo = make_place(name='Blue Palm Cafe')
        self.without_photo = make_place(name='Corner Chai Stall', city='Barabanki')
        self.found = {'url': 'https://commons.example/p.jpg', 'credit': 'Someone / CC BY-SA 4.0'}

    def test_fills_missing_images_and_stores_the_credit(self):
        with patch.object(food_images, 'find_food_photo', return_value=self.found):
            stats = food_images.backfill(FoodPlace.objects.all(), delay=0)

        self.assertEqual(stats['filled'], 2)
        self.assertEqual(stats['no_match'], 0)
        self.with_photo.refresh_from_db()
        self.assertEqual(self.with_photo.image_url, 'https://commons.example/p.jpg')
        # Wikimedia photographs carry attribution requirements.
        self.assertEqual(self.with_photo.image_credit, 'Someone / CC BY-SA 4.0')

    def test_counts_no_match_without_writing(self):
        with patch.object(food_images, 'find_food_photo', return_value=None):
            stats = food_images.backfill(FoodPlace.objects.all(), delay=0)

        self.assertEqual(stats['no_match'], 2)
        self.with_photo.refresh_from_db()
        # Left empty on purpose: the frontend renders generated artwork.
        self.assertEqual(self.with_photo.image_url, '')

    def test_only_missing_leaves_existing_images_alone(self):
        self.with_photo.image_url = 'https://example.org/existing.jpg'
        self.with_photo.save(update_fields=['image_url'])

        with patch.object(food_images, 'find_food_photo', return_value=self.found) as finder:
            stats = food_images.backfill(FoodPlace.objects.all(), delay=0)

        self.assertEqual(stats['filled'], 1)
        self.with_photo.refresh_from_db()
        self.assertEqual(self.with_photo.image_url, 'https://example.org/existing.jpg')

    def test_can_target_a_category(self):
        make_place(name='Tunday Kababi', category='dhaba')
        with patch.object(food_images, 'find_food_photo', return_value=self.found):
            stats = food_images.backfill(
                FoodPlace.objects.all(), categories=('cafe',), delay=0
            )
        self.assertEqual(stats['filled'], 2)
        self.assertFalse(
            FoodPlace.objects.get(name='Tunday Kababi').image_url
        )

    def test_limit_caps_the_rows_processed(self):
        with patch.object(food_images, 'find_food_photo', return_value=self.found) as finder:
            stats = food_images.backfill(FoodPlace.objects.all(), limit=1, delay=0)
        self.assertEqual(stats['filled'], 1)
        self.assertEqual(finder.call_count, 1)


class BackfillCommandTests(TestCase):
    def setUp(self):
        make_place(name='Blue Palm Cafe', category='cafe')
        make_place(name='Tunday Kababi', category='dhaba')

    def test_defaults_to_cafes_only(self):
        with patch('food.services.images.backfill') as backfill, \
             patch.object(food_images, 'find_food_photo'):
            backfill.return_value = {'filled': 1, 'no_match': 0, 'failed': 0}
            call_command('backfill_food_images')

        queryset = backfill.call_args.args[0]
        self.assertEqual([p.name for p in queryset], ['Blue Palm Cafe'])

    def test_all_flag_covers_every_category(self):
        with patch('food.services.images.backfill') as backfill:
            backfill.return_value = {'filled': 2, 'no_match': 0, 'failed': 0}
            call_command('backfill_food_images', '--all')

        self.assertEqual(len(list(backfill.call_args.args[0])), 2)

    def test_place_flag_narrows_to_one_row(self):
        with patch('food.services.images.backfill') as backfill:
            backfill.return_value = {'filled': 1, 'no_match': 0, 'failed': 0}
            call_command('backfill_food_images', '--place', 'Tunday')

        self.assertEqual(
            [p.name for p in backfill.call_args.args[0]], ['Tunday Kababi']
        )