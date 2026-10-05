from django.test import SimpleTestCase

from attractions.services.images import _NON_PHOTO, _name_tokens, _title_matches


class NameTokenTests(SimpleTestCase):
    def test_generic_words_are_dropped(self):
        self.assertEqual(_name_tokens("Park of the Garden"), [])
        self.assertEqual(_name_tokens("Taj Mahal"), ["taj", "mahal"])

    def test_short_words_are_dropped(self):
        # A name of "1" or "." carries nothing to match on, so it must not fall
        # back to matching on whatever else is in the query.
        self.assertEqual(_name_tokens("1"), [])
        self.assertEqual(_name_tokens("."), [])


class TitleMatchTests(SimpleTestCase):
    """
    Commons and Wikipedia search by keyword, so the title check is the only thing
    standing between a query and an unrelated photograph. These cases are all ones
    that actually came back during a real backfill.
    """

    def test_exact_name_matches(self):
        self.assertTrue(
            _title_matches("Starbucks in New Delhi's Connaught Place.jpg", ["starbucks"])
        )

    def test_every_identifying_word_must_be_present(self):
        # "Blue Tokai" against a shopping mall in Cape Town. The old check passed
        # this on the single word "blue".
        self.assertFalse(
            _title_matches(
                "Blue Route Mall (Southern Entrance), in Tokai, Cape Town.jpg",
                ["blue", "tokai", "delhi"],
            )
        )

    def test_one_common_word_is_not_enough(self):
        # "Cafe Coffee Day" against a stock cup of coffee.
        self.assertFalse(
            _title_matches("A small cup of coffee.JPG", ["cafe", "coffee", "day"])
        )

    def test_all_words_present_matches(self):
        self.assertTrue(
            _title_matches(
                "Blue Tokai Coffee House, Delhi.jpg", ["blue", "tokai", "delhi"]
            )
        )

    def test_no_tokens_matches_nothing(self):
        # Nothing to verify means nothing may be claimed.
        self.assertFalse(_title_matches("Anything At All.jpg", []))

    def test_punctuation_in_title_is_normalised(self):
        self.assertTrue(_title_matches("Hawa_Mahal (Jaipur), 2019.jpg", ["hawa", "mahal"]))


class NonPhotoTests(SimpleTestCase):
    def test_maps_and_logos_are_rejected(self):
        self.assertTrue(_NON_PHOTO.search("Taj Mahal locator map.png"))

    def test_film_poster_is_rejected(self):
        # The top result for a cafe called "After Hours".
        self.assertTrue(_NON_PHOTO.search("After Hours poster.jpg"))

    def test_ordinary_photograph_is_kept(self):
        self.assertFalse(_NON_PHOTO.search("Cafe interior, Barabanki.jpg"))