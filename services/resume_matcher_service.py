import spacy
from utils.logger import logger

nlp = spacy.load("en_core_web_md")

class ResumeMatcherService:
    """
    Updated to accept user_data from the database instead of reading JSON files.
    Falls back to JSON files if no user_data is passed (backwards compatible).
    """

    def __init__(self, user_data: dict = None, skills_path="data/skills.json", experience_path="data/experience.json"):
        self.nlp = spacy.load("en_core_web_md")

        if user_data:
            # ── DB path: data comes from Supabase via SupabaseService.get_full_profile()
            self.skills_data   = user_data.get("skills", {})
            self.experience_data = self._shape_experience(user_data)
        else:
            # ── Legacy path: read from local JSON files (old CLI flow still works)
            import json
            self.skills_data     = self._load_json(skills_path)
            self.experience_data = self._load_json(experience_path)

    # ── Data shapers ──────────────────────────────────────────────────────────

    def _shape_experience(self, user_data: dict) -> dict:
        """
        Converts the flat DB rows from Supabase into the same shape
        the old experience.json used, so match_experience() needs no changes.

        DB experience row:  { company, role, stack[], highlights[], ... }
        DB projects row:    { title, description, stack[], metrics[], link }

        Shaped output:
        {
          "work_experience": [ { company, role, stack, highlights, ... } ],
          "technical_projects": [ { title, description, stack, metrics } ],
          "education": [ { institution, degree, ... } ]
        }
        """
        work_exp = []
        for exp in user_data.get("experience", []):
            work_exp.append({
                "company":    exp.get("company", ""),
                "role":       exp.get("role", ""),
                "location":   exp.get("location", ""),
                "stack":      exp.get("stack") or [],
                "highlights": exp.get("highlights") or [],
                "start_date": exp.get("start_date", ""),
                "end_date":   exp.get("end_date", ""),
                "is_internship": exp.get("is_internship", False),
            })

        projects = []
        for p in user_data.get("projects", []):
            projects.append({
                "title":       p.get("title", ""),
                "description": p.get("description", ""),
                "stack":       p.get("stack") or [],
                "metrics":     p.get("metrics") or [],
                "link":        p.get("link", ""),
            })

        education = []
        for e in user_data.get("education", []):
            education.append({
                "institution":     e.get("institution", ""),
                "degree":          e.get("degree", ""),
                "field_of_study":  e.get("field_of_study", ""),
                "graduation_year": e.get("graduation_year", ""),
                "status":          e.get("status", ""),
            })

        return {
            "work_experience":    work_exp,
            "technical_projects": projects,
            "education":          education,
        }

    def _load_json(self, path):
        import json
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: File not found at {path}")
            return {}

    # ── NLP methods (unchanged) ───────────────────────────────────────────────

    def extract_keywords_from_jd(self, jd_text: str) -> set:
        doc = self.nlp(jd_text.lower())
        return {token.lemma_ for token in doc if token.pos_ in ["NOUN", "PROPN"]}

    def match_skills(self, jd_text: str) -> dict:
        jd_keywords = self.extract_keywords_from_jd(jd_text)
        logger.info(f"JD Keywords: {jd_keywords}")
        matched = {}
        for category, skill_list in self.skills_data.items():
            # skills_data is already a dict: { "Backend": ["Python", ...], ... }
            matches = [s for s in skill_list if s.lower() in jd_keywords]
            if matches:
                matched[category] = matches
        
        logger.info(f"Matched: {matched}")
        return matched

    def match_experience(self, matched_skills: dict) -> list:
        relevant = []
        all_matches = [s.lower() for sublist in matched_skills.values() for s in sublist]

        for project in self.experience_data.get("technical_projects", []):
            stack = [s.lower() for s in project.get("stack", [])]
            if any(skill in stack for skill in all_matches):
                relevant.append(project)

        return relevant