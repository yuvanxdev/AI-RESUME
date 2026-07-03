import unittest

from utils.resume_analyzer import ResumeAnalyzer


class ResumeAnalyzerGeminiTests(unittest.TestCase):
    def test_refine_gemini_output_filters_existing_suggestions_and_duplicates(self):
        analyzer = ResumeAnalyzer()
        parsed = {
            "ats_score": 72,
            "skill_gaps": ["Python", "AWS", "Communication"],
            "improvement_suggestions": [
                "Add Python experience to your resume.",
                "Highlight AWS projects in your resume.",
                "Improve your bullet points with measurable results.",
                "Improve your bullet points with measurable results.",
            ],
        }
        resume_text = "I have strong Python experience and AWS project work. My bullet points already include measurable results."

        refined = analyzer._refine_gemini_output(
            parsed,
            resume_text,
            existing_analysis={"ats_score": 70},
            job_description="Build cloud-native applications using AWS and Kubernetes."
        )

        self.assertEqual(refined["ats_score"], 71)
        self.assertEqual(refined["skill_gaps"], ["Communication"])
        self.assertIn("Improve your bullet points with measurable results.", refined["improvement_suggestions"])
        self.assertTrue(any("AWS" in suggestion or "Kubernetes" in suggestion for suggestion in refined["improvement_suggestions"]))

    def test_rule_based_analysis_adds_role_specific_suggestions(self):
        analyzer = ResumeAnalyzer()
        resume_data = {
            "raw_text": "Experienced software engineer with Python and SQL experience.\n\nSkills\nPython\nSQL\n"
        }
        job_requirements = {
            "required_skills": ["Python", "AWS", "Docker"],
            "require_gpa": False,
        }

        result = analyzer.analyze_resume(resume_data, job_requirements)

        self.assertGreater(result["keyword_match"]["score"], 0)
        self.assertIn("AWS", result["keyword_match"]["missing_skills"])
        self.assertTrue(any("AWS" in suggestion for suggestion in result["suggestions"]))

    def test_calculate_keyword_match_supports_modern_stack_aliases(self):
        analyzer = ResumeAnalyzer()
        resume_text = "Deployed workloads with k8s and tf in AWS."
        required_skills = ["Kubernetes", "Terraform", "AWS"]

        result = analyzer.calculate_keyword_match(resume_text, required_skills)

        self.assertIn("Kubernetes", result["found_skills"])
        self.assertIn("Terraform", result["found_skills"])
        self.assertIn("AWS", result["found_skills"])

    def test_rule_based_suggestions_use_role_context(self):
        analyzer = ResumeAnalyzer()
        resume_data = {
            "raw_text": "Experience\nSoftware Engineer\nBuilt backend services and led deployments for internal tools.\nSkills\nPython, SQL, AWS, Docker"
        }
        job_requirements = {
            "required_skills": ["AWS", "Kubernetes", "Docker"],
            "description": "Build and scale cloud-native applications using AWS, Kubernetes, and Docker.",
            "require_gpa": False,
        }

        result = analyzer.analyze_resume(resume_data, job_requirements)

        self.assertTrue(any("Highlight" in suggestion and "Kubernetes" in suggestion for suggestion in result["suggestions"]))
        self.assertTrue(any("cloud" in suggestion.lower() or "Kubernetes" in suggestion for suggestion in result["suggestions"]))

    def test_gemini_refinement_turns_generic_suggestions_into_role_specific_tips(self):
        analyzer = ResumeAnalyzer()
        parsed = {
            "ats_score": 74,
            "skill_gaps": ["AWS", "Kubernetes"],
            "improvement_suggestions": ["Improve your resume", "Make it more relevant"]
        }

        refined = analyzer._refine_gemini_output(
            parsed,
            "I built Python applications and worked with SQL.",
            existing_analysis={"keyword_match": {"missing_skills": ["AWS", "Kubernetes"]}},
            job_description="Build cloud-native applications using AWS and Kubernetes."
        )

        self.assertTrue(any("AWS" in suggestion or "Kubernetes" in suggestion for suggestion in refined["improvement_suggestions"]))
        self.assertTrue(any("skills" in suggestion.lower() or "projects" in suggestion.lower() for suggestion in refined["improvement_suggestions"]))


if __name__ == "__main__":
    unittest.main()
