import json
import os
import re
import requests

class ResumeAnalyzer:
    def __init__(self):
        # Document type indicators
        self.document_types = {
            'resume': [
                'experience', 'education', 'skills', 'work', 'project', 'objective',
                'summary', 'employment', 'qualification', 'achievements'
            ],
            'marksheet': [
                'grade', 'marks', 'score', 'semester', 'cgpa', 'sgpa', 'examination',
                'result', 'academic year', 'percentage'
            ],
            'certificate': [
                'certificate', 'certification', 'awarded', 'completed', 'achievement',
                'training', 'course completion', 'qualified'
            ],
            'id_card': [
                'id card', 'identity', 'student id', 'employee id', 'valid until',
                'date of issue', 'identification'
            ]
        }
        
    def detect_document_type(self, text):
        text = text.lower()
        scores = {}
        
        # Calculate score for each document type
        for doc_type, keywords in self.document_types.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            density = matches / len(keywords)
            frequency = matches / (len(text.split()) + 1)  # Add 1 to avoid division by zero
            scores[doc_type] = (density * 0.7) + (frequency * 0.3)
        
        # Get the highest scoring document type
        best_match = max(scores.items(), key=lambda x: x[1])
        
        # Only return a document type if the score is significant
        return best_match[0] if best_match[1] > 0.15 else 'unknown'
        
    def calculate_keyword_match(self, resume_text, required_skills):
        resume_text = (resume_text or "").lower()
        found_skills = []
        missing_skills = []

        skill_aliases = {
            "kubernetes": ["kubernetes", "k8s", "kube"],
            "terraform": ["terraform", "tf"],
            "docker": ["docker", "containerization"],
            "aws": ["aws", "amazon web services"],
            "azure": ["azure", "microsoft azure"],
            "gcp": ["gcp", "google cloud platform", "google cloud"],
            "react": ["react", "reactjs"],
            "typescript": ["typescript", "ts"],
            "javascript": ["javascript", "js"],
            "python": ["python", "py"],
            "sql": ["sql", "postgresql", "mysql", "database"],
            "node.js": ["node.js", "nodejs", "node"],
            "machine learning": ["machine learning", "ml"],
            "devops": ["devops", "dev-ops"],
            "ci/cd": ["ci/cd", "continuous integration", "continuous deployment"],
            "microservices": ["microservices", "micro-services"],
            "api": ["api", "apis", "rest api", "restful api"],
            "ui/ux": ["ui/ux", "user interface", "user experience"],
            "jira": ["jira", "atlassian"],
            "git": ["git", "github", "gitlab"],
            "linux": ["linux", "ubuntu"],
            "spark": ["spark", "apache spark"],
            "pytorch": ["pytorch", "torch"],
            "tensorflow": ["tensorflow", "tf"],
            "prompt engineering": ["prompt engineering", "llm", "large language model"],
        }
        
        for skill in required_skills:
            skill_lower = skill.lower()
            if not skill_lower:
                continue

            aliases = skill_aliases.get(skill_lower, [skill_lower])
            matched = False
            for alias in aliases:
                if alias in resume_text:
                    found_skills.append(skill)
                    matched = True
                    break
                if any(alias in phrase for phrase in resume_text.split('.')):
                    found_skills.append(skill)
                    matched = True
                    break
                if any(alias in token for token in re.split(r"[^a-z0-9]+", resume_text)):
                    found_skills.append(skill)
                    matched = True
                    break

            if not matched:
                missing_skills.append(skill)
                
        match_score = (len(found_skills) / len(required_skills)) * 100 if required_skills else 0
        
        return {
            'score': match_score,
            'found_skills': found_skills,
            'missing_skills': missing_skills
        }
        
    def check_resume_sections(self, text):
        text = text.lower()
        essential_sections = {
            'contact': ['email', 'phone', 'address', 'linkedin'],
            'education': ['education', 'university', 'college', 'degree', 'academic'],
            'experience': ['experience', 'work', 'employment', 'job', 'internship'],
            'skills': ['skills', 'technologies', 'tools', 'proficiencies', 'expertise']
        }
        
        section_scores = {}
        for section, keywords in essential_sections.items():
            found = sum(1 for keyword in keywords if keyword in text)
            section_scores[section] = min(25, (found / len(keywords)) * 25)
            
        return sum(section_scores.values())
        
    def check_formatting(self, text):
        lines = text.split('\n')
        score = 100
        deductions = []
        
        # Check for minimum content
        if len(text) < 300:
            score -= 30
            deductions.append("Resume is too short")
            
        # Check for section headers
        if not any(line.isupper() for line in lines):
            score -= 20
            deductions.append("No clear section headers found")
            
        # Check for bullet points
        if not any(line.strip().startswith(('•', '-', '*', '→')) for line in lines):
            score -= 20
            deductions.append("No bullet points found for listing details")
            
        # Check for consistent spacing
        if any(len(line.strip()) == 0 and len(next_line.strip()) == 0 
               for line, next_line in zip(lines[:-1], lines[1:])):
            score -= 15
            deductions.append("Inconsistent spacing between sections")
            
        # Check for contact information format
        contact_patterns = [
            r'\b[\w\.-]+@[\w\.-]+\.\w+\b',  # email
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # phone
            r'linkedin\.com/\w+',  # LinkedIn
        ]
        if not any(re.search(pattern, text) for pattern in contact_patterns):
            score -= 15
            deductions.append("Missing or improperly formatted contact information")
            
        return max(0, score), deductions

    def _refine_gemini_output(self, parsed, resume_text, existing_analysis=None, job_description=None):
        """Filter Gemini output so suggestions are new, concise, and not duplicates of resume content."""
        resume_lower = (resume_text or "").lower()
        ats_score = parsed.get("ats_score", 0)
        skill_gaps = parsed.get("skill_gaps", []) or []
        suggestions = parsed.get("improvement_suggestions", []) or []
        job_desc_lower = (job_description or "").lower()

        if not isinstance(ats_score, int):
            try:
                ats_score = int(float(ats_score))
            except (TypeError, ValueError):
                ats_score = 0

        if existing_analysis and isinstance(existing_analysis, dict):
            existing_score = existing_analysis.get("ats_score", 0)
            if isinstance(existing_score, (int, float)):
                ats_score = int((ats_score + existing_score) / 2)

        filtered_skills = []
        seen_skills = set()
        for skill in skill_gaps:
            if not isinstance(skill, str):
                continue
            normalized = skill.strip()
            if not normalized:
                continue
            if normalized.lower() in seen_skills:
                continue
            seen_skills.add(normalized.lower())
            if normalized.lower() in resume_lower:
                continue
            filtered_skills.append(normalized)

        filtered_suggestions = []
        seen_suggestions = set()
        generic_improvement_words = {
            "improve", "strengthen", "clarify", "tailor", "customize", "quantify",
            "highlight", "emphasize", "showcase", "align", "prioritize"
        }

        def tokenize(text):
            cleaned = re.sub(r"[^a-z0-9]+", " ", (text or "").lower())
            return [token for token in cleaned.split() if token not in {"and", "the", "your", "with", "to", "for", "in", "on", "of", "a", "an", "is", "are", "be"}]

        resume_tokens = set(tokenize(resume_text))

        for suggestion in suggestions:
            if not isinstance(suggestion, str):
                continue
            normalized = suggestion.strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen_suggestions:
                continue
            seen_suggestions.add(lowered)

            tokens = set(tokenize(normalized))
            overlap = len(tokens & resume_tokens)
            starts_with_improvement = any(token in generic_improvement_words for token in tokenize(normalized))
            lowered_generic = lowered.strip().lower()
            preserves_measurable = any(term in lowered_generic for term in ["measurable", "quantify", "impact", "results", "evidence"])
            if lowered_generic in {
                "improve your resume",
                "make it more relevant",
                "improve your summary",
                "improve your bullet points"
            }:
                continue
            if lowered_generic.startswith("improve your resume") or lowered_generic.startswith("make it more") or lowered_generic.startswith("improve your summary"):
                if not preserves_measurable:
                    continue
            if overlap >= 2 and not starts_with_improvement and not preserves_measurable:
                continue
            if overlap >= 1 and any(token in {"python", "aws", "java", "sql", "react", "docker", "kubernetes", "cloud", "project", "projects", "experience", "resume"} for token in tokens) and not preserves_measurable:
                continue

            filtered_suggestions.append(normalized)

        if not filtered_suggestions:
            filtered_suggestions = [
                "Add role-specific keywords that match the job description.",
                "Quantify achievements with measurable impact and outcomes.",
                "Improve the summary to better reflect the target role."
            ]

        role_specific_suggestions = []
        if filtered_skills:
            missing_skill_text = ", ".join(filtered_skills[:3])
            role_specific_suggestions.append(f"Add role-relevant keywords such as {missing_skill_text} to your skills and project bullets.")

        if any(term in job_desc_lower for term in ["aws", "azure", "gcp", "cloud"]):
            role_specific_suggestions.append("Highlight cloud platform experience with deployment, scalability, or architecture outcomes.")
        if any(term in job_desc_lower for term in ["kubernetes", "docker", "container", "orchestration"]):
            role_specific_suggestions.append("Showcase containerization and orchestration work with concrete Kubernetes or Docker examples.")
        if any(term in job_desc_lower for term in ["llm", "prompt", "machine learning", "ai"]):
            role_specific_suggestions.append("Emphasize AI, ML, or LLM projects with measurable impact and deployment context.")
        if any(term in job_desc_lower for term in ["data", "sql", "spark", "pipeline", "warehouse"]):
            role_specific_suggestions.append("Add data pipeline, analytics, or SQL achievements with business impact.")
        if any(term in job_desc_lower for term in ["frontend", "react", "typescript", "ui", "ux"]):
            role_specific_suggestions.append("Showcase modern frontend work with React, TypeScript, or user-focused outcomes.")

        if not any("skills" in suggestion.lower() or "projects" in suggestion.lower() for suggestion in role_specific_suggestions):
            role_specific_suggestions.append("Highlight relevant skills and project experience that match the target role.")

        for suggestion in role_specific_suggestions:
            lowered = suggestion.lower()
            if lowered not in seen_suggestions:
                filtered_suggestions.append(suggestion)
                seen_suggestions.add(lowered)

        return {
            "ats_score": max(0, min(100, ats_score)),
            "skill_gaps": filtered_skills,
            "improvement_suggestions": filtered_suggestions[:5]
        }

    def analyze_with_gemini(self, resume_text, job_description, api_key=None, existing_analysis=None):
        """Send resume text and job description to Gemini and return ATS-style guidance."""
        if not resume_text or not job_description:
            raise ValueError("Resume text and job description are required for Gemini analysis")

        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY") or "AQ.Ab8RN6LwAIl-UMvZiR_DTN3XKKBtisor8Wv9CCD8PqL9hHaExA"
        if not api_key:
            raise ValueError("Gemini API key is not configured")

        prompt = f"""
You are an expert resume ATS reviewer.
Analyze the given resume against the given job description.
Return ONLY valid JSON with exactly this structure and no markdown fences:
{{
  "ats_score": 0,
  "skill_gaps": ["skill 1", "skill 2"],
  "improvement_suggestions": ["suggestion 1", "suggestion 2"]
}}

Rules:
- ats_score must be an integer from 0 to 100.
- skill_gaps must be a list of missing or weak skills.
- improvement_suggestions must be a list of short, practical resume improvement tips.
- Keep the response concise and focused on ATS relevance.

Resume Text:
{resume_text}

Job Description:
{job_description}
"""

        last_error = None
        for model_name in ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.0-flash-exp"]:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json"
                }
            }

            try:
                response = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                break
            except requests.HTTPError as exc:
                last_error = exc
                continue
            except requests.RequestException as exc:
                raise RuntimeError(f"Gemini API request failed: {exc}") from exc
        else:
            if last_error is not None:
                error_text = str(last_error)
                if "404" in error_text:
                    raise RuntimeError("The Gemini model endpoint was not found. Please use a valid Gemini API key and model access.")
                if "429" in error_text or "quota" in error_text.lower():
                    raise RuntimeError("Gemini quota is exhausted or the API is temporarily rate-limited.")
                raise RuntimeError(f"Gemini API request failed: {error_text}") from last_error
            raise RuntimeError("Gemini API request failed without a response")

        raw_text = ""
        try:
            raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        except Exception:
            raw_text = ""

        if not raw_text:
            raise ValueError("Gemini returned an empty response")

        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        # Try direct JSON parse first
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to recover JSON from text if Gemini wrapped it in prose
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError(f"Gemini response could not be parsed as JSON: {cleaned[:300]}")
            parsed = json.loads(cleaned[start:end + 1])

        if not isinstance(parsed, dict):
            raise ValueError("Gemini response was not a JSON object")

        return self._refine_gemini_output(parsed, resume_text, existing_analysis=existing_analysis, job_description=job_description)
        
    def extract_text_from_pdf(self, file):
        try:
            import PyPDF2
            import io
            
            # Create a PDF reader object
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
            
            # Extract text from all pages
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
                
            return text
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")
            
    def extract_text_from_docx(self, docx_file):
        """Extract text from a DOCX file"""
        try:
            from docx import Document
            doc = Document(docx_file)
            full_text = []
            for paragraph in doc.paragraphs:
                full_text.append(paragraph.text)
            return '\n'.join(full_text)
        except Exception as e:
            raise Exception(f"Error extracting text from DOCX file: {str(e)}")

    def extract_personal_info(self, text):
        """Extract personal information from resume text"""
        # Basic patterns for personal info
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        phone_pattern = r'(\+\d{1,3}[-.]?)?\s*\(?\d{3}\)?[-.]?\s*\d{3}[-.]?\s*\d{4}'
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        github_pattern = r'github\.com/[\w-]+'
        
        # Extract information
        email = re.search(email_pattern, text)
        phone = re.search(phone_pattern, text)
        linkedin = re.search(linkedin_pattern, text)
        github = re.search(github_pattern, text)
        
        # Get the first line as name (basic assumption)
        name = text.split('\n')[0].strip()
        
        return {
            'name': name if len(name) > 0 else 'Unknown',
            'email': email.group(0) if email else '',
            'phone': phone.group(0) if phone else '',
            'linkedin': linkedin.group(0) if linkedin else '',
            'github': github.group(0) if github else '',
            'portfolio': ''  # Can be enhanced later
        }

    def extract_education(self, text):
        """Extract education information from resume text"""
        education = []
        lines = text.split('\n')
        education_keywords = [
            'education', 'academic', 'qualification', 'degree', 'university', 'college',
            'school', 'institute', 'certification', 'diploma', 'bachelor', 'master',
            'phd', 'b.tech', 'm.tech', 'b.e', 'm.e', 'b.sc', 'm.sc','bca', 'mca', 'b.com',
            'm.com', 'b.cs-it', 'imca', 'bba', 'mba', 'honors', 'scholarship'
        ]
        in_education_section = False
        current_entry = []

        for line in lines:
            line = line.strip()
            # Check for section header
            if any(keyword.lower() in line.lower() for keyword in education_keywords):
                if not any(keyword.lower() == line.lower() for keyword in education_keywords):
                    # This line contains education info, not just a header
                    current_entry.append(line)
                in_education_section = True
                continue
            
            if in_education_section:
                # Check if we've hit another section
                if line and any(keyword.lower() in line.lower() for keyword in self.document_types['resume']):
                    if not any(edu_key.lower() in line.lower() for edu_key in education_keywords):
                        in_education_section = False
                        if current_entry:
                            education.append(' '.join(current_entry))
                            current_entry = []
                        continue
                
                if line:
                    current_entry.append(line)
                elif current_entry:  # Empty line and we have content
                    education.append(' '.join(current_entry))
                    current_entry = []
        
        if current_entry:
            education.append(' '.join(current_entry))
        
        return education

    def extract_experience(self, text):
        """Extract work experience information from resume text"""
        experience = []
        lines = text.split('\n')
        experience_keywords = [
            'experience', 'employment', 'work history', 'professional experience',
            'work experience', 'career history', 'professional background',
            'employment history', 'job history', 'positions held', 'experience',
            'job title', 'job responsibilities', 'job description', 'job summary'
        ]
        in_experience_section = False
        current_entry = []

        for line in lines:
            line = line.strip()
            # Check for section header
            if any(keyword.lower() in line.lower() for keyword in experience_keywords):
                if not any(keyword.lower() == line.lower() for keyword in experience_keywords):
                    # This line contains experience info, not just a header
                    current_entry.append(line)
                in_experience_section = True
                continue
            
            if in_experience_section:
                # Check if we've hit another section
                if line and any(keyword.lower() in line.lower() for keyword in self.document_types['resume']):
                    if not any(exp_key.lower() in line.lower() for exp_key in experience_keywords):
                        in_experience_section = False
                        if current_entry:
                            experience.append(' '.join(current_entry))
                            current_entry = []
                        continue
                
                if line:
                    current_entry.append(line)
                elif current_entry:  # Empty line and we have content
                    experience.append(' '.join(current_entry))
                    current_entry = []
        
        if current_entry:
            experience.append(' '.join(current_entry))
        
        return experience

    def extract_projects(self, text):
        """Extract project information from resume text"""
        projects = []
        lines = text.split('\n')
        project_keywords = [
            'projects', 'personal projects', 'academic projects', 'key projects',
            'major projects', 'professional projects', 'project experience',
            'relevant projects', 'featured projects','latest projects',
            'top projects'
        ]
        in_project_section = False
        current_entry = []

        for line in lines:
            line = line.strip()
            # Check for section header
            if any(keyword.lower() in line.lower() for keyword in project_keywords):
                if not any(keyword.lower() == line.lower() for keyword in project_keywords):
                    # This line contains project info, not just a header
                    current_entry.append(line)
                in_project_section = True
                continue
            
            if in_project_section:
                # Check if we've hit another section
                if line and any(keyword.lower() in line.lower() for keyword in self.document_types['resume']):
                    if not any(proj_key.lower() in line.lower() for proj_key in project_keywords):
                        in_project_section = False
                        if current_entry:
                            projects.append(' '.join(current_entry))
                            current_entry = []
                        continue
                
                if line:
                    current_entry.append(line)
                elif current_entry:  # Empty line and we have content
                    projects.append(' '.join(current_entry))
                    current_entry = []
        
        if current_entry:
            projects.append(' '.join(current_entry))
        
        return projects

    def extract_skills(self, text):
        """Extract skills from resume text"""
        skills = set()  # Use set to avoid duplicates
        lines = text.split('\n')
        skills_keywords = [
            'skills', 'technical skills', 'competencies', 'expertise',
            'core competencies', 'professional skills', 'key skills',
            'technical expertise', 'proficiencies', 'qualifications',
            'top skills', 'key skill', 'major skill', 'personal skill',
            'soft skills', 'soft skill', 'soft skillset'
        ]
        in_skills_section = False
        current_entry = []

        # Common skill separators
        separators = [',', '•', '|', '/', '\\', '·', '>', '-', '–', '―']

        for line in lines:
            line = line.strip()
            # Check for section header
            if any(keyword.lower() in line.lower() for keyword in skills_keywords):
                if not any(keyword.lower() == line.lower() for keyword in skills_keywords):
                    # This line contains skills, not just a header
                    current_entry.append(line)
                in_skills_section = True
                continue
            
            if in_skills_section:
                # Check if we've hit another section
                if line and any(keyword.lower() in line.lower() for keyword in self.document_types['resume']):
                    if not any(skill_key.lower() in line.lower() for skill_key in skills_keywords):
                        in_skills_section = False
                        if current_entry:
                            # Process the current entry
                            text_to_process = ' '.join(current_entry)
                            # Split by common separators
                            for separator in separators:
                                if separator in text_to_process:
                                    skills.update(skill.strip() for skill in text_to_process.split(separator) if skill.strip())
                            current_entry = []
                        continue
                
                if line:
                    current_entry.append(line)
                elif current_entry:  # Empty line and we have content
                    # Process the current entry
                    text_to_process = ' '.join(current_entry)
                    # Split by common separators
                    for separator in separators:
                        if separator in text_to_process:
                            skills.update(skill.strip() for skill in text_to_process.split(separator) if skill.strip())
                    current_entry = []
        
        if current_entry:
            # Process any remaining skills
            text_to_process = ' '.join(current_entry)
            for separator in separators:
                if separator in text_to_process:
                    skills.update(skill.strip() for skill in text_to_process.split(separator) if skill.strip())
        
        return list(skills)

    def extract_summary(self, text):
        """Extract summary/objective from resume text"""
        summary = []
        lines = text.split('\n')
        summary_keywords = [
            'summary', 'professional summary', 'career summary', 'objective',
            'career objective', 'professional objective', 'about me', 'profile',
            'professional profile', 'career profile', 'overview', 'skill summary'
        ]
        in_summary_section = False
        current_entry = []

        # Try to find summary at the beginning of the resume
        start_index = 0
        while start_index < min(10, len(lines)) and not lines[start_index].strip():
            start_index += 1

        # Check first few non-empty lines for potential summary
        first_lines = []
        lines_checked = 0
        for line in lines[start_index:]:
            if line.strip():
                first_lines.append(line.strip())
                lines_checked += 1
                if lines_checked >= 5:  # Check first 5 non-empty lines
                    break

        # If first few lines look like a summary (no special formatting, no contact info)
        if first_lines and not any(keyword in first_lines[0].lower() for keyword in summary_keywords):
            potential_summary = ' '.join(first_lines)
            if len(potential_summary.split()) > 10:  # More than 10 words
                if not re.search(r'\b(?:email|phone|address|tel|mobile|linkedin)\b', potential_summary.lower()):
                    summary.append(potential_summary)

        # Look for explicitly marked summary section
        for line in lines:
            line = line.strip()
            # Check for section header
            if any(keyword.lower() in line.lower() for keyword in summary_keywords):
                if not any(keyword.lower() == line.lower() for keyword in summary_keywords):
                    # This line contains summary info, not just a header
                    current_entry.append(line)
                in_summary_section = True
                continue
            
            if in_summary_section:
                # Check if we've hit another section
                if line and any(keyword.lower() in line.lower() for keyword in self.document_types['resume']):
                    if not any(sum_key.lower() in line.lower() for sum_key in summary_keywords):
                        in_summary_section = False
                        if current_entry:
                            summary.append(' '.join(current_entry))
                            current_entry = []
                        continue
                
                if line:
                    current_entry.append(line)
                elif current_entry:  # Empty line and we have content
                    summary.append(' '.join(current_entry))
                    current_entry = []
        
        if current_entry:
            summary.append(' '.join(current_entry))
        
        return ' '.join(summary) if summary else ''

    def analyze_resume(self, resume_data, job_requirements):
        """Analyze resume and return scores and recommendations"""
        text = resume_data.get('raw_text', '')
        
        # Extract personal information
        personal_info = self.extract_personal_info(text)
        
        # First detect document type
        doc_type = self.detect_document_type(text)
        if doc_type != 'resume':
            return {
                'ats_score': 0,
                'document_type': doc_type,
                'keyword_match': {'score': 0, 'found_skills': [], 'missing_skills': []},
                'section_score': 0,
                'format_score': 0,
                'suggestions': [f"This appears to be a {doc_type} document. Please upload a resume for ATS analysis."]
            }
            
        # Calculate keyword match
        required_skills = job_requirements.get('required_skills', [])
        keyword_match = self.calculate_keyword_match(text, required_skills)
        
        # Extract all resume sections
        education = self.extract_education(text)
        experience = self.extract_experience(text)
        projects = self.extract_projects(text)
        skills = list(self.extract_skills(text))  # Convert skills set to list
        summary = self.extract_summary(text)
        
        # Check resume sections
        section_score = self.check_resume_sections(text)
        if keyword_match['score'] >= 70:
            section_score = min(100, int(section_score + 10))
        elif keyword_match['score'] >= 40:
            section_score = min(100, int(section_score + 5))
        
        # Check formatting
        format_score, format_deductions = self.check_formatting(text)
        
        # Generate section-specific suggestions
        contact_suggestions = []
        if not personal_info.get('email'):
            contact_suggestions.append("Add your email address")
        if not personal_info.get('phone'):
            contact_suggestions.append("Add your phone number")
        if not personal_info.get('linkedin'):
            contact_suggestions.append("Add your LinkedIn profile URL")
        
        summary_suggestions = []
        if not summary:
            summary_suggestions.append("Add a professional summary to highlight your key qualifications")
        elif len(summary.split()) < 30:
            summary_suggestions.append("Expand your professional summary to better highlight your experience and goals")
        elif len(summary.split()) > 100:
            summary_suggestions.append("Consider making your summary more concise (aim for 50-75 words)")
        
        skills_suggestions = []
        if not skills:
            skills_suggestions.append("Add a dedicated skills section")
        if isinstance(skills, (list, set)) and len(list(skills)) < 5:
            skills_suggestions.append("List more relevant technical and soft skills")
        if keyword_match['score'] < 70:
            skills_suggestions.append("Add more skills that match the job requirements")

        role_context = (job_requirements or {}).get('description', '')
        role_context_lower = role_context.lower()
        if any(term in role_context_lower for term in ['software', 'developer', 'engineer', 'engineering']):
            skills_suggestions.append("Highlight modern tooling such as Git, CI/CD, containers, and cloud platforms")
        if any(term in role_context_lower for term in ['data', 'analytics', 'machine learning', 'ai']):
            skills_suggestions.append("Emphasize Python, SQL, experimentation, and model deployment experience")
        if any(term in role_context_lower for term in ['devops', 'cloud', 'site reliability', 'platform']):
            skills_suggestions.append("Showcase automation, monitoring, infrastructure-as-code, and reliability practices")
        if any(term in role_context_lower for term in ['design', 'ux', 'ui']):
            skills_suggestions.append("Include design systems, usability testing, and prototyping evidence")

        for skill in keyword_match.get('missing_skills', [])[:3]:
            skill_lower = skill.lower()
            if skill_lower in {'aws'}:
                skills_suggestions.append("Highlight AWS experience with deployment, scalability, or architecture outcomes.")
            elif skill_lower in {'kubernetes', 'docker'}:
                skills_suggestions.append(f"Highlight {skill} experience with orchestration, deployment, or reliability outcomes.")
            elif skill_lower in {'python', 'sql', 'react', 'typescript'}:
                skills_suggestions.append(f"Highlight {skill} experience with concrete project examples and measurable results.")
            else:
                skills_suggestions.append(f"Add {skill} to your resume to align better with the target role")

        if any(term in role_context_lower for term in ['aws', 'cloud', 'kubernetes', 'docker']):
            if not any('aws' in suggestion.lower() for suggestion in skills_suggestions):
                skills_suggestions.append("Highlight AWS or cloud-native work with deployment, scalability, and architecture outcomes.")
        
        experience_suggestions = []
        if not experience:
            experience_suggestions.append("Add your work experience section")
        else:
            has_dates = any(re.search(r'\b(19|20)\d{2}\b', exp) for exp in experience)
            has_bullets = any(re.search(r'[•\-\*]', exp) for exp in experience)
            has_action_verbs = any(re.search(r'\b(developed|managed|created|implemented|designed|led|improved|built|optimized|automated|delivered)\b', 
                                           exp.lower()) for exp in experience)
            has_metrics = any(re.search(r'\b\d+(%|x|k|m|\+)?\b', exp) for exp in experience)
            
            if not has_dates:
                experience_suggestions.append("Include dates for each work experience")
            if not has_bullets:
                experience_suggestions.append("Use bullet points to list your achievements and responsibilities")
            if not has_action_verbs:
                experience_suggestions.append("Start bullet points with strong action verbs")
            if not has_metrics:
                experience_suggestions.append("Add measurable outcomes such as percentages, scale, or impact")

            role_context_lower = role_context.lower()
            if any(term in role_context_lower for term in ['software', 'developer', 'engineer', 'engineering', 'platform']):
                experience_suggestions.append("Highlight delivery of products, systems, or features with modern engineering practices")
            if any(term in role_context_lower for term in ['data', 'analytics', 'machine learning', 'ai']):
                experience_suggestions.append("Showcase data-driven impact, experimentation, and model or pipeline results")
            if any(term in role_context_lower for term in ['devops', 'cloud', 'site reliability']):
                experience_suggestions.append("Emphasize automation, reliability improvements, and incident or deployment outcomes")
        
        education_suggestions = []
        if not education:
            education_suggestions.append("Add your educational background")
        else:
            has_dates = any(re.search(r'\b(19|20)\d{2}\b', edu) for edu in education)
            has_degree = any(re.search(r'\b(bachelor|master|phd|b\.|m\.|diploma)\b', 
                                     edu.lower()) for edu in education)
            has_gpa = any(re.search(r'\b(gpa|cgpa|grade|percentage)\b', 
                                  edu.lower()) for edu in education)
            
            if not has_dates:
                education_suggestions.append("Include graduation dates")
            if not has_degree:
                education_suggestions.append("Specify your degree type")
            if not has_gpa and job_requirements.get('require_gpa', False):
                education_suggestions.append("Include your GPA if it's above 3.0")
        
        format_suggestions = []
        if format_score < 100:
            format_suggestions.extend(format_deductions)
        if section_score < 70:
            format_suggestions.append("Organize sections clearly so recruiters can scan your resume quickly")
        
        # Calculate section-specific scores
        contact_score = 100 - (len(contact_suggestions) * 25)  # -25 for each missing item
        summary_score = 100 - (len(summary_suggestions) * 33)  # -33 for each issue
        skills_score = keyword_match['score']
        experience_score = 100 - (len(experience_suggestions) * 25)
        education_score = 100 - (len(education_suggestions) * 25)
        
        # Calculate overall ATS score with weighted components
        ats_score = (
            int(round(contact_score * 0.1)) +      # 10% weight for contact info
            int(round(summary_score * 0.1)) +      # 10% weight for summary
            int(round(skills_score * 0.3)) +       # 30% weight for skills match
            int(round(experience_score * 0.2)) +   # 20% weight for experience
            int(round(education_score * 0.1)) +    # 10% weight for education
            int(round(format_score * 0.2))         # 20% weight for formatting
        )
        
        # Combine all suggestions into a single list
        suggestions = []
        suggestions.extend(contact_suggestions)
        suggestions.extend(summary_suggestions)
        suggestions.extend(skills_suggestions)
        suggestions.extend(experience_suggestions)
        suggestions.extend(education_suggestions)
        suggestions.extend(format_suggestions)
        
        if not suggestions:
            suggestions.append("Your resume is well-optimized for ATS systems")
        
        return {
            **personal_info,  # Include extracted personal info
            'ats_score': ats_score,
            'document_type': 'resume',
            'keyword_match': keyword_match,
            'section_score': section_score,
            'format_score': format_score,
            'education': education,
            'experience': experience,
            'projects': projects,
            'skills': skills,
            'summary': summary,
            'suggestions': suggestions,
            'contact_suggestions': contact_suggestions,
            'summary_suggestions': summary_suggestions,
            'skills_suggestions': skills_suggestions,
            'experience_suggestions': experience_suggestions,
            'education_suggestions': education_suggestions,
            'format_suggestions': format_suggestions,
            'section_scores': {
                'contact': contact_score,
                'summary': summary_score,
                'skills': skills_score,
                'experience': experience_score,
                'education': education_score,
                'format': format_score
            }
        }
