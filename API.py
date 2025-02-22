import unittest
from calibre.library  import db

class TestCalibreWeb(unittest.TestCase) :

    def setUp(self):
        """Set up the Calibre database connection."""
        library_path = r"C:\Users\dwafi\IdeaProjects\calibre-web\library"
        self.calibre_db = db(library_path).new_api

    def test_connection(self):
        """Test if the connection to the Calibre database is successful."""
        self.assertIsNotNone(self.calibre_db, "Failed to connect to Calibre database")

    def test_all_book_ids(self):
        """Test fetching all book IDs."""
        all_ids = self.calibre_db.all_book_ids()

        print("All Book IDs:", all_ids)
        self.assertEquals(all_ids, {2, 3, 4, 5, 6, 7, 8}, "all_book_ids did not return a list")



    def test_has_id(self):
        """Test checking if a book ID exists."""

        book_id = 2
        has_id = self.calibre_db.has_id(book_id)
        print(f"Book {book_id} exists:", has_id)
        self.assertTrue(has_id, "Book ID should exist but was not found.")




    def test_get_metadata(self):
        """Test fetching metadata for a specific book."""

        book_id = 2
        metadata = self.calibre_db.get_metadata(book_id)
        print(f"Metadata for book {book_id}:", metadata)


        book_info = {
        "Title": "Harry Potter: The Complete Collection",
        "Title sort": "Harry Potter: The Complete Collection",
        "Author(s)": "['Rowling, J.K.']",
        "Publisher": "Arthur A. Levine Books",
        "Languages": "eng",
        "Timestamp": "2024-12-23T09:08:05+00:00",
        "Published": "2015-12-13T23:00:00+00:00",
        "FBook 2 exists": True
         }





        self.assertEqual(str(metadata.title), str(book_info["Title"]), "Title mismatch")
        self.assertEqual(str(metadata.title_sort), str(book_info["Title sort"]), "Title sort mismatch")

        self.assertEqual(str(metadata.publisher), str(book_info["Publisher"]), "Publisher mismatch")





if __name__ == "__main__" :
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCalibreWeb)
    runner = unittest.TextTestRunner()
    runner.run(suite)
