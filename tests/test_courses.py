import unittest

from config.courses import INTERVIEW_VIDEOS, RESUME_VIDEOS, get_category_for_role, get_courses_for_role


class CourseLookupTests(unittest.TestCase):
    def test_new_roles_have_course_recommendations(self):
        self.assertEqual(get_category_for_role("Data Engineer"), "Data Science and Analytics")
        self.assertEqual(get_category_for_role("AI Engineer"), "Data Science and Analytics")
        self.assertEqual(get_category_for_role("Cloud Engineer"), "Cloud Computing and DevOps")

        self.assertTrue(get_courses_for_role("Data Engineer"))
        self.assertTrue(get_courses_for_role("AI Engineer"))
        self.assertTrue(get_courses_for_role("Cloud Engineer"))

    def test_existing_roles_still_have_course_recommendations(self):
        self.assertEqual(get_category_for_role("Frontend Developer"), "Software Development and Engineering")
        self.assertEqual(get_category_for_role("Product Manager"), "Project Management")

        self.assertTrue(get_courses_for_role("Frontend Developer"))
        self.assertTrue(get_courses_for_role("Product Manager"))

    def test_course_recommendations_are_free_only(self):
        courses = get_courses_for_role("Frontend Developer")
        self.assertIsNotNone(courses)
        for title, url in courses:
            self.assertIn("[Free]", title)
            self.assertNotIn("udemy.com", url)
            self.assertNotIn("codecademy.com", url)
            self.assertNotIn("udacity.com", url)

    def test_video_links_are_direct_youtube_watch_links(self):
        for video_group in (RESUME_VIDEOS, INTERVIEW_VIDEOS):
            for _, videos in video_group.items():
                for _, url in videos:
                    self.assertTrue(
                        url.startswith("https://www.youtube.com/watch?v=") or url.startswith("https://youtu.be/"),
                        msg=f"Invalid video URL: {url}"
                    )
                    self.assertNotIn("results?search_query", url)


if __name__ == "__main__":
    unittest.main()
