import os
from supabase import create_client, Client
from postgrest.exceptions import APIError

class SupabaseService:
    def __init__(self, user_id: str):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env")

        self.supabase: Client = create_client(self.url, self.key)
        self.user_id = user_id

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def get_client() -> Client:
        """Single source of truth for creating a Supabase client."""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # ← fixed, was SUPABASE_KEY
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env")
        return create_client(url, key)

    @staticmethod
    def verify_token(token: str):
        """Verifies a Supabase JWT. Returns the user object or None."""
        try:
            auth_response = SupabaseService.get_client().auth.get_user(token)
            return auth_response.user
        except Exception as e:
            print(f"Token verification failed: {e}")
            return None

    @staticmethod
    def sign_up(email: str, password: str):
        """Creates a new Supabase auth user."""
        return SupabaseService.get_client().auth.sign_up({"email": email, "password": password})

    @staticmethod
    def sign_in(email: str, password: str):
        """Signs in an existing user. Returns session with access_token."""
        return SupabaseService.get_client().auth.sign_in_with_password({"email": email, "password": password})

    # ── Instance methods ──────────────────────────────────────────────────────

    def get_full_profile(self):
        """Fetches all data linked to the user_id from the relational schema."""
        try:
            profile = self.supabase.table("profiles").select("*").eq("id", self.user_id).single().execute()
            skills  = self.supabase.table("skills").select("*").eq("user_id", self.user_id).execute()
            exp     = self.supabase.table("experience").select("*").eq("user_id", self.user_id).execute()
            projects = self.supabase.table("projects").select("*").eq("user_id", self.user_id).execute()
            education = self.supabase.table("education").select("*").eq("user_id", self.user_id).execute()
            certs   = self.supabase.table("certifications").select("*").eq("user_id", self.user_id).execute()

            return {
                "profile":        profile.data,
                "skills":         self._format_skills(skills.data),
                "experience":     exp.data,
                "projects":       projects.data,
                "education":      education.data,
                "certifications": certs.data,
            }
        except APIError as e:
            print(f"Database error: {e}")
            return None

    def _format_skills(self, skills_list):
        """Converts flat DB rows into the category-based dict the Matcher expects."""
        formatted = {}
        for item in skills_list:
            cat  = item["category"]
            name = item["skill_name"]
            formatted.setdefault(cat, []).append(name)
        return formatted